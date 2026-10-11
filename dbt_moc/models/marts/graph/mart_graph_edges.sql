{{ config(materialized='table') }}

select
  src_id,
  src_label,
  rel_type,
  dst_id,
  dst_label,
  properties_json
from {{ ref('stg_graph_edges') }}
