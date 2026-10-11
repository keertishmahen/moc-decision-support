{{ config(materialized='table') }}

select
  moc_id,
  title,
  change_type,
  asset_id,
  asset_name,
  asset_category,
  area_name,
  risk_level,
  overall_risk_score,
  actual_cost,
  actual_downtime,
  incident_occurred,
  n_dependencies,
  n_hazards,
  n_work_orders,
  date_initiated
from {{ ref('int_moc_enriched') }}
