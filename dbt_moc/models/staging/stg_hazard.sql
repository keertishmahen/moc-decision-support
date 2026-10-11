{{ config(materialized='view') }}

select
  moc_id,
  asset_id,
  hazard_description,
  risk_level,
  overall_risk_score,
  risk_people,
  risk_asset,
  risk_community,
  risk_env,
  risk_likelihood
from {{ source('bronze', 'raw_hazard') }}
