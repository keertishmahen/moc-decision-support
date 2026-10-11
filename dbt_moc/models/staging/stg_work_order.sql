{{ config(materialized='view') }}

select
  wo_id,
  id,
  moc_id,
  title,
  work_type,
  priority,
  asset_id,
  planned_hrs,
  actual_hrs,
  estimated_cost,
  actual_cost,
  status,
  delay_reason
from {{ source('bronze', 'raw_work_order') }}
