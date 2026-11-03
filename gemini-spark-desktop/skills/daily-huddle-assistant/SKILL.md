---
name: daily-huddle-assistant
description: Runs the morning shift health check, team pacing analysis, priority exception triage, and zero-CDN timeline canvas rendering for daily operational huddles.
version: 1.0.0
---

# Daily Operational Huddle Assistant

Executes the automated morning shift review, triage, and schedule generation across local workspace connectors and remote BigQuery / Knowledge Catalog MCP endpoints.

## Governance Rules

1. **Deterministic Single Snapshot Execution**:
   - Run the snapshot command once to execute concurrent MCP checks and generate the zero-CDN Gantt canvas:
     ```bash
     /usr/bin/python3 scripts/desktop_agent_data_mcp.py --cli morning-snapshot --render-canvas
     ```
   - Avoid redundant follow-up CLI calls within the same turn.

2. **Priority Ordering for Morning Review**:
   - **P0 Service Disruptions**: Immediate operational blocks, logistics delays, or system alerts requiring proactive mitigation before 10:00.
   - **P1 High-Value Opportunities**: Client inquiries and quotes ready for confirmation to achieve shift commercial targets.
   - **P2 Routine Operational Follow-ups**: Scheduled quality assurance checks, customer check-ins, and order dispatch reviews.

3. **Time-Blocked Shift Schedule & Inline Visual Flow**:
   - Emit a color-coded `flowchart LR` diagram outlining the planned shift timeline:
     ```mermaid
     flowchart LR
       T1["08:45 - 09:00<br/>Shift Desk Triage"] --> T2["09:00 - 09:20<br/>Morning Team Huddle"]
       T2 --> T3["09:20 - 10:30<br/>P0 Service Exceptions"]
       T3 --> T4["10:30 - 11:30<br/>P1 High-Value Orders"]
       T4 --> T5["11:30 - 12:30<br/>P2 Customer Follow-ups"]
       classDef fixed fill:#002B5C,stroke:#001B3A,color:#FFFFFF
       classDef p0 fill:#D93025,stroke:#A50E0E,color:#FFFFFF
       classDef p1 fill:#C98A00,stroke:#8F6200,color:#FFFFFF
       classDef p2 fill:#009FE3,stroke:#006FA1,color:#FFFFFF
       class T1,T2 fixed
       class T3 p0
       class T4 p1
       class T5 p2
     ```
   - Reference the companion zero-CDN scorecard canvas (`~/operational_shift_canvas.html`) for interactive visual review.

4. **Remuneration Guardrail**:
   - Exclude employee salaries, individual bonuses, and payroll data from all huddle notes and query plans.
