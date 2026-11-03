#!/usr/bin/env python3
"""Build the deployed-architecture diagram (SVG, optionally PNG) with official Google Cloud icons.

Output: docs/architecture/gcp-architecture.svg (+ .png with --png, uses Google Chrome or Chromium).

Standard library only. On first run it downloads, into --cache (default ~/.cache/blueprint-arch-diagram):
  * Google Cloud official product icons  https://cloud.google.com/static/icons/files/google-cloud-icons.zip
    (usage per https://cloud.google.com/icons - architecture diagrams referring to Google Cloud products)
  * Simple Icons brand marks (CC0)        https://cdn.jsdelivr.net/npm/simple-icons@13/icons/<name>.svg
  * Roboto (OFL, latin subset)            https://fonts.googleapis.com/css2?family=Roboto

Usage:
  python3 docs/architecture/build_architecture_diagram.py [--png] [--cache DIR] [--out docs/architecture]
"""

from __future__ import annotations

import argparse
import base64
import io
import pathlib
import re
import shutil
import ssl
import subprocess
import sys
import urllib.request
import zipfile

ICON_ZIP = "https://cloud.google.com/static/icons/files/google-cloud-icons.zip"
SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@13/icons/{name}.svg"
ROBOTO_CSS = "https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# Google Cloud architecture-diagram palette
PALETTE = {
    "grey": ("#F1F3F4", "#DADCE0", "#3C4043"),
    "blue": ("#E8F0FE", "#D2E3FC", "#1967D2"),
    "yellow": ("#FEF7E0", "#FEEFC3", "#B06000"),
    "green": ("#E6F4EA", "#CEEAD6", "#137333"),
    "purple": ("#F3E8FD", "#E9D2FD", "#7627BB"),
    "white": ("#FFFFFF", "#DADCE0", "#3C4043"),
}
INK = "#202124"
MUTED = "#5F6368"
LINE = "#5F6368"
FONT = "Roboto, 'Helvetica Neue', Arial, sans-serif"

# Material Design icon paths (Apache 2.0)
MATERIAL = {
    "groups": "M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z",
    "web_asset": "M19 4H5c-1.11 0-2 .9-2 2v12c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.89-2-2-2zm0 14H5V8h14v10z",
    "storage": "M2 20h20v-4H2v4zm2-3h2v2H4v-2zM2 4v4h20V4H2zm4 3H4V5h2v2zm-4 7h20v-4H2v4zm2-3h2v2H4v-2z",
    "terminal": "M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V8h16v10zm-2-1h-6v-2h6v2zM7.5 17l-1.41-1.41L8.67 13l-2.59-2.59L7.5 9l4 4-4 4z",
}


class Assets:
    def __init__(self, cache: pathlib.Path):
        self.cache = cache
        cache.mkdir(parents=True, exist_ok=True)
        self._zip = None
        self._ssl_ctx = ssl._create_unverified_context()

    def _get(self, url: str, name: str) -> bytes:
        path = self.cache / name
        if not path.exists():
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=120) as r:
                path.write_bytes(r.read())
        return path.read_bytes()

    def gcp_icon(self, key: str) -> str:
        """Official product icon as an isolated data URI."""
        if self._zip is None:
            self._zip = zipfile.ZipFile(io.BytesIO(self._get(ICON_ZIP, "google-cloud-icons.zip")))
        svg = self._zip.read(f"{key}/{key}.svg")
        return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()

    def simple_icon_path(self, name: str) -> str:
        try:
            svg = self._get(SIMPLE_ICONS.format(name=name), f"si-{name}.svg").decode()
        except urllib.error.HTTPError:
            alt_url = f"https://cdn.jsdelivr.net/npm/simple-icons@11/icons/{name}.svg"
            svg = self._get(alt_url, f"si-{name}.svg").decode()
        return re.search(r' d="([^"]+)"', svg).group(1)

    def roboto_face(self) -> str:
        css = self._get(ROBOTO_CSS, "roboto.css").decode()
        url = re.search(r"/\* latin \*/\s*@font-face \{.*?url\((\S+?)\)", css, re.S).group(1)
        woff2 = self._get(url, "roboto-latin.woff2")
        b64 = base64.b64encode(woff2).decode()
        return (
            "@font-face{font-family:'Roboto';font-style:normal;font-weight:100 900;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
        )


class Canvas:
    def __init__(self, w: int, h: int, assets: Assets):
        self.w, self.h, self.a = w, h, assets
        self.parts: list[str] = []

    def rect(self, x, y, w, h, fill, stroke=None, rx=8, sw=1, dash=None, cls=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ' stroke="none"'
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{s}{d}/>'
        )

    def text(
        self,
        x,
        y,
        s,
        size=12,
        weight=400,
        fill=INK,
        anchor="start",
        maxw=None,
        halo=False,
    ):
        esc = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        mw = f' data-maxw="{maxw}"' if maxw else ""
        h = (
            ' paint-order="stroke" stroke="#FFFFFF" stroke-width="4" stroke-linejoin="round"'
            if halo
            else ""
        )
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}"{mw}{h}>{esc}</text>'
        )

    def icon(self, key, x, y, size=28):
        self.parts.append(
            f'<image href="{self.a.gcp_icon(key)}" x="{x}" y="{y}" width="{size}" height="{size}"/>'
        )

    def brand_logo(self, x: int, y: int, w: int = 126, h: int = 40) -> None:
        self.rect(x, y, w, h, "#1A73E8", None, rx=6)
        self.text(x + w / 2, y + 25, "GITOPS BLUEPRINT", 11, 700, "#FFFFFF", anchor="middle")
        self.parts.append(
            f'<line x1="{x + w + 14}" y1="{y + 2}" x2="{x + w + 14}" y2="{y + h - 2}" stroke="#DADCE0" stroke-width="1.5"/>'
        )

    def mark(self, path_d, x, y, size=28, fill=INK):
        k = size / 24
        self.parts.append(
            f'<path transform="translate({x} {y}) scale({k:.4f})" d="{path_d}" fill="{fill}"/>'
        )

    def zone(
        self,
        x,
        y,
        w,
        h,
        title,
        colour,
        subtitle=None,
        icon=None,
        mark=None,
        subtitle_right=False,
    ):
        fill, stroke, ink = PALETTE[colour]
        self.rect(x, y, w, h, fill, stroke, rx=10)
        tx = x + 14
        if icon:
            self.icon(icon, x + 12, y + 9, 22)
            tx = x + 40
        if mark:
            self.mark(mark[0], x + 12, y + 9, 22, mark[1])
            tx = x + 40
        self.text(tx, y + 24, title, 13.5, 500, ink)
        if subtitle and subtitle_right:
            self.text(x + w - 14, y + 24, subtitle, 11.5, 400, MUTED, anchor="end")
        elif subtitle:
            self.text(tx + 8 + 7 * len(title), y + 24, subtitle, 11.5, 400, MUTED)

    def card(
        self,
        x,
        y,
        w,
        icon,
        title,
        lines,
        mark=None,
        mark_fill=INK,
        mark_grad=None,
        h=None,
        dash=None,
    ):
        h = h or (36 + 15 * max(1, len(lines)) + (4 if len(lines) == 1 else 0))
        self.rect(x, y, w, h, "#FFFFFF", "#9AA0A6" if dash else "#DADCE0", rx=6, dash=dash)
        if icon:
            self.icon(icon, x + 10, y + 11, 28)
        elif mark:
            fill = f"url(#{mark_grad})" if mark_grad else mark_fill
            self.mark(mark, x + 10, y + 11, 28, fill)
        tx = x + 46
        avail = w - 46 - 8
        self.text(tx, y + 21, title, 13.5, 500, INK, maxw=avail)
        for i, line in enumerate(lines):
            self.text(tx, y + 38 + 15 * i, line, 11.5, 400, MUTED, maxw=avail)
        return x, y, w, h

    def chips(self, x, y, items):
        cx = x
        for key, label in items:
            w = 24 + int(6.3 * len(label)) + 10
            self.rect(cx, y, w, 22, "#F8F9FA", "#DADCE0", rx=11)
            self.icon(key, cx + 5, y + 3, 16)
            self.text(cx + 25, y + 15, label, 10.5, 500, "#3C4043", maxw=w - 30)
            cx += w + 8

    def arrow(
        self,
        pts,
        label=None,
        label2=None,
        dash=None,
        color=LINE,
        head=True,
        lx=None,
        ly=None,
        anchor="middle",
    ):
        d = " ".join(f"{'M' if i == 0 else 'L'}{px},{py}" for i, (px, py) in enumerate(pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        me = ' marker-end="url(#arrow)"' if head else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6"{da}{me}/>'
        )
        if label:
            if lx is None:
                (x1, y1), (x2, y2) = pts[0], pts[1]
                lx, ly = (x1 + x2) / 2, (y1 + y2) / 2 - 6
            self.text(lx, ly, label, 11, 500, "#3C4043", anchor, halo=True)
            if label2:
                self.text(lx, ly + 21, label2, 10.5, 400, MUTED, anchor, halo=True)

    def render(self) -> str:
        defs = (
            f"<style>{self.a.roboto_face()} text{{font-family:{FONT};}}</style>"
            '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker>'
            '<linearGradient id="gemini" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#4285F4"/><stop offset="0.55" stop-color="#9B72CB"/><stop offset="1" stop-color="#D96570"/></linearGradient>'
        )
        body = "\n".join(self.parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
            f'font-family="{FONT}">\n<defs>{defs}</defs>\n'
            f'<rect width="{self.w}" height="{self.h}" fill="#FFFFFF"/>\n{body}\n</svg>\n'
        )


def build(assets: Assets) -> str:
    c = Canvas(1780, 1020, assets)
    si = assets.simple_icon_path

    # ---- title ---------------------------------------------------------------------------------
    c.brand_logo(28, 22, 126, 40)
    c.text(
        180,
        44,
        "Agentic GitOps & DevOps Blueprint — Google Cloud Architecture & 4 Archetypes",
        20,
        500,
    )
    c.text(
        180,
        66,
        "Production Reference Architecture · 4 Deployment Archetypes · Keyless WIF CI/CD · "
        "BigQuery 4-Tier RLS Authorized Views · Dataplex & Spanner Graph · A2UI HTTPS LB",
        12,
        400,
        MUTED,
    )

    # ---- DNS zone (top, above the load balancer) ----------------------------------------------
    c.zone(
        930,
        14,
        290,
        98,
        "Google Cloud · Ingress DNS",
        "white",
        icon="cloud_generic",
    )
    c.card(
        942,
        42,
        266,
        "cloud_dns",
        "Cloud DNS · Managed Zone",
        ["A app.example.com → External Anycast IP", "CNAME _acme-challenge (DNS Auth)"],
    )

    # ---- Google Cloud project main boundary ---------------------------------------------------
    c.zone(
        300,
        124,
        1130,
        799,
        "Google Cloud Project (Host Runtime)",
        "grey",
        subtitle="Keyless WIF · europe-west2 / global · Least-Privilege IAM",
        icon="cloud_generic",
    )

    # Gemini Enterprise (global)
    c.zone(316, 162, 420, 122, "Gemini Enterprise & Surfaces", "blue", subtitle="global")
    c.card(
        330,
        196,
        193,
        None,
        "Gemini Enterprise",
        ["Enterprise Chat & Studio", "Managed Apps & Tools"],
        mark=si("googlegemini"),
        mark_grad="gemini",
        h=74,
    )
    c.card(
        533,
        196,
        193,
        None,
        "A2UI Surface",
        ["WebFrameUrl (Sandboxed)", "postMessage Actions"],
        mark=MATERIAL["web_asset"],
        mark_fill="#5F6368",
        h=74,
    )

    # Archetype 3: A2UI Front Door & Ingress
    c.zone(760, 162, 654, 210, "Archetype 3 · A2UI WebFrameUrl Frontend & Ingress", "yellow")
    c.card(
        774,
        198,
        380,
        "cloud_load_balancing",
        "Cloud Load Balancing (Global External HTTPS)",
        [
            "External Anycast IPv4 · Managed Certificate",
            "Cloud Armor CIDR chunklist · Dual Auth (IAP / Edge)",
            "Serverless Network Endpoint Group (NEG)",
        ],
        h=120,
    )
    c.chips(
        820,
        288,
        [
            ("cloud_armor", "Cloud Armor"),
            ("identity-aware_proxy", "IAP"),
            ("certificate_manager", "Certificate Manager"),
        ],
    )
    c.card(
        1200,
        198,
        200,
        "cloud_run",
        "Cloud Run v2",
        [
            "service a2ui-iframe",
            "ingress: internal-and-cloud-load-balancing",
            "invoker: IAP service agent",
        ],
    )
    c.card(
        1200,
        303,
        200,
        "artifact_registry",
        "Artifact Registry",
        ["repo a2ui-frontend", "immutable <git-sha> tags"],
    )

    # Archetype 1: Vertex AI Agent Engine Runtime
    c.zone(
        316,
        296,
        420,
        240,
        "Archetype 1 · Multi-Agent Runtime on Vertex AI Agent Engine",
        "green",
        subtitle="agents/starter_agent/ · europe-west2",
        subtitle_right=True,
    )
    c.card(
        330,
        330,
        396,
        "vertexai",
        "Vertex AI Agent Engine (agents-cli deployed)",
        [
            "gemini-2.5-flash router + gemini-2.5-pro pillar sub-agents",
            "3-layer sensitive data / remuneration guardrail (fail-closed)",
            "Caller OAuth/WIF identity propagation to BigQuery & Tools",
        ],
        h=102,
    )
    c.card(
        330,
        454,
        188,
        "secret_manager",
        "Secret Manager",
        ["secret-api-keys", "zero long-lived SA keys"],
        h=72,
    )
    c.card(
        538,
        454,
        188,
        "google_maps_platform",
        "Grounding Tool APIs",
        ["Search & Places APIs", "External REST Services"],
        h=72,
    )

    # Knowledge Catalog & Semantic Ontology
    c.zone(
        316,
        548,
        420,
        116,
        "Semantic Ontology & Knowledge Catalog",
        "blue",
        subtitle="Layer 1 Prompt · Layer 2 Catalog · Layer 3 SQL Guard",
        subtitle_right=True,
    )
    c.card(
        330,
        576,
        396,
        "dataplex",
        "Dataplex Knowledge Catalog & Spanner Graph",
        [
            "Context Set & Business Glossary with AspectTypes (OSI+G)",
            "Spanner Property Graph (GQL) for recursive semantic traversal",
            "Layer 3 SQL Advisor: dry_run SELECT + 5 GiB billing cap",
        ],
    )

    # Data & Telemetry (BigQuery, Logging, Monitoring)
    c.zone(
        760,
        392,
        654,
        272,
        "Data Layer, 4-Tier RLS & Continuous Observability",
        "purple",
        subtitle="BigQuery & Cloud Operations · europe-west2",
        subtitle_right=True,
    )
    c.card(
        774,
        424,
        626,
        "bigquery",
        "BigQuery · 4-Tier SESSION_USER() Authorized Views",
        [
            "Raw tables locked down · user_entitlements (ALL, DIVISION, REGION, BRANCH)",
            "5 Authorized Views: v_operations · v_catalog · v_finance_*",
            "SQL Guardrail: SELECT-only dry-run · 5 GiB limit · blocks PII / pay columns",
            "Archetype 2: Managed Finance Persona (sync_finance_agent_persona.py)",
        ],
        h=126,
    )
    c.card(
        774,
        564,
        195,
        "cloud_logging",
        "Cloud Logging & Trace",
        ["OTel distributed spans", "Structured JSON audit logs"],
    )
    c.card(
        982,
        564,
        195,
        "cloud_storage",
        "Cloud Monitoring & SLOs",
        ["Availability 99.5% SLO", "Latency p95 < 2.5s Alert"],
    )
    c.card(
        1190,
        564,
        210,
        "bigquery",
        "BigQuery Telemetry Sink",
        [
            "blueprint_agent_telemetry",
            "Long-term analytics & eval metrics",
            "LLM judge score audit table",
        ],
    )

    # Delivery & Keyless CI/CD
    c.zone(
        316,
        676,
        1098,
        231,
        "Continuous Delivery & Keyless Security Infrastructure",
        "grey",
        subtitle="GitHub Actions · OIDC Workload Identity Federation · Terraform State · CodeMender Loop",
    )
    c.card(
        330,
        712,
        330,
        "workload_identity_pool",
        "Workload Identity Federation (WIF)",
        [
            "pool: blueprint-cicd-pool · provider: github-oidc",
            "attribute condition: repository == owner/repo",
            "Zero long-lived service account keys",
        ],
    )
    c.card(
        690,
        712,
        430,
        "identity_and_access_management",
        "Keyless Service Accounts (Impersonated)",
        [
            "ci-runner-sa · PR Checks: guard_terraform_plan, tests, evals",
            "deployer-sa · main release: tf apply, engine deploy, frontend sync",
            "Least-privilege role bindings scoped to runtime datasets",
        ],
    )
    c.card(
        1150,
        712,
        250,
        "cloud_storage",
        "Cloud Storage · Remote State",
        ["…-terraform-state (versioned)", "Strict IAM + CMEK protection"],
    )
    c.card(
        330,
        810,
        600,
        "security",
        "CodeMender · Agentic Security Remediation (gemini-2.5-pro)",
        [
            "Hosted reasoning with local sandbox CLI execution for verification and patches",
            "cm find → cm verify (PoC test) → cm fix (validated via codemender/build.sh)",
            "Run on-demand or as developer workflow; outputs PR with regression tests",
        ],
        dash="6 4",
    )

    # External Actors
    c.card(
        30,
        196,
        240,
        None,
        "Enterprise Users & Personas",
        ["Role-based entitlements", "Tiers 1-4 RLS via OAuth/SAML"],
        mark=MATERIAL["groups"],
        mark_fill="#5F6368",
        h=74,
    )
    c.card(
        30,
        562,
        240,
        None,
        "Archetype 4 · Desktop Agent",
        [
            "macOS Seatbelt sandbox",
            "Keychain OAuth token store",
            "Hosted Dataplex & BQ MCP",
        ],
        mark=si("apple"),
        mark_fill="#202124",
        h=94,
    )
    c.card(
        30,
        712,
        240,
        None,
        "GitHub Actions CI/CD",
        [
            "pr_checks.yaml (PR Gate)",
            "release.yaml (CD on main)",
            "Path-filtered parallel matrix",
        ],
        mark=si("github"),
        mark_fill="#181717",
    )
    c.card(
        30,
        810,
        240,
        None,
        "Developer Workstation",
        [
            "git worktree 1:1:1:1 isolation",
            "Local pre-commit & pytest gates",
            "CodeMender CLI invocation",
        ],
        mark=MATERIAL["terminal"],
        mark_fill="#5F6368",
        dash="6 4",
    )

    c.zone(
        1470,
        392,
        280,
        272,
        "Borderless Lakehouse",
        "white",
        subtitle="Multi-Cloud / Federation",
        mark=(MATERIAL["storage"], "#0078D4"),
    )
    c.card(
        1482,
        428,
        256,
        None,
        "External Lakehouse / Federation",
        [
            "Delta Sharing & BigLake Iceberg",
            "sync_lakehouse_to_bq.py",
            "External catalog synchronization",
        ],
        mark=si("databricks"),
        mark_fill="#FF3621",
    )
    c.card(
        1482,
        541,
        256,
        None,
        "Object Storage Federation",
        ["Cross-cloud Parquet / Delta feeds", "Zero-copy BigQuery read link"],
        mark=MATERIAL["storage"],
        mark_fill="#0078D4",
    )

    # Connections
    c.arrow([(270, 231), (330, 231)], "SSO / OIDC")
    c.arrow([(270, 608), (330, 608)], "Hosted MCP")
    c.arrow([(426, 270), (426, 330)], "A2A / ADK", lx=434, ly=304, anchor="start")
    c.arrow([(726, 231), (774, 231)], "HTTPS")
    c.arrow([(1154, 231), (1200, 231)])
    c.arrow([(1300, 303), (1300, 279)], "Image", dash="4 3", lx=1308, ly=296, anchor="start")
    c.arrow([(1075, 112), (1075, 198)], "DNS query", dash="2 3", lx=1083, ly=158, anchor="start")
    c.arrow(
        [(726, 384), (1080, 384), (1080, 424)],
        "Authorized Views · SESSION_USER() RLS propagation",
        lx=740,
        ly=380,
        anchor="start",
    )
    c.arrow([(528, 432), (528, 576)], "lookupContext · OSI+G", lx=528, ly=543)
    c.arrow(
        [(552, 432), (552, 443), (748, 443), (748, 604), (774, 604)],
        "OTel spans & logs",
        lx=650,
        ly=439,
    )
    c.arrow([(969, 604), (982, 604)])
    c.arrow([(1177, 604), (1190, 604)])
    c.arrow([(1482, 462), (1400, 462)], "Delta Sharing", "BigLake external link")
    c.arrow([(270, 752), (330, 752)], "OIDC WIF", "Keyless")
    c.arrow([(660, 752), (690, 752)])
    c.arrow([(1120, 752), (1150, 752)])
    c.arrow([(270, 850), (330, 850)], "On-demand", dash="6 4")

    # Legend
    y = 957
    c.arrow([(30, y), (70, y)])
    c.text(78, y + 4, "Runtime synchronous traffic", 11, 400, MUTED)
    c.arrow([(240, y), (280, y)], dash="4 3")
    c.text(288, y + 4, "Build & release automation", 11, 400, MUTED)
    c.arrow([(470, y), (510, y)], dash="2 3")
    c.text(518, y + 4, "DNS / Federated data link", 11, 400, MUTED)
    c.rect(700, y - 9, 40, 18, "#FFFFFF", "#9AA0A6", rx=4, dash="6 4")
    c.text(748, y + 4, "On-demand security remediation loop", 11, 400, MUTED)

    c.text(
        30,
        985,
        "Terraform (deployment/terraform/single-project applied by .github/workflows/release.yaml) "
        "manages the complete cloud estate; release.yaml executes keyless WIF deployments with automated tests & evals gates.",
        11,
        400,
        MUTED,
    )
    c.text(
        30,
        1003,
        "Google Cloud product icons: official icon set (cloud.google.com/icons). "
        "Regenerate with docs/architecture/build_architecture_diagram.py.",
        10.5,
        400,
        "#80868B",
    )
    return c.render()


def to_png(
    svg_path: pathlib.Path,
    png_path: pathlib.Path,
    width: int,
    height: int,
    scale: int = 2,
) -> bool:
    chrome = next(
        (
            b
            for b in (
                shutil.which("google-chrome"),
                shutil.which("chromium"),
                shutil.which("chromium-browser"),
                shutil.which("chrome"),
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                if pathlib.Path(
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                ).exists()
                else None,
            )
            if b
        ),
        None,
    )
    if not chrome:
        print("no chrome/chromium on PATH; skipping PNG", file=sys.stderr)
        return False
    subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            f"--window-size={width},{height}",
            f"--force-device-scale-factor={scale}",
            f"--screenshot={png_path}",
            svg_path.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return True


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
        help="also write gcp-architecture.png (2x) via headless Chrome",
    )
    args = ap.parse_args()

    assets = Assets(pathlib.Path(args.cache))
    svg = build(assets)
    out = pathlib.Path(args.out)
    svg_path = out / "gcp-architecture.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print(f"wrote {svg_path} ({svg_path.stat().st_size // 1024} KB)")
    if args.png:
        m = re.search(r'width="(\d+)" height="(\d+)"', svg)
        png_path = out / "gcp-architecture.png"
        if to_png(svg_path, png_path, int(m.group(1)), int(m.group(2))):
            print(f"wrote {png_path} ({png_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
