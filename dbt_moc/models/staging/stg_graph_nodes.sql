{{ config(materialized='view') }}

select
  node_id,
  node_label,
  properties_json
from {{ source('bronze', 'raw_graph_nodes') }}
