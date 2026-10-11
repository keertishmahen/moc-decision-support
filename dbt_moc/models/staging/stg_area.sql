{{ config(materialized='view') }}

select
  id as area_id,
  name as area_name
from {{ source('bronze', 'raw_area') }}
