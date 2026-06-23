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

import math
import struct
import time

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .types.voice import (
        VoiceCodec as VoiceCodecPayload,
        VoiceStream as VoiceStreamPayload,
        VoiceStreamResolution as VoiceStreamResolutionPayload,
    )

__all__ = (
    'VoiceCodec',
    'VoiceStream',
    'VoiceStreamResolution',
)

RTP_ONE_BYTE_EXTENSION_PROFILE = b'\xbe\xde'
RTP_AUDIO_LEVEL_SILENCE = 127


def _rtp_header_with_one_byte_extensions(header: bytes | bytearray, extension_payload: bytes) -> bytes:
    header_buffer = bytearray(header[:12])
    if not extension_payload:
        header_buffer[0] &= ~0x10
        return bytes(header_buffer)

    header_buffer[0] |= 0x10
    header_buffer.extend(RTP_ONE_BYTE_EXTENSION_PROFILE)
    header_buffer.extend(struct.pack('>H', len(extension_payload) // 4))
    return bytes(header_buffer)


def _audio_level_from_pcm(data: bytes | bytearray | memoryview) -> int:
    raw = bytes(data)
    sample_bytes = len(raw) & ~1
    if sample_bytes == 0:
        return RTP_AUDIO_LEVEL_SILENCE

    square_sum = 0
    sample_count = 0
    for (sample,) in struct.iter_unpack('<h', raw[:sample_bytes]):
        square_sum += sample * sample
        sample_count += 1

    if square_sum == 0:
        return RTP_AUDIO_LEVEL_SILENCE

    rms = math.sqrt(square_sum / sample_count)
    ratio = min(rms / 32767.0, 1.0)
    if ratio <= 0:
        return RTP_AUDIO_LEVEL_SILENCE

    return min(RTP_AUDIO_LEVEL_SILENCE, max(0, round(-20.0 * math.log10(ratio))))


def _audio_rtp_extension_payload(speaking: int, *, audio_level: int = RTP_AUDIO_LEVEL_SILENCE) -> bytes:
    level = min(RTP_AUDIO_LEVEL_SILENCE, max(0, audio_level))
    voice_activity = 0x80 if speaking else 0

    speaking_value = 0
    if speaking & 4:
        speaking_value |= 0b001
    if speaking & 1:
        speaking_value |= 0b010
    if speaking & 2:
        speaking_value |= 0b100

    extensions = (
        (1, bytes((voice_activity | level,))),
        (3, (int((time.time() % 64) * (1 << 18)) & 0xFFFFFF).to_bytes(3, 'big')),
        (9, bytes((speaking_value,))),
        (10, b'audio'),
    )
    payload = bytearray()
    for extension_id, data in extensions:
        if not 1 <= extension_id <= 14:
            raise ValueError(f'RTP extension id must be in [1, 14], got {extension_id!r}')
        if not 1 <= len(data) <= 16:
            raise ValueError(f'RTP extension data length must be in [1, 16], got {len(data)!r}')

        payload.append((extension_id << 4) | (len(data) - 1))
        payload.extend(data)

    padding = (-len(payload)) % 4
    if padding:
        payload.extend(b'\x00' * padding)
    return bytes(payload)


class VoiceCodec:
    """Represents a Discord voice codec.

    .. versionadded:: 2.2

    Attributes
    ----------
    name: :class:`str`
        The name of the codec. Currently, must be one of:
        ``opus``, ``VP8``, ``VP9``, ``H264``, ``H265``, or ``AV1``.
    type: :class:`str`
        The type of the codec. Must be either ``audio`` or ``video``.
    priority: :class:`int`
        The priority of the codec. Lower values indicate higher priority.
        By convention, this starts at ``1000`` and increments by 1000 for each additional codec.
    payload_type: :class:`int`
        The RTP payload type for the codec.
    rtx_payload_type: Optional[:class:`int`]
        The RTP payload type for RTX retransmissions of this video codec, if supported.
    encode: :class:`bool`
        Whether the client can encode this codec.
    decode: :class:`bool`
        Whether the client can decode this codec.
    """

    __slots__ = ('name', 'type', 'priority', 'payload_type', 'rtx_payload_type', 'encode', 'decode')

    def __init__(
        self,
        name: str,
        type: Literal['audio', 'video'],
        *,
        priority: int,
        payload_type: int,
        rtx_payload_type: int | None = None,
        encode: bool = True,
        decode: bool = True,
    ) -> None:
        self.name: str = name
        self.type: Literal['audio', 'video'] = type
        self.priority: int = priority
        self.payload_type: int = payload_type
        self.rtx_payload_type: int | None = rtx_payload_type
        self.encode: bool = encode
        self.decode: bool = decode

    def __eq__(self, other: object) -> bool:
        if isinstance(other, VoiceCodec):
            return (
                self.name == other.name
                and self.type == other.type
                and self.priority == other.priority
                and self.payload_type == other.payload_type
                and self.rtx_payload_type == other.rtx_payload_type
                and self.encode == other.encode
                and self.decode == other.decode
            )
        return NotImplemented

    @classmethod
    def opus(cls, *, priority: int = 1000, payload_type: int = 120) -> VoiceCodec:
        """A factory method for creating an Opus audio codec.
        Voice clients are required to support encoding and decoding Opus.

        Parameters
        -----------
        priority: :class:`int`
            The priority of the codec. Lower values indicate higher priority.
            By convention, this starts at ``1000`` and increments by 1000 for each additional codec.
            As this is the only audio codec currently supported by Discord, this should not need to be changed.
        payload_type: :class:`int`
            The RTP payload type for the codec. By convention, this defaults to ``120`` for Opus.

        Returns
        --------
        :class:`VoiceCodec`
            The created voice codec.
        """
        return cls('opus', 'audio', priority=priority, payload_type=payload_type)

    @classmethod
    def video(
        cls,
        name: str,
        *,
        priority: int,
        payload_type: int,
        rtx_payload_type: int,
        encode: bool = True,
        decode: bool = True,
    ) -> VoiceCodec:
        """A factory method for creating a video codec.

        Parameters
        -----------
        name: :class:`str`
            The name of the codec. Currently, must be one of: ``VP8``, ``VP9``, ``H264``, ``H265``, or ``AV1``.
        priority: :class:`int`
            The priority of the codec. Lower values indicate higher priority.
        payload_type: :class:`int`
            The RTP payload type for the codec.
        rtx_payload_type: :class:`int`
            The RTP payload type for the RTX codec.
        encode: :class:`bool`
            Whether the client can encode this codec. Defaults to ``True``,
            matching the voice server's behavior when this field is omitted.
        decode: :class:`bool`
            Whether the client can decode this codec. Defaults to ``True``,
            matching the voice server's behavior when this field is omitted.

        Returns
        --------
        :class:`VoiceCodec`
            The created voice codec.
        """
        return cls(
            name.upper(),
            'video',
            priority=priority,
            payload_type=payload_type,
            rtx_payload_type=rtx_payload_type,
            encode=encode,
            decode=decode,
        )

    @classmethod
    def from_dict(cls, data: VoiceCodecPayload) -> VoiceCodec:
        return cls(
            data['name'],
            data['type'],
            priority=data['priority'],
            payload_type=data['payload_type'],
            rtx_payload_type=data.get('rtx_payload_type'),
            encode=data.get('encode', True),
            decode=data.get('decode', True),
        )

    def replace(self, **kwargs: Any) -> VoiceCodec:
        data: dict[str, Any] = {
            'name': self.name,
            'type': self.type,
            'priority': self.priority,
            'payload_type': self.payload_type,
            'rtx_payload_type': self.rtx_payload_type,
            'encode': self.encode,
            'decode': self.decode,
        }
        data.update(kwargs)
        name = data.pop('name')
        codec_type = data.pop('type')
        return self.__class__(name, codec_type, **data)

    def to_dict(self) -> VoiceCodecPayload:
        payload: VoiceCodecPayload = {
            'name': self.name,
            'type': self.type,
            'priority': self.priority,
            'payload_type': self.payload_type,
            # These aren't sent on audio by clients, but it doesn't matter
            'encode': self.encode,
            'decode': self.decode,
        }
        if self.rtx_payload_type is not None:
            payload['rtx_payload_type'] = self.rtx_payload_type
        return payload

    def __repr__(self) -> str:
        return f'<VoiceCodec name={self.name!r} type={self.type!r} priority={self.priority!r}>'


class VoiceStreamResolution:
    """Represents the maximum resolution for a Discord voice media stream.

    Attributes
    ----------
    type: :class:`str`
        The type of resolution. Must be either ``source`` or ``fixed``.
    width: :class:`int`
        The width of the resolution in pixels. Only applicable if ``type`` is ``fixed``.
    height: :class:`int`
        The height of the resolution in pixels. Only applicable if ``type`` is ``fixed``.
    """

    __slots__ = ('type', 'width', 'height')

    def __init__(self, *, type: Literal['source', 'fixed'], width: int = 0, height: int = 0) -> None:
        self.type: Literal['source', 'fixed'] = type
        self.width: int = width
        self.height: int = height

    def __eq__(self, other: object) -> bool:
        if isinstance(other, VoiceStreamResolution):
            return self.type == other.type and self.width == other.width and self.height == other.height
        return NotImplemented

    @classmethod
    def source(cls) -> VoiceStreamResolution:
        """A factory method for creating a source resolution.

        Returns
        --------
        :class:`VoiceStreamResolution`
             The created source resolution.
        """
        return cls(type='source', width=0, height=0)

    @classmethod
    def fixed(cls, *, width: int, height: int) -> VoiceStreamResolution:
        """A factory method for creating a fixed resolution.

        Parameters
        -----------
        width: :class:`int`
            The width of the resolution in pixels.
        height: :class:`int`
            The height of the resolution in pixels.

        Returns
        --------
        :class:`VoiceStreamResolution`
             The created fixed resolution.
        """
        return cls(type='fixed', width=width, height=height)

    @classmethod
    def from_dict(cls, data: VoiceStreamResolutionPayload) -> VoiceStreamResolution:
        return cls(
            type=data['type'],
            width=data['width'],
            height=data['height'],
        )

    def to_dict(self) -> VoiceStreamResolutionPayload:
        return {
            'type': self.type,
            'width': self.width,
            'height': self.height,
        }

    def __repr__(self) -> str:
        return f'<VoiceStreamResolution type={self.type!r} width={self.width!r} height={self.height!r}>'


class VoiceStream:
    """Represents a Discord video stream.

    Attributes
    ----------
    type: :class:`str`
        The type of the stream. Must be either ``video`` or ``screen``.
    rid: :class:`str`
        The RTP stream ID (RID) for the stream.
        Defaults to a stringified representation of the :attr:`quality`.
    quality: :class:`int`
        The quality of the stream, as an integer percentage from 1 to 100.
        Values lower than 100 represent a reduced-quality simulcast stream.
    active: :class:`bool`
        Whether the stream is active and sent by the client.
    max_bitrate: Optional[:class:`int`]
        The maximum bitrate for the stream in bits per second.
    max_framerate: Optional[:class:`int`]
        The maximum framerate for the stream in frames per second.
    max_resolution: Optional[:class:`VoiceStreamResolution`]
        The maximum resolution for the stream.
    ssrc: Optional[:class:`int`]
        The RTP SSRC for the stream.
    rtx_ssrc: Optional[:class:`int`]
        The RTP SSRC for RTX retransmissions of the stream.
    """

    __slots__ = (
        'type',
        'rid',
        'quality',
        'active',
        'max_bitrate',
        'max_framerate',
        'max_resolution',
        'ssrc',
        'rtx_ssrc',
    )

    def __init__(
        self,
        type: Literal['video', 'screen'],
        *,
        rid: str | None = None,
        quality: int = 100,
        active: bool = True,
        max_bitrate: int | None = None,
        max_framerate: int | None = None,
        max_resolution: VoiceStreamResolution | None = None,
        ssrc: int | None = None,
        rtx_ssrc: int | None = None,
    ) -> None:
        self.type: Literal['video', 'screen'] = type
        self.rid: str = str(quality) if rid is None else rid
        self.quality: int = quality
        self.active: bool = active
        self.max_bitrate: int | None = max_bitrate
        self.max_framerate: int | None = max_framerate
        self.max_resolution: VoiceStreamResolution | None = max_resolution
        self.ssrc: int | None = ssrc
        self.rtx_ssrc: int | None = rtx_ssrc

    def __eq__(self, other: object) -> bool:
        if isinstance(other, VoiceStream):
            return (
                self.type == other.type
                and self.rid == other.rid
                and self.quality == other.quality
                and self.active == other.active
                and self.max_bitrate == other.max_bitrate
                and self.max_framerate == other.max_framerate
                and self.max_resolution == other.max_resolution
                and self.ssrc == other.ssrc
                and self.rtx_ssrc == other.rtx_ssrc
            )
        return NotImplemented

    @classmethod
    def video(
        cls,
        *,
        rid: str | None = None,
        quality: int = 100,
        max_bitrate: int | None = None,
        max_framerate: int | None = None,
        max_resolution: VoiceStreamResolution | None = None,
    ) -> VoiceStream:
        """A factory method that creates a camera/self-video stream descriptor.

        Parameters
        ----------
        rid: :class:`str`
            The RTP stream ID (RID) for the stream.
            Defaults to a stringified representation of the :attr:`quality`.
        quality: :class:`int`
            The quality of the stream, as an integer percentage from 1 to 100.
            Values lower than 100 represent a reduced-quality simulcast stream.
        max_bitrate: Optional[:class:`int`]
            The maximum bitrate for the stream in bits per second.
        max_framerate: Optional[:class:`int`]
            The maximum framerate for the stream in frames per second.
        max_resolution: Optional[:class:`VoiceStreamResolution`]
            The maximum resolution for the stream.

        Returns
        -------
        :class:`VoiceStream`
            The created stream descriptor.
        """
        return cls(
            'video',
            rid=rid,
            quality=quality,
            active=True,
            max_bitrate=max_bitrate,
            max_framerate=max_framerate,
            max_resolution=max_resolution,
        )

    @classmethod
    def screen(
        cls,
        *,
        rid: str | None = None,
        quality: int = 100,
        max_bitrate: int | None = None,
        max_framerate: int | None = None,
        max_resolution: VoiceStreamResolution | None = None,
    ) -> VoiceStream:
        """A factory method that creates a Go Live screen stream descriptor.

        Parameters
        ----------
        rid: :class:`str`
            The RTP stream ID (RID) for the stream.
            Defaults to a stringified representation of the :attr:`quality`.
        quality: :class:`int`
            The quality of the stream, as an integer percentage from 1 to 100.
            Values lower than 100 represent a reduced-quality simulcast stream.
        max_bitrate: Optional[:class:`int`]
            The maximum bitrate for the stream in bits per second.
        max_framerate: Optional[:class:`int`]
            The maximum framerate for the stream in frames per second.
        max_resolution: Optional[:class:`VoiceStreamResolution`]
            The maximum resolution for the stream.

        Returns
        -------
        :class:`VoiceStream`
            The created stream descriptor.
        """
        return cls(
            'screen',
            rid=rid,
            quality=quality,
            active=True,
            max_bitrate=max_bitrate,
            max_framerate=max_framerate,
            max_resolution=max_resolution,
        )

    @classmethod
    def from_dict(cls, data: VoiceStreamPayload) -> VoiceStream:
        max_resolution = data.get('max_resolution')
        if max_resolution is not None:
            max_resolution = VoiceStreamResolution.from_dict(max_resolution)

        return cls(
            data['type'],
            rid=data['rid'],
            quality=data.get('quality', 100),
            active=data.get('active', True),
            max_bitrate=data.get('max_bitrate'),
            max_framerate=data.get('max_framerate'),
            max_resolution=max_resolution,
            ssrc=data.get('ssrc'),
            rtx_ssrc=data.get('rtx_ssrc'),
        )

    def _update(self, data: VoiceStreamPayload) -> None:
        if 'type' in data:
            self.type = data['type']
        if 'quality' in data:
            self.quality = data['quality']
        if 'active' in data:
            self.active = data['active']
        if 'max_bitrate' in data:
            self.max_bitrate = data['max_bitrate']
        if 'max_framerate' in data:
            self.max_framerate = data['max_framerate']
        if 'max_resolution' in data:
            resolution = data['max_resolution']
            self.max_resolution = None if resolution is None else VoiceStreamResolution.from_dict(resolution)
        if 'ssrc' in data:
            self.ssrc = data['ssrc']
        if 'rtx_ssrc' in data:
            self.rtx_ssrc = data['rtx_ssrc']

    def replace(self, **kwargs: Any) -> VoiceStream:
        data: dict[str, Any] = {
            'type': self.type,
            'rid': self.rid,
            'quality': self.quality,
            'active': self.active,
            'max_bitrate': self.max_bitrate,
            'max_framerate': self.max_framerate,
            'max_resolution': self.max_resolution,
            'ssrc': self.ssrc,
            'rtx_ssrc': self.rtx_ssrc,
        }
        data.update(kwargs)
        stream_type = data.pop('type')
        return self.__class__(stream_type, **data)

    def to_dict(self) -> VoiceStreamPayload:
        payload: VoiceStreamPayload = {
            'type': self.type,
            'rid': self.rid,
            'quality': self.quality,
            'active': self.active,
        }
        if self.max_bitrate is not None:
            payload['max_bitrate'] = self.max_bitrate
        if self.max_framerate is not None:
            payload['max_framerate'] = self.max_framerate
        if self.max_resolution is not None:
            payload['max_resolution'] = self.max_resolution.to_dict()
        if self.ssrc is not None:
            payload['ssrc'] = self.ssrc
        if self.rtx_ssrc is not None:
            payload['rtx_ssrc'] = self.rtx_ssrc
        return payload

    def __repr__(self) -> str:
        return f'<VoiceStream type={self.type!r} rid={self.rid!r} quality={self.quality!r}>'
