"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

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

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union
from typing_extensions import NotRequired

from .application import IntegrationApplication
from .command import ApplicationCommand
from .components import Component, ComponentBase
from .member import Member
from .message import PartialAttachment
from .snowflake import Snowflake
from .user import User

InteractionType = Literal[1, 2, 3, 4, 5]
InteractionContextType = Literal[0, 1, 2]
InteractionInstallationType = Literal[0, 1]
IFrameModalSize = Literal[1, 2, 3]


class ResolvedData(TypedDict, total=False):
    users: Dict[str, User]
    members: Dict[str, Member]
    roles: Dict[str, Any]
    channels: Dict[str, Any]
    messages: Dict[str, Any]
    attachments: Dict[str, PartialAttachment]


class _BaseApplicationCommandInteractionDataOption(TypedDict):
    name: str


class _CommandGroupApplicationCommandInteractionDataOption(_BaseApplicationCommandInteractionDataOption):
    type: Literal[1, 2]
    options: List[ApplicationCommandInteractionDataOption]


class _BaseValueApplicationCommandInteractionDataOption(_BaseApplicationCommandInteractionDataOption, total=False):
    focused: bool


class _StringValueApplicationCommandInteractionDataOption(_BaseValueApplicationCommandInteractionDataOption):
    type: Literal[3]
    value: str


class _IntegerValueApplicationCommandInteractionDataOption(_BaseValueApplicationCommandInteractionDataOption):
    type: Literal[4]
    value: int


class _BooleanValueApplicationCommandInteractionDataOption(_BaseValueApplicationCommandInteractionDataOption):
    type: Literal[5]
    value: bool


class _SnowflakeValueApplicationCommandInteractionDataOption(_BaseValueApplicationCommandInteractionDataOption):
    type: Literal[6, 7, 8, 9, 11]
    value: Snowflake


class _NumberValueApplicationCommandInteractionDataOption(_BaseValueApplicationCommandInteractionDataOption):
    type: Literal[10]
    value: float


_ValueApplicationCommandInteractionDataOption = Union[
    _StringValueApplicationCommandInteractionDataOption,
    _IntegerValueApplicationCommandInteractionDataOption,
    _BooleanValueApplicationCommandInteractionDataOption,
    _SnowflakeValueApplicationCommandInteractionDataOption,
    _NumberValueApplicationCommandInteractionDataOption,
]


ApplicationCommandInteractionDataOption = Union[
    _CommandGroupApplicationCommandInteractionDataOption,
    _ValueApplicationCommandInteractionDataOption,
]


class _BaseApplicationCommandInteractionData(TypedDict):
    id: Snowflake
    name: str
    version: Snowflake
    guild_id: NotRequired[Snowflake]
    application_command: ApplicationCommand
    attachments: List[PartialAttachment]
    options: List[ApplicationCommandInteractionDataOption]


class ChatInputCommandInteractionData(_BaseApplicationCommandInteractionData, total=False):
    type: Literal[1]


class _BaseNonChatInputApplicationCommandInteractionData(_BaseApplicationCommandInteractionData):
    target_id: Snowflake


class UserCommandInteractionData(_BaseNonChatInputApplicationCommandInteractionData):
    type: Literal[2]


class MessageCommandInteractionData(_BaseNonChatInputApplicationCommandInteractionData):
    type: Literal[3]


class PrimaryEntryPointCommandInteractionData(_BaseApplicationCommandInteractionData, total=False):
    type: Literal[4]


ApplicationCommandInteractionData = Union[
    ChatInputCommandInteractionData,
    UserCommandInteractionData,
    MessageCommandInteractionData,
    PrimaryEntryPointCommandInteractionData,
]


class _BaseMessageComponentInteractionData(TypedDict):
    custom_id: str


class ButtonInteractionData(_BaseMessageComponentInteractionData):
    component_type: Literal[2]


class SelectInteractionData(_BaseMessageComponentInteractionData):
    component_type: Literal[3, 5, 6, 7, 8]
    values: List[str]
    resolved: NotRequired[ResolvedData]


MessageComponentInteractionData = Union[ButtonInteractionData, SelectInteractionData]


class TextInputInteractionData(ComponentBase):
    type: Literal[4]
    custom_id: str
    value: str


class ModalSubmitSelectInteractionData(ComponentBase):
    type: Literal[3, 5, 6, 7, 8]
    custom_id: str
    values: List[str]


class ModalSubmitFileUploadInteractionData(ComponentBase):
    type: Literal[19]
    custom_id: str
    values: List[str]


class ModalSubmitRadioGroupInteractionData(ComponentBase):
    type: Literal[21]
    custom_id: str
    value: Optional[str]


class ModalSubmitCheckboxGroupInteractionData(ComponentBase):
    type: Literal[22]
    custom_id: str
    values: List[str]


class ModalSubmitCheckboxInteractionData(ComponentBase):
    type: Literal[23]
    custom_id: str
    value: bool


ModalSubmitLabelComponentItemInteractionData = Union[
    TextInputInteractionData,
    ModalSubmitSelectInteractionData,
    ModalSubmitFileUploadInteractionData,
    ModalSubmitRadioGroupInteractionData,
    ModalSubmitCheckboxGroupInteractionData,
    ModalSubmitCheckboxInteractionData,
]


class MessageActionRowData(TypedDict):
    type: Literal[1]
    components: List[MessageComponentInteractionData]


class ModalSubmitActionRowData(ComponentBase):
    type: Literal[1]
    components: List[ModalSubmitLabelComponentItemInteractionData]


class ModalSubmitTextDisplayInteractionData(ComponentBase):
    type: Literal[10]
    content: str


class ModalSubmitLabelInteractionData(ComponentBase):
    type: Literal[18]
    component: ModalSubmitLabelComponentItemInteractionData


ModalSubmitComponentInteractionData = Union[
    ModalSubmitActionRowData,
    ModalSubmitTextDisplayInteractionData,
    ModalSubmitLabelInteractionData,
]


class ModalSubmitInteractionData(TypedDict):
    id: Snowflake
    custom_id: str
    components: List[ModalSubmitComponentInteractionData]
    resolved: NotRequired[ResolvedData]
    attachments: NotRequired[List[PartialAttachment]]


ActionRowInteractionData = Union[MessageActionRowData, ModalSubmitActionRowData]
ComponentInteractionData = Union[MessageComponentInteractionData, ModalSubmitComponentInteractionData]
InteractionData = Union[
    ApplicationCommandInteractionData,
    MessageComponentInteractionData,
    ModalSubmitInteractionData,
]


class MessageInteraction(TypedDict):
    id: Snowflake
    type: InteractionType
    name: str
    user: User
    member: NotRequired[Member]


class Modal(TypedDict):
    id: int
    nonce: NotRequired[Snowflake]
    channel_id: Snowflake
    title: str
    custom_id: str
    application: IntegrationApplication
    components: List[Component]
