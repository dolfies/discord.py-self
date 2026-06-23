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

from typing import Any, Callable, Sequence, TYPE_CHECKING, TypeVar, cast

from .enums import StreamDeleteReason, StreamType
from .errors import ClientException
from .utils import _bytes_to_base64_data
from .voice_media import VoiceCodec, VoiceStream

if TYPE_CHECKING:
    from .channel import DMChannel, GroupChannel, StageChannel, VoiceChannel
    from .client import Client
    from .guild import Guild
    from .state import ConnectionState
    from .types import gateway as gw
    from .types.voice import TransportEncryptionModes
    from .user import User
    from .voice_client import VoiceProtocol

    StreamPayload = gw.StreamEvent | gw.StreamCreateEvent | gw.StreamDeleteEvent
else:
    StreamPayload = Any

__all__ = (
    'Stream',
    'StreamKey',
    'StreamType',
    'StreamProtocol',
)

ST = TypeVar('ST', bound='StreamProtocol')


class StreamKey:
    """Represents a Discord stream key.

    .. versionadded:: 2.2

    Attributes
    -----------
    type: :class:`StreamType`
        The type of stream. One of ``guild``, ``call``, or ``test``.
    guild_id: Optional[:class:`int`]
        The guild ID for guild streams.
    channel_id: Optional[:class:`int`]
        The channel ID the stream belongs to, if the stream key has one.
    owner_id: :class:`int`
        The user ID of the stream owner.
    """

    __slots__ = ('type', 'guild_id', 'channel_id', 'owner_id')

    def __init__(
        self,
        type: StreamType,
        *,
        guild_id: int | None = None,
        channel_id: int | None = None,
        owner_id: int,
    ) -> None:
        self.type: StreamType = type
        self.guild_id: int | None = guild_id
        self.channel_id: int | None = channel_id
        self.owner_id: int = owner_id

    @classmethod
    def from_guild(cls, *, guild_id: int, channel_id: int, owner_id: int) -> StreamKey:
        """Create a guild stream key."""

        return cls(StreamType.guild, guild_id=guild_id, channel_id=channel_id, owner_id=owner_id)

    @classmethod
    def from_call(cls, *, channel_id: int, owner_id: int) -> StreamKey:
        """Create a private call stream key."""

        return cls(StreamType.call, channel_id=channel_id, owner_id=owner_id)

    @classmethod
    def from_test(cls, *, owner_id: int) -> StreamKey:
        """Create a test stream key."""

        return cls(StreamType.test, owner_id=owner_id)

    @classmethod
    def from_value(cls, value: str) -> StreamKey:
        """Parse a stream key string."""

        parts = value.split(':')
        stream_type = parts[0] if parts else ''
        try:
            if stream_type == StreamType.guild.value and len(parts) == 4:
                return cls.from_guild(guild_id=int(parts[1]), channel_id=int(parts[2]), owner_id=int(parts[3]))
            if stream_type == StreamType.call.value and len(parts) == 3:
                return cls.from_call(channel_id=int(parts[1]), owner_id=int(parts[2]))
            if stream_type == StreamType.test.value and len(parts) == 2:
                return cls.from_test(owner_id=int(parts[1]))
        except ValueError:
            pass

        raise ValueError(f'Invalid stream key: {value!r}')

    def __str__(self) -> str:
        if self.type is StreamType.guild:
            return f'{self.type.value}:{self.guild_id}:{self.channel_id}:{self.owner_id}'
        if self.type is StreamType.call:
            return f'{self.type.value}:{self.channel_id}:{self.owner_id}'
        if self.type is StreamType.test:
            return f'{self.type.value}:{self.owner_id}'
        return f'{self.type.value}:{self.owner_id}'

    def __repr__(self) -> str:
        return (
            f'<StreamKey type={self.type!r} guild_id={self.guild_id!r} '
            f'channel_id={self.channel_id!r} owner_id={self.owner_id!r}>'
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, StreamKey):
            return (
                self.type == other.type
                and self.guild_id == other.guild_id
                and self.channel_id == other.channel_id
                and self.owner_id == other.owner_id
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.type, self.guild_id, self.channel_id, self.owner_id))


class Stream:
    """Represents a Discord Go Live stream.

    .. versionadded:: 2.2

    Attributes
    -----------
    key: :class:`discord.StreamKey`
        The stream key that uniquely identifies this stream.
    rtc_server_id: Optional[:class:`int`]
        The RTC server ID used when connecting to the stream voice server.
        May be ``None`` for failed streams.
    rtc_channel_id: Optional[:class:`int`]
        The RTC channel ID used when connecting to the stream voice server.
        May be ``None`` for failed streams.
    region: Optional[:class:`str`]
        The voice region the stream is in.
        May be ``None`` for failed streams.
    viewer_ids: List[:class:`int`]
        The user IDs currently watching the stream.
    paused: :class:`bool`
        Whether the stream is paused.
    unavailable: :class:`bool`
        Whether the stream is unavailable due to an outage.
    """

    __slots__ = (
        '_state',
        'key',
        'rtc_server_id',
        'rtc_channel_id',
        'region',
        'viewer_ids',
        'paused',
        'unavailable',
    )

    def __init__(self, *, state: ConnectionState, data: StreamPayload) -> None:
        self._state: ConnectionState = state
        self.key: StreamKey
        self.rtc_server_id: int | None = None
        self.rtc_channel_id: int | None = None
        self.region: str | None = None
        self.viewer_ids: list[int] = []
        self.paused: bool = False
        self.unavailable: bool = False
        self._update(data)

    def _update(self, data: StreamPayload) -> None:
        self.key = StreamKey.from_value(data['stream_key'])

        if 'rtc_server_id' in data:
            self.rtc_server_id = int(data['rtc_server_id'])
        if 'rtc_channel_id' in data:
            self.rtc_channel_id = int(data['rtc_channel_id'])
        if 'region' in data:
            self.region = data['region']
        if 'viewer_ids' in data:
            self.viewer_ids = [int(user_id) for user_id in data['viewer_ids']]
        if 'paused' in data:
            self.paused = data['paused']

    @property
    def type(self) -> StreamType:
        """:class:`StreamType`: The type of stream."""
        return self.key.type

    @property
    def guild_id(self) -> int | None:
        """Optional[:class:`int`]: The guild ID for guild streams."""
        return self.key.guild_id

    @property
    def channel_id(self) -> int | None:
        """Optional[:class:`int`]: The channel ID the stream belongs to, if the stream key has one."""
        return self.key.channel_id

    @property
    def owner_id(self) -> int:
        """:class:`int`: The user ID of the stream owner."""
        return self.key.owner_id

    @property
    def guild(self) -> Guild | None:
        """Optional[:class:`Guild`]: The guild this stream belongs to."""
        if self.guild_id is None:
            return None
        return self._state._get_guild(self.guild_id)

    @property
    def channel(self) -> VoiceChannel | StageChannel | DMChannel | GroupChannel | None:
        """Optional[Union[:class:`VoiceChannel`, :class:`StageChannel`, :class:`DMChannel`, :class:`GroupChannel`]]:
        The channel this stream belongs to, if cached and present in the stream key.
        """
        channel_id = self.channel_id
        if channel_id is None:
            return None

        if self.guild_id is not None:
            guild = self.guild
            if guild is None:
                return None
            return cast('VoiceChannel | StageChannel | None', guild.get_channel(channel_id))

        return cast('DMChannel | GroupChannel | None', self._state.get_channel(channel_id))

    @property
    def owner(self) -> User | None:
        """Optional[:class:`User`]: The user who owns this stream, if cached."""
        return self._state.get_user(self.owner_id)

    def is_owner(self) -> bool:
        """Whether the client user is the owner of this stream."""
        return self.owner_id == self._state.self_id

    async def watch(
        self,
        *,
        timeout: float = 30.0,
        reconnect: bool = True,
        cls: Callable[[VoiceProtocol, Stream], ST],
    ) -> ST:
        """|coro|

        Connects to the stream with the provided stream protocol.

        Parameters
        -----------
        timeout: :class:`float`
            The timeout in seconds to wait for the stream connection to complete.
        reconnect: :class:`bool`
            Whether the stream protocol should attempt reconnects.
        cls: Type[:class:`StreamProtocol`]
            A type that subclasses :class:`StreamProtocol` to connect with.

        Raises
        -------
        ~discord.ClientException
            You are not connected to the stream's voice channel, or you tried to watch your own stream.

        Returns
        --------
        :class:`StreamProtocol`
            The connected stream protocol.
        """
        if self.is_owner():
            raise ClientException('Cannot watch a stream you own')

        voice_client = self._state._get_voice_client_for_stream_key(self.key)
        if voice_client is None:
            raise ClientException('Must be connected to the stream voice channel before watching')

        async def request() -> None:
            await self._state.ws.stream_watch(str(self.key))

        return await self._state._connect_stream(
            voice_client,
            self.key,
            request,
            cls=cls,
            timeout=timeout,
            reconnect=reconnect,
        )

    async def delete(self) -> None:
        """|coro|

        Deletes this stream if owned by the client, or disconnects from it otherwise.
        """
        await self._state.ws.stream_delete(str(self.key))

    async def ping(self) -> None:
        """|coro|

        Requests a server-side health check for this stream.
        """
        await self._state.ws.stream_ping(str(self.key))

    async def create_preview(self, image: bytes | bytearray | memoryview, /) -> None:
        """|coro|

        Uploads a preview image for this stream.

        Parameters
        -----------
        image: :class:`bytes`
            A :term:`py:bytes-like object` representing the preview image.

        Raises
        -------
        ~discord.ClientException
            The stream is not owned by the client.
        """
        if not self.is_owner():
            raise ClientException('Cannot create a preview for a stream you do not own')
        await self._state.http.upload_stream_preview(str(self.key), _bytes_to_base64_data(bytes(image)))

    async def set_paused(self, paused: bool) -> None:
        """|coro|

        Pauses or resumes this stream.

        Raises
        -------
        ~discord.ClientException
            The stream is not owned by the client.
        """
        if not self.is_owner():
            raise ClientException('Cannot pause a stream you do not own')
        await self._state.ws.stream_set_paused(str(self.key), paused)

    async def pause(self) -> None:
        """|coro|

        Shorthand that pauses this stream.

        Raises
        -------
        ~discord.ClientException
            The stream is not owned by the client.
        """
        if self.paused:
            return
        await self.set_paused(True)

    async def resume(self) -> None:
        """|coro|

        Shorthand that resumes this stream.

        Raises
        -------
        ~discord.ClientException
            The stream is not owned by the client.
        """
        if not self.paused:
            return
        await self.set_paused(False)

    def __repr__(self) -> str:
        return f'<Stream key={self.key!r} region={self.region!r} paused={self.paused!r}>'


class StreamProtocol:
    """A class that represents a Discord stream protocol.

    This mirrors :class:`VoiceProtocol` for Go Live streams. The library does
    not provide a first-party Python stream client yet, but external implementations
    can register themselves to implement streaming.

    Parameters
    -----------
    voice_client: :class:`VoiceProtocol`
        The voice client connected to the stream's voice channel.
    stream: :class:`Stream`
        The stream being connected to.
    """

    supported_modes: tuple[TransportEncryptionModes, ...] = ()
    experiments: tuple[str, ...] = ()

    def __init__(self, voice_client: VoiceProtocol, stream: Stream) -> None:
        self.voice_client: VoiceProtocol = voice_client
        self.client: Client = voice_client.client
        self.stream: Stream = stream

    def supports_video(self) -> bool:
        """Checks whether the stream protocol implementation supports video.

        Defaults to ``False``. If your implementation supports video, override this method.

        .. versionadded:: 2.2
        """
        return False

    def get_experiments(self, ready_experiments: Sequence[str]) -> Sequence[str]:
        """Returns the voice experiments to select from those offered by the voice server.

        Defaults to no experiments. If your implementation wishes to enable voice
        experiments, override this method.

        .. versionadded:: 2.2

        Parameters
        ----------
        ready_experiments: List[:class:`str`]
            The experiments offered by the server. This list is non-exhaustive.
        """
        return ()

    @property
    def codecs(self) -> tuple[VoiceCodec, ...]:
        """Tuple[:class:`VoiceCodec`]: The codecs that the stream protocol supports. Defaults to Opus (required).
        For video support, you must include the video codecs here as well.

        .. versionadded:: 2.2
        """
        return (VoiceCodec.opus(),)

    @property
    def video_streams(self) -> tuple[VoiceStream, ...]:
        """Tuple[:class:`VoiceStream`]: The video streams that the stream protocol advertises on connection. Defaults to none.

        .. versionadded:: 2.2
        """
        return ()

    @property
    def stream_key(self) -> StreamKey:
        """:class:`discord.StreamKey`: The stream key being connected to."""
        return self.stream.key

    async def on_stream_create(self, stream: Stream, /) -> None:
        """Handle a stream create event for this stream client."""
        pass

    async def on_stream_available(self, stream: Stream, /) -> None:
        """Handle a stream becoming available."""
        pass

    async def on_stream_server_update(self, data: gw.StreamServerUpdateEvent, /) -> None:
        """Handle a stream server update event."""
        raise NotImplementedError

    async def on_stream_update(self, before: Stream, after: Stream, /) -> None:
        """Handle an in-place stream update event."""
        pass

    async def on_stream_unavailable(self, stream: Stream, /) -> None:
        """Handle a stream becoming temporarily unavailable."""
        pass

    async def on_stream_delete(self, stream: Stream, reason: StreamDeleteReason, /) -> None:
        """Handle a stream delete event."""
        raise NotImplementedError

    async def connect(self, *, timeout: float, reconnect: bool) -> None:
        """Connect this protocol to the stream RTC server."""
        raise NotImplementedError

    async def disconnect(self, *, force: bool) -> None:
        """Disconnect this protocol from the stream RTC server."""
        raise NotImplementedError

    def cleanup(self) -> None:
        """Clean up this stream protocol and unregister it from state."""
        self.client._connection._remove_stream_client(self.stream_key)
