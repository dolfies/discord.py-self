# -*- coding: utf-8 -*-
"""
Discord API Wrapper
~~~~~~~~~~~~~~~~~~~

A basic wrapper for the Discord API.

:copyright: (c) 2015-present Rapptz
:license: MIT, see LICENSE for more details.

"""

__title__ = "discord"
__author__ = "Rapptz"
__license__ = "MIT"
__copyright__ = "Copyright 2015-present Rapptz"
__version__ = "1.7.7"

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

import logging
from collections import namedtuple

from . import abc, opus, utils
from .activity import *
from .appinfo import AppInfo
from .asset import Asset
from .audit_logs import AuditLogChanges, AuditLogDiff, AuditLogEntry
from .calls import CallMessage, GroupCall
from .channel import *
from .client import Client
from .colour import Color, Colour
from .embeds import Embed
from .emoji import Emoji
from .enums import *
from .errors import *
from .file import File
from .flags import *
from .guild import Guild
from .integrations import Integration, IntegrationAccount
from .invite import Invite, PartialInviteChannel, PartialInviteGuild
from .member import Member, VoiceState
from .mentions import AllowedMentions
from .message import *
from .object import Object
from .partial_emoji import PartialEmoji
from .permissions import PermissionOverwrite, Permissions
from .player import *
from .raw_models import *
from .reaction import Reaction
from .relationship import Relationship
from .role import Role, RoleTags
from .shard import AutoShardedClient, ShardInfo
from .sticker import Sticker
from .team import *
from .template import Template
from .user import ClientUser, Profile, User
from .voice_client import VoiceClient, VoiceProtocol
from .webhook import *
from .widget import Widget, WidgetChannel, WidgetMember

VersionInfo = namedtuple("VersionInfo", "major minor micro releaselevel serial")

version_info = VersionInfo(major=1, minor=7, micro=7, releaselevel="final", serial=0)

logging.getLogger(__name__).addHandler(logging.NullHandler())
