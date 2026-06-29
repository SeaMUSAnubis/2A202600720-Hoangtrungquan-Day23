# Agent Lab Report

## 1. Executive Summary

This lab implements a LangGraph support-ticket agent with stateful routing, mock tool execution, bounded retry, human-in-the-loop approval simulation, dead-letter handling, metrics export, and automated markdown report generation.

Current run result: **100.00% success rate** across **7 scenarios**. All sample scenarios passed.

## 2. Metrics Summary

| Metric | Value |
|---|---:|
| Total scenarios | 7 |
| Success rate | 100.00% |
| Average nodes visited | 6.43 |
| Total retries | 3 |
| Total approval steps | 2 |
| Resume success | No |

## 3. Per-Scenario Results

| Scenario | Success | Expected route | Actual route | Nodes visited | Retries | Approval observed | Errors |
|---|---|---|---|---:|---:|---|---|
| S01_simple | Yes | simple | simple | 4 | 0 | No | - |
| S02_tool | Yes | tool | tool | 6 | 0 | No | - |
| S03_missing | Yes | missing_info | missing_info | 4 | 0 | No | - |
| S04_risky | Yes | risky | risky | 8 | 0 | Yes | - |
| S05_error | Yes | error | error | 10 | 2 | No | Attempt 1 failed, retrying...<br>Attempt 2 failed, retrying... |
| S06_delete | Yes | risky | risky | 8 | 0 | Yes | - |
| S07_dead_letter | Yes | error | error | 5 | 1 | No | Attempt 1 failed, retrying... |

## 4. Architecture Explanation

The graph starts with `intake`, then sends the normalized query to `classify`. `classify_node` asks an LLM for structured route classification and falls back to a small heuristic only when the LLM call fails, which keeps the workflow runnable during local testing or API rate limits.

After classification, `route_after_classify` dispatches the state to one of five flows:

- `simple`: answer directly with `answer_node`, then `finalize`.
- `tool`: call `tool_node`, evaluate with `evaluate_node`, then either answer or retry.
- `missing_info`: call `ask_clarification_node` so the agent asks for more details instead of hallucinating.
- `risky`: prepare a proposed action, pass through `approval_node`, then continue to tool execution only when approved.
- `error`: enter the retry path first, then either retry tool execution or go to `dead_letter`.

The shared `AgentState` keeps the workflow serializable and inspectable. Append-only fields such as `messages`, `tool_results`, `errors`, and `events` preserve execution history. Overwrite fields such as `route`, `risk_level`, `attempt`, `evaluation_result`, `pending_question`, `proposed_action`, `approval`, and `final_answer` capture the latest decision or output.

Every terminal path goes through `finalize`, which creates a final audit event before the graph reaches `END`.

## 5. Route Behavior

| Route | Main path | Purpose |
|---|---|---|
| `simple` | `classify -> answer -> finalize` | Handle general support questions without tools. |
| `tool` | `classify -> tool -> evaluate -> answer -> finalize` | Use tool context before generating the answer. |
| `missing_info` | `classify -> clarify -> finalize` | Ask the user for required details. |
| `risky` | `classify -> risky_action -> approval -> tool -> evaluate -> answer -> finalize` | Require approval before side-effecting actions. |
| `error` | `classify -> retry -> tool -> evaluate -> retry/dead_letter` | Recover transient failures with a bounded retry loop. |

## 6. Output Files

- `outputs/metrics.json`: machine-readable run result used by local validation and grading. It stores summary metrics plus one detailed record per scenario.
- `reports/lab_report.md`: human-readable report generated from `outputs/metrics.json`.
- `data/sample/scenarios.jsonl`: sample inputs used to exercise all graph routes.

## 7. Failure Analysis

1. **LLM API failure or rate limit**: `classify_node` and `answer_node` catch provider errors. Classification falls back to deterministic heuristics, and answering returns a safe fallback message so the graph still terminates.
2. **Transient tool failure**: `tool_node` can return an error result for `error` scenarios. `evaluate_node` marks that as `needs_retry`, and `retry_or_fallback_node` increments `attempt`.
3. **Unbounded retry risk**: `route_after_retry` compares `attempt` with `max_attempts`. When the limit is reached, the graph routes to `dead_letter` instead of looping forever.
4. **Risky side effects**: refund, delete, email, and similar actions route through `risky_action_node` and `approval_node` before tool execution.
5. **Missing user context**: vague requests route to `ask_clarification_node`, avoiding unsupported assumptions.

## 8. Current Limitations

- `approval_node` currently uses mock approval for CI/local repeatability; it does not pause for a real reviewer.
- Persistence currently uses the memory checkpointer from `configs/lab.yaml`; SQLite/Postgres checkpointing is left as an extension.
- `evaluate_node` uses a simple heuristic instead of an LLM-as-judge.
- Tool execution is mocked, so no real order, refund, email, or account system is called.

## 9. Improvement Plan

- Add SQLite checkpointing and demonstrate state history or crash resume.
- Replace mock approval with LangGraph `interrupt()` for a real human review flow.
- Add LLM-as-judge evaluation for richer tool-result quality checks.
- Add latency measurement per node so `latency_ms` becomes meaningful.
- Expand hidden-style scenarios to test route priority, ambiguous requests, and retry edge cases.
