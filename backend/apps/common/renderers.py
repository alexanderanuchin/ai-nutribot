from __future__ import annotations

import json
from typing import Any

from rest_framework.renderers import BaseRenderer


class EventStreamRenderer(BaseRenderer):
    """Renderer for Server-Sent Events streams."""

    media_type = "text/event-stream"
    format = "event-stream"
    charset = "utf-8"
    render_style = "binary"

    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: dict[str, Any] | None = None,
    ) -> bytes:  # pragma: no cover - streaming bypasses rendering
        if data is None:
            return b""
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        if isinstance(data, str):
            return data.encode(self.charset or "utf-8")
        try:
            return json.dumps(data, ensure_ascii=False).encode(self.charset or "utf-8")
        except TypeError:
            return str(data).encode(self.charset or "utf-8")


__all__ = ["EventStreamRenderer"]
