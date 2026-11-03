-- Copyright 2026 The Project Contributors
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
--
-- Canonical catalog view over pre-aggregated `hotel_places_catalog` / `catalog_places_enriched`
-- (cross-supplier variant deduplication, non-PII product reference data).
-- Materialized at hydration/reconcile time by `sync_lakehouse_to_bq.py`
-- (templated: {project}, {dataset}) so branch-scoped consultants resolve all
-- canonical catalog properties, cross-supplier variants, and availability
-- without caller RLS on raw operations collapsing aggregates.
CREATE OR REPLACE VIEW `{project}.{dataset}.v_catalog_enriched` AS
SELECT
  canonical_place_id,
  normalized_hotel_key,
  canonical_hotel_name,
  canonical_resort,
  canonical_country,
  destination_sector,
  destination_category,
  star_rating,
  raw_supplier_hotel_variants,
  raw_supplier_resort_variants,
  tour_operators,
  supplier_variant_count,
  total_bookings,
  avg_gross_price_gbp,
  avg_profit_gbp,
  available_on_preferred_network,
  licensed_image_library_id
FROM `{project}.{dataset}.hotel_places_catalog`;
