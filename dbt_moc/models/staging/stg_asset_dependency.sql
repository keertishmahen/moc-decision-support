{{ config(materialized='view') }}

select
  upstream_asset_id,
  downstream_asset_id
from {{ source('bronze', 'raw_dependency') }}
