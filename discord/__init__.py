# -*- coding: utf-8 -*-

"""
Discord API Wrapper
~~~~~~~~~~~~~~~~~~~

A basic wrapper for the Discord user API.

:copyright: (c) 2015-present Rapptz
:license: MIT, see LICENSE for more details.
"""

__title__ = 'discord'
__author__ = 'Rapptz'
__license__ = 'MIT'
__copyright__ = 'Copyright 2015-present Rapptz'
__version__ = '0.0.1'

__path__ = __import__('pkgutil').extend_path(__path__, __name__)

from collections import namedtuple
import logging

from . import utils, opus, abc, auth
from .client import Client
from .appinfo import AppInfo
from .user import User, ClientUser, Profile
from .emoji import Emoji
from .partial_emoji import PartialEmoji
from .activity import *
from .channel import *
from .guild import Guild
from .flags import *
from .relationship import Relationship
from .member import Member, VoiceState
from .message import *
from .asset import Asset
from .errors import *
from .calls import CallMessage, GroupCall
from .permissions import Permissions, PermissionOverwrite
from .role import Role, RoleTags
from .file import File
from .colour import Color, Colour
from .integrations import Integration, IntegrationAccount
from .invite import Invite, PartialInviteChannel, PartialInviteGuild
from .template import Template
from .widget import Widget, WidgetMember, WidgetChannel
from .object import Object
from .reaction import Reaction
from .enums import *
from .embeds import Embed
from .mentions import AllowedMentions
from .player import *
from .recorder import *
from .webhook import *
from .voice_client import VoiceClient, VoiceProtocol
from .audit_logs import AuditLogChanges, AuditLogEntry, AuditLogDiff
from .raw_models import *
from .team import *
from .sticker import Sticker

_VersionInfo = namedtuple('VersionInfo', 'major minor micro releaselevel serial')

version_info = _VersionInfo(major=1, minor=10, micro=0, releaselevel='alpha', serial=0)

logging.getLogger(__name__).addHandler(logging.NullHandler())
