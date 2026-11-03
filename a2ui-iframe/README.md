<!--
Copyright 2026 The Project Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# A2UI IFrame — Custom Canvas Frontend for Gemini Enterprise (`Canvas` + `IFrameUrl`)

This directory contains the custom Agent-to-User Interface (A2UI) frontend container deployed to Cloud Run and embedded into the Gemini Enterprise right-hand side panel using the A2UI v0.9 composite catalog's **`Canvas`** and **`IFrameUrl`** components (`https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json`).

Gemini Enterprise mounts the allowlisted URL in a sandboxed iframe and relays bidirectional `postMessage` events (`type: "a2ui_action"`) back to the conversational agent as structured user turns.

---

## Architectural Topology

```text
Gemini Enterprise Right-Hand Canvas Panel
└── IFrameUrl = https://<a2ui-domain>/?view=pillar2&branch=0015&persona=jenkins&origin=REPLACE_WITH_PARENT_ORIGIN#state=<base64url>
      ├── Cloud Load Balancing: Certificate Manager TLS · Cloud Armor · IAP / Edge Auth
      ├── Cloud Run Service: a2ui-iframe (Ingress: internal-and-cloud-load-balancing, Zero IAM privileges)
      └── window.parent.postMessage({ type: 'a2ui_action', action, data }, resolvedOrigin) → Conversational Turn
```

---

## Architecture & Security Contract

### 1. Zero-Privilege Stateless Hydration (`#state=<base64url>`)
The `a2ui-iframe` Cloud Run service account holds **zero read or write privileges** on BigQuery datasets, Cloud Storage buckets, or Dataplex resources (`a2ui_iframe.tf`).
Instead, the conversational agent queries authorized BigQuery views under the caller's verified Workload Identity Federation (WIF) entitlements, serializes the tailored state as JSON, and encodes it into the URL fragment (`#state=<base64url>` or raw DEFLATE `#s=z.<deflate-raw-b64url>`).

Because URL fragments are never sent in HTTP request headers:
- HTTP 414 URI-Too-Long errors are avoided across intermediate proxies.
- Sensitive business payloads and tailored customer copy are kept out of proxy access logs.
- The browser client inflates the fragment locally using `window.atob()` or `DecompressionStream('deflate-raw')`.

### 2. Framing Security & CSP Headers
Nginx is explicitly configured (`nginx.conf`) to permit framing by approved enterprise origins while preventing clickjacking across untrusted third-party domains:
- Never sets `X-Frame-Options` (which would unconditionally block iframe rendering in parent portals).
- Sets `Content-Security-Policy: frame-ancestors 'self' https://*.google.com https://*.cloud.google.com https://*.run.app https://*.example.com;`.
- Sets `Cache-Control: no-store, no-cache, must-revalidate` to avoid stale state caching across consultant sessions.

### 3. IAP Cookie Warm-Up & Edge Auth
When `a2ui_iframe_auth_mode = "iap"`, Identity-Aware Proxy requires an initial user interaction to establish the `GCP_IAAP_AUTH_TOKEN` session cookie. Because browser third-party cookie restrictions may block redirects within nested iframes, users can visit the standalone URL once per session, or administrators can configure `a2ui_iframe_auth_mode = "edge"` to authenticate via Cloud Armor edge tokens.

### 4. Origin-Checked `a2ui_action` Bridge
When Gemini Enterprise mounts the iframe, it substitutes `origin=REPLACE_WITH_PARENT_ORIGIN` in the query string with the host portal's verified origin. The bridge validates origins against an allowlist pattern before dispatching actions:
```javascript
window.parent.postMessage({
  type: "a2ui_action",
  action: "send_curated_pitch",
  data: {
    offerId: "offer-vista-1",
    totalBasket: 2337,
    selectedAncillaries: ["In-Branch Foreign Exchange", "Airport Parking"]
  }
}, targetOrigin);
```

---

## Workspace Modes

The canvas UI provides three integrated operational modes:

| Mode | Route Parameter | Purpose | Key Actions |
|---|---|---|---|
| **Curated Catalog & Ideator** | `?view=pillar2` | Package comparison, climate metrics, interactive 3-day POI itinerary builder, and real-time ancillary gap basket. | `select_offer_card`, `toggle_poi_itinerary`, `toggle_ancillary_gap`, `send_curated_pitch` |
| **Marketing Studio** | `?view=pillar3` | Dialect and channel-tailored campaign generator with live 5-point regulatory compliance verification. | `switch_marketing_dialect`, `switch_marketing_format`, `publish_marketing_asset` |
| **Operations Cockpit** | `?view=pillar1` | Branch KPI metrics, T+7 post-service customer follow-up queue, and 14-day balance due resolution. | `log_t7_welcome_call`, `send_balance_reminder` |

---

## Local Development & Testing

### Running Locally with Docker
```bash
cd a2ui-iframe
docker build -t a2ui-iframe:local .
docker run -p 8080:8080 a2ui-iframe:local
```
Open `http://localhost:8080/?view=pillar2&branch=0015&persona=jenkins` in your browser.

### Verifying Frame Headers
```bash
curl -I http://localhost:8080/
```
Verify:
- `X-Frame-Options` is **not present**.
- `Content-Security-Policy` contains `frame-ancestors`.
- `Cache-Control` is `no-store, no-cache, must-revalidate`.
