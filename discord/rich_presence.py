from __future__ import annotations

import time
import datetime
from typing import Dict, List, Optional

from .http import Route


class RichPresence:
    """
    @mikasa: A builder for rich presence activities.

    Supports:
      - application_id (required for proper rich presence)
      - name, type, url, state, details
      - timestamps (start/end or duration)
      - assets (large/small image + text + URL)
      - buttons
    """

    __slots__ = (
        "application_id",
        "name",
        "type",
        "url",
        "state",
        "details",
        "start",
        "end",
        "large_image",
        "large_text",
        "large_url",
        "small_image",
        "small_text",
        "small_url",
        "buttons",
        "metadata"
    )

    def __init__(
        self,
        *,
        application_id: Optional[int] = None,
        name: str = "",
        type: int = 0,
        url: Optional[str] = None,
        state: Optional[str] = None,
        details: Optional[str] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        large_image: Optional[str] = None,
        large_text: Optional[str] = None,
        large_url: Optional[str] = None,
        small_image: Optional[str] = None,
        small_text: Optional[str] = None,
        small_url: Optional[str] = None,
        buttons: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        self.application_id: Optional[int] = application_id

        self.name: str = name
        self.type: int = type
        self.url: Optional[str] = url
        self.state: Optional[str] = state
        self.details: Optional[str] = details

        # unix ms timestamps
        self.start: Optional[int] = start
        self.end: Optional[int] = end

        # assets (keys or mp:/external_asset_path values)
        self.large_image: Optional[str] = large_image
        self.large_text: Optional[str] = large_text
        self.large_url: Optional[str] = large_url
        self.small_image: Optional[str] = small_image
        self.small_text: Optional[str] = small_text
        self.small_url: Optional[str] = small_url

        self.buttons: List[str] = []
        self.metadata: Dict[str, Any] = {}

        if buttons:
            for b in buttons:
                label = b.get("label") or b.get("name")
                url_val = b.get("url")
                if label and url_val:
                    self.add_button(label, url_val)

    # ---------- Builder helpers ----------

    def set_application_id(self, app_id: int) -> "RichPresence":
        self.application_id = app_id
        return self

    def set_name(self, name: str) -> "RichPresence":
        self.name = name
        return self

    def set_type(self, t: int) -> "RichPresence":
        self.type = t
        return self

    def set_state(self, state: str) -> "RichPresence":
        self.state = state
        return self

    def set_details(self, details: str) -> "RichPresence":
        self.details = details
        return self

    def set_url(self, url: str) -> "RichPresence":
        self.url = url
        return self

    def set_start_timestamp(self, start_ms: Optional[int] = None) -> "RichPresence":
        if start_ms is None:
            start_ms = int(time.time() * 1000)
        self.start = start_ms
        return self

    def set_end_timestamp(self, end_ms: int) -> "RichPresence":
        self.end = end_ms
        return self

    def set_duration(self, seconds: int) -> "RichPresence":
        now_ms = int(time.time() * 1000)
        self.start = now_ms
        self.end = now_ms + seconds * 1000
        return self

    def set_assets_large_image(self, key: str) -> "RichPresence":
        self.large_image = key
        return self

    def set_assets_large_text(self, text: str) -> "RichPresence":
        self.large_text = text
        return self

    def set_assets_large_url(self, url: str) -> "RichPresence":
        """
        URL that should open when clicking the large image.
        """
        self.large_url = url
        return self

    def set_assets_small_image(self, key: str) -> "RichPresence":
        self.small_image = key
        return self

    def set_assets_small_text(self, text: str) -> "RichPresence":
        self.small_text = text
        return self

    def set_assets_small_url(self, url: str) -> "RichPresence":
        """
        URL that should open when clicking the small image.
        """
        self.small_url = url
        return self

    def add_button(self, name: str, url: str) -> "RichPresence":
        """
        Add a single button.
        - up to 2 buttons
        - names go to .buttons
        - URLs go to metadata['button_urls']
        """
        if not name or not url:
            raise ValueError("Button must have name and url")
        if len(self.buttons) >= 2:
            raise ValueError("RichPresence can only have up to 2 buttons")

        self.buttons.append(name)

        urls = self.metadata.get("button_urls")
        if isinstance(urls, list):
            urls.append(url)
        else:
            self.metadata["button_urls"] = [url]

        return self

    def set_buttons(self, *buttons: Dict[str, str]) -> "RichPresence":
        """
        Set/replace buttons from a list of {name,label,url} dicts.
        Accepts at most 2.
        """
        flat = []
        for b in buttons:
            if isinstance(b, (list, tuple)):
                flat.extend(b)
            else:
                flat.append(b)

        if len(flat) > 2:
            raise ValueError("RichPresence can only have up to 2 buttons")

        self.buttons.clear()
        self.metadata.pop("button_urls", None)

        for b in flat:
            name = b.get("name") or b.get("label")
            url = b.get("url")
            if not name or not url:
                raise ValueError("Each button must have name/label and url")
            self.add_button(name, url)

        return self


    # ---------- Conversion to gateway activity dict ----------

    def _to_unix_ms(self, value):
        """Convert datetime/float/int to Unix ms, or None."""
        if value is None:
            return None

        # already ms
        if isinstance(value, int):
            return value

        # seconds as float
        if isinstance(value, float):
            return int(value * 1000)

        # datetime -> ms
        if isinstance(value, datetime.datetime):
            # assume UTC if naive
            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.timezone.utc)
            return int(value.timestamp() * 1000)

        raise TypeError(f"Unsupported timestamp type: {type(value)!r}")

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "name": self.name,
            "type": self.type,
        }

        if self.application_id is not None:
            data["application_id"] = str(self.application_id)

        if self.url:
            data["url"] = self.url
        if self.state:
            data["state"] = self.state
        if self.details:
            data["details"] = self.details

        # ----- timestamps -----
        start_ms = self._to_unix_ms(self.start)
        end_ms = self._to_unix_ms(self.end)
        if start_ms is not None or end_ms is not None:
            ts: Dict[str, int] = {}
            if start_ms is not None:
                ts["start"] = start_ms
            if end_ms is not None:
                ts["end"] = end_ms
            data["timestamps"] = ts

        # ----- assets -----
        assets: Dict[str, Any] = {}
        if self.large_image:
            assets["large_image"] = self.large_image
        if self.large_text:
            assets["large_text"] = self.large_text
        if self.large_url:
            assets["large_url"] = self.large_url
        if self.small_image:
            assets["small_image"] = self.small_image
        if self.small_text:
            assets["small_text"] = self.small_text
        if self.small_url:
            assets["small_url"] = self.small_url
        if assets:
            data["assets"] = assets

        # ----- buttons + metadata.button_urls -----
        if self.buttons:
            data["buttons"] = list(self.buttons)
            # merge any existing metadata (e.g. future secrets) with button_urls
            md = dict(self.metadata) if self.metadata else {}
            urls = md.get("button_urls")
            if not isinstance(urls, list) or len(urls) != len(self.buttons):
                # ensure same length & alignment
                md["button_urls"] = self.metadata.get("button_urls", [])[: len(self.buttons)]
                # if lengths mismatch, best to rebuild from scratch:
                if len(md["button_urls"]) != len(self.buttons):
                    md["button_urls"] = []
                    # we don't actually have the URLs here if you didn't add via add_button,
                    # but in your own usage you'll always use add_button / set_buttons.
            data["metadata"] = md
        elif self.metadata:
            # no buttons, but metadata in use
            data["metadata"] = dict(self.metadata)

        return data

async def get_external_assets(client, application_id: int, *urls: str) -> List[str]:
    """
    Calls POST /applications/{id}/external-assets and returns a list of
    keys suitable for use as assets.large_image / assets.small_image.

    The endpoint returns external_asset_path values like "external/...",
    but the Rich Presence payload expects them prefixed with "mp:".

    So:
      external_asset_path="external/abc"
      -> "mp:external/abc"
    """
    route = Route(
        "POST",
        "/applications/{application_id}/external-assets",
        application_id=application_id,
    )
    payload = {"urls": list(urls)}

    data = await client.http.request(route, json=payload)
    paths: List[str] = []

    if isinstance(data, list):
        for item in data:
            raw = item.get("external_asset_path")
            if not raw:
                continue

            # ensure it has the mp: prefix exactly once
            if raw.startswith("mp:"):
                key = raw
            else:
                key = "mp:" + raw

            paths.append(key)

    return paths

