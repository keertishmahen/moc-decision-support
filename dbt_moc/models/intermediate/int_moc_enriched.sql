{{ config(materialized='view') }}

select
  m.moc_id,
  m.title,
  m.change_type,
  m.asset_id,
  a.name as asset_name,
  a.equipment_type as asset_category,
  a.area_id,
  ar.area_name,
  m.risk_level,
  m.overall_risk_score,
  m.hazop_required,
  m.pssr_required,
  m.estimated_cost,
  m.actual_cost,
  m.estimated_downtime,
  m.actual_downtime,
  m.incident_occurred,
  m.hazard_description,
  m.lessons_learned,
  m.date_initiated,
  m.work_order_ids,
  coalesce(g.n_dependencies, 0) as n_dependencies,
  coalesce(g.n_hazards, 0) as n_hazards,
  coalesce(g.n_mocs, 0) as n_mocs,
  coalesce(g.n_work_orders, 0) as n_work_orders
from {{ ref('stg_moc') }} m
left join {{ ref('stg_asset') }} a on m.asset_id = a.asset_id
left join {{ ref('stg_area') }} ar on a.area_id = ar.area_id
left join {{ ref('int_asset_graph_metrics') }} g on m.asset_id = g.asset_id
