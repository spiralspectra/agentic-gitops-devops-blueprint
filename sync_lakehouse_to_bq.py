#!/usr/bin/env python3
# Copyright 2026 The Project Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Hydrates enterprise Lakehouse Delta Sharing tables into BigQuery.

Target Dataset: $GOOGLE_CLOUD_PROJECT:lakehouse_sharing (europe-west2),
                created by Terraform (deployment/terraform/single-project).
Source Share:   enterprise_data_share.lakehouse_sharing
Tables:         bookings, customermaster, customermosaicdemographics, supplier, branch

Modes:
  default                      load from Delta Sharing (authoritative source;
                               needs DELTA_SHARING_PROFILE_PATH or the
                               DELTA_SHARING_ENDPOINT/_BEARER_TOKEN env vars)
  --from-bigquery PROJECT      clone tables from another project's
                               lakehouse_sharing dataset (same region)
  --views-only                 (re)create the SQL views only
  --skip-views                 load tables but leave views untouched
  --dry-run                    print actions without executing BQ jobs

After the tables are loaded the script:
  * re-applies the 4-tier Row Access Policy (`rls_4_tier_wif_policy`) on `bookings`
  * materializes `hotel_places_catalog`
  * (re)creates the views in deployment/data/views/*.sql in file-name order
  * registers every view as an Authorized View on the dataset.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request
from typing import Any

import pyarrow as pa
from google.cloud import bigquery


def _load_share_credentials() -> tuple[str, str]:
    """Loads Delta Sharing endpoint and bearer token from env vars or .share profile JSON."""
    profile_path = os.getenv("DELTA_SHARING_PROFILE_PATH")
    if profile_path and os.path.isfile(profile_path):
        with open(profile_path, encoding="utf-8") as f:
            profile = json.load(f)
        return profile["endpoint"].rstrip("/"), profile["bearerToken"]
    endpoint = os.getenv("DELTA_SHARING_ENDPOINT", "").rstrip("/")
    token = os.getenv("DELTA_SHARING_BEARER_TOKEN", "")
    if not endpoint or not token:
        raise RuntimeError(
            "Set DELTA_SHARING_PROFILE_PATH=/path/to/profile.share or both "
            "DELTA_SHARING_ENDPOINT and DELTA_SHARING_BEARER_TOKEN environment variables."
        )
    return endpoint, token


SHARE = os.getenv("DELTA_SHARING_SHARE", "enterprise_data_share")
SCHEMA = os.getenv("DELTA_SHARING_SCHEMA", "lakehouse_sharing")
PROJECT_ID = (
    os.getenv("GOOGLE_CLOUD_PROJECT")
    or os.getenv("BQ_PROJECT")
    or os.getenv("GCP_PROJECT_ID")
    or "retail-enterprise-gemini"
)
DATASET_ID = (
    os.getenv("BQ_DATASET_ID")
    or os.getenv("BQ_DATASET")
    or os.getenv("APP_BQ_DATASET")
    or "lakehouse_sharing"
)
LOCATION = os.getenv("BQ_LOCATION") or os.getenv("APP_BQ_LOCATION") or "europe-west2"
ENTITLEMENTS_TABLE = os.getenv("ENTITLEMENTS_TABLE", "user_entitlements")

DEFAULT_RLS_GRANTEES = (
    f"serviceAccount:enterprise-agent-ci@{PROJECT_ID}.iam.gserviceaccount.com,"
    f"serviceAccount:enterprise-agent-deployer@{PROJECT_ID}.iam.gserviceaccount.com"
)
RLS_GRANTEES = [
    g.strip() for g in os.getenv("RLS_GRANTEES", DEFAULT_RLS_GRANTEES).split(",") if g.strip()
]

VIEWS_DIR = pathlib.Path(__file__).resolve().parent / "deployment" / "data" / "views"
TABLES = [
    "supplier",
    "branch",
    "customermaster",
    "customermosaicdemographics",
    "bookings",
]


def sanitize_col_name(name: str) -> str:
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        return name
    m = re.search(r"substring\(([a-zA-Z0-9_]+)", name)
    if m:
        return m.group(1)
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_")
    return cleaned if cleaned and not cleaned[0].isdigit() else f"col_{cleaned}"


def build_phys_to_logical_map(
    delta_fields: list[dict[str, Any]],
) -> dict[str, tuple[str, dict[str, Any]]]:
    """Builds a recursive physicalName -> (logicalName, nestedMap) lookup from Delta schemaString."""
    mapping: dict[str, tuple[str, dict[str, Any]]] = {}
    for f in delta_fields:
        phys = f.get("metadata", {}).get("delta.columnMapping.physicalName", f["name"])
        logical = sanitize_col_name(f["name"])
        sub_map: dict[str, Any] = {}
        ftype = f["type"]
        if isinstance(ftype, dict):
            if ftype.get("type") == "struct":
                sub_map = build_phys_to_logical_map(ftype.get("fields", []))
            elif (
                ftype.get("type") == "array"
                and isinstance(ftype.get("elementType"), dict)
                and ftype["elementType"].get("type") == "struct"
            ):
                sub_map = build_phys_to_logical_map(ftype["elementType"].get("fields", []))
        mapping[phys] = (logical, sub_map)
    return mapping


def build_description_map(delta_fields: list[dict[str, Any]]) -> dict[str, str]:
    """Extracts top-level column descriptions from the Delta schemaString."""
    descriptions: dict[str, str] = {}
    for f in delta_fields:
        comment = f.get("metadata", {}).get("comment")
        if comment:
            descriptions[sanitize_col_name(f["name"])] = comment
    return descriptions


def _rename_type(
    arrow_type: pa.DataType, sub_map: dict[str, tuple[str, dict[str, Any]]]
) -> pa.DataType:
    if pa.types.is_struct(arrow_type):
        new_fields = []
        for i in range(arrow_type.num_fields):
            f = arrow_type.field(i)
            if f.name in sub_map:
                log_name, child_map = sub_map[f.name]
                new_type = _rename_type(f.type, child_map)
                new_fields.append(pa.field(log_name, new_type, nullable=f.nullable))
            else:
                new_fields.append(f)
        return pa.struct(new_fields)
    elif pa.types.is_list(arrow_type):
        item_field = arrow_type.value_field
        if item_field.name in sub_map:
            log_name, child_map = sub_map[item_field.name]
            new_val_type = _rename_type(item_field.type, child_map)
            return pa.list_(pa.field(log_name, new_val_type, nullable=item_field.nullable))
        new_val_type = _rename_type(item_field.type, sub_map)
        return pa.list_(pa.field(item_field.name, new_val_type, nullable=item_field.nullable))
    return arrow_type


def rename_arrow_schema(
    schema: pa.Schema,
    phys_to_logical: dict[str, tuple[str, dict[str, Any]]],
) -> pa.Schema:
    new_fields = []
    for f in schema:
        if f.name in phys_to_logical:
            log_name, sub_map = phys_to_logical[f.name]
            new_type = _rename_type(f.type, sub_map)
            new_fields.append(pa.field(log_name, new_type, nullable=f.nullable))
        else:
            new_fields.append(f)
    return pa.schema(new_fields)


def _query_label() -> bigquery.QueryJobConfig:
    return bigquery.QueryJobConfig(labels={"datacloud": "blueprint-sync"})


def ensure_authorized_views(client: bigquery.Client, view_names: list[str]) -> None:
    """Idempotently registers SQL views in `DATASET_ID` as Authorized Views on the dataset."""
    if not view_names:
        return
    ds = client.get_dataset(f"{PROJECT_ID}.{DATASET_ID}")
    entries = list(ds.access_entries)
    existing_views = {
        (
            e.entity_id.get("projectId"),
            e.entity_id.get("datasetId"),
            e.entity_id.get("tableId"),
        )
        for e in entries
        if e.entity_type == "view" and isinstance(e.entity_id, dict)
    }
    added: list[str] = []
    for vname in view_names:
        key = (PROJECT_ID, DATASET_ID, vname)
        if key not in existing_views:
            entries.append(
                bigquery.AccessEntry(
                    role=None,
                    entity_type="view",
                    entity_id={
                        "projectId": PROJECT_ID,
                        "datasetId": DATASET_ID,
                        "tableId": vname,
                    },
                )
            )
            existing_views.add(key)
            added.append(vname)
    if added:
        ds.access_entries = entries
        client.update_dataset(ds, ["access_entries"])
        print(f"  authorized view(s) on {PROJECT_ID}.{DATASET_ID}: {', '.join(added)}")
    else:
        print(f"  all {len(view_names)} view(s) already authorized on {PROJECT_ID}.{DATASET_ID}")


def _table_exists(client: bigquery.Client, table_name: str) -> bool:
    """Checks whether a table exists in the target BigQuery dataset."""
    try:
        client.get_table(f"{PROJECT_ID}.{DATASET_ID}.{table_name}")
        return True
    except Exception:
        return False


def ensure_hotel_places_catalog(client: bigquery.Client) -> None:
    """Materializes `hotel_places_catalog` across all transactions.

    `bookings` carries a 4-tier `SESSION_USER()` Row Access Policy, so aggregating
    over `bookings` directly in a plain view would collapse consultant catalog lookups.
    Pre-aggregating this non-PII product catalog table under the deployer identity
    lets Authorized View `v_catalog_enriched` serve canonical catalog items,
    cross-supplier variants, and preferred partner flags.
    """
    if not _table_exists(client, "bookings") or not _table_exists(client, "supplier"):
        print(
            f"WARN: Table 'bookings' or 'supplier' does not exist in {PROJECT_ID}.{DATASET_ID}; "
            "skipping hotel_places_catalog materialization."
        )
        return

    catalog_sql = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.hotel_places_catalog`
    OPTIONS(
      description="Pre-aggregated non-PII product catalog over bookings.HotelDetails (cross-supplier variant dedup, preferred partner flag), refreshed by sync_lakehouse_to_bq.py and exposed via Authorized View v_catalog_enriched."
    )
    AS WITH normalized AS (
      SELECT
        b.BookingReference,
        b.GrossPrice,
        CAST(b.Profit AS FLOAT64) AS Profit,
        b.DestinationType.DestinationSector AS destination_sector,
        b.DestinationType.DestinationCategory AS destination_category,
        COALESCE(NULLIF(TRIM(h.Country), ''), b.DestinationType.Destination) AS canonical_country,
        TRIM(h.HotelName) AS raw_hotel_name,
        TRIM(h.Resort) AS raw_resort,
        h.StarRating AS star_rating,
        h.Traveltek_CreditorName AS tour_operator,
        UPPER(REGEXP_REPLACE(TRIM(COALESCE(h.HotelName, '')), r'[^A-Za-z0-9 ]', '')) AS normalized_hotel_key,
        UPPER(TRIM(COALESCE(NULLIF(TRIM(h.Country), ''), b.DestinationType.Destination, ''))) AS normalized_country_key,
        (s.SupplierID = 'DIR0001' OR UPPER(s.SupplierName) LIKE '%DIRECT%') AS is_preferred
      FROM `{PROJECT_ID}.{DATASET_ID}.bookings` b
      CROSS JOIN UNNEST(b.HotelDetails) AS h
      LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.supplier` s
        ON b.AE_SupplierKey = s.SupplierKey
      WHERE b.Cancelled = 'N'
        AND h.HotelName IS NOT NULL
        AND TRIM(h.HotelName) != ''
    )
    SELECT
      CONCAT(
        'place_ent_',
        SUBSTR(TO_HEX(SHA256(CONCAT(normalized_hotel_key, '|', normalized_country_key))), 1, 16)
      ) AS canonical_place_id,
      normalized_hotel_key,
      ANY_VALUE(raw_hotel_name) AS canonical_hotel_name,
      ANY_VALUE(raw_resort) AS canonical_resort,
      ANY_VALUE(canonical_country) AS canonical_country,
      ANY_VALUE(destination_sector) AS destination_sector,
      ANY_VALUE(destination_category) AS destination_category,
      MAX(star_rating) AS star_rating,
      ARRAY_AGG(DISTINCT raw_hotel_name IGNORE NULLS LIMIT 10) AS raw_supplier_hotel_variants,
      ARRAY_AGG(DISTINCT raw_resort IGNORE NULLS LIMIT 10) AS raw_supplier_resort_variants,
      ARRAY_AGG(DISTINCT tour_operator IGNORE NULLS LIMIT 10) AS tour_operators,
      COUNT(DISTINCT tour_operator) AS supplier_variant_count,
      COUNT(DISTINCT BookingReference) AS total_bookings,
      ROUND(AVG(GrossPrice), 2) AS avg_gross_price_gbp,
      ROUND(AVG(Profit), 2) AS avg_profit_gbp,
      LOGICAL_OR(is_preferred) AS available_on_preferred_network,
      CONCAT(
        'ENT-IMG-',
        UPPER(SUBSTR(TO_HEX(SHA256(CONCAT(normalized_hotel_key, '|', normalized_country_key))), 1, 10))
      ) AS licensed_image_library_id
    FROM normalized
    GROUP BY canonical_place_id, normalized_hotel_key, normalized_country_key;
    """
    client.query(catalog_sql, job_config=_query_label()).result()
    print(f"  materialized {PROJECT_ID}.{DATASET_ID}.hotel_places_catalog")


def ensure_views(client: bigquery.Client) -> None:
    """(Re)creates the dataset's views from deployment/data/views/*.sql, in file-name order."""
    files = sorted(VIEWS_DIR.glob("*.sql"))
    if not files:
        print(f"WARN: no view definitions found in {VIEWS_DIR}; skipping views.")
        return
    applied_views: list[str] = []
    for path in files:
        sql = path.read_text(encoding="utf-8").format(project=PROJECT_ID, dataset=DATASET_ID)
        client.query(sql, job_config=_query_label()).result()
        print(f"  applied {path.name}")
        m = re.search(
            r"CREATE\s+OR\s+REPLACE\s+VIEW\s+`?[^`\s]+\.[^`\s]+\.([a-zA-Z0-9_]+)`?",
            sql,
            flags=re.IGNORECASE,
        )
        if m:
            vname = m.group(1)
            client.query(
                f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{vname}` LIMIT 0",
                job_config=bigquery.QueryJobConfig(
                    dry_run=True,
                    use_query_cache=False,
                    labels={"datacloud": "blueprint-sync"},
                ),
            )
            applied_views.append(vname)
    ensure_authorized_views(client, applied_views)


def apply_bookings_rls_policy(client: bigquery.Client) -> None:
    """Re-applies the 4-tier WIF/OIDC Row Access Policy on bookings after WRITE_TRUNCATE."""
    if not _table_exists(client, "bookings") or not _table_exists(client, ENTITLEMENTS_TABLE):
        print(
            f"WARN: Table 'bookings' or '{ENTITLEMENTS_TABLE}' does not exist in {PROJECT_ID}.{DATASET_ID}; "
            "skipping RLS policy enforcement."
        )
        return

    grantees = ", ".join("'" + g.replace("'", "") + "'" for g in RLS_GRANTEES)
    caller_match = (
        "(LOWER(NULLIF(TRIM(wif_subject), '')) = LOWER(SESSION_USER()) "
        "OR LOWER(NULLIF(TRIM(user_email), '')) = LOWER(SESSION_USER()))"
    )
    rls_sql = f"""
    CREATE OR REPLACE ROW ACCESS POLICY rls_4_tier_wif_policy
    ON `{PROJECT_ID}.{DATASET_ID}.bookings`
    GRANT TO ({grantees})
    FILTER USING (
      (
        (SaleBranchID IN (
           SELECT branch_id FROM `{PROJECT_ID}.{DATASET_ID}.{ENTITLEMENTS_TABLE}`
           WHERE {caller_match} AND role = 'BRANCH_STAFF'
         )
         OR EXISTS (
           SELECT 1 FROM `{PROJECT_ID}.{DATASET_ID}.{ENTITLEMENTS_TABLE}`
           WHERE {caller_match} AND role = 'BRANCH_STAFF' AND branch_id = '*'
         ))
        AND (
          Username IN (
            SELECT username FROM `{PROJECT_ID}.{DATASET_ID}.{ENTITLEMENTS_TABLE}`
            WHERE {caller_match} AND role = 'BRANCH_STAFF'
          )
          OR EXISTS (
            SELECT 1 FROM `{PROJECT_ID}.{DATASET_ID}.{ENTITLEMENTS_TABLE}`
            WHERE {caller_match} AND role = 'BRANCH_STAFF' AND username = '*'
          )
        )
      )
      OR SaleBranchID IN (
         SELECT branch_id FROM `{PROJECT_ID}.{DATASET_ID}.{ENTITLEMENTS_TABLE}`
         WHERE {caller_match} AND role = 'BRANCH_MANAGER'
       )
      OR EXISTS (
         SELECT 1 FROM `{PROJECT_ID}.{DATASET_ID}.{ENTITLEMENTS_TABLE}`
         WHERE {caller_match} AND role = 'BRANCH_MANAGER' AND branch_id = '*'
       )
      OR SellingBranch.BranchGroup IN (
         SELECT region_group FROM `{PROJECT_ID}.{DATASET_ID}.{ENTITLEMENTS_TABLE}`
         WHERE {caller_match} AND role = 'REGIONAL_MANAGER'
       )
      OR EXISTS (
         SELECT 1 FROM `{PROJECT_ID}.{DATASET_ID}.{ENTITLEMENTS_TABLE}`
         WHERE {caller_match}
           AND role = 'REGIONAL_MANAGER' AND UPPER(TRIM(region_group)) = 'ALL'
       )
      OR SellingBranch.BranchBusinessDivision IN (
         SELECT division FROM `{PROJECT_ID}.{DATASET_ID}.{ENTITLEMENTS_TABLE}`
         WHERE {caller_match} AND role = 'DIVISIONAL_HEAD'
       )
      OR EXISTS (
         SELECT 1 FROM `{PROJECT_ID}.{DATASET_ID}.{ENTITLEMENTS_TABLE}`
         WHERE {caller_match}
           AND role = 'DIVISIONAL_HEAD' AND UPPER(TRIM(division)) = 'ALL'
       )
    );
    """
    client.query(rls_sql, job_config=_query_label()).result()
    print(
        f"  Re-applied ROW ACCESS POLICY rls_4_tier_wif_policy on bookings (granted to {len(RLS_GRANTEES)} principal(s))."
    )


ALLOWED_PARQUET_HOST_SUFFIXES = (
    ".blob.core.windows.net",
    ".dfs.core.windows.net",
    "storage.googleapis.com",
    ".storage.googleapis.com",
    "s3.amazonaws.com",
    ".amazonaws.com",
    ".r2.cloudflarestorage.com",
)


def _validate_parquet_url(url: str) -> str:
    """Validates that a Delta Sharing Parquet URL uses HTTPS and an allowed cloud storage host."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https":
        raise ValueError(f"Insecure Parquet download scheme: {parsed.scheme!r}")
    host = parsed.netloc.split(":")[0].lower()
    if not host.endswith(ALLOWED_PARQUET_HOST_SUFFIXES):
        raise ValueError(f"Untrusted cloud storage host: {host!r}")
    return url


def sync_delta_sharing_table(
    client: bigquery.Client,
    endpoint: str,
    bearer_token: str,
    table_name: str,
) -> None:
    """Fetches metadata and parquet data from Delta Sharing REST API and loads into BigQuery."""
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
    # 1. Fetch table metadata for schema
    meta_url = f"{endpoint}/shares/{SHARE}/schemas/{SCHEMA}/tables/{table_name}/metadata"
    req = urllib.request.Request(meta_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            meta_lines = resp.read().decode("utf-8").strip().splitlines()
    except Exception as e:
        print(f"  Failed to fetch Delta Sharing metadata for {table_name}: {e}")
        return

    delta_fields: list[dict[str, Any]] = []
    for line in meta_lines:
        try:
            item = json.loads(line)
            if "metaData" in item:
                schema_str = item["metaData"].get("schemaString", "{}")
                schema_obj = json.loads(schema_str)
                delta_fields = schema_obj.get("fields", [])
                break
        except Exception:
            continue

    phys_to_logical = build_phys_to_logical_map(delta_fields)
    _ = build_description_map(delta_fields)

    # 2. Query table files
    query_url = f"{endpoint}/shares/{SHARE}/schemas/{SCHEMA}/tables/{table_name}/query"
    query_req = urllib.request.Request(
        query_url,
        data=json.dumps({}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(query_req, timeout=30) as resp:
            query_lines = resp.read().decode("utf-8").strip().splitlines()
    except Exception as e:
        print(f"  Failed to query Delta Sharing files for {table_name}: {e}")
        return

    parquet_urls: list[str] = []
    for line in query_lines:
        try:
            item = json.loads(line)
            if "file" in item and "url" in item["file"]:
                validated_url = _validate_parquet_url(item["file"]["url"])
                parquet_urls.append(validated_url)
        except Exception:
            continue

    print(f"  Discovered {len(parquet_urls)} file(s) for table `{table_name}`")
    if not parquet_urls:
        return

    # 3. Read and rename parquet schema
    import pyarrow.dataset as ds

    tables_to_concat = []
    for purl in parquet_urls:
        try:
            dataset = ds.dataset(purl, format="parquet")
            sub_table = dataset.to_table()
            if phys_to_logical:
                new_schema = rename_arrow_schema(sub_table.schema, phys_to_logical)
                sub_table = sub_table.cast(new_schema)
            tables_to_concat.append(sub_table)
        except Exception as err:
            print(f"  Warning: failed reading parquet partition {purl[:60]}...: {err}")

    if not tables_to_concat:
        print(f"  No valid parquet partitions loaded for {table_name}")
        return

    combined_table = pa.concat_tables(tables_to_concat)
    print(f"  Hydrated {combined_table.num_rows} row(s) for `{table_name}`")

    # 4. Load into BigQuery table
    target_table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        labels={"datacloud": "blueprint-sync"},
    )
    load_job = client.load_table_from_dataframe(
        combined_table.to_pandas(), target_table_id, job_config=job_config
    )
    load_job.result()
    print(f"  Successfully loaded `{target_table_id}`")


def clone_from_bigquery(
    client: bigquery.Client, source_project: str, dry_run: bool = False
) -> None:
    """Clones the 5 Lakehouse tables from another project's dataset."""
    print(f"Cloning tables from {source_project}.{DATASET_ID} to {PROJECT_ID}.{DATASET_ID}...")
    for tname in TABLES:
        src = f"`{source_project}.{DATASET_ID}.{tname}`"
        dst = f"`{PROJECT_ID}.{DATASET_ID}.{tname}`"
        sql = f"CREATE OR REPLACE TABLE {dst} CLONE {src}"
        if dry_run:
            print(f"  [DRY-RUN] {sql}")
            continue
        try:
            client.query(sql, job_config=_query_label()).result()
            print(f"  cloned {tname}")
        except Exception as e:
            print(f"  CLONE failed for {tname} ({e}), falling back to CREATE TABLE AS SELECT...")
            copy_sql = f"CREATE OR REPLACE TABLE {dst} AS SELECT * FROM {src}"
            client.query(copy_sql, job_config=_query_label()).result()
            print(f"  copied {tname}")


def validate_view_definitions() -> list[str]:
    """Validates SQL files in VIEWS_DIR under dry-run mode without network calls."""
    files = sorted(VIEWS_DIR.glob("*.sql"))
    if not files:
        print(f"WARN: no view definitions found in {VIEWS_DIR}")
        return []
    valid_views: list[str] = []
    for path in files:
        raw_sql = path.read_text(encoding="utf-8")
        formatted_sql = raw_sql.format(project=PROJECT_ID, dataset=DATASET_ID)
        m = re.search(
            r"CREATE\s+OR\s+REPLACE\s+VIEW\s+`?[^`\s]+\.[^`\s]+\.([a-zA-Z0-9_]+)`?",
            formatted_sql,
            flags=re.IGNORECASE,
        )
        if not m:
            raise ValueError(f"Could not parse CREATE OR REPLACE VIEW name in {path.name}")
        view_name = m.group(1)
        valid_views.append(view_name)
        print(f"  [DRY-RUN VALIDATED] {path.name} -> {PROJECT_ID}.{DATASET_ID}.{view_name}")
    return valid_views


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Lakehouse Delta Share tables to BigQuery.")
    parser.add_argument(
        "--from-bigquery",
        metavar="SOURCE_PROJECT",
        help="Clone tables from an existing BigQuery dataset instead of Delta Sharing",
    )
    parser.add_argument("--views-only", action="store_true", help="Only (re)create SQL views")
    parser.add_argument(
        "--skip-views", action="store_true", help="Load tables without updating views"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Log actions without modifying BigQuery"
    )
    args = parser.parse_args()

    if args.dry_run:
        print(
            f"[DRY-RUN] Validating BigQuery views in {VIEWS_DIR} for {PROJECT_ID}.{DATASET_ID}..."
        )
        valid_views = validate_view_definitions()
        print(
            f"[DRY-RUN] Successfully validated {len(valid_views)} view definitions without network calls."
        )
        print(f"[DRY-RUN] Target dataset: {PROJECT_ID}.{DATASET_ID} (location: {LOCATION})")
        print(
            f"[DRY-RUN] Mode flags: from_bigquery={bool(args.from_bigquery)}, views_only={args.views_only}, skip_views={args.skip_views}"
        )
        print("Lakehouse reconciliation dry-run complete (exit 0).")
        return

    bq_client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

    if not args.views_only:
        if args.from_bigquery:
            clone_from_bigquery(bq_client, args.from_bigquery, dry_run=args.dry_run)
        else:
            print(f"Syncing Delta Share `{SHARE}.{SCHEMA}` to `{PROJECT_ID}.{DATASET_ID}`...")
            endpoint, bearer_token = _load_share_credentials()
            print(f"  Connected to endpoint: {endpoint}")
            for tname in TABLES:
                print(f"  Hydrating table `{tname}`...")
                sync_delta_sharing_table(bq_client, endpoint, bearer_token, tname)

        ensure_hotel_places_catalog(bq_client)
        apply_bookings_rls_policy(bq_client)

    if not args.skip_views:
        print("Applying Authorized Views...")
        ensure_views(bq_client)

    print("Lakehouse reconciliation complete.")


if __name__ == "__main__":
    main()
