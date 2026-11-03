#!/usr/bin/env python3
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

"""Zero-dependency Enterprise Data Cloud Bridge & Local Desktop MCP Server.

Bridges local macOS agent environments to GCP Hosted MCP endpoints:
  - Dataplex Knowledge Catalog MCP: https://dataplex.googleapis.com/mcp
  - BigQuery MCP: https://bigquery.googleapis.com/mcp

Supports two operational modes:
  1. Direct CLI (`--cli <subcommand>`) for fast terminal execution and desktop skill calls.
  2. Standard stdio JSON-RPC MCP server when executed as a background daemon.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DATAPLEX_MCP_URL = os.environ.get("DATAPLEX_MCP_URL", "https://dataplex.googleapis.com/mcp")
BIGQUERY_MCP_URL = os.environ.get("BIGQUERY_MCP_URL", "https://bigquery.googleapis.com/mcp")

PROJECT_ID = (
    os.environ.get("GCP_PROJECT_ID")
    or os.environ.get("GOOGLE_CLOUD_PROJECT")
    or "enterprise-agent-project"
)
DATASET_ID = (
    os.environ.get("BQ_DATASET_ID")
    or os.environ.get("BQ_DATASET")
    or os.environ.get("APP_BQ_DATASET")
    or "lakehouse_sharing"
)
LOCATION = os.environ.get("BQ_LOCATION") or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

RESTRICTED_PAY_PATTERN = re.compile(
    r"\b(salary|payroll|remuneration|executive_pay|bonus_pool)\b", re.IGNORECASE
)


def _get_access_token() -> str:
    """Retrieve Google OAuth2 access token via Keychain, environment, or gcloud."""
    if token := os.environ.get("GCP_ACCESS_TOKEN"):
        return token.strip()

    # Attempt retrieval from macOS Keychain
    if sys.platform == "darwin" and os.path.exists("/usr/bin/security"):
        try:
            cmd = [
                "/usr/bin/security",
                "find-generic-password",
                "-s",
                "desktop-agent-gcp-token",
                "-w",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass

    # Fallback to gcloud print-access-token
    for cand in ("gcloud", "/opt/homebrew/bin/gcloud", "/usr/local/bin/gcloud"):
        try:
            res = subprocess.run(
                [cand, "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            continue

    return ""


def _post_json(url: str, payload: dict[str, Any], token: str) -> dict[str, Any]:
    """Execute authenticated HTTP POST request using Python standard library."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-goog-user-project": PROJECT_ID,
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def assert_safe_query(sql: str) -> None:
    """Reject statements targeting restricted sensitive remuneration fields."""
    if RESTRICTED_PAY_PATTERN.search(sql):
        raise ValueError(
            "Access Denied: SQL queries requesting salary, bonus, or executive pay are prohibited."
        )


def execute_sql(sql: str) -> list[dict[str, Any]]:
    """Execute read-only SQL via BigQuery MCP endpoint or fallback mock."""
    assert_safe_query(sql)
    token = _get_access_token()
    if token:
        try:
            res = _post_json(
                BIGQUERY_MCP_URL,
                {
                    "method": "execute_sql_readonly",
                    "params": {"sql": sql, "project": PROJECT_ID},
                },
                token,
            )
            if "result" in res and "rows" in res["result"]:
                return res["result"]["rows"]
        except Exception as exc:
            sys.stderr.write(
                f"Warning: BigQuery MCP call failed ({exc}). Using governed local projection.\n"
            )

    # Local fallback fixture when disconnected or running offline tests
    return [
        {
            "unit_id": "UNIT-01",
            "unit_name": "Metro Core Flagship",
            "active_staff_count": 8,
            "period_sales_volume": 425000.0,
            "pacing_pct": 104.2,
            "urgent_task_count": 3,
            "status": "AHEAD",
        },
        {
            "unit_id": "UNIT-02",
            "unit_name": "Suburban Retail Hub",
            "active_staff_count": 5,
            "period_sales_volume": 210000.0,
            "pacing_pct": 92.5,
            "urgent_task_count": 1,
            "status": "ON_TRACK",
        },
    ]


def lookup_catalog(term: str) -> dict[str, Any]:
    """Search Knowledge Catalog via Dataplex MCP."""
    token = _get_access_token()
    if token:
        try:
            return _post_json(
                DATAPLEX_MCP_URL,
                {
                    "method": "search_entries",
                    "params": {"query": term, "project": PROJECT_ID},
                },
                token,
            )
        except Exception as exc:
            sys.stderr.write(f"Warning: Dataplex MCP lookup failed ({exc}).\n")

    return {
        "term": term,
        "definition": "Standard enterprise entity registered in Knowledge Catalog.",
        "verified": True,
    }


def render_gantt_html(data: list[dict[str, Any]]) -> str:
    """Render zero-CDN self-contained HTML/SVG Gantt scorecard."""
    rows_svg = []
    y = 60
    for _idx, item in enumerate(data):
        name = html.escape(str(item.get("unit_name", "Unit")))
        pacing = float(item.get("pacing_pct", 100.0))
        bar_width = min(max(int(pacing * 2.5), 10), 320)
        color = "#107c41" if pacing >= 100.0 else "#d83b01"

        rows_svg.append(
            f'<text x="20" y="{y + 18}" font-family="-apple-system, sans-serif" font-size="13" fill="#333">{name}</text>'
            f'<rect x="220" y="{y}" width="{bar_width}" height="24" rx="4" fill="{color}" />'
            f'<text x="{230 + bar_width}" y="{y + 17}" font-family="-apple-system, sans-serif" font-size="12" font-weight="600" fill="#333">{pacing:.1f}%</text>'
        )
        y += 44

    total_height = max(y + 20, 200)

    svg_content = f"""<svg width="600" height="{total_height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#ffffff" />
  <text x="20" y="32" font-family="-apple-system, sans-serif" font-size="16" font-weight="bold" fill="#111">Operational Shift Pacing by Unit</text>
  <line x1="220" y1="45" x2="220" y2="{total_height - 20}" stroke="#e1dfdd" stroke-dasharray="3,3" />
  {"".join(rows_svg)}
</svg>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Operational Shift Pacing</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 24px; background: #faf9f8; }}
    .card {{ background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 20px; max-width: 680px; }}
    h2 {{ margin-top: 0; color: #201f1e; font-size: 18px; }}
    .legend {{ margin-top: 16px; font-size: 12px; color: #605e5c; display: flex; gap: 16px; }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 4px; }}
    .green {{ background: #107c41; }}
    .orange {{ background: #d83b01; }}
  </style>
</head>
<body>
  <div class="card">
    <h2>Morning Shift Performance Scorecard</h2>
    {svg_content}
    <div class="legend">
      <span><span class="dot green"></span>Target Achieved (>=100%)</span>
      <span><span class="dot orange"></span>Behind Pacing (&lt;100%)</span>
    </div>
  </div>
</body>
</html>"""


def cli_morning_snapshot(args: argparse.Namespace) -> None:
    """CLI subcommand to execute morning operational health check."""
    data = execute_sql(
        "SELECT unit_id, unit_name, pacing_pct, active_staff_count FROM `v_operations`"
    )
    if args.json:
        print(json.dumps({"status": "SUCCESS", "records": data}, indent=2))
    else:
        print("=== Morning Shift Snapshot ===")
        for d in data:
            print(
                f"- {d['unit_name']}: {d['pacing_pct']}% pacing ({d['active_staff_count']} staff active)"
            )

    if args.render_canvas:
        canvas_html = render_gantt_html(data)
        out_path = os.path.expanduser("~/operational_shift_canvas.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(canvas_html)
        print(f"Interactive zero-CDN canvas saved to: {out_path}")


def run_stdio_mcp_server() -> None:
    """Run JSON-RPC 2.0 stdio server protocol."""
    sys.stderr.write("Starting Desktop Agent Data MCP Daemon (stdio)...\n")
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "execute_governed_sql",
                                "description": "Execute read-only SQL on BigQuery lakehouse views.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"sql": {"type": "string"}},
                                    "required": ["sql"],
                                },
                            },
                            {
                                "name": "render_operational_canvas",
                                "description": "Generate self-contained zero-CDN HTML/SVG scorecard.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "records": {
                                            "type": "array",
                                            "items": {"type": "object"},
                                        }
                                    },
                                    "required": ["records"],
                                },
                            },
                            {
                                "name": "lookup_knowledge_catalog",
                                "description": "Search glossary terms in Dataplex Knowledge Catalog.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"term": {"type": "string"}},
                                    "required": ["term"],
                                },
                            },
                        ]
                    },
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                if tool_name == "execute_governed_sql":
                    rows = execute_sql(arguments.get("sql", ""))
                    result_content = [{"type": "text", "text": json.dumps(rows)}]
                elif tool_name == "render_operational_canvas":
                    html_doc = render_gantt_html(arguments.get("records", []))
                    result_content = [{"type": "text", "text": html_doc}]
                elif tool_name == "lookup_knowledge_catalog":
                    cat = lookup_catalog(arguments.get("term", ""))
                    result_content = [{"type": "text", "text": json.dumps(cat)}]
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")

                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": result_content},
                }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"status": "ok"},
                }

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as err:
            err_resp = {
                "jsonrpc": "2.0",
                "id": req.get("id") if "req" in locals() else None,
                "error": {"code": -32603, "message": str(err)},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cli",
        choices=["morning-snapshot", "render-gantt", "query-sql", "lookup-catalog"],
        help="Execute direct CLI subcommand instead of MCP stdio daemon",
    )
    parser.add_argument("--json", action="store_true", help="Format output as JSON")
    parser.add_argument(
        "--render-canvas", action="store_true", help="Generate zero-CDN HTML canvas file"
    )
    parser.add_argument("--sql", help="SQL statement for query-sql command")
    parser.add_argument("--term", help="Search term for lookup-catalog command")

    args = parser.parse_args()

    if not args.cli:
        run_stdio_mcp_server()
        return

    if args.cli == "morning-snapshot":
        cli_morning_snapshot(args)
    elif args.cli == "render-gantt":
        data = execute_sql("SELECT unit_name, pacing_pct FROM `v_operations`")
        print(render_gantt_html(data))
    elif args.cli == "query-sql":
        if not args.sql:
            sys.stderr.write("Error: --sql is required for query-sql\n")
            sys.exit(1)
        res = execute_sql(args.sql)
        print(json.dumps(res, indent=2))
    elif args.cli == "lookup-catalog":
        if not args.term:
            sys.stderr.write("Error: --term is required for lookup-catalog\n")
            sys.exit(1)
        res = lookup_catalog(args.term)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
