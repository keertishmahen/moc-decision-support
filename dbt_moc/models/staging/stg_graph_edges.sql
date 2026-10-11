{{ config(materialized='view') }}

select
  src_id,
  src_label,
  rel_type,
  dst_id,
  dst_label,
  properties_json
from {{ source('bronze', 'raw_graph_edges') }}
