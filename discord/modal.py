"""
The MIT License (MIT)

Copyright (c) 2021-present Dolfies

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

import yarl

from .components import _component_factory
from .enums import IFrameModalSize, InteractionType, try_enum
from .interactions import _wrapped_interaction
from .mixins import Hashable
from .utils import _generate_nonce

if TYPE_CHECKING:
    from .application import IntegrationApplication
    from .abc import MessageableChannel
    from .components import Component
    from .file import _FileBase
    from .interactions import Interaction
    from .state import ConnectionState
    from .types.gateway import InteractionIframeModalCreateEvent
    from .types.interactions import Modal as ModalPayload, ModalSubmitInteractionData
    from .types.message import PartialAttachment as PartialAttachmentPayload

# fmt: off
__all__ = (
    'Modal',
    'IFrameModal',
)
# fmt: on


class Modal(Hashable):
    """Represents a modal from the Discord Bot UI Kit.

    .. versionadded:: 2.0

    .. container:: operations

        .. describe:: x == y

            Checks if two modals are equal.

        .. describe:: x != y

            Checks if two modals are not equal.

        .. describe:: hash(x)

            Return the modal's hash.

        .. describe:: str(x)

            Returns the modal's title.

    Attributes
    -----------
    id: :class:`int`
        The interaction ID.
    nonce: Optional[Union[:class:`int`, :class:`str`]]
        The modal's nonce. May not be present.
    title: :class:`str`
        The modal's title.
    custom_id: :class:`str`
        The ID of the modal that gets received during an interaction.
    components: List[:class:`Component`]
        A list of components in the modal.
    application: :class:`IntegrationApplication`
        The application that sent the modal.
    """

    __slots__ = ('_state', 'interaction', 'id', 'nonce', 'title', 'custom_id', 'components', 'application')

    def __init__(self, *, data: ModalPayload, interaction: Interaction):
        self._state = interaction._state
        self.interaction = interaction
        self.id = int(data['id'])
        self.nonce: Optional[Union[int, str]] = data.get('nonce')
        self.title: str = data.get('title', '')
        self.custom_id: str = data.get('custom_id', '')
        self.components: List[Component] = []
        for component_data in data.get('components', []):
            component = _component_factory(component_data)
            if component is not None:
                self.components.append(component)
        self.application: IntegrationApplication = interaction._state.create_integration_application(data['application'])

    def __str__(self) -> str:
        return self.title

    def to_dict(self, files: Optional[List[_FileBase]] = None) -> ModalSubmitInteractionData:
        submit_files: List[_FileBase] = [] if files is None else files
        attachments: List[PartialAttachmentPayload] = []
        payload: ModalSubmitInteractionData = {
            'id': str(self.id),
            'custom_id': self.custom_id,
            'components': [c.to_submit_dict(submit_files, attachments) for c in self.components],  # type: ignore
        }
        if attachments:
            payload['attachments'] = attachments
        return payload

    async def submit(self) -> None:
        """|coro|

        Submits the modal.

        All required components must be already answered.

        .. versionchanged:: 2.2

            This no longer returns the created interaction.

        Raises
        -------
        NotFound
            The originating message was not found.
        HTTPException
            Submitting the modal failed.
        """
        interaction = self.interaction
        files: List[_FileBase] = []
        await _wrapped_interaction(
            self._state,
            _generate_nonce(),
            InteractionType.modal_submit,
            None,
            interaction.channel,
            self.to_dict(files),
            application_id=self.application.id,
            files=files or None,
        )


class IFrameModal(Hashable):
    """Represents an iFrame modal from an interaction.

    .. versionadded:: 2.1

    Attributes
    -----------
    id: :class:`int`
        The interaction ID.
    nonce: Optional[Union[:class:`int`, :class:`str`]]
        The modal's nonce. May not be present.
    channel: :class:`abc.Messageable`
        The channel this iFrame modal originated from.
    interaction: Optional[:class:`Interaction`]
        The interaction that created this iFrame modal, if it was cached.
    title: :class:`str`
        The modal's title.
    custom_id: :class:`str`
        The modal's custom ID.
    iframe_path: :class:`str`
        The iFrame path Discord provided for the modal.
    modal_size: :class:`IFrameModalSize`
        The modal size Discord provided.
    application: :class:`IntegrationApplication`
        The application that sent the iFrame modal.
    """

    __slots__ = (
        '_state',
        'interaction',
        'id',
        'nonce',
        'channel',
        'title',
        'custom_id',
        'iframe_path',
        'modal_size',
        'application',
        '_frame_id',
    )

    def __init__(
        self,
        *,
        data: InteractionIframeModalCreateEvent,
        state: ConnectionState,
        channel: MessageableChannel,
        interaction: Optional[Interaction] = None,
    ) -> None:
        self._state = state
        self.interaction = interaction
        self.id = int(data['id'])
        self.nonce: Optional[Union[int, str]] = data.get('nonce')
        self.channel = channel
        self.title: str = data.get('title', '')
        self.custom_id: str = data.get('custom_id', '')
        self.iframe_path: str = data['iframe_path']
        self.modal_size: IFrameModalSize = try_enum(IFrameModalSize, data['modal_size'])
        self.application: IntegrationApplication = state.create_integration_application(data['application'])
        self._frame_id: str = str(uuid.uuid4())

    def __str__(self) -> str:
        return self.title

    def __repr__(self) -> str:
        return f'<IFrameModal id={self.id} title={self.title!r} application={self.application!r}>'

    @property
    def url(self) -> str:
        """:class:`str`: The fully formatted iFrame URL."""
        state = self._state
        params: List[Tuple[str, Union[int, str]]] = [
            ('instance_id', f'{self.channel.id}:{self.application.id}:{self.custom_id}'),
            ('custom_id', self.custom_id),
            ('channel_id', self.channel.id),
        ]

        guild_id = getattr(self.channel, 'guild_id', None)
        if guild_id is None:
            guild = getattr(self.channel, 'guild', None)
            if guild is not None:
                guild_id = guild.id
        if guild_id:
            params.append(('guild_id', guild_id))

        params.append(('frame_id', self._frame_id))
        params.append(('platform', 'mobile' if state.client.http.headers.is_mobile() else 'desktop'))
        return str(
            yarl.URL.build(scheme='https', host=f'{self.application.id}.discordsays.com')
            .with_path(self.iframe_path)
            .with_query(params)
        )
