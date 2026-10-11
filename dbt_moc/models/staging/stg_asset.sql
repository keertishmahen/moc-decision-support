{{ config(materialized='view') }}

select
  asset_id,
  id,
  name,
  equipment_type,
  area_id,
  criticality,
  pid_reference
from {{ source('bronze', 'raw_asset') }}
