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

import asyncio
import logging
import struct
from typing import Any, Callable, List, Optional, Sequence, TYPE_CHECKING, Tuple, TypeVar

from . import opus
from .gateway import *
from .errors import ClientException
from .flags import SpeakingFlags
from .player import AudioPlayer, AudioSource
from .utils import MISSING
from .voice_state import VoiceConnectionState
from .voice_media import (
    RTP_AUDIO_LEVEL_SILENCE,
    _audio_level_from_pcm,
    _audio_rtp_extension_payload,
    _rtp_header_with_one_byte_extensions,
    VoiceCodec,
    VoiceStream,
    VoiceStreamResolution,
)
from .stream import Stream, StreamKey, StreamProtocol

if TYPE_CHECKING:
    from .gateway import DiscordVoiceWebSocket
    from .client import Client
    from .guild import Guild
    from .state import ConnectionState
    from .user import ClientUser
    from .opus import Encoder, APPLICATION_CTL, BAND_CTL, SIGNAL_CTL
    from . import abc

    from .types.gateway import VoiceStateUpdateEvent as VoiceStateUpdatePayload
    from .types.voice import (
        GuildVoiceState as GuildVoiceStatePayload,
        VoiceServerUpdate as VoiceServerUpdatePayload,
        TransportEncryptionModes,
    )

    VocalChannel = abc.VocalChannel


has_nacl: bool
nacl_secret: Any
nacl_utils: Any

try:
    import nacl.secret as nacl_secret  # type: ignore
    import nacl.utils as nacl_utils  # type: ignore

    has_nacl = True
except ImportError:
    nacl_secret = None
    nacl_utils = None
    has_nacl = False

__all__ = (
    'VoiceProtocol',
    'VoiceClient',
    'VoiceCodec',
    'VoiceStream',
    'VoiceStreamResolution',
)


_log = logging.getLogger(__name__)
ST = TypeVar('ST', bound=StreamProtocol)


class VoiceProtocol:
    """A class that represents the Discord voice protocol.

    This is an abstract class. The library provides a concrete implementation
    under :class:`VoiceClient`.

    This class allows you to implement a protocol to allow for an external
    method of sending voice, such as Lavalink_ or a native library implementation.

    These classes are passed to :meth:`abc.Connectable.connect <VoiceChannel.connect>`.

    .. _Lavalink: https://github.com/freyacodes/Lavalink

    Parameters
    ------------
    client: :class:`Client`
        The client (or its subclasses) that started the connection request.
    channel: Union[:class:`VoiceChannel`, :class:`StageChannel`, :class:`DMChannel`, :class:`GroupChannel`]
        The voice channel that is being connected to.
    """

    supported_modes: tuple[TransportEncryptionModes, ...] = ()
    experiments: tuple[str, ...] = ()

    def __init__(self, client: Client, channel: VocalChannel) -> None:
        self.client: Client = client
        self.channel: VocalChannel = channel

    def supports_video(self) -> bool:
        """Checks whether the voice protocol implementation supports video.

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
    def codecs(self) -> Tuple[VoiceCodec, ...]:
        """Tuple[:class:`VoiceCodec`]: The codecs that the voice protocol supports. Defaults to Opus (required).
        For video support, you must include the video codecs here as well.

        .. versionadded:: 2.2
        """
        return (VoiceCodec.opus(),)

    @property
    def video_streams(self) -> Tuple[VoiceStream, ...]:
        """Tuple[:class:`VoiceStream`]: The video streams that the voice protocol advertises on connection. Defaults to none.

        .. versionadded:: 2.2
        """
        return ()

    @property
    def streams(self) -> Tuple[Stream, ...]:
        """Tuple[:class:`Stream`]: The Go Live streams known for this voice connection.

        .. versionadded:: 2.2
        """
        return self.client._connection._streams_for_voice_client(self)

    @property
    def stream_clients(self) -> Tuple[StreamProtocol, ...]:
        """Tuple[:class:`StreamProtocol`]: The Go Live stream clients attached to this voice connection.

        .. versionadded:: 2.2
        """
        return self.client._connection._stream_clients_for_voice_client(self)

    def get_stream(self, stream_key: StreamKey) -> Optional[Stream]:
        """Optional[:class:`Stream`]: Returns a known Go Live stream by stream key for this voice connection.

        .. versionadded:: 2.2
        """
        state = self.client._connection
        if state._get_voice_client_for_stream_key(stream_key) is not self:
            return None
        return state.get_stream(stream_key)

    async def watch_stream(
        self,
        stream_key: StreamKey,
        *,
        timeout: float = 30.0,
        reconnect: bool = True,
        cls: Callable[[VoiceProtocol, Stream], ST],
    ) -> ST:
        """|coro|

        Watches a Go Live stream by stream key and connects with the provided stream protocol.

        This is useful when the stream is not already cached. If the stream is cached,
        this delegates to :meth:`Stream.watch`.

        Parameters
        -----------
        stream_key: :class:`StreamKey`
            The stream key to watch.
        timeout: :class:`float`
            The timeout in seconds to wait for the stream connection to complete.
        reconnect: :class:`bool`
            Whether the stream protocol should attempt reconnects.
        cls: Type[:class:`StreamProtocol`]
            A type that subclasses :class:`StreamProtocol` to connect with.

        .. versionadded:: 2.2

        Raises
        -------
        ~discord.ClientException
            You are not connected to the stream's voice channel, or you tried to watch your own stream.

        Returns
        --------
        :class:`StreamProtocol`
            The connected stream protocol.
        """
        state = self.client._connection
        if stream_key.owner_id == state.self_id:
            raise ClientException('Cannot watch a stream you own')
        if state._get_voice_client_for_stream_key(stream_key) is not self:
            raise ClientException('Must be connected to the stream voice channel before watching')

        stream = state.get_stream(stream_key)
        if stream is not None:
            return await stream.watch(timeout=timeout, reconnect=reconnect, cls=cls)

        async def request() -> None:
            await state.ws.stream_watch(str(stream_key))

        return await state._connect_stream(
            self,
            stream_key,
            request,
            cls=cls,
            timeout=timeout,
            reconnect=reconnect,
        )

    async def create_stream(
        self,
        *,
        timeout: float = 30.0,
        reconnect: bool = True,
        cls: Callable[[VoiceProtocol, Stream], ST],
    ) -> ST:
        """|coro|

        Creates a Go Live stream for this voice connection and connects with the provided stream protocol.

        Parameters
        -----------
        timeout: :class:`float`
            The timeout in seconds to wait for the stream connection to complete.
        reconnect: :class:`bool`
            Whether the stream protocol should attempt reconnects.
        cls: Type[:class:`StreamProtocol`]
            A type that subclasses :class:`StreamProtocol` to connect with.

        .. versionadded:: 2.2

        Returns
        --------
        :class:`StreamProtocol`
            The connected stream protocol.
        """
        state = self.client._connection
        stream_key = state._stream_key_for_voice_client(self)

        async def request() -> None:
            guild = getattr(self.channel, 'guild', None)
            await state.ws.stream_create(
                stream_type=stream_key.type.value,
                guild_id=guild.id if guild is not None else None,
                channel_id=self.channel.id,
            )

        return await state._connect_stream(
            self,
            stream_key,
            request,
            cls=cls,
            timeout=timeout,
            reconnect=reconnect,
        )

    async def on_voice_state_update(self, data: VoiceStateUpdatePayload, /) -> None:
        """|coro|

        An abstract method that is called when the client's voice state
        has changed. This corresponds to ``VOICE_STATE_UPDATE``.

        .. warning::

            This method is not the same as the event. See: :func:`on_voice_state_update`

        Parameters
        ------------
        data: :class:`dict`
            The raw :ddocs:`voice state payload <resources/voice#voice-state-object>`.
        """
        raise NotImplementedError

    async def on_voice_server_update(self, data: VoiceServerUpdatePayload, /) -> None:
        """|coro|

        An abstract method that is called when initially connecting to voice.
        This corresponds to ``VOICE_SERVER_UPDATE``.

        Parameters
        ------------
        data: :class:`dict`
            The raw :ddocs:`voice server update payload <topics/gateway-events#voice-server-update>`.
        """
        raise NotImplementedError

    async def connect(
        self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False, self_video: bool = False
    ) -> None:
        """|coro|

        An abstract method called when the client initiates the connection request.

        When a connection is requested initially, the library calls the constructor
        under ``__init__`` and then calls :meth:`connect`. If :meth:`connect` fails at
        some point then :meth:`disconnect` is called.

        Within this method, to start the voice connection flow it is recommended to
        use :meth:`Guild.change_voice_state` to start the flow. After which,
        :meth:`on_voice_server_update` and :meth:`on_voice_state_update` will be called.
        The order that these two are called is unspecified.

        Parameters
        ------------
        timeout: :class:`float`
            The timeout for the connection.
        reconnect: :class:`bool`
            Whether reconnection is expected.
        self_mute: :class:`bool`
            Indicates if the client should be self-muted.

            .. versionadded:: 2.0
        self_deaf: :class:`bool`
            Indicates if the client should be self-deafened.

            .. versionadded:: 2.0
        self_video: :class:`bool`
            Indicates if the client should join with video enabled.

            .. versionadded:: 2.2
        """
        raise NotImplementedError

    async def disconnect(self, *, force: bool) -> None:
        """|coro|

        An abstract method called when the client terminates the connection.

        See :meth:`cleanup`.

        Parameters
        ------------
        force: :class:`bool`
            Whether the disconnection was forced.
        """
        raise NotImplementedError

    def cleanup(self) -> None:
        """This method *must* be called to ensure proper clean-up during a disconnect.

        It is advisable to call this from within :meth:`disconnect` when you are
        completely done with the voice protocol instance.

        This method removes it from the internal state cache that keeps track of
        currently alive voice clients. Failure to clean-up will cause subsequent
        connections to report that it's still connected.
        """
        key_id, _ = self.channel._get_voice_client_key()
        self.client._connection._remove_voice_client(key_id)


class VoiceClient(VoiceProtocol):
    """Represents a Discord voice connection.

    You do not create these, you typically get them from
    e.g. :meth:`VoiceChannel.connect`.

    Warning
    --------
    In order to use PCM based AudioSources, you must have the opus library
    installed on your system and loaded through :func:`opus.load_opus`.
    Otherwise, your AudioSources must be opus encoded (e.g. using :class:`FFmpegOpusAudio`)
    or the library will not be able to transmit audio.

    Attributes
    -----------
    session_id: :class:`str`
        The voice connection session ID.
    token: :class:`str`
        The voice connection token.
    endpoint: :class:`str`
        The endpoint we are connecting to.
    channel: Union[:class:`VoiceChannel`, :class:`StageChannel`, :class:`DMChannel`, :class:`GroupChannel`]
        The voice channel connected to.
    """

    channel: VocalChannel

    def __init__(self, client: Client, channel: VocalChannel) -> None:
        if not has_nacl:
            raise RuntimeError('PyNaCl library needed in order to use voice')

        super().__init__(client, channel)
        state = client._connection
        self.server_id: int = MISSING
        self.socket = MISSING
        self.loop: asyncio.AbstractEventLoop = state.loop
        self._state: ConnectionState = state

        self.sequence: int = 0
        self.timestamp: int = 0
        self._player: Optional[AudioPlayer] = None
        self.encoder: Encoder = MISSING
        self._lite_nonce: int = 0
        self._incr_nonce: int = 0
        self._speaking_flags: SpeakingFlags = SpeakingFlags.none()

        self._connection: VoiceConnectionState = self.create_connection_state()

    warn_nacl: bool = not has_nacl
    supported_modes: Tuple[TransportEncryptionModes, ...] = (
        'aead_xchacha20_poly1305_rtpsize',
        'xsalsa20_poly1305_lite',
        'xsalsa20_poly1305_suffix',
        'xsalsa20_poly1305',
    )

    @property
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`Guild`]: The guild we're connected to, if applicable."""
        return getattr(self.channel, 'guild', None)

    @property
    def user(self) -> ClientUser:
        """:class:`ClientUser`: The user connected to voice (i.e. ourselves)."""
        return self._state.user  # type: ignore

    @property
    def session_id(self) -> Optional[str]:
        """Optional[:class:`str`]: The current voice session ID."""

        return self._connection.session_id

    @property
    def token(self) -> Optional[str]:
        """Optional[:class:`str`]: The current voice server token."""

        return self._connection.token

    @property
    def endpoint(self) -> Optional[str]:
        """Optional[:class:`str`]: The current voice server endpoint."""

        return self._connection.endpoint

    @property
    def ssrc(self) -> int:
        """:class:`int`: The negotiated audio SSRC."""

        return self._connection.ssrc

    @property
    def mode(self) -> TransportEncryptionModes:
        """:class:`str`: The negotiated transport encryption mode."""

        return self._connection.mode

    @property
    def secret_key(self) -> List[int]:
        """List[:class:`int`]: The negotiated transport secret key."""

        return self._connection.secret_key

    @property
    def ws(self) -> DiscordVoiceWebSocket:
        """:class:`DiscordVoiceWebSocket`: The active voice websocket."""

        return self._connection.ws

    @property
    def timeout(self) -> float:
        """:class:`float`: The voice connection timeout in seconds."""

        return self._connection.timeout

    @property
    def voice_privacy_code(self) -> Optional[str]:
        """:class:`str`: Get the voice privacy code of this E2EE session's group.

        A new privacy code is created and cached each time a new transition is executed.
        This can be None if there is no active DAVE session happening.

        .. versionadded:: 2.1
        """
        return self._connection.dave_session.voice_privacy_code if self._connection.dave_session else None

    def checked_add(self, attr: str, value: int, limit: int) -> None:
        """Add to an integer attribute and wrap it to zero past a limit."""

        val = getattr(self, attr)
        if val + value > limit:
            setattr(self, attr, 0)
        else:
            setattr(self, attr, val + value)

    # connection related

    def create_connection_state(self) -> VoiceConnectionState:
        """Create the connection state object for this voice client."""

        return VoiceConnectionState(self)

    async def on_voice_state_update(self, data: VoiceStateUpdatePayload) -> None:
        """Handle a VOICE_STATE_UPDATE gateway payload for this client."""

        await self._connection.voice_state_update(data)

    async def on_voice_server_update(self, data: VoiceServerUpdatePayload) -> None:
        """Handle a VOICE_SERVER_UPDATE gateway payload for this client."""

        await self._connection.voice_server_update(data)

    async def connect(
        self, *, reconnect: bool, timeout: float, self_deaf: bool = False, self_mute: bool = False, self_video: bool = False
    ) -> None:
        """Connect this voice client to its channel."""

        await self._connection.connect(
            reconnect=reconnect,
            timeout=timeout,
            self_deaf=self_deaf,
            self_mute=self_mute,
            self_video=self_video,
            resume=False,
        )

    def wait_until_connected(self, timeout: Optional[float] = 30.0) -> bool:
        """Block until the voice connection is ready or times out."""

        self._connection.wait(timeout)
        return self._connection.is_connected()

    @property
    def latency(self) -> float:
        """:class:`float`: Latency between a HEARTBEAT and a HEARTBEAT_ACK in seconds.

        This could be referred to as the Discord Voice WebSocket latency and is
        an analogue of user's voice latencies as seen in the Discord client.

        .. versionadded:: 1.4
        """
        ws = self._connection.ws
        return float('inf') if not ws else ws.latency

    @property
    def average_latency(self) -> float:
        """:class:`float`: Average of most recent 20 HEARTBEAT latencies in seconds.

        .. versionadded:: 1.4
        """
        ws = self._connection.ws
        return float('inf') if not ws else ws.average_latency

    async def disconnect(self, *, force: bool = False) -> None:
        """|coro|

        Disconnects this voice client from voice.
        """
        self.stop()
        await self._connection.disconnect(force=force, wait=True)
        self.cleanup()

    async def move_to(self, channel: Optional[abc.Snowflake], *, timeout: Optional[float] = 30.0) -> None:
        """|coro|

        Moves you to a different voice channel.

        Parameters
        -----------
        channel: Optional[:class:`~abc.Snowflake`]
            The channel to move to. Must be a voice channel.
        timeout: Optional[:class:`float`]
            How long to wait for the move to complete.

            .. versionadded:: 2.1

        Raises
        -------
        asyncio.TimeoutError
            The move did not complete in time, but may still be ongoing.
        """
        await self._connection.move_to(channel, timeout)

    def is_connected(self) -> bool:
        """Indicates if the voice client is connected to voice."""
        return self._connection.is_connected()

    # audio related

    async def update_speaking_state(self, flags: SpeakingFlags) -> None:
        """Update the current speaking flags.

        Parameters
        ----------
        flags: :class:`SpeakingFlags`
            The new speaking flags.
        """
        self._speaking_flags = flags
        await self.ws.speak(flags)

    def _get_voice_packet(self, data: bytes, *, audio_level: int = RTP_AUDIO_LEVEL_SILENCE):
        packet = (
            self._connection.dave_session.encrypt_opus(data)
            if self._connection.dave_session and self._connection.can_encrypt
            else data
        )
        header = bytearray(12)

        # Formulate rtp header
        header[0] = 0x80
        header[1] = 0x78
        struct.pack_into('>H', header, 2, self.sequence)
        struct.pack_into('>I', header, 4, self.timestamp)
        struct.pack_into('>I', header, 8, self.ssrc)

        extension_payload = _audio_rtp_extension_payload(self._speaking_flags.value, audio_level=audio_level)
        if extension_payload:
            header = bytearray(_rtp_header_with_one_byte_extensions(header, extension_payload))
            packet = extension_payload + packet

        encrypt_packet = getattr(self, '_encrypt_' + self.mode)
        return encrypt_packet(header, packet)

    def _encrypt_aead_xchacha20_poly1305_rtpsize(self, header: bytes, data) -> bytes:
        box = nacl_secret.Aead(bytes(self.secret_key))
        nonce = bytearray(24)

        nonce[:4] = struct.pack('>I', self._incr_nonce)
        self.checked_add('_incr_nonce', 1, 4294967295)

        return header + box.encrypt(bytes(data), bytes(header), bytes(nonce)).ciphertext + nonce[:4]

    def _encrypt_xsalsa20_poly1305(self, header: bytes, data) -> bytes:
        box = nacl_secret.SecretBox(bytes(self.secret_key))
        nonce = bytearray(24)
        nonce[:12] = header[:12]

        return header + box.encrypt(bytes(data), bytes(nonce)).ciphertext

    def _encrypt_xsalsa20_poly1305_suffix(self, header: bytes, data) -> bytes:
        box = nacl_secret.SecretBox(bytes(self.secret_key))
        nonce = nacl_utils.random(nacl_secret.SecretBox.NONCE_SIZE)

        return header + box.encrypt(bytes(data), nonce).ciphertext + nonce

    def _encrypt_xsalsa20_poly1305_lite(self, header: bytes, data) -> bytes:
        box = nacl_secret.SecretBox(bytes(self.secret_key))
        nonce = bytearray(24)

        nonce[:4] = struct.pack('>I', self._lite_nonce)
        self.checked_add('_lite_nonce', 1, 4294967295)

        return header + box.encrypt(bytes(data), bytes(nonce)).ciphertext + nonce[:4]

    def play(
        self,
        source: AudioSource,
        *,
        after: Optional[Callable[[Optional[Exception]], Any]] = None,
        application: APPLICATION_CTL = 'audio',
        bitrate: int = 128,
        fec: bool = True,
        expected_packet_loss: float = 0.15,
        bandwidth: BAND_CTL = 'full',
        signal_type: SIGNAL_CTL = 'auto',
    ) -> None:
        """Plays an :class:`AudioSource`.

        The finalizer, ``after`` is called after the source has been exhausted
        or an error occurred.

        If an error happens while the audio player is running, the exception is
        caught and the audio player is then stopped.  If no after callback is
        passed, any caught exception will be logged using the library logger.

        Extra parameters may be passed to the internal opus encoder if a PCM based
        source is used.  Otherwise, they are ignored.

        .. versionchanged:: 2.0
            Instead of writing to ``sys.stderr``, the library's logger is used.

        .. versionchanged:: 2.1
            Added encoder parameters as keyword arguments.

        Parameters
        -----------
        source: :class:`AudioSource`
            The audio source we're reading from.
        after: Callable[[Optional[:class:`Exception`]], Any]
            The finalizer that is called after the stream is exhausted.
            This function must have a single parameter, ``error``, that
            denotes an optional exception that was raised during playing.
        application: :class:`str`
            Configures the encoder's intended application.  Can be one of:
            ``'audio'``, ``'voip'``, ``'lowdelay'``.
            Defaults to ``'audio'``.
        bitrate: :class:`int`
            Configures the bitrate in the encoder.  Can be between ``16`` and ``512``.
            Defaults to ``128``.
        fec: :class:`bool`
            Configures the encoder's use of inband forward error correction.
            Defaults to ``True``.
        expected_packet_loss: :class:`float`
            Configures the encoder's expected packet loss percentage.  Requires FEC.
            Defaults to ``0.15``.
        bandwidth: :class:`str`
            Configures the encoder's bandpass.  Can be one of:
            ``'narrow'``, ``'medium'``, ``'wide'``, ``'superwide'``, ``'full'``.
            Defaults to ``'full'``.
        signal_type: :class:`str`
            Configures the type of signal being encoded.  Can be one of:
            ``'auto'``, ``'voice'``, ``'music'``.
            Defaults to ``'auto'``.

        Raises
        -------
        ClientException
            Already playing audio or not connected.
        TypeError
            Source is not a :class:`AudioSource` or after is not a callable.
        OpusNotLoaded
            Source is not opus encoded and opus is not loaded.
        ValueError
            An improper value was passed as an encoder parameter.
        """

        if not self.is_connected():
            raise ClientException('Not connected to voice.')

        if self.is_playing():
            raise ClientException('Already playing audio.')

        if not isinstance(source, AudioSource):
            raise TypeError(f'source must be an AudioSource not {source.__class__.__name__}')

        if not source.is_opus():
            self.encoder = opus.Encoder(
                application=application,
                bitrate=bitrate,
                fec=fec,
                expected_packet_loss=expected_packet_loss,
                bandwidth=bandwidth,
                signal_type=signal_type,
            )

        self._player = AudioPlayer(source, self, after=after)
        self._player.start()

    def is_playing(self) -> bool:
        """Indicates if we're currently playing audio."""
        return self._player is not None and self._player.is_playing()

    def is_paused(self) -> bool:
        """Indicates if we're playing audio, but if we're paused."""
        return self._player is not None and self._player.is_paused()

    def stop(self) -> None:
        """Stops playing audio."""
        if self._player:
            self._player.stop()
            self._player = None

    def pause(self) -> None:
        """Pauses the audio playing."""
        if self._player:
            self._player.pause()

    def resume(self) -> None:
        """Resumes the audio playing."""
        if self._player:
            self._player.resume()

    @property
    def source(self) -> Optional[AudioSource]:
        """Optional[:class:`AudioSource`]: The audio source being played, if playing.

        This property can also be used to change the audio source currently being played.
        """
        return self._player.source if self._player else None

    @source.setter
    def source(self, value: AudioSource) -> None:
        """Set the audio source currently being played."""

        if not isinstance(value, AudioSource):
            raise TypeError(f'expected AudioSource not {value.__class__.__name__}')

        if self._player is None:
            raise ValueError('Not playing anything')

        self._player.set_source(value)

    def send_audio_packet(self, data: bytes, *, encode: bool = True) -> None:
        """Sends an audio packet composed of the data.

        You must be connected to play audio.

        Parameters
        ----------
        data: :class:`bytes`
            The :term:`py:bytes-like object` denoting PCM or Opus voice data.
        encode: :class:`bool`
            Indicates if ``data`` should be encoded into Opus.

        Raises
        -------
        ClientException
            You are not connected.
        opus.OpusError
            Encoding the data failed.
        """
        self.checked_add('sequence', 1, 65535)
        if encode:
            audio_level = _audio_level_from_pcm(data)
            encoded_data = self.encoder.encode(data, self.encoder.SAMPLES_PER_FRAME)
        else:
            audio_level = RTP_AUDIO_LEVEL_SILENCE if data == opus.OPUS_SILENCE else 0
            encoded_data = data
        packet = self._get_voice_packet(encoded_data, audio_level=audio_level)
        try:
            self._connection.send_packet(packet)
        except OSError:
            _log.debug('A packet has been dropped (seq: %s, timestamp: %s).', self.sequence, self.timestamp)

        self.checked_add('timestamp', opus.Encoder.SAMPLES_PER_FRAME, 4294967295)
