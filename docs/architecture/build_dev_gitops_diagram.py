#!/usr/bin/env python3
"""Build the Developer Onboarding, Kanban Worktree & Keyless GitOps diagram (SVG + optional PNG).

Uses official Google Cloud product icons and Simple Icons brand marks
cached via build_architecture_diagram.Assets.

Usage:
  python3 docs/architecture/build_dev_gitops_diagram.py [--png] [--cache DIR] [--out docs/architecture]
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_architecture_diagram import MUTED, Assets, Canvas, to_png

EXTRA_MARKS = {
    "assignment": "M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z",
    "check_circle": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",
}


def step_badge(c: Canvas, x: int, y: int, label: str, bg: str, fg: str = "#FFFFFF") -> None:
    w = max(22, 10 + int(6.8 * len(label)))
    c.rect(x, y, w, 18, bg, None, rx=9)
    c.text(x + w / 2, y + 13, label, 10.5, 700, fg, anchor="middle")


def build(assets: Assets) -> str:
    c = Canvas(1840, 1020, assets)
    si = assets.simple_icon_path

    # ---- header --------------------------------------------------------------------------------
    c.brand_logo(28, 20, 126, 40)
    c.text(
        180,
        42,
        "Agentic GitOps & DevOps Blueprint — Contributor Onboarding, Kanban Worktree Flow & Keyless GitOps Pipeline",
        20,
        500,
    )
    c.text(
        180,
        64,
        "Workstation + ADC auth  →  GitHub Project v2 (Kanban)  →  isolated git worktree  →  "
        "PR Checks (CI SA)  →  Release on main (Deployer SA)  →  4 Deployment Archetypes",
        12,
        400,
        MUTED,
    )

    # ============================================================================================
    # COLUMN 1: CONTRIBUTOR ONBOARDING & LOCAL WORKTREE
    # ============================================================================================
    c.zone(
        28,
        86,
        362,
        844,
        "1. Contributor Onboarding & Local Worktree",
        "blue",
        icon="compute_engine",
    )

    c.card(
        44,
        130,
        330,
        "compute_engine",
        "Workstation Setup & Cloudtop",
        [
            "Connect via SSH / Workstation terminal",
            "Authenticate developer workstation identity",
        ],
        h=78,
    )
    step_badge(c, 336, 138, "1A", "#1967D2")

    c.card(
        44,
        228,
        330,
        None,
        "GitHub CLI & Identity Auth",
        [
            "gh auth login -s repo,read:org,workflow,project",
            "Verify SSO authorization with corporate identity",
        ],
        mark=si("github"),
        mark_fill="#181717",
        h=78,
    )
    step_badge(c, 336, 236, "1B", "#1967D2")

    c.card(
        44,
        326,
        330,
        "cloud_shell",
        "gcloud Login + Local ADC",
        [
            "gcloud auth login",
            "gcloud auth application-default login",
            "gcloud config set project <PROJECT_ID>",
        ],
        h=92,
    )
    step_badge(c, 336, 334, "1C", "#1967D2")

    c.card(
        44,
        438,
        330,
        None,
        "Prerequisites Toolchain",
        [
            "Install uv, terraform, agents-cli, pre-commit",
            "uv sync --locked --extra dev --extra eval",
            "pre-commit install for client-side git hooks",
        ],
        mark=si("python"),
        mark_fill="#3776AB",
        h=92,
    )
    step_badge(c, 336, 446, "1D", "#1967D2")

    c.card(
        44,
        550,
        330,
        None,
        "Clone + Isolated git worktree",
        [
            "git clone <REPO_URL> ~/blueprint-workspace",
            "git worktree add ../wt-<N> -b feat/issue-<N>",
            "1 folder per Issue -> safe for multi-agent swarms",
            "Zero branch collision across parallel agents",
        ],
        mark=si("git"),
        mark_fill="#F05032",
        h=110,
    )
    step_badge(c, 336, 558, "1E", "#1967D2")

    c.card(
        44,
        680,
        330,
        None,
        "Local Verification & AI Coding Agents",
        [
            "Modular architecture (<100L root app files)",
            "Run ruff check && pytest tests/unit/",
            "Multiple AI agents safely execute in separate trees",
        ],
        mark=si("googlegemini"),
        mark_grad="gemini",
        h=94,
    )
    step_badge(c, 336, 688, "1F", "#1967D2")

    c.card(
        44,
        794,
        330,
        "security",
        "CodeMender Security Loop (Ad-Hoc)",
        [
            "./codemender/cm.sh (gemini-2.5-pro)",
            "Local find -> verify -> fix sandbox loop",
        ],
        h=78,
        dash="6 4",
    )

    # Vertical sequence arrows inside Col 1
    for y1, y2 in [(208, 228), (306, 326), (418, 438), (530, 550), (660, 680)]:
        c.arrow([(209, y1), (209, y2)])

    # ============================================================================================
    # COLUMN 2: GITHUB ISSUE, KANBAN & PULL REQUEST
    # ============================================================================================
    c.zone(
        430,
        86,
        368,
        844,
        "2. GitHub Issue, Kanban & PR Lifecycle",
        "yellow",
        mark=(si("github"), "#181717"),
    )

    c.card(
        446,
        130,
        336,
        None,
        "GitHub Project v2 — Kanban Board",
        [
            "Columns: Backlog · Ready · In Progress · In Review · Done",
            "Metadata: Priority · Component · Linked Branch · PR",
            "Automated transition workflows synchronize cards",
            "Multi-agent swarm coordination via issue claims",
        ],
        mark=si("github"),
        mark_fill="#181717",
        h=116,
    )
    step_badge(c, 742, 138, "2A", "#B06000")

    c.card(
        446,
        282,
        336,
        None,
        "GitHub Issue #<N> (1:1 Kanban Card)",
        [
            "Claim issue: assign @me -> moves to In Progress",
            "New requirement? gh issue create with template",
            "Project board auto-adds card to Backlog/Ready",
            "Iron Rule: 1 Issue = 1 Card = 1 Worktree = 1 PR",
        ],
        mark=EXTRA_MARKS["assignment"],
        mark_fill="#B06000",
        h=118,
    )
    step_badge(c, 742, 290, "2B", "#B06000")

    c.card(
        446,
        438,
        336,
        None,
        "Pull Request ('Fixes #<N>')",
        [
            "Open Draft PR early to publish work-in-progress",
            "'Fixes #<N>' automatically links diff to card",
            "Mark Ready for Review -> moves card to In Review",
            "Protected main branch requires status checks green",
        ],
        mark=si("git"),
        mark_fill="#F05032",
        h=118,
    )
    step_badge(c, 742, 446, "2C", "#B06000")

    c.card(
        446,
        604,
        336,
        None,
        "Squash-Merge & Auto-Cleanup",
        [
            "Squash-merge PR once all checks pass & approved:",
            "1) 'Fixes #<N>' closes Issue #<N>",
            "2) Kanban card automatically transitions -> Done",
            "3) deleteBranchOnMerge deletes remote head branch",
            "4) Local cleanup: git worktree remove ../wt-<N>",
        ],
        mark=EXTRA_MARKS["check_circle"],
        mark_fill="#137333",
        h=134,
    )
    step_badge(c, 742, 612, "2D", "#137333")

    c.card(
        446,
        774,
        336,
        None,
        "Optimistic Merge & Conflict Hygiene",
        [
            "Isolation: ../wt-<N> worktree per Issue/Agent",
            "Strict status checks + branch up-to-date enforcement",
            "Rebase on origin/main before readying PR",
        ],
        mark=si("github"),
        mark_fill="#5F6368",
        h=98,
        dash="4 3",
    )

    c.arrow([(614, 246), (614, 282)], "claim issue", lx=622, ly=268, anchor="start")
    c.arrow([(614, 400), (614, 438)], "Fixes #<N>", lx=622, ly=423, anchor="start")
    c.arrow([(614, 556), (614, 604)], "checks pass", lx=622, ly=584, anchor="start")

    # ============================================================================================
    # COLUMN 3: KEYLESS GITHUB ACTIONS GITOPS PIPELINE
    # ============================================================================================
    c.zone(
        838,
        86,
        526,
        844,
        "3. Keyless GitHub Actions GitOps Pipeline",
        "grey",
        mark=(si("githubactions"), "#2088FF"),
    )

    c.card(
        854,
        130,
        494,
        "workload_identity_pool",
        "Workload Identity Federation (WIF) · Zero Long-Lived SA Keys",
        [
            "OIDC condition: assertion.repository == 'owner/repo'",
            "PR checks -> ci-runner-sa (read-only)  |  main -> deployer-sa",
        ],
        h=80,
    )

    # Sub-zone 3A: PR Checks
    c.zone(
        854,
        224,
        494,
        296,
        "PR Gate · pr_checks.yaml (pull_request)",
        "blue",
        subtitle="CI SA (read-only) · cancel-in-progress: true",
        subtitle_right=True,
    )
    c.card(
        868,
        260,
        466,
        None,
        "terraform-plan (IaC validate + guard_terraform_plan.py)",
        [
            "terraform fmt · validate · read-only plan vs remote GCS state",
            "Blocks unexpected IAM escalations or disruptive deletions",
        ],
        mark=si("terraform"),
        mark_fill="#844FBA",
        h=72,
    )
    c.card(
        868,
        344,
        466,
        None,
        "tests (uv sync --locked · pytest unit · BQ dry-run)",
        [
            "preflight_bq_access · dry-run views/*.sql · RLS tests",
        ],
        mark=si("python"),
        mark_fill="#3776AB",
        h=72,
    )
    c.card(
        868,
        428,
        466,
        "vertexai",
        "evals + a2ui-build (LLM Judge & Docker Smoke)",
        [
            "LLM Judge: quality >= 0.75, grounding = 1.0, guardrail = 1.0",
        ],
        h=74,
    )

    # Sub-zone 3B: Release on main
    c.zone(
        854,
        536,
        494,
        378,
        "Release Pipeline · release.yaml (push to main)",
        "green",
        subtitle="Deployer SA · cancel-in-progress: false",
        subtitle_right=True,
    )
    c.card(
        868,
        570,
        466,
        None,
        "1. terraform-apply (IaC Infrastructure + Authorized Views)",
        [
            "Deploys Cloud Run, IAM, BigQuery datasets, Views & Secret Manager",
        ],
        mark=si("terraform"),
        mark_fill="#844FBA",
        h=60,
    )
    c.card(
        868,
        638,
        466,
        "security",
        "2. tests + evals (Mandatory Post-Apply Release Gate)",
        [
            "Live 4-tier RLS verification · dry-run views · eval pass rate >= 70%",
        ],
        h=60,
    )
    c.card(
        868,
        706,
        466,
        None,
        "3. deploy-agent-runtime + register-ge-oauth",
        [
            "agents-cli deploy (Agent Engine) · publish Gemini Enterprise app",
        ],
        mark=si("googlegemini"),
        mark_grad="gemini",
        h=64,
    )
    c.card(
        868,
        778,
        466,
        "vertexai",
        "4. sync-finance-persona (Config-as-Code Agent)",
        [
            "Declarative sync for AnalystAgentPersona + BYOS skills ZIP",
        ],
        h=60,
    )
    c.card(
        868,
        846,
        466,
        None,
        "5. deploy-a2ui-frontend (Cloud Run v2 + HTTPS LB)",
        [
            "Builds image to Artifact Registry · deploys Cloud Run behind LB",
        ],
        mark=si("docker"),
        mark_fill="#2496ED",
        h=60,
    )

    # ============================================================================================
    # COLUMN 4: TARGET GCP ENVIRONMENT & THE 4 ARCHETYPES
    # ============================================================================================
    c.zone(
        1404,
        86,
        408,
        844,
        "4. Target Cloud Runtime & 4 Archetypes",
        "purple",
        subtitle="europe-west2 / global",
        subtitle_right=True,
        icon="cloud_generic",
    )

    c.card(
        1420,
        130,
        376,
        None,
        "Archetype 1: Vertex AI Agent Engine",
        [
            "Custom Multi-Agent System on Agent Engine",
            "gemini-2.5-flash router + gemini-2.5-pro pillars",
            "3-layer guardrail + fail-closed caller RLS",
        ],
        mark=si("googlegemini"),
        mark_grad="gemini",
        h=102,
    )

    c.card(
        1420,
        252,
        376,
        "vertexai",
        "Archetype 2: Managed Config-as-Code Agent",
        [
            "Declarative persona & skills configuration",
            "sync_finance_agent_persona.py + BYOS skills",
            "Table-scoped BigQuery IAM + pseudonymized views",
        ],
        h=118,
    )

    c.card(
        1420,
        390,
        376,
        "cloud_run",
        "Archetype 3: A2UI WebFrameUrl Frontend",
        [
            "Cloud Run v2 behind Global HTTPS Load Balancer",
            "Cloud Armor CIDR allowlist + IAP dual auth",
            "postMessage bidirectional UI bridge (a2ui_action)",
        ],
        h=142,
    )
    c.chips(
        1432,
        500,
        [
            ("artifact_registry", "Artifact Registry"),
            ("cloud_load_balancing", "HTTPS LB"),
            ("identity-aware_proxy", "IAP"),
        ],
    )

    c.card(
        1420,
        552,
        376,
        "bigquery",
        "Archetype 4 & Governed Lakehouse",
        [
            "macOS Spark Desktop Agent Extension (Seatbelt/Keychain)",
            "Hosted Dataplex & BigQuery MCP endpoints",
            "4-Tier SESSION_USER() RLS (ALL, DIVISION, REGION, BRANCH)",
            "Dataplex Knowledge Catalog & Spanner Property Graph",
        ],
        h=136,
    )
    c.chips(
        1432,
        656,
        [
            ("dataplex", "Knowledge Catalog"),
            ("cloud_logging", "Cloud Logging"),
        ],
    )

    c.card(
        1420,
        708,
        376,
        "cloud_storage",
        "Platform Observability & Governance",
        [
            "Cloud Monitoring SLOs (99.5% availability, p95 latency)",
            "Cloud Trace distributed telemetry & error reporting",
            "Remote Terraform state buckets with CMEK encryption",
            "Secret Manager zero-trust credential isolation",
        ],
        h=152,
    )
    c.chips(
        1432,
        828,
        [
            ("secret_manager", "Secret Manager"),
            ("cloud_storage", "GCS Remote State"),
        ],
    )

    # ============================================================================================
    # CROSS-COLUMN ARROWS
    # ============================================================================================
    # Col 2 -> Col 1: claim issue & branch locally
    c.arrow(
        [(446, 340), (406, 340), (406, 605), (374, 605)],
        "claim #<N>",
        lx=406,
        ly=330,
        anchor="middle",
    )

    # Col 1 -> Col 2: git push + gh pr create
    c.arrow(
        [(374, 726), (418, 726), (418, 497), (446, 497)],
        "git push + PR",
        lx=410,
        ly=744,
        anchor="middle",
        color="#1967D2",
    )

    # Col 2 -> Col 3: PR event
    c.arrow(
        [(782, 486), (812, 486), (812, 360), (868, 360)],
        "PR event",
        lx=812,
        ly=348,
        anchor="middle",
        color="#1967D2",
    )

    # Col 3 -> Col 2: gates pass
    c.arrow(
        [(854, 504), (812, 504), (812, 636), (782, 636)],
        "gates ✔",
        dash="4 3",
        lx=812,
        ly=566,
        anchor="middle",
        color="#137333",
    )

    # Col 2 -> Col 3: squash-merge
    c.arrow(
        [(782, 671), (812, 671), (812, 570), (854, 570)],
        "merge main",
        lx=812,
        ly=620,
        anchor="middle",
        color="#137333",
    )

    # Col 3 -> Col 4: deploy release
    c.arrow(
        [(1348, 720), (1420, 720)],
        "deploy",
        lx=1384,
        ly=710,
        anchor="middle",
        color="#137333",
    )

    # Footer
    c.text(
        30,
        965,
        "Developer and multi-agent GitOps flow: GitHub Project v2 Kanban coordinates parallel worktrees; "
        "pr_checks.yaml validates changes via keyless WIF, and release.yaml deploys all 4 archetypes to Google Cloud.",
        11,
        400,
        MUTED,
    )
    c.text(
        30,
        985,
        "Official Google Cloud product icons (cloud.google.com/icons). "
        "Regenerate with docs/architecture/build_dev_gitops_diagram.py.",
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
        help="also write dev-gitops-workflow.png (2x) via headless Chrome",
    )
    args = ap.parse_args()

    assets = Assets(pathlib.Path(args.cache))
    svg = build(assets)
    out = pathlib.Path(args.out)
    svg_path = out / "dev-gitops-workflow.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print(f"wrote {svg_path} ({svg_path.stat().st_size // 1024} KB)")
    if args.png:
        m = re.search(r'width="(\d+)" height="(\d+)"', svg)
        png_path = out / "dev-gitops-workflow.png"
        if to_png(svg_path, png_path, int(m.group(1)), int(m.group(2))):
            print(f"wrote {png_path} ({png_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
