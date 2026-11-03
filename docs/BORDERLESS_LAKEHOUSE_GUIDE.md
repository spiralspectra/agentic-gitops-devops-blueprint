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

# Enabling Google Cloud Borderless Lakehouse with Azure Databricks Unity Catalog

This guide provides technical steps to connect **Google Cloud Borderless Lakehouse (BigLake Iceberg REST Catalog Federation)** directly to **Azure Databricks Unity Catalog** (`*.azuredatabricks.net` backed by Azure Data Lake Storage Gen2 `abfss://`), enabling zero-copy SQL queries from **BigQuery** and **Vertex AI / ADK Agents** in `europe-west2` (London).

---

## 1. Architectural Overview: Open Sharing (`config.share`) vs. Borderless Lakehouse Federation

| Dimension | Option 1: **Databricks Open Sharing (`config.share`)** | Option 2: **Borderless Lakehouse Federation (`--federated-catalog-type=unity`)** |
| :--- | :--- | :--- |
| **Protocol & Endpoint** | Delta Sharing REST protocol (`/api/2.0/opensharing/...`) | Apache Iceberg REST Catalog v1 API (`/api/2.1/unity-catalog/iceberg-rest/v1`) |
| **Catalog Authentication** | Pre-issued static `bearerToken` in `.share` files | **Databricks Service Principal** via **Secretless GCP OIDC Federation** (recommended) or **OAuth M2M (`client_id` / `client_secret`)** in Regional Secret Manager |
| **Supported Source Objects** | Delta Tables and Dynamic Views | **Physical Delta Tables in an External Location** with **Delta UniForm (`IcebergCompatV2`)** enabled *(SQL Views and tables with `deletionVectors` or Unity Catalog Row Filters/Masks are not exposed by Iceberg REST API)* |
| **Storage Access** | Vends short-lived pre-signed ADLS URLs per file | Vends short-lived scoped ADLS SAS tokens (`adls.sas-token.*`) via `X-Iceberg-Access-Delegation: vended-credentials` |
| **BigQuery Experience** | Hydrates Parquet snapshots into native BigQuery tables | **Zero-copy query in-place** using 4-part table names (`project.catalog.namespace.table`) with automatic local block caching in GCP (`europe-west2`) |
| **End-User Row-Level Security (RLS)** | Native BigQuery `ROW ACCESS POLICY` + `v_operations` view via Workforce Identity Federation (`SESSION_USER()`) | BigQuery `v_operations` RLS view over the 4-part federated table via Workforce Identity Federation (`SESSION_USER()`) |

---

## 2. Phase 1: Azure Databricks Prerequisites & Table Preparation

Complete the following 5 steps in the Azure Databricks workspace (`adb-xxxxxxxxxxxxxxxx.xx.azuredatabricks.net`) and Azure Portal:

### Step 1.1: Enable External Data Access on Unity Catalog Metastore
By default, Unity Catalog disables credential vending to external Iceberg engines.

1. Log in to the **Azure Databricks Account Console** (or Workspace Admin Settings).
2. Navigate to **Catalog** $\rightarrow$ select the target **Metastore** $\rightarrow$ **Access** tab.
3. Enable **External data access** (*Allow external engines to access data in this metastore via credential vending*).

### Step 1.2: Enable Delta UniForm (`IcebergCompatV2`) & Materialize Shared Views
Unity Catalog's Iceberg REST endpoint (`/api/2.1/unity-catalog/iceberg-rest/v1`) enforces three requirements on shared tables:

1. **Physical Tables Only (No SQL Views):** Dynamic SQL `VIEW`s are not exposed over the Iceberg REST API. Any view must be materialized as a physical Delta table stored in an ADLS Gen2 External Location.
2. **Valid Column Aliases for Masked Expressions:** Calculated expressions such as `concat(substring(AgentName, 1, 2), '*****')` must have explicit SQL aliases (`AS AgentName`) so they map to valid column names in Iceberg and BigQuery.
3. **Disable Deletion Vectors & Do Not Attach Unity Catalog Row Filters/Column Masks:**
    * Delta UniForm (`IcebergCompatV2`) requires `'delta.enableDeletionVectors' = 'false'`.
    * Do **not** attach Unity Catalog `ROW FILTER` or `COLUMN MASK` policies onto federated tables, as Unity Catalog blocks Iceberg storage credential vending when dynamic row filters or masks are present. Static masking should be baked into the `SELECT` query, and dynamic per-user Row-Level Security is enforced in BigQuery via `SESSION_USER()`.

#### A. Materializing a View into a Physical Delta UniForm Table
```sql
CREATE OR REPLACE TABLE <unity_catalog_name>.lakehouse_sharing.bookings_uniform
USING DELTA
LOCATION 'abfss://<container>@dlsdatalakegen2.dfs.core.windows.net/lakehouse_sharing/bookings_uniform'
TBLPROPERTIES (
  'delta.enableDeletionVectors' = 'false',
  'delta.columnMapping.mode' = 'name',
  'delta.enableIcebergCompatV2' = 'true',
  'delta.universalFormat.enabledFormats' = 'iceberg'
)
AS SELECT
  BookingReference,
  DeltaId,
  LastModified,
  Adults,
  concat(substring(AgentName, 1, 2), '*****') AS AgentName,
  BalanceDue,
  BondingType,
  BookingDate,
  BookingSource,
  Branch,
  Cancelled,
  Children,
  Commission,
  CreatedDate,
  DepartureDate,
  Duration,
  GrossPrice,
  Infants,
  Outstanding,
  Passengers,
  Profit,
  ReturnDate,
  SaleBranchID,
  TotalPayment,
  Username,
  AE_SupplierKey,
  DestinationType,
  DeparturePoint,
  ArrivalPoint,
  FlightDetails,
  HotelDetails,
  CruiseDetails,
  BuyingBranch,
  SellingBranch,
  InsuranceDetails,
  AttractionsEventsDetails
FROM <source_catalog>.<source_schema>.<source_bookings_table_or_view>;
```

#### B. Enabling UniForm on Existing Base Tables
If enabling UniForm in-place on existing physical Delta tables that currently have `deletionVectors` enabled, disable deletion vectors, purge them with `REORG TABLE`, and enable `IcebergCompatV2`:

```sql
ALTER TABLE <unity_catalog_name>.lakehouse_sharing.customermaster
SET TBLPROPERTIES (
  'delta.enableDeletionVectors' = 'false',
  'delta.columnMapping.mode' = 'name'
);

REORG TABLE <unity_catalog_name>.lakehouse_sharing.customermaster APPLY (PURGE);

ALTER TABLE <unity_catalog_name>.lakehouse_sharing.customermaster
SET TBLPROPERTIES (
  'delta.enableIcebergCompatV2' = 'true',
  'delta.universalFormat.enabledFormats' = 'iceberg'
);
```

### Step 1.3: Create a Databricks Service Principal & Grant Privileges
1. In Azure Databricks, go to **Settings** $\rightarrow$ **Identity and access** $\rightarrow$ **Service principals** $\rightarrow$ **Add service principal**.
2. Create a new Databricks-managed Service Principal (for example, `gcp-biglake-federation`) and copy its **Application ID (UUID)**.
3. Grant the Service Principal read access and the mandatory **`EXTERNAL USE SCHEMA`** privilege (which allows Unity Catalog to vend short-lived ADLS SAS tokens to BigQuery):

```sql
GRANT USE CATALOG
  ON CATALOG <unity_catalog_name>
  TO `<SERVICE_PRINCIPAL_APPLICATION_ID>`;

GRANT USE SCHEMA, EXTERNAL USE SCHEMA, SELECT
  ON SCHEMA <unity_catalog_name>.lakehouse_sharing
  TO `<SERVICE_PRINCIPAL_APPLICATION_ID>`;
```

### Step 1.4: Verify Azure ADLS Gen2 Storage Firewall Rules
Because BigQuery workers in `europe-west2` read Parquet blocks directly from Azure ADLS using SAS tokens vended by Unity Catalog, verify in Azure Portal (**Storage accounts** $\rightarrow$ `dlsdatalakegen2` $\rightarrow$ **Networking**) that external read requests authenticated with valid SAS tokens from Google Cloud (`europe-west2`) are permitted.

### Step 1.5: Parameters to Share with Google Cloud Team
1. **Azure Databricks Workspace Hostname:** `adb-xxxxxxxxxxxxxxxx.xx.azuredatabricks.net`
2. **Unity Catalog Name & Schema Name:** `<unity_catalog_name>` and `lakehouse_sharing`
3. **Service Principal Application ID (UUID):** `<SERVICE_PRINCIPAL_APPLICATION_ID>`

---

## 3. Phase 2: Google Cloud Setup (`europe-west2`)

Run these commands in the target Google Cloud project (e.g., `PROJECT_ID="retail-enterprise-gemini"`).

### Step 2.1: Enable Required APIs
```bash
export PROJECT_ID="retail-enterprise-gemini"

gcloud services enable \
  biglake.googleapis.com \
  bigquery.googleapis.com \
  secretmanager.googleapis.com \
  --project="${PROJECT_ID}"
```

### Step 2.2: Create the Federated Lakehouse Catalog

#### Option A: Secretless OIDC Federation (Recommended)
```bash
# 1. Create the federated catalog in europe-west2 with cross-cloud caching enabled
gcloud alpha biglake iceberg catalogs create enterprise_unity_catalog \
  --project="${PROJECT_ID}" \
  --primary-location="europe-west2" \
  --catalog-type="federated" \
  --federated-catalog-type="unity" \
  --unity-instance-name="adb-xxxxxxxxxxxxxxxx.xx.azuredatabricks.net" \
  --unity-catalog-name="<UNITY_CATALOG_NAME>" \
  --unity-service-principal-application-id="<SERVICE_PRINCIPAL_APPLICATION_ID>" \
  --cross-cloud-cache="enabled" \
  --refresh-interval="300s" \
  --namespace-filters="lakehouse_sharing"

# 2. Retrieve the 21-digit numeric Google Service Account Unique ID
gcloud alpha biglake iceberg catalogs describe enterprise_unity_catalog \
  --project="${PROJECT_ID}" \
  --format='value(biglake-service-account-id)'
```

#### Option B: Secret-Based Authentication (Regional Secret Manager)
```bash
# 1. Point gcloud to regional Secret Manager endpoint for europe-west2
gcloud config set api_endpoint_overrides/secretmanager \
  https://secretmanager.europe-west2.rep.googleapis.com/

# 2. Create regional secret containing {"client_id": "...", "client_secret": "..."}
gcloud secrets create databricks-unity-oauth \
  --location="europe-west2" \
  --project="${PROJECT_ID}" \
  --data-file=credentials.json

# 3. Create federated catalog referencing the regional secret
gcloud alpha biglake iceberg catalogs create enterprise_unity_catalog \
  --project="${PROJECT_ID}" \
  --primary-location="europe-west2" \
  --catalog-type="federated" \
  --federated-catalog-type="unity" \
  --unity-instance-name="adb-xxxxxxxxxxxxxxxx.xx.azuredatabricks.net" \
  --unity-catalog-name="<UNITY_CATALOG_NAME>" \
  --secret-name="projects/${PROJECT_ID}/locations/europe-west2/secrets/databricks-unity-oauth" \
  --cross-cloud-cache="enabled" \
  --refresh-interval="300s" \
  --namespace-filters="lakehouse_sharing"

# 4. Grant catalog service account access to secret
gcloud secrets add-iam-policy-binding databricks-unity-oauth \
  --project="${PROJECT_ID}" \
  --location="europe-west2" \
  --member="serviceAccount:$(gcloud alpha biglake iceberg catalogs describe enterprise_unity_catalog \
    --project="${PROJECT_ID}" \
    --format='value(biglake-service-account)')" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 4. Phase 3: Complete OIDC Trust Handshake in Azure Databricks (Option A Only)

If using **Option A (Secretless OIDC Federation)**, add the trust policy on the Databricks Service Principal:

1. In Azure Databricks, open **Settings** $\rightarrow$ **Identity and access** $\rightarrow$ **Service principals** $\rightarrow$ select the Service Principal created in Step 1.3.
2. Open the **Federation policies** tab $\rightarrow$ click **Add policy**.
3. Enter the following exact values:
    * **Issuer URL:** `https://accounts.google.com`
    * **Subject:** `<biglake-service-account-id>` *(the 21-digit numeric Google Service Account ID from Step 2.2)*
    * **Audience:** `https://accounts.cloud.databricks.com`
4. Click **Save**.

---

## 5. Phase 4: Verify Synchronization & Querying in BigQuery

### Step 4.1: Verify Catalog & Table Synchronization
BigLake automatically syncs namespaces and Iceberg table metadata from Unity Catalog every 5 minutes (`--refresh-interval="300s"`).
```bash
# Check catalog refresh status
gcloud alpha biglake iceberg catalogs describe enterprise_unity_catalog \
  --project="${PROJECT_ID}"

# Confirm that the lakehouse_sharing namespace and tables have synchronized
gcloud alpha biglake iceberg namespaces list \
  --project="${PROJECT_ID}" \
  --catalog="enterprise_unity_catalog"

gcloud alpha biglake iceberg tables list \
  --project="${PROJECT_ID}" \
  --catalog="enterprise_unity_catalog" \
  --namespace="lakehouse_sharing"
```

### Step 4.2: Query Directly in BigQuery (4-Part `P.C.N.T` Syntax)
Query the federated catalog directly in BigQuery Studio or via the `bq` CLI using `project.federated_catalog.namespace.table`:
```sql
SELECT
  BookingReference,
  SaleBranchID,
  SellingBranch.BranchName AS BranchName,
  AgentName,
  BookingDate,
  GrossPrice,
  Commission
FROM `retail-enterprise-gemini.enterprise_unity_catalog.lakehouse_sharing.bookings_uniform`
WHERE BookingDate >= '2026-10-01'
  AND Cancelled = 'N'
LIMIT 20;
```

### Step 4.3: Verify Intelligent Cross-Cloud Caching
When BigQuery reads Parquet blocks from Azure ADLS, BigLake caches those blocks locally in `europe-west2` (`--cross-cloud-cache="enabled"`). Subsequent queries read from local GCP cache rather than re-fetching from Azure.

Verify cache hit statistics on any BigQuery job ID:
```bash
bq show --format=prettyjson --j <JOB_ID> | grep -A 6 "objectStorageStats"
```
* `cloudProvider`: `"AZURE"`
* `objectStorageBytesRead`: Bytes fetched over network from Azure ADLS Gen2
* `cacheBytesRead`: Bytes served directly from local `europe-west2` cache

---

## 6. End-User Row-Level Security (RLS) with Workforce Identity Federation (WIF) & OIDC

Because 4-part Federated Catalog tables do not support base-table `CREATE ROW ACCESS POLICY` or Databricks-side `ROW FILTER`s, **4-tier Row-Level Security (`BRANCH_STAFF`, `BRANCH_MANAGER`, `REGIONAL_MANAGER`, `DIVISIONAL_HEAD`) is enforced in BigQuery using Workforce Identity Federation (WIF) + OIDC (`SESSION_USER()`) and the `v_operations` view**:

### Step 6.1: Identity Flow from Corporate Identity Provider to BigQuery
1. Users sign in via corporate identity provider (e.g. Entra ID / Okta) and receive an OIDC ID Token (`id_token` JWT).
2. The AI Agent exchanges that OIDC JWT at Google Cloud STS (`https://sts.googleapis.com/v1/token`) against the GCP Workforce Identity Pool (`enterprise-oidc-pool`).
3. BigQuery executes all agent queries under caller federated identity (`SESSION_USER() = 'principal://iam.googleapis.com/locations/global/workforcePools/enterprise-oidc-pool/subject/<user_upn>'`).

### Step 6.2: Point `v_operations` RLS View to the 4-Part Federated Table
Point `deployment/data/views/10_v_operations.sql` at the 4-part federated `bookings_uniform` table:

```sql
CREATE OR REPLACE VIEW `retail-enterprise-gemini.lakehouse_sharing.v_operations` AS
WITH caller_entitlements AS (
  SELECT ARRAY_AGG(STRUCT(
    e.role,
    e.branch_id,
    e.username,
    e.region_group,
    e.division
  )) AS scopes
  FROM `retail-enterprise-gemini.lakehouse_sharing.user_entitlements` e
  WHERE LOWER(NULLIF(TRIM(e.wif_subject), '')) = LOWER(SESSION_USER())
     OR LOWER(NULLIF(TRIM(e.user_email), '')) = LOWER(SESSION_USER())
)
SELECT b.* EXCEPT(Commission)
FROM `retail-enterprise-gemini.enterprise_unity_catalog.lakehouse_sharing.bookings_uniform` b
CROSS JOIN caller_entitlements ce
WHERE EXISTS (
  SELECT 1
  FROM UNNEST(ce.scopes) AS e
  WHERE (
          e.role = 'BRANCH_STAFF'
          AND (e.branch_id = '*' OR b.SaleBranchID = e.branch_id)
          AND (e.username = '*' OR b.Username = e.username)
        )
     OR (
          e.role = 'BRANCH_MANAGER'
          AND (e.branch_id = '*' OR b.SaleBranchID = e.branch_id)
        )
     OR (
          e.role = 'REGIONAL_MANAGER'
          AND (UPPER(TRIM(e.region_group)) = 'ALL' OR b.SellingBranch.BranchGroup = e.region_group)
        )
     OR (
          e.role = 'DIVISIONAL_HEAD'
          AND (UPPER(TRIM(e.division)) = 'ALL' OR b.SellingBranch.BranchBusinessDivision = e.division)
        )
);
```

Register the view as an Authorized View on the dataset so end users need table-level `roles/bigquery.dataViewer` on `v_operations` only, never on `bookings_uniform` or `user_entitlements`.

---

## 7. Knowledge Catalog Context Set, BigQuery Property Graph & Spanner Graph Interoperability

To bridge structured relational lakehouse data with enterprise knowledge representations, the blueprint provisions a unified property graph:

### 7.1 Native BigQuery Property Graph (`enterprise_ontology_graph`)
Created and reconciled idempotently by [`sync_knowledge_catalog_ontology.py`](../sync_knowledge_catalog_ontology.py):
```sql
CREATE OR REPLACE PROPERTY GRAPH `retail-enterprise-gemini.lakehouse_sharing.enterprise_ontology_graph`
  NODE TABLES (
    `bookings` KEY (BookingReference) LABEL Booking,
    `customermaster` KEY (CustomerID) LABEL Customer,
    `customermosaicdemographics` KEY (CustomerID, ValidFrom) LABEL MosaicDemographic,
    `supplier` KEY (SupplierKey) LABEL Supplier,
    `branch` KEY (BranchId) LABEL Branch
  )
  EDGE TABLES (
    `bookings` KEY (BookingReference)
      SOURCE KEY (BookingReference) REFERENCES bookings (BookingReference)
      DESTINATION KEY (AE_SupplierKey) REFERENCES supplier (SupplierKey)
      LABEL OPERATED_BY_SUPPLIER,
    `bookings` KEY (BookingReference)
      SOURCE KEY (BookingReference) REFERENCES bookings (BookingReference)
      DESTINATION KEY (SaleBranchID) REFERENCES branch (BranchId)
      LABEL SOLD_BY_BRANCH,
    `customermosaicdemographics` KEY (CustomerID, ValidFrom)
      SOURCE KEY (CustomerID, ValidFrom) REFERENCES customermosaicdemographics (CustomerID, ValidFrom)
      DESTINATION KEY (CustomerID) REFERENCES customermaster (CustomerID)
      LABEL SEGMENTED_CUSTOMER
  );
```

### 7.2 BigQuery & Spanner Graph Interoperability
- **ISO GQL Standards Alignment**: The BigQuery Property Graph conforms to ISO/IEC 39075:2024 (GQL), allowing `GRAPH_TABLE` queries with declarative path traversal:
  ```sql
  SELECT * FROM GRAPH_TABLE(
    `retail-enterprise-gemini.lakehouse_sharing.enterprise_ontology_graph`,
    MATCH (b:Booking)-[:OPERATED_BY_SUPPLIER]->(s:Supplier)
    WHERE b.Cancelled = 'N'
    COLUMNS (b.BookingReference, s.SupplierName, b.GrossPrice)
  );
  ```
- **Spanner Graph Interoperability**: For operational low-latency workloads, Spanner Graph instances replicate or federate graph topologies using identical node/edge definitions, enabling hybrid transactional and analytical processing (HTAP) across Google Cloud without schema impedance mismatch.

