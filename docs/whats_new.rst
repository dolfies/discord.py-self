.. currentmodule:: discord

.. |commands| replace:: [:ref:`ext.commands <discord_ext_commands>`]
.. |tasks| replace:: [:ref:`ext.tasks <discord_ext_tasks>`]

.. _whats_new:

Changelog
============

This page keeps a detailed human friendly rendering of what's new and changed
in specific versions.

.. _vp2p1p0:

v2.1.0
-------

Due to the enormous amount of changes in this release, some minor changes may be omitted from this changelog. Please refer to the documentation for more details on specific features.

New Features
~~~~~~~~~~~~

- Add new flags to :class:`ApplicationFlags`, :class:`PublicUserFlags`, :class:`MessageFlags`, :class:`MemberFlags`, :class:`ChannelFlags`, and more
- Support new :class:`MessageType` values, update :attr:`Message.system_content` accordingly
- Support new :class:`ConnectionType` values
- Overhaul rich presence, adding support for viewing and sending all activity fields (including many new fields)
    - New activity type: :attr:`ActivityType.hang`, supported via :class:`HangActivity`
    - New classes: :class:`ActivityParty`, :class:`ActivityAssets`, :class:`ActivitySecrets`, and :class:`ActivityTimestamps`
    - Deprecated :class:`Game` and :class:`Streaming` in favour of :class:`Activity`
    - Made :class:`Spotify` constructible and sendable via :meth:`Client.change_presence`
    - Add :meth:`Client.proxy_external_application_assets` to proxy external assets for rich presence

- Support read states
    - New low-level interface: :class:`ReadState`
    - Access all read states from :attr:`Client.read_states` and access per-channel read states via the :attr:`TextChannel.read_state` attribute
    - Add rich attributes: :attr:`TextChannel.acked_message_id`, :attr:`TextChannel.acked_message`, :attr:`TextChannel.acked_pin_timestamp`, :attr:`TextChannel.mention_count`, and :attr:`TextChannel.last_viewed_timestamp`
    - Add :meth:`abc.Messageable.unack` to unacknowledge all messages in a channel
    - Add :meth:`Client.bulk_ack` to acknowledge multiple read states at once

- Support experiments
    - Add :class:`UserExperiment` and :class:`GuildExperiment`
    - Access user experiments via :attr:`Client.experiments` and guild experiments via :attr:`Client.guild_experiments`
    - Add :func:`Client.get_experiment` helper and :meth:`Client.fetch_experiments` coroutine

- Add message search functionality
    - Search guilds with :meth:`Guild.search`
    - Search channels with :meth:`abc.Messageable.search`

- Add support for the new username system (also known as "pomelo")
    - Add :func:`User.is_pomelo` to check if a user has been migrated
    - Add :attr:`User.global_name` to get their global nickname or "display name"
    - Update :attr:`User.display_name` and :attr:`Member.display_name` to understand global nicknames
    - Update ``__str__`` for :class:`User` to drop discriminators if the user has been migrated
    - Update :meth:`Guild.get_member_named` to work with migrated users
    - Update :attr:`User.default_avatar` to work with migrated users
    - Update :meth:`ClientUser.edit` to allow migrating and changing global names
    - |commands| Update user and member converters to understand migrated users

- Add GCP uploads
    - Allows pre-uploading files to Google Cloud Storage for faster file sending
    - Supports uploading in parallel and allows reusing previously uploaded files
    - Allows sending files up to 500 MiB each (Nitro only)
    - Implemented via :class:`CloudFile` and :meth:`abc.Messageable.upload_files`
    - The :class:`CloudFile` instances can be used in place of :class:`File` instances when sending messages

- Support application command fetching V3
    - Add :meth:`abc.Messageable.application_commands` and :meth:`Guild.application_commands` to get all application commands in a guild or private channel
    - Alias and deprecate all old application command fetching methods
    - It is highly recommended that the result of this method is cached to avoid rate limits

- Support hubs
    - Add :class:`DirectoryChannel`, :class:`DirectoryEntry`, and relevant methods for fetching and creating
    - Add :attr:`Guild.hub_type`
    - Add :meth:`Client.join_hub_waitlist`, :meth:`Client.lookup_hubs`, and :meth:`Client.join_hub`

- Support friend suggestions
    - Add :class:`FriendSuggestion` and :attr:`Client.friend_suggestion_count`
    - Add :meth:`Client.friend_suggestions`
    - Add new events, :func:`on_friend_suggestion_add` and :func:`on_friend_suggestion_remove`

- Support OAuth2 authorizations
    - Add :meth:`Client.oauth2_tokens`, :meth:`Client.fetch_authorization`, :meth:`Client.create_authorization`

- Heavily improve guild subscriptions
    - [BREAKING] Remove ``Guild.request`` method; use :meth:`Guild.subscribe` instead
    - Allow disabling auto guild subscription via ``guild_subscriptions`` parameter in :class:`Client`
    - Add :func:`Guild.is_subscribed` and :func:`Guild.is_subscribed_to` to check if the client is subscribed to a guild
    - Add :meth:`Guild.subscribe` and :meth:`Guild.subscribe_to` to allow manually managing guild subscriptions

- [BREAKING] User notes handling is now entirely rewritten
    - The ``UserNote`` class is removed; notes are now represented as strings
    - ``Client.notes`` is renamed to :meth:`Client.fetch_notes` for forward-compatibility

- Update various payment and billing related models to add new fields
    - [BREAKING] Remove ``Payment.refund`` as it is no longer supported by the API
    - Add ``BRAINTREE_KEY``, ``STRIPE_KEY``, and ``ADYEN_KEY`` to package exports

- Add ``message_send_cooldown`` and ``thread_create_cooldown`` attributes to the :meth:`abc.Messageable.typing` context manager.
- Add :meth:`Client.channel_affinities` to get channel affinities and :meth:`Client.premium_affinities` to get premium user affinities
- Add various new fields to :class:`Application` and :class:`PartialApplication`, update implementations to match API
- Allow passing ``activities``, ``afk``, and ``idle_since`` to :class:`Client` for initial presence setup
- Add :func:`Client.is_afk` and :attr:`Client.idle_since` helpers
- Allow passing ``preferred_rtc_regions`` to :class:`Client` to override Discord's suggested RTC regions
    - [BREAKING] Rename ``Client.preferred_voice_regions`` to :attr:`Client.preferred_rtc_regions` to match the API
    - [BREAKING] Rename ``Client.fetch_preferred_voice_regions`` to :meth:`Client.fetch_preferred_rtc_regions` to match the API
    - [BREAKING] Remove ``preferred_region`` from :meth:`Client.change_voice_state` and :meth:`Guild.change_voice_state`
    - Allow setting the :attr:`Client.preferred_rtc_regions` property after initialisation

- Allow passing ``canary`` to :class:`Client` to use the canary API
- Allow passing ``timezone`` to :class:`Client` to configure the timezone broadcasted to Discord
- Add :class:`Tutorial` and :attr:`Client.tutorial` to access new user tutorial information
- Add ``with_permissions`` to :meth:`Client.fetch_invite`
- Add :meth:`Client.create_invite` and :meth:`Client.revoke_invites` to create and revoke friend invites
- Allow :meth:`Client.create_group` to create a group channel with only one other recipient
- [BREAKING] Rename ``Client.relationship_activity_statistics`` to :meth:`Client.global_activity_statistics` to better reflect its purpose
- Add :meth:`Client.user_offer` to replace deprecated :meth:`Client.trial_offer`
- Add :meth:`Client.report_unverified_application` to report game detection issues
- Add :meth:`Client.recent_avatars` to get recently used avatars
- Add :meth:`Guild.query_recent_members` to fetch members who recently joined
- Add various new fields to :class:`UserProfile` and :class:`MemberProfile`
    - Note that nearly all fields are unavailable if the user has blocked the client user. This can be determined with :func:`UserProfile.is_blocker`

- Add :attr:`DefaultAvatar.pink` for new pink default avatars
- Add :meth:`Colour.pink` to get the pink default avatar colour
- Add support for voice messages (:issue:`9358`)
    - Add :attr:`Attachment.duration` and :attr:`Attachment.waveform`
    - Add :meth:`Attachment.is_voice_message`
    - This does not support *sending* voice messages yet

- Add support for :attr:`TextChannel.default_thread_slowmode_delay`
- Add support for :attr:`ForumChannel.default_sort_order`
- Add support for ``default_reaction_emoji`` and ``default_forum_layout`` in :meth:`Guild.create_forum`
- Add support for ``widget_channel``, ``widget_enabled``, and ``mfa_level`` in :meth:`Guild.edit`
- Add various new :class:`Permissions` and changes
- Add support for ``with_counts`` parameter to :meth:`Client.fetch_guilds`
- Add new :meth:`Guild.get_emoji` helper
- Add :attr:`Guild.max_stage_video_channel_users` and :attr:`Guild.safety_alerts_channel`
- Add support for ``raid_alerts_disabled`` and ``safety_alerts_channel`` in :meth:`Guild.edit`.
- Add support for Polls (:issue:`9759`).
    - Polls can be created using :class:`Poll` and the ``poll`` keyword-only parameter in various message sending methods
    - Add :class:`PollAnswer` and :class:`PollMedia`
    - Add :meth:`Message.end_poll` method to end polls
    - Add new events, :func:`on_poll_vote_add`, :func:`on_poll_vote_remove`, :func:`on_raw_poll_vote_add`, and :func:`on_raw_poll_vote_remove`

- Voice handling has been completely rewritten to fix many bugs
- Add support for :attr:`RawReactionActionEvent.message_author_id`
- Add support for :attr:`AuditLogAction.creator_monetization_request_created` and :attr:`AuditLogAction.creator_monetization_terms_accepted`
- Add support for :class:`AttachmentFlags`, accessed via :attr:`Attachment.flags`
- Add support for :class:`RoleFlags`, accessed via :attr:`Role.flags`
- Add support for :attr:`ChannelType.media`, accessed via :meth:`ForumChannel.is_media`
- Add shortcut for :attr:`CategoryChannel.forums`.
- Add encoder options to :meth:`VoiceClient.play`
- Add optional attribute ``integration_type`` in :attr:`AuditLogEntry.extra` for ``kick`` or ``member_role_update`` actions
- Add support for reading burst reactions
    - Add :attr:`Reaction.normal_count`
    - Add :attr:`Reaction.burst_count`
    - Add :attr:`Reaction.me_burst`

- Add ``scheduled_event`` parameter for :meth:`StageChannel.create_instance`
- Add support for auto mod members
    - Add ``type`` keyword argument to :class:`AutoModRuleAction`
    - Add :attr:`AutoModTrigger.mention_raid_protection`
    - Add :attr:`AutoModRuleTriggerType.member_profile`
    - Add :attr:`AutoModRuleEventType.member_update`
    - Add :attr:`AutoModRuleActionType.block_member_interactions`

- Add support for getting/fetching threads from :class:`Message`
    - Add :attr:`PartialMessage.thread`
    - Add :attr:`Message.thread`
    - Add :meth:`Message.fetch_thread`

- Add support for adding forum thread tags via webhook
- Add :attr:`Locale.latin_american_spanish`
- Add support for setting voice channel status
- Add support for guild incidents
    - Updated :meth:`Guild.edit` with ``invites_disabled_until`` and ``dms_disabled_until`` parameters
    - Add :attr:`Guild.invites_paused_until`
    - Add :attr:`Guild.dms_paused_until`
    - Add :meth:`Guild.invites_paused`
    - Add :meth:`Guild.dms_paused`

- Add support for :attr:`abc.User.avatar_decoration`
- Add support for GIF stickers
- Add support for bulk banning members via :meth:`Guild.bulk_ban`
- Add ``reason`` keyword argument to :meth:`Thread.delete`
- Add support for reaction types to raw and non-raw models
- Add support for message forwarding
    - Adds :class:`MessageReferenceType`
    - Adds :class:`MessageSnapshot`
    - Adds ``type`` parameter to :class:`MessageReference`, :meth:`MessageReference.from_message`, and :meth:`PartialMessage.to_reference`
    - Add :meth:`PartialMessage.forward`ionCallbackResponse.resource` will be different

- Add :attr:`PartialWebhookChannel.mention` attribute
- Add richer :meth:`Role.move` interface
- Add support for :class:`EmbedFlags` via :attr:`Embed.flags`

- Add :attr:`ForumChannel.members` property
- Add :attr:`PartialMessageable.mention`

- Add support for purchase notification messages
    - Add new type :attr:`MessageType.purchase_notification`
    - Add new models :class:`GuildProductPurchase` and :class:`PurchaseNotification`
    - Add :attr:`Message.purchase_notification`

- Add ``category`` parameter to :meth:`.abc.GuildChannel.clone`
- Parse full message for message edit event
    - Adds :attr:`RawMessageUpdateEvent.message` attribute
    - Potentially speeds up :func:`on_message_edit` by no longer copying data

- Allow passing ``None`` for ``scopes`` parameter in :func:`utils.oauth_url`
- Add :attr:`Guild.dm_spam_detected_at` and :meth:`Guild.is_dm_spam_detected`
- Add :attr:`Guild.raid_detected_at` and :meth:`Guild.is_raid_detected`
- Add :meth:`Client.fetch_sticker_pack`
- Add :meth:`Guild.fetch_role`
- Add new :class:`Attachment` fields
- Add :attr:`Member.guild_banner` and :attr:`Member.display_banner`
- Add support for guild tags (also known as primary guilds)
    - This is through the :class:`PrimaryGuild` class
    - You retrieve this via :attr:`Member.primary_guild`

- Add support for the new pins endpoint
    - This turns :meth:`abc.Messageable.pins` into an async iterator
    - The old eager behaviour of using ``await`` is still supported, but is now deprecated

- Add support for guild onboarding
    - Completing onboarding is still not supported

- Add support new gradient and holographic role colours 
- Add :attr:`Locale.language_code` attribute 
- Add support for guest invites
- Add :attr:`File.uri` to get the ``attachment://<filename>`` URI of a file
- Add ability to create a media-only forum channel via ``media`` parameter in :meth:`Guild.create_forum`
- Add new colours from the new Discord themes 
    - This updates the old :meth:`Colour.dark_theme`, :meth:`Colour.light_theme`, :meth:`Colour.light_embed` and :meth:`Colour.dark_embed`
    - This adds :meth:`Colour.ash_theme`, :meth:`Colour.ash_embed`, :meth:`Colour.onyx_theme`, and :meth:`Colour.onyx_embed`

- |tasks| Add ``name`` parameter to :meth:`~ext.tasks.loop` to name the internal :class:`asyncio.Task`
- |commands| Add fallback behaviour to :class:`~ext.commands.CurrentGuild`
- |commands| Add logging for errors that occur during :meth:`~ext.commands.Cog.cog_unload`
- |commands| Add support for :class:`typing.NewType` and ``type`` keyword type aliases
- |commands| Add support for positional-only flag parameters
- |commands| Add support for channel URLs in ChannelConverter related classes
- |commands| Add :attr:`BadLiteralArgument.argument <ext.commands.BadLiteralArgument.argument>` to get the failed argument's value
- |commands| Add :attr:`Context.filesize_limit <ext.commands.Context.filesize_limit>` property
- |commands| Add support for :attr:`Parameter.displayed_name <ext.commands.Parameter.displayed_name>`

Bug Fixes
~~~~~~~~~

- Fix TLS fingerprinting issues causing unnecessary CAPTCHA challenges and blocked requests
- Fix the type of :attr:`ClientUser.phone` to be a string
- Fix various state issues when managing guild subscriptions
- [BREAKING] Remove no longer functional ``validate`` parameter from :meth:`abc.GuildChannel.create_invite`
- Improve presence syncing to reduce unnecessary updates and lost presences
- [BREAKING] Update return type of :meth:`Client.detectable_applications` to fix a crash due to an API change
- [BREAKING] Remove nonexistant ``Gift.revoked`` attribute
- [BREAKING] Rename ``Guild.owner_application_id`` to ``Guild.application_id`` to match API and upstream
- [BREAKING] Remove no longer functional ``Guild.application_command_counts`` attribute
- Fix crash in :class:`Integration` with the Twitch integration ID being a string
- Improve member and relationship presence support and handling

- Fix ``FileHandler`` handlers being written ANSI characters when the bot is executed inside PyCharm
    - This has the side effect of removing coloured logs from the PyCharm terminal due an upstream bug involving TTY detection. This issue is tracked under `PY-43798 <https://youtrack.jetbrains.com/issue/PY-43798>`_

- Fix channel edits with :meth:`Webhook.edit` sending two requests instead of one
- Fix :attr:`StageChannel.last_message_id` always being ``None``
- Fix piped audio input ending prematurely
- Fix AutoMod audit log entry error due to empty ``channel_id``
- Fix handling of ``around`` parameter in :meth:`abc.Messageable.history`
- Fix :func:`utils.escape_markdown` not escaping the new markdown
- Fix webhook targets not being converted in audit logs
- Fix error when not passing ``enabled`` in :meth:`Guild.create_automod_rule`
- Fix how various parameters are handled in :meth:`Guild.create_scheduled_event`
- Fix not sending the ``ssrc`` parameter when sending the ``SPEAKING`` voice payload
- Fix username lookup in :meth:`Guild.get_member_named`
- Fix false positives in :meth:`PartialEmoji.from_str` inappropriately setting ``animated`` to ``True``
- Fix ``NameError`` when using :meth:`abc.GuildChannel.create_invite`
- Fix escape behaviour for lists and headers in :meth:`~utils.escape_markdown`
- Fixes and improvements for :class:`FFmpegAudio` and all related subclasses
- Fix :meth:`Template.source_guild` attempting to resolve from cache
- Fix :exc:`IndexError` being raised instead of :exc:`ValueError` when calling :meth:`Colour.from_str` with an empty string
- Fix possible error in voice cleanup logic
- Fix possible bad voice state where you move to a voice channel with missing permissions
- Fix handling of :class:`AuditLogDiff` when relating to auto mod triggers
- Fix race condition in voice logic relating to disconnect and connect
- Fix restriction on auto moderation audit log ID range
- Fix comparison between :class:`Object` classes with a ``type`` set
- Fix handling of an enum in :meth:`AutoModRule.edit`
- Fix handling of :meth:`Client.close` within :meth:`Client.__aexit__`
- Fix channel deletion not evicting related threads from cache
- Fix bug with cache superfluously incrementing role positions
- Fix ``exempt_channels`` not being passed along in :meth:`Guild.create_automod_rule`
- Fix :meth:`abc.GuildChannel.purge` failing if the message was deleted
- Handle improper 1000 close code closures by Discord
- Add support for AEAD XChaCha20 Poly1305 encryption model
    - This allows voice to continue working when the older encryption modes eventually get removed

- Update all channel clone implementations to work as expected
- Fix :meth:`TextChannel.clone` always sending slowmode when not applicable to news channels
- Fix :attr:`Sticker.url` for GIF stickers 
- Fix :attr:`User.default_avatar` for team users and webhooks
- Fix :attr:`AuditLogEntry.target` causing errors for :attr:`AuditLogAction.message_pin` and :attr:`AuditLogAction.message_unpin` actions
- Fix path sanitisation for absolute Windows paths when using ``__main__``
- Create :class:`ScheduledEvent` on cache miss for :func:`on_scheduled_event_delete`
- Add defaults for :class:`Message` creation preventing some crashes
- Fix voice connection issues and upgrade the voice version to 8
- Fix calculation of hashed rate limit keys
- Fix :attr:`Thread.applied_tags` being empty for media channels
- Fix potentially stuck ratelimit buckets in certain circumstances
- Fix audit log ``automod_rule_trigger_type`` extra being missing

- |tasks| Fix race condition when setting timer handle when using uvloop
- |commands| Fix issue with category cooldowns outside of guild channels
- |commands| Fix callable FlagConverter defaults on hybrid commands not being called
- |commands| Unwrap :class:`~discord.ext.commands.Parameter` if given as default to :func:`~ext.commands.parameter`
- |commands| Fix fallback behaviour not being respected when calling replace for :class:`~.ext.commands.Parameter`
- |commands| Fix :class:`~ext.commands.HelpCommand` defined checks not carrying over during copy
- |commands| Fix the wrong :meth:`~ext.commands.HelpCommand.on_help_command_error` being called when ejected from a cog
- |commands| Fix ``=None`` being displayed in :attr:`~ext.commands.Command.signature`
- |commands| Change lookup order for :class:`~ext.commands.MemberConverter` and :class:`~ext.commands.UserConverter` to prioritise usernames instead of nicknames

Miscellaneous
~~~~~~~~~~~~~

- Minimum version is now Python 3.10
- New dependency: ``curl_cffi``
- Update filesize limit constants
- Additional documentation added for logging capabilities
- Performance increases of constructing :class:`Permissions` using keyword arguments
- Improve ``__repr__`` of :class:`SyncWebhook` and :class:`Webhook`
- Change internal thread names to be consistent 
- Use a fallback package for ``audioop`` to allow the library to work in Python 3.13 or newer
- Remove ``aiodns`` from being used on Windows
- Add zstd gateway compression to ``speed`` extras 
    - This can be installed using ``discord.py-self[speed]``

- Add proxy support fetching from the CDN
- Remove ``/`` from being safe from URI encoding when constructing paths internally
- Sanitize invite argument before calling the invite info endpoint
- Avoid returning in finally in specific places to prevent exception swallowing
- Deprecate the ``with_expiration`` parameter in :meth:`Client.fetch_invite`
- Allow creating NSFW voice/stage channels
- The :class:`Invite` is now returned when using :meth:`Invite.delete` or :meth:`Client.delete_invite`
- Update PyNaCl minimum version dependency
- ``AppCommandType`` is now  ``ApplicationCommandType`` for consistency; the old name is still available as an alias
- ``AppCommandOptionType`` is now ``ApplicationCommandOptionType`` for consistency; the old name is still available as an alias
- [BREAKING] Remove all achievement support as the endpoints have been removed by Discord
- [BREAKING] Updated CAPTCHA handler implementation
    - The old ``CaptchaHandler`` class has been removed
    - New interface is via the ``captcha_handler`` parameter in :class:`Client`, which accepts a :class:`CaptchaRequired` class instance and the :class:`Client` itself as parameters
    - You can also override :meth:`Client.handle_captcha` in a subclass
- [BREAKING] Swap all ``exclude_*`` parameters in fetch methods to ``include_*`` parameters for consistency

.. _vp2p0p0:

v2.0.0
-------

This is considered the initial stable version. All previous versions were mostly a stepping stone to this one. The changes are too enormous to list here, so please check out the rest of the documentation.
