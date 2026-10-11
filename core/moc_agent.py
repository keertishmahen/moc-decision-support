"""
core/moc_agent.py
Enhancement 3: Agent-Based Execution for Advanced Reasoning

A multi-step reasoning agent that uses OpenAI function/tool calling to
orchestrate Neo4j graph queries, vector search, downtime propagation, and
risk analysis in a structured loop.

The agent:
  1. Receives a user query
  2. Decides which tools to call (graph queries, vector search, propagation)
  3. Executes the tools and observes results
  4. Iterates until it has enough information to answer
  5. Returns a structured, grounded response

This replaces the single-shot RAG approach for complex multi-step queries
like "What would happen if R-201 goes offline for 48 hours?" or
"Compare the risk profiles of all instrumentation MoCs".
"""

from __future__ import annotations
import json
from typing import Any
from openai import OpenAI

from core.config import OPENAI_API_KEY, OPENAI_MODEL
from core.neo4j_client import Neo4jClient
from core.downtime_propagator import DowntimePropagator, propagation_result_to_dict
from core.vector_store import VectorStore


# ── Tool definitions for OpenAI function calling ───────────────────────────
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_moc_detail",
            "description": (
                "Retrieve full details of a specific MoC record including risk scores, "
                "costs, hazards, work orders, HAZOP/PSSR status, and lessons learned."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "moc_id": {
                        "type": "string",
                        "description": "MoC ID e.g. MoC-001, MoC-005"
                    }
                },
                "required": ["moc_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_asset_connectivity",
            "description": (
                "Get the full connectivity map for an asset — all upstream and downstream "
                "connections with relationship types, flow metadata, and criticality scores."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "string",
                        "description": "Asset ID e.g. P-101, R-201, SV-204"
                    }
                },
                "required": ["asset_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propagate_downtime",
            "description": (
                "Propagate downtime from a source asset through the process topology. "
                "Returns all downstream assets with estimated propagated downtime hours, "
                "confidence intervals, coupling factors, and risk levels. "
                "Use this when asked about the impact of an asset going offline."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "string",
                        "description": "The asset that is going offline"
                    },
                    "downtime_hours": {
                        "type": "number",
                        "description": "Estimated downtime at the source asset in hours"
                    }
                },
                "required": ["asset_id", "downtime_hours"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_similar_mocs",
            "description": (
                "Search for semantically similar MoCs using vector similarity. "
                "Returns the most relevant historical MoCs for a given description or query."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language description to search for"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_impact_chain",
            "description": (
                "Get the enriched impact chain for an asset — all downstream assets "
                "with hop distances, relationship types, criticality, and active MoC counts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "string",
                        "description": "Asset ID to trace impacts from"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Maximum hop depth (default 4)",
                        "default": 4
                    }
                },
                "required": ["asset_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_assessment",
            "description": (
                "Get the risk assessment details for a specific MoC including "
                "risk scores, likelihood, consequence categories, and HAZOP/PSSR outcomes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "moc_id": {
                        "type": "string",
                        "description": "MoC ID to get risk assessment for"
                    }
                },
                "required": ["moc_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_process_topology",
            "description": (
                "Get the complete FCC Unit process flow topology as a list of "
                "directed edges between assets with relationship types and flow metadata. "
                "Use this for system-wide topology analysis."
            ),
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_connectivity_score",
            "description": (
                "Compute a connectivity score for an asset based on its number of "
                "connections, associated MoCs, hazards, criticality, and ESD status. "
                "Higher score = more critical node in the process network."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "string",
                        "description": "Asset ID to score"
                    }
                },
                "required": ["asset_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_work_orders",
            "description": (
                "Get all work orders for a specific MoC with planned vs actual "
                "hours, costs, delay reasons, and failure modes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "moc_id": {
                        "type": "string",
                        "description": "MoC ID to get work orders for"
                    }
                },
                "required": ["moc_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hazards_for_asset",
            "description": (
                "Get all hazards associated with an asset including failure modes, "
                "risk scores, and categories."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "string",
                        "description": "Asset ID to get hazards for"
                    }
                },
                "required": ["asset_id"]
            }
        }
    },
]

# ── Agent system prompt ────────────────────────────────────────────────────
AGENT_SYSTEM_PROMPT = """You are MoCBot Agent — an advanced reasoning agent for the FCC Unit
Management of Change (MoC) system at Refinery A.

You have access to tools that query the live Neo4j knowledge graph, perform
vector similarity search, and run downtime propagation analysis.

REASONING APPROACH:
1. Analyse the user's question to identify what data you need
2. Call the appropriate tools to gather that data
3. Synthesise the tool results into a precise, grounded answer
4. Always cite specific MoC IDs, asset IDs, costs, and risk scores
5. For downtime/impact questions, always run propagate_downtime first
6. For topology questions, use get_process_topology or get_asset_connectivity
7. Never guess — if data is missing, say so explicitly

DATASET CONTEXT:
- 10 MoC records (MoC-001 to MoC-010) covering the FCC Unit
- 22 assets including R-201 (Reactor), SV-204 (Catalyst Slide Valve),
  CTL-205 (Transfer Line), RG-401 (Regenerator), F-501 (Fractionator)
- 21 work orders, 4 incidents, 10 hazards, 10 risk assessments

STRICT RULES:
- Always use tool results — never fabricate data
- Cite exact values from tool outputs (costs, hours, scores)
- For multi-asset queries, call tools for each relevant asset
- Limit tool calls to what is necessary (max 6 per query)
"""


class MoCAgent:
    """
    Agent-based execution engine for advanced MoC reasoning.

    Uses OpenAI function calling to orchestrate multiple tool calls
    in a reasoning loop before generating a final answer.

    Usage:
        agent = MoCAgent()
        result = agent.run("What would happen if R-201 goes offline for 48 hours?")
        print(result["response"])
    """

    def __init__(self, max_iterations: int = 6):
        self.client     = OpenAI(api_key=OPENAI_API_KEY)
        self.neo4j      = Neo4jClient()
        self.propagator = DowntimePropagator(self.neo4j)
        self.vector     = VectorStore()
        self.max_iter   = max_iterations

    def run(self, user_query: str) -> dict:
        """
        Execute the agent loop for a user query.

        Returns:
            dict with keys: response, tool_calls_made, iterations, context_used
        """
        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user",   "content": user_query},
        ]

        tool_calls_log: list[dict] = []
        iterations = 0

        while iterations < self.max_iter:
            iterations += 1

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                tools=AGENT_TOOLS,
                tool_choice="auto",
                temperature=0.1,
            )

            msg = response.choices[0].message

            # No more tool calls — final answer
            if not msg.tool_calls:
                return {
                    "response":        msg.content or "",
                    "tool_calls_made": tool_calls_log,
                    "iterations":      iterations,
                    "context_used":    [tc["tool"] for tc in tool_calls_log],
                }

            # Append assistant message with tool calls
            messages.append({
                "role":       "assistant",
                "content":    msg.content,
                "tool_calls": [
                    {
                        "id":       tc.id,
                        "type":     "function",
                        "function": {
                            "name":      tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in msg.tool_calls
                ],
            })

            # Execute each tool call
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                result = self._execute_tool(tool_name, args)
                tool_calls_log.append({
                    "tool":   tool_name,
                    "args":   args,
                    "result": result,
                })

                # Append tool result to messages
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      json.dumps(result, default=str),
                })

        # Max iterations reached — ask for final answer without tools
        messages.append({
            "role":    "user",
            "content": "Please provide your final answer based on the tool results above.",
        })
        final = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.1,
        )
        return {
            "response":        final.choices[0].message.content or "",
            "tool_calls_made": tool_calls_log,
            "iterations":      iterations,
            "context_used":    [tc["tool"] for tc in tool_calls_log],
        }

    def _execute_tool(self, tool_name: str, args: dict) -> Any:
        """Dispatch a tool call to the appropriate backend method."""
        try:
            if tool_name == "get_moc_detail":
                result = self.neo4j.get_moc_full_detail(args["moc_id"])
                return result or {"error": f"MoC {args['moc_id']} not found"}

            elif tool_name == "get_asset_connectivity":
                result = self.neo4j.get_full_connectivity_map(args["asset_id"])
                return result or {"error": f"Asset {args['asset_id']} not found"}

            elif tool_name == "propagate_downtime":
                result = self.propagator.propagate(
                    source_asset_id=args["asset_id"],
                    source_downtime_hours=float(args.get("downtime_hours", 24.0)),
                )
                return propagation_result_to_dict(result)

            elif tool_name == "search_similar_mocs":
                hits = self.vector.search(
                    args["query"],
                    top_k=int(args.get("top_k", 5))
                )
                return {"hits": hits, "count": len(hits)}

            elif tool_name == "get_impact_chain":
                chain = self.neo4j.get_enriched_impact_chain(
                    args["asset_id"],
                    depth=int(args.get("depth", 4))
                )
                return {"chain": chain, "count": len(chain)}

            elif tool_name == "get_risk_assessment":
                ra = self.neo4j.get_risk_assessment(args["moc_id"])
                hp = self.neo4j.get_hazop_pssr(args["moc_id"])
                return {"risk_assessment": ra, "hazop_pssr": hp}

            elif tool_name == "get_process_topology":
                topology = self.neo4j.get_process_flow_topology()
                # Summarise to avoid token overflow
                return {
                    "edge_count": len(topology),
                    "edges": topology[:50],  # First 50 edges
                    "note": f"Showing 50 of {len(topology)} total edges"
                }

            elif tool_name == "get_connectivity_score":
                score = self.neo4j.get_asset_connectivity_score(args["asset_id"])
                return score

            elif tool_name == "get_work_orders":
                wos = self.neo4j.get_work_orders_for_moc(args["moc_id"])
                return {"work_orders": wos, "count": len(wos)}

            elif tool_name == "get_hazards_for_asset":
                hazards = self.neo4j.get_hazards_for_asset(args["asset_id"])
                return {"hazards": hazards, "count": len(hazards)}

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"error": f"Tool execution failed: {type(e).__name__}: {str(e)[:200]}"}


# ── Convenience function for API use ──────────────────────────────────────

def run_agent(query: str, max_iterations: int = 6) -> dict:
    """
    Convenience wrapper to run the MoCAgent for a single query.
    Handles agent instantiation and returns a serialisable result dict.
    """
    agent = MoCAgent(max_iterations=max_iterations)
    return agent.run(query)
