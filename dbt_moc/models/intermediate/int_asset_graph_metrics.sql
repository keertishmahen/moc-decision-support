{{ config(materialized='view') }}

with dep_counts as (
  select asset_id, count(*) as n_dependencies
  from (
    select upstream_asset_id as asset_id from {{ ref('stg_asset_dependency') }}
    union all
    select downstream_asset_id as asset_id from {{ ref('stg_asset_dependency') }}
  ) d
  group by asset_id
),
moc_counts as (
  select asset_id, count(*) as n_mocs
  from {{ ref('stg_moc') }}
  group by asset_id
),
wo_counts as (
  select asset_id, count(*) as n_work_orders
  from {{ ref('stg_work_order') }}
  group by asset_id
),
hazard_counts as (
  select asset_id, count(*) as n_hazards
  from {{ ref('stg_hazard') }}
  group by asset_id
)

select
  a.asset_id,
  a.name as asset_name,
  a.equipment_type,
  a.area_id,
  a.criticality,
  coalesce(d.n_dependencies, 0) as n_dependencies,
  coalesce(h.n_hazards, 0) as n_hazards,
  coalesce(m.n_mocs, 0) as n_mocs,
  coalesce(w.n_work_orders, 0) as n_work_orders
from {{ ref('stg_asset') }} a
left join dep_counts d on a.asset_id = d.asset_id
left join hazard_counts h on a.asset_id = h.asset_id
left join moc_counts m on a.asset_id = m.asset_id
left join wo_counts w on a.asset_id = w.asset_id
