#!/usr/bin/env python3
"""Build the Desktop Agent Extension (Spark) macOS Local Productivity architecture diagram (SVG + optional PNG).

Shows how the desktop application on macOS interfaces with:
  - Channel A: Federated Enterprise Connectors (Mail, Drive, Intranet, Teams/Slack) via loopback MCP.
  - Channel B: Hosted Google Cloud MCP endpoints for Knowledge Catalog (https://dataplex.googleapis.com/mcp)
    and BigQuery (https://bigquery.googleapis.com/mcp) via the desktop skill CLI and isolated OAuth ADC.

Usage:
  python3 docs/architecture/build_desktop_spark_diagram.py [--png] [--cache DIR] [--out docs/architecture]
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_architecture_diagram import (
    MATERIAL,
    MUTED,
    Assets,
    Canvas,
    to_png,
)


def badge(c: Canvas, x: int, y: int, label: str, bg: str, fg: str = "#FFFFFF") -> None:
    w = max(24, 12 + int(6.6 * len(label)))
    c.rect(x, y, w, 18, bg, None, rx=9)
    c.text(x + w / 2, y + 13, label, 10, 700, fg, anchor="middle")


def build(assets: Assets) -> str:
    c = Canvas(1880, 990, assets)
    si = assets.simple_icon_path

    # ---- header --------------------------------------------------------------------------------
    c.brand_logo(28, 20, 126, 40)
    c.text(
        180,
        42,
        "Archetype 4: macOS Desktop Agent Extension (Spark) — Governed MCP & Local Productivity Architecture",
        20,
        500,
    )
    c.text(
        180,
        64,
        "Seatbelt Sandbox + macOS Keychain  ·  Federated SaaS Connectors  ·  "
        "Hosted Google Cloud MCP (Dataplex Knowledge Catalog & BigQuery)  ·  Zero-CDN HTML Canvas",
        12,
        400,
        MUTED,
    )

    # ============================================================================================
    # COLUMN 1: MACOS DESKTOP — DESKTOP SPARK EXTENSION
    # ============================================================================================
    c.zone(
        28,
        88,
        510,
        788,
        "macOS · Desktop Agent Extension",
        "blue",
        subtitle="Spark · ~/spark_workspace",
        mark=(si("apple"), "#202124"),
        subtitle_right=True,
    )

    # 1A: Desktop User Persona & Surfaces
    c.card(
        44,
        130,
        478,
        None,
        "Enterprise Persona & Desktop Workspace",
        [
            "Identity: user@example.com (Entitled Role / Department)",
            "Automated scheduled routines (daily operational briefings & tasks)",
            "Interactive zero-CDN HTML Canvas Gantt & flowchart renderer",
            "Seatbelt sandbox.json: enabled = true, allow_network = true",
        ],
        mark=si("googlegemini"),
        mark_grad="gemini",
        h=108,
    )
    badge(c, 454, 138, "SPARK UI", "#1967D2")

    # 1B: Channel A — Federated Enterprise Connector Client
    c.card(
        44,
        262,
        478,
        "cloud_api_gateway",
        "Channel A — Federated SaaS Connector Client",
        [
            "Built-in skill: enterprise-connectors (loopback MCP gateway)",
            "In-app OAuth cookie partition (persist:connector-oauth)",
            "Federated search & actions across Mail, Calendar, Drive & Chat",
            "Extracts operational context and action items into local state",
        ],
        h=108,
    )
    badge(c, 444, 270, "CHANNEL A", "#1967D2")

    # 1C: Channel B — Governed Data Cloud Skill & MCP CLI
    c.card(
        44,
        446,
        478,
        None,
        "Channel B — Governed Data Cloud Skill & MCP Bridge",
        [
            "skills/desktop-huddle/SKILL.md -> desktop_data_mcp_cli.py",
            "Commands: --cli morning-snapshot · search-catalog · query-bq-mcp",
            "Grounds on Dataplex Business Glossary & Spanner Property Graph",
            "Blocks sensitive columns & raw PII tables (fail-closed guardrail)",
            "Human confirmation gate required before publishing external updates",
        ],
        mark=si("python"),
        mark_fill="#3776AB",
        h=142,
    )
    badge(c, 444, 454, "CHANNEL B", "#137333")

    # 1D: macOS Keychain Credential Store
    c.card(
        44,
        626,
        478,
        "identity_and_access_management",
        "macOS Keychain Credential Store (Zero Workspace Secrets)",
        [
            "Keychain services: desktop-agent-gcp-adc & desktop-agent-saas-oauth",
            "Exchanges OAuth2 refresh_token -> short-lived Bearer tokens in RAM",
            "No plaintext API keys or credentials stored on disk or git",
        ],
        h=84,
    )

    # 1E: Desktop Installer & Verification
    c.card(
        44,
        730,
        478,
        None,
        "Desktop Installer & Sandbox Configuration",
        [
            "install_on_mac.sh (purges legacy tokens, configures Seatbelt sandbox)",
            "verify_desktop_env.py (checks ADC, Keychain items & MCP liveness)",
        ],
        mark=MATERIAL["terminal"],
        mark_fill="#5F6368",
        h=82,
        dash="6 4",
    )

    c.chips(
        44,
        828,
        [
            ("security", "Seatbelt + Keychain"),
            ("security", "Fail-Closed Guardrail"),
            ("bigquery", "4-Tier RLS"),
        ],
    )

    # Internal macOS vertical arrows
    c.arrow([(283, 238), (283, 262)])
    c.arrow([(44, 206), (35, 206), (35, 496), (44, 496)])
    c.arrow([(283, 626), (283, 588)], "Bearer token", lx=292, ly=611, anchor="start")

    # ============================================================================================
    # COLUMN 2: GOOGLE CLOUD PLATFORM — GOVERNED MCP SERVICES
    # ============================================================================================
    c.zone(
        670,
        88,
        610,
        788,
        "Google Cloud Platform (Host Runtime)",
        "grey",
        subtitle="Least-Privilege IAM · Hosted MCP Endpoints",
        icon="cloud_generic",
    )

    # 2A: Gemini Enterprise & Connector Gateway
    c.zone(
        686,
        130,
        578,
        214,
        "Gemini Enterprise & Federated Connector Gateway",
        "blue",
        subtitle="global",
        subtitle_right=True,
    )
    c.card(
        702,
        166,
        546,
        None,
        "Gemini Enterprise Engine & Workspace Integration",
        [
            "Gemini Enterprise App Engine · Desktop Widget & Extensions",
            "Discovery Engine Federated Search + BAP Actions Gateway (OAuth/PKCE)",
            "Active Enterprise Data Connectors: Email, Cloud Drive, Docs, Chat",
        ],
        mark=si("googlegemini"),
        mark_grad="gemini",
        h=96,
    )
    c.card(
        702,
        272,
        546,
        "vertexai",
        "Vertex AI Agent Engine (Cloud Orchestrator Parity)",
        [
            "Shared Cloud Agent Engine (agents/starter_agent/) · Web & A2A Parity",
        ],
        h=58,
        dash="4 3",
    )

    # 2B: Hosted Dataplex Knowledge Catalog MCP
    c.zone(
        686,
        362,
        578,
        212,
        "Google Cloud Knowledge Catalog (Dataplex MCP)",
        "green",
        subtitle="Hosted MCP · dataplex.googleapis.com/mcp",
        subtitle_right=True,
    )
    c.card(
        702,
        398,
        546,
        "dataplex",
        "Hosted Knowledge Catalog MCP Endpoint",
        [
            "MCP tools: get_glossary · search_entries · lookup_context",
            "Governed Business Glossary: metric definitions, business terms",
            "AspectTypes (OSI+G) & Context Graph EntryLinks for semantic relations",
            "Grounds agent queries before SQL generation to eliminate hallucinations",
        ],
        h=112,
    )
    c.chips(
        702,
        522,
        [
            ("identity_and_access_management", "roles/dataplex.catalogViewer"),
            ("identity_and_access_management", "roles/mcp.toolUser"),
        ],
    )

    # 2C: Hosted BigQuery MCP
    c.zone(
        686,
        592,
        578,
        268,
        "Google Cloud BigQuery Lakehouse (BigQuery MCP)",
        "purple",
        subtitle="Hosted MCP · bigquery.googleapis.com/mcp",
        subtitle_right=True,
    )
    c.card(
        702,
        628,
        546,
        "bigquery",
        "Hosted BigQuery MCP Endpoint",
        [
            "MCP tools: execute_sql_readonly · get_table_info · list_table_ids",
            "5 Governed Authorized Views with 4-Tier SESSION_USER() RLS",
            "SELECT-only dry-run enforcement with 5 GiB maximum bytes billed cap",
            "Spanner Property Graph (GQL) for recursive semantic entity traversal",
            "Raw underlying PII tables completely hidden from agent identity",
        ],
        h=130,
    )
    c.chips(
        702,
        772,
        [
            ("identity_and_access_management", "roles/bigquery.jobUser"),
            ("identity_and_access_management", "Authorized Views"),
            ("workload_identity_pool", "4-Tier SESSION_USER() RLS"),
        ],
    )
    c.text(
        702,
        842,
        "All BigQuery jobs audited in INFORMATION_SCHEMA.JOBS_BY_PROJECT with caller identity",
        11,
        400,
        MUTED,
    )

    # Governance link: Knowledge Catalog -> BigQuery
    c.arrow([(975, 574), (975, 592)], dash="3 3")

    # ============================================================================================
    # COLUMN 3: FEDERATED ENTERPRISE SAAS TENANT
    # ============================================================================================
    c.zone(
        1410,
        88,
        442,
        788,
        "Federated Enterprise SaaS Tenant",
        "white",
        subtitle="SaaS & Collaboration Services",
        mark=(si("microsoft"), "#0078D4"),
        subtitle_right=True,
    )

    # 3A: Email & Calendar
    c.card(
        1426,
        130,
        410,
        None,
        "Corporate Email & Calendar Service",
        [
            "Federated connector with search & draft actions",
            "Priority triage: schedule changes, urgent customer inquiries",
            "Meeting schedule parsing & morning calendar agenda sync",
            "Draft reply generation with grounding context from lakehouse",
        ],
        mark=si("microsoftoutlook"),
        mark_fill="#0078D4",
        h=112,
    )

    # 3B: Cloud Drive & Spreadsheets
    c.card(
        1426,
        262,
        410,
        None,
        "Enterprise Cloud Storage & Sheets",
        [
            "Federated connector for cloud office documents",
            "Operational performance trackers & targets spreadsheet",
            "Reconciles local spreadsheet values against governed BigQuery data",
        ],
        mark=si("microsoftonedrive"),
        mark_fill="#0078D4",
        h=96,
    )

    # 3C: Corporate Intranet & Knowledge Base
    c.card(
        1426,
        378,
        410,
        None,
        "Enterprise Intranet & Policy Repositories",
        [
            "Federated connector indexing internal portal sites",
            "Standard Operating Procedures (SOPs) & regulatory guidelines",
            "Grounds operational recommendations in official company policy",
        ],
        mark=si("microsoftsharepoint"),
        mark_fill="#038387",
        h=112,
    )

    # 3D: Team Chat & Collaboration
    c.card(
        1426,
        510,
        410,
        None,
        "Team Messaging & Collaboration Service",
        [
            "Federated connector with proactive channel messaging",
            "Morning standup summary draft posted upon explicit user confirmation",
            "Team channel incident notifications and critical status alerts",
        ],
        mark=si("microsoftteams"),
        mark_fill="#6264A7",
        h=112,
    )

    # ============================================================================================
    # CROSS-ZONE CONNECTION ARROWS
    # ============================================================================================
    # Col 1 (Spark UI) -> Col 2 (GE Engine)
    c.arrow(
        [(522, 178), (702, 178)],
        "Desktop sync",
        "OAuth Bearer",
        color="#1967D2",
    )

    # Col 1 (Channel A) -> Col 2 (Connector Gateway)
    c.arrow(
        [(522, 310), (702, 230)],
        "Federated queries",
        "Loopback MCP",
        color="#1967D2",
    )

    # Col 2 (Connector Gateway) -> Col 3 (SaaS Connectors)
    c.arrow(
        [(1248, 186), (1426, 186)],
        "Email & Calendar sync",
        color="#0078D4",
    )
    c.arrow(
        [(1248, 206), (1426, 310)],
        "Docs & Sheets sync",
        color="#0078D4",
    )
    c.arrow(
        [(1248, 226), (1426, 434)],
        "Intranet search",
        color="#038387",
    )
    c.arrow(
        [(1248, 246), (1426, 566)],
        "Team Chat post",
        "confirmed=True",
        color="#6264A7",
    )

    # Col 1 (Channel B) -> Col 2 (Hosted Dataplex MCP)
    c.arrow(
        [(522, 490), (702, 450)],
        "dataplex.googleapis.com/mcp",
        "Glossary & AspectTypes",
        color="#137333",
    )

    # Col 1 (Channel B) -> Col 2 (Hosted BigQuery MCP)
    c.arrow(
        [(522, 530), (702, 690)],
        "bigquery.googleapis.com/mcp",
        "4-Tier SESSION_USER() RLS",
        color="#7627BB",
    )

    # Footer
    c.text(
        30,
        965,
        "macOS Desktop Agent Extension (Spark): local Seatbelt sandbox and macOS Keychain protect host credentials; "
        "Channel A queries enterprise SaaS connectors; Channel B routes through hosted Google Cloud MCP endpoints with fail-closed RLS.",
        11,
        400,
        MUTED,
    )
    c.text(
        30,
        985,
        "Official Google Cloud product icons (cloud.google.com/icons). "
        "Regenerate with docs/architecture/build_desktop_spark_diagram.py.",
        10.5,
        400,
        "#80868B",
    )
    return c.render()


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--cache", default=str(pathlib.Path.home() / ".cache" / "blueprint-arch-diagram")
    )
    ap.add_argument("--out", default=str(pathlib.Path(__file__).parent))
    ap.add_argument(
        "--png",
        action="store_true",
        help="also write desktop-spark-architecture.png (2x) via headless Chrome",
    )
    args = ap.parse_args()

    assets = Assets(pathlib.Path(args.cache))
    svg = build(assets)
    out = pathlib.Path(args.out)
    svg_path = out / "desktop-spark-architecture.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print(f"wrote {svg_path} ({svg_path.stat().st_size // 1024} KB)")
    if args.png:
        m = re.search(r'width="(\d+)" height="(\d+)"', svg)
        png_path = out / "desktop-spark-architecture.png"
        if to_png(svg_path, png_path, int(m.group(1)), int(m.group(2))):
            print(f"wrote {png_path} ({png_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
