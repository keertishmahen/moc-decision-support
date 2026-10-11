{{ config(materialized='table') }}

-- ML labels: seed GROUND_TRUTH, else CSV actual_manhours, else MoC actual_downtime
with csv_moc as (
  select
    node_id as moc_id,
    try_to_double(to_varchar(parse_json(properties_json):actual_manhours)) as actual_manhours,
    try_to_double(to_varchar(parse_json(properties_json):actual_cost)) as csv_cost
  from {{ ref('stg_graph_nodes') }}
  where node_label = 'MoC'
)

select
  e.moc_id,
  e.change_type,
  e.asset_category,
  e.risk_level,
  coalesce(l.shutdown_required, case when e.actual_downtime > 0 or e.estimated_downtime > 0 then 1 else 0 end) as shutdown_required,
  case when e.hazop_required then 1 else 0 end as hazop_required,
  case when e.pssr_required then 1 else 0 end as pssr_required,
  coalesce(l.n_dependencies, e.n_dependencies) as n_dependencies,
  coalesce(l.n_hazards, e.n_hazards) as n_hazards,
  coalesce(l.n_mocs, e.n_mocs) as n_mocs,
  coalesce(l.n_work_orders, e.n_work_orders) as n_work_orders,
  coalesce(l.cost, c.csv_cost, e.actual_cost) as cost,
  coalesce(
    l.downtime,
    c.actual_manhours,
    case
      when e.actual_downtime > 0 then e.actual_downtime
      else greatest(e.estimated_downtime, e.n_work_orders * 10)
    end
  ) as downtime
from {{ ref('int_moc_enriched') }} e
left join {{ ref('moc_ml_labels') }} l on e.moc_id = l.moc_id
left join csv_moc c on e.moc_id = c.moc_id
