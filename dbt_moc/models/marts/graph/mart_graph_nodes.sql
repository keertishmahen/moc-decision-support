{{ config(materialized='table') }}

-- Full Bloom schema: all labels from JSON export + Plant/ApprovalStage/Resource/_GraphConfig
select
  node_id,
  node_label,
  properties_json
from {{ ref('stg_graph_nodes') }}
