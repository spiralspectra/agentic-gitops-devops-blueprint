# Copyright 2026 The Project Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Signed A2UI WebFrameUrl launcher and self-contained inline HTML/SVG scorecard builder."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import urllib.parse
from typing import Any

from app.core.config import A2UI_IFRAME_BASE_URL

# Key used for HMAC signing of embedded WebFrame state
_HMAC_SECRET = os.getenv("A2UI_HMAC_SECRET", "default-insecure-dev-hmac-key").encode(
    "utf-8"
)


def build_a2ui_webframe_url(
    view: str,
    params: dict[str, Any] | None = None,
    height: int = 760,
) -> dict[str, Any]:
    """Generates an allowlisted, cryptographically-signed A2UI WebFrameUrl payload.

    Args:
        view: Target view or dashboard mode (e.g. 'operations_overview', 'catalog_explorer', 'studio').
        params: Key-value parameters passed to the embedded interface.
        height: Display container height in pixels.

    Returns:
        Dictionary conforming to the Gemini Enterprise A2UI WebFrameUrl schema:
        {"url": {"literalString": "https://...#state=...&sig=..."}, "height": height}
    """
    safe_params = params or {}
    state_json = json.dumps(
        {"view": view, "params": safe_params}, separators=(",", ":"), sort_keys=True
    )
    state_b64 = (
        base64.urlsafe_b64encode(state_json.encode("utf-8")).decode("utf-8").rstrip("=")
    )

    signature = hmac.new(
        _HMAC_SECRET, state_b64.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    encoded_view = urllib.parse.quote(view)
    full_url = (
        f"{A2UI_IFRAME_BASE_URL}/?view={encoded_view}#state={state_b64}&sig={signature}"
    )

    return {
        "url": {"literalString": full_url},
        "height": height,
        "view": view,
        "state_signature": signature,
    }


def build_inline_scorecard_svg(
    title: str,
    kpi_metric: str,
    kpi_label: str,
    trend_pct: float,
    status: str = "healthy",
    sparkline_points: list[float] | None = None,
) -> str:
    """Builds a self-contained SVG scorecard with metrics, trend badge, and sparkline.

    Args:
        title: Title of the scorecard block.
        kpi_metric: Main display metric string (e.g., "$1.24M", "99.98%").
        kpi_label: Secondary context label.
        trend_pct: Percentage change (+5.2 or -1.4).
        status: Status badge ('healthy', 'warning', 'critical').
        sparkline_points: Array of numeric values to render a sparkline path.

    Returns:
        Self-contained SVG XML string.
    """
    status_colors = {
        "healthy": "#10b981",  # Emerald
        "warning": "#f59e0b",  # Amber
        "critical": "#ef4444",  # Red
    }
    status_color = status_colors.get(status.lower(), "#3b82f6")

    trend_sign = "+" if trend_pct >= 0 else ""
    trend_color = "#10b981" if trend_pct >= 0 else "#ef4444"

    # Generate sparkline SVG path
    points = sparkline_points or [10, 15, 12, 18, 22, 20, 26, 30]
    min_val = min(points)
    max_val = max(points) if max(points) != min(points) else min_val + 1
    width = 160
    height = 40
    step = width / max(1, len(points) - 1)

    path_coords = []
    for i, val in enumerate(points):
        x = i * step
        y = height - ((val - min_val) / (max_val - min_val) * (height - 8) + 4)
        path_coords.append(f"{x:.1f},{y:.1f}")

    sparkline_d = "M " + " L ".join(path_coords)

    svg = f"""<svg width="340" height="150" viewBox="0 0 340 150" fill="none" xmlns="http://www.w3.org/2000/svg" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <rect width="340" height="150" rx="12" fill="#18181B" stroke="#27272A" stroke-width="1.5"/>
  <circle cx="24" cy="28" r="5" fill="{status_color}"/>
  <text x="36" y="32" fill="#A1A1AA" font-size="13" font-weight="500">{title}</text>

  <text x="24" y="78" fill="#FAFAFA" font-size="28" font-weight="700">{kpi_metric}</text>
  <text x="24" y="98" fill="#71717A" font-size="12">{kpi_label}</text>

  <rect x="24" y="112" width="70" height="22" rx="6" fill="#27272A"/>
  <text x="32" y="127" fill="{trend_color}" font-size="11" font-weight="600">{trend_sign}{trend_pct:.1f}%</text>

  <g transform="translate(156, 92)">
    <path d="{sparkline_d}" fill="none" stroke="{status_color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</svg>"""
    return svg
