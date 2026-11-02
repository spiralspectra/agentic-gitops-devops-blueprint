# SRE Alert Runbook & Incident Response

This runbook defines triage, diagnosis, mitigation, and escalation procedures for all automated Cloud Monitoring alert policies.

---

## Alert: Fast Burn Availability

### Metadata
- **Severity:** Critical (SEV1)
- **SLO Target:** 99.5% 28-day rolling availability
- **Trigger Condition:** 1-hour error budget burn rate exceeds 14.4x (>2% budget consumed in 1 hour)

### Symptom
High volume of 5xx HTTP errors, uncaught exceptions, or container crash loops in Vertex AI Reasoning Engine or Cloud Run agent runtime.

### Triage Queries

#### 1. Cloud Logging (LQL)
```sql
resource.type="aiplatform.googleapis.com/ReasoningEngine"
severity>=ERROR
timestamp >= NOW() - 1h
```

#### 2. BigQuery Telemetry (`completions_view`)
```sql
SELECT
  FORMAT_TIMESTAMP('%Y-%m-%d %H:%M', timestamp) AS minute_window,
  status,
  error_message,
  COUNT(*) AS failure_count
FROM
  `your-gcp-project-id.my_agent_service_telemetry.completions_view`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  AND status != "SUCCESS"
GROUP BY
  minute_window, status, error_message
ORDER BY
  minute_window DESC;
```

### Mitigation
1. **Rollback Release:** If triggered immediately following a deployment:
   - Identify the previous healthy Reasoning Engine ID or container digest.
   - Update `deployment_metadata.json` and `vars/env.tfvars` with the previous `reasoning_engine_id`.
   - Dispatch the `release.yaml` workflow or execute:
     ```bash
     agents-cli deploy --engine-id="<PREVIOUS_ENGINE_ID>"
     ```
2. **Quota & Throttling Check:** Inspect Vertex AI model quotas (e.g., TPM/RPM on `gemini-2.5-pro`) in Google Cloud Console.
3. **Dependency Outage:** Check upstream BigQuery or external API reachability.

### Escalation
If unmitigated after 15 minutes, notify the designated SRE on-call rotation and technical lead.

---

## Alert: Slow Burn Availability

### Metadata
- **Severity:** High (SEV2)
- **SLO Target:** 99.5% 28-day rolling availability
- **Trigger Condition:** 6-hour error budget burn rate exceeds 6.0x (>5% budget consumed over 6 hours)

### Symptom
Intermittent failures, gradual degradation, or isolated tool invocation timeouts causing chronic error budget depletion.

### Triage Queries

#### BigQuery Telemetry Latency & Error Breakdown
```sql
SELECT
  model,
  COUNTIF(status != "SUCCESS") AS errors,
  COUNT(*) AS total_calls,
  ROUND(COUNTIF(status != "SUCCESS") / COUNT(*) * 100, 2) AS error_rate_pct,
  ROUND(AVG(latency_ms), 0) AS avg_latency_ms
FROM
  `your-gcp-project-id.my_agent_service_telemetry.completions_view`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 HOUR)
GROUP BY
  model;
```

### Mitigation
1. Check for stale BigQuery schema changes or expired service account credentials.
2. Investigate specific slow tools or intermittent upstream latency.

---

## Alert: High Latency (p95 > 8000ms)

### Metadata
- **Severity:** Medium (SEV3)
- **SLO Target:** 95% of queries respond within 8,000ms over 28-day rolling window
- **Trigger Condition:** p95 latency exceeds 8s over evaluated window

### Triage Queries
```sql
SELECT
  trace_id,
  latency_ms,
  prompt_tokens,
  completion_tokens,
  error_message
FROM
  `your-gcp-project-id.my_agent_service_telemetry.completions_view`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
  AND latency_ms > 8000
ORDER BY
  latency_ms DESC
LIMIT 50;
```

### Mitigation
1. Determine whether large token contexts or deep tool loops are inflating generation time.
2. Consider enabling context caching or switching high-volume classification tasks to `gemini-2.5-flash`.
