import openai
import json
import os
from dotenv import load_dotenv
import numpy as np
from collections import defaultdict
from typing import List, Tuple, Set

# Load environment variables
load_dotenv('secret.env')

# Set OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# Initialize OpenAI client with new API
client = openai.OpenAI(api_key=api_key)

MAX_ROUNDS = 10

# Available tool names
AVAILABLE_TOOLS = {
    "summarize_field",
    "resample_evidence",
    "highlight_anomalies",
    "get_values_near_time",
    "list_possible_fields",
    "get_change_points",
    "compute_duration_above_threshold",
    "detect_event_instances"
}

def pretty_print_tool_result(tool_name, args, result):
    """Pretty print the result of a tool call."""
    print("\n" + "="*60)
    print(f"🔧 TOOL CALL: {tool_name}")
    print("="*60)
    
    # Print arguments
    print("📥 Arguments:")
    for key, value in args.items():
        if isinstance(value, list) and len(value) > 5:
            print(f"  {key}: {value[:3]}... (showing first 3 of {len(value)})")
        else:
            print(f"  {key}: {value}")
    
    print("\n📤 Result:")
    
    # Handle different result types
    if isinstance(result, dict):
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            for key, value in result.items():
                if isinstance(value, list):
                    if len(value) > 10:
                        print(f"  {key}: {len(value)} items (showing first 5)")
                        for i, item in enumerate(value[:5]):
                            print(f"    {i+1}. {item}")
                        print(f"    ... and {len(value) - 5} more items")
                    else:
                        print(f"  {key}: {len(value)} items")
                        for i, item in enumerate(value):
                            print(f"    {i+1}. {item}")
                elif isinstance(value, (int, float)):
                    # Format numbers nicely
                    if isinstance(value, float):
                        print(f"  {key}: {value:.6f}")
                    else:
                        print(f"  {key}: {value}")
                else:
                    print(f"  {key}: {value}")
    else:
        print(f"  {result}")
    
    print("="*60 + "\n")

def validate_tool_calls(tool_calls):
    """Validate tool calls and return errors and valid calls."""
    errors = []
    valid_calls = []

    for i, call in enumerate(tool_calls):
        tool = call.get("tool")
        if not tool:
            errors.append(f"Tool call {i}: Missing 'tool' field")
        elif tool not in AVAILABLE_TOOLS:
            errors.append(f"Tool call {i}: Unknown tool '{tool}'")
        else:
            valid_calls.append(call)

    return {
        "valid": not errors,
        "errors": errors,
        "valid_calls": valid_calls
    }

def get_available_tools():
    """Return list of tool names."""
    return list(AVAILABLE_TOOLS)

def handle_tool_calls(tool_calls, parsed_data):
    """Process validated tool calls with real implementations."""
    print(f"Handling tool calls: {tool_calls}")
    validation = validate_tool_calls(tool_calls)

    if not validation["valid"]:
        return {
            "validation_error": True,
            "errors": validation["errors"],
            "available_tools": get_available_tools()
        }

    results = defaultdict(list)

    for call in validation["valid_calls"]:
        tool = call["tool"]
        args = call.get("args", {})

        try:
            if tool == "summarize_field":
                result = summarize_field(
                    field=args["field"],
                    message_types=args["message_types"],
                    parsed_data=parsed_data
                )

            elif tool == "get_change_points":
                result = get_change_points(
                    field=args["field"],
                    message_types=args["message_types"],
                    parsed_data=parsed_data
                )

            elif tool == "get_values_near_time":
                result = get_values_near_time(
                    field=args["field"],
                    message_types=args["message_types"],
                    parsed_data=parsed_data,
                    query_time_us=args["query_time_us"],
                    tolerance=args.get("tolerance", 1_000_000)
                )

            elif tool == "compute_duration_above_threshold":
                result = compute_duration_above_threshold(
                    field=args["field"],
                    message_types=args["message_types"],
                    parsed_data=parsed_data,
                    threshold=args["threshold"]
                )

            elif tool == "highlight_anomalies":
                result = highlight_anomalies(
                    field=args["field"],
                    message_types=args["message_types"],
                    parsed_data=parsed_data,
                    z_thresh=args.get("z_thresh", 3.0)
                )

            elif tool == "list_possible_fields":
                result = list_possible_fields(parsed_data)

            elif tool == "resample_evidence":
                result = resample_evidence(
                    evidence=args["evidence"],
                    n_samples=args.get("n_samples", 10)
                )

            elif tool == "detect_event_instances":
                result = detect_event_instances(
                    field=args["field"],
                    message_types=args["message_types"],
                    parsed_data=parsed_data,
                    trigger_value=args.get("trigger_value", 1)
                )

            else:
                result = {"error": f"Unhandled tool '{tool}'"}

        except Exception as e:
            result = {"error": f"Exception during tool execution: {str(e)}"}

        # Pretty print the tool result
        pretty_print_tool_result(tool, args, result)
        
        results[tool].append(result)

    return dict(results)

def handle_tool_calls_with_strategies(
    tool_calls: List[dict],
    parsed_data: dict,
    available_fields: Set[str],
    attempted_fields: Set[Tuple[str, Tuple[str, ...]]],
    successful_summaries: int,
    round_count: int,
    max_rounds: int = 10,
    max_summary_limit: int = 2
):
    filtered_calls = []

    for call in tool_calls:
        tool = call.get("tool")
        args = call.get("args", {})

        field = args.get("field")
        message_types = tuple(args.get("message_types", []))  # normalize as tuple

        if not field or not message_types:
            continue  # malformed call

        key = (field, message_types)

        # Skip already-attempted fields or unavailable ones
        if key in attempted_fields or field not in available_fields:
            continue

        attempted_fields.add(key)
        filtered_calls.append(call)

    if not filtered_calls:
        return {
            "status": "stopped",
            "reason": "No valid or new tool calls",
            "result": {}
        }

    # Actually run the tool calls
    result = handle_tool_calls(filtered_calls, parsed_data)

    # Count new successful summaries
    for r in result.get("summarize_field", []):
        if isinstance(r, dict) and "mean" in r:
            successful_summaries += 1

    round_count += 1

    # If we’ve collected enough useful results or exhausted rounds,
    # it's better to return them and let the LLM synthesize a final answer
    if successful_summaries >= max_summary_limit or round_count >= max_rounds:
        return {
            "status": "done_collecting",
            "result": result,
            "reason": "Collected enough evidence or hit round limit",
            "round_count": round_count,
            "successful_summaries": successful_summaries,
            "attempted_fields": attempted_fields
        }

    return {
        "status": "continue",
        "result": result,
        "round_count": round_count,
        "successful_summaries": successful_summaries,
        "attempted_fields": attempted_fields
    }


def summarize_field(field: str, message_types: list, parsed_data: dict):
    values = []
    for msg in message_types:
        for row in parsed_data.get(msg, []):
            if field in row:
                try:
                    values.append(float(row[field]))
                except (ValueError, TypeError):
                    continue

    if not values:
        return {"error": f"No valid values found for field '{field}' in messages {message_types}"}

    array = np.array(values)
    return {
        "min": float(np.min(array)),
        "max": float(np.max(array)),
        "mean": float(np.mean(array)),
        "std": float(np.std(array))
    }

def get_change_points(field: str, message_types: list, parsed_data: dict):
    change_points = []

    for msg in message_types:
        last_val = None
        for row in parsed_data.get(msg, []):
            if field in row:
                val = row[field]
                if last_val is not None and val != last_val:
                    change_points.append({
                        "time": row.get("timeus"),
                        "value": val,
                        "message_type": msg
                    })
                last_val = val

    return {"change_points": change_points}

def get_values_near_time(field: str, message_types: list, parsed_data: dict, query_time_us: int, tolerance: int = 1_000_000):
    matched = []

    for msg in message_types:
        for row in parsed_data.get(msg, []):
            row_time = row.get("timeus")
            if row_time is not None and abs(row_time - query_time_us) <= tolerance:
                if field in row:
                    matched.append({
                        "time": row_time,
                        "value": row[field],
                        "message_type": msg
                    })

    return {"matched_rows": matched}


def compute_duration_above_threshold(field: str, message_types: list, parsed_data: dict, threshold: float):
    total_time = 0
    for msg in message_types:
        rows = parsed_data.get(msg, [])
        rows = sorted(rows, key=lambda r: r.get("timeus", 0))

        for i in range(1, len(rows)):
            prev, curr = rows[i-1], rows[i]
            if field in prev and float(prev[field]) > threshold:
                delta = curr.get("timeus", 0) - prev.get("timeus", 0)
                total_time += max(delta, 0)

    return {"duration_above_threshold": total_time}


def highlight_anomalies(field: str, message_types: list, parsed_data: dict, z_thresh: float = 3.0):
    values = []
    indexed_rows = []

    for msg in message_types:
        for row in parsed_data.get(msg, []):
            if field in row:
                try:
                    val = float(row[field])
                    values.append(val)
                    indexed_rows.append((row.get("timeus"), val, msg))
                except (ValueError, TypeError):
                    continue

    if not values:
        return {"anomalies_found": 0, "anomalies": []}

    mean = np.mean(values)
    std = np.std(values)

    anomalies = [
        {"time": t, "value": v, "message_type": m}
        for t, v, m in indexed_rows
        if abs(v - mean) > z_thresh * std
    ]

    return {"anomalies_found": len(anomalies), "anomalies": anomalies}


def list_possible_fields(parsed_data: dict):
    field_set = set()
    for msg_rows in parsed_data.values():
        for row in msg_rows:
            field_set.update(row.keys())
    return {"available_fields": sorted(field_set)}


def resample_evidence(evidence: list, n_samples: int = 10):
    if not evidence:
        return {"resampled_points": 0, "resampled": []}

    step = max(1, len(evidence) // n_samples)
    sampled = evidence[::step][:n_samples]

    return {
        "resampled_points": len(sampled),
        "resampled": sampled
    }


def detect_event_instances(field: str, message_types: list, parsed_data: dict, trigger_value=1):
    events = []
    for msg in message_types:
        for row in parsed_data.get(msg, []):
            if field in row and row[field] == trigger_value:
                events.append({
                    "time": row.get("timeus"),
                    "message_type": msg,
                    "condition_met": True
                })

    return {"event_instances": events}


def run_stage_3(parsed_data: dict, question=None, stage2=None, extra_context=None, messages=None, model="gpt-4.1-mini-2025-04-14"):
    parser_data_keys = list(parsed_data.keys())

    system_prompt = f"""You are a MAVLink log-analysis assistant.

Your job is to process telemetry log queries by combining:
- the original question ("original_question"),
- Stage 2's "intent", "field", "candidate_messages" and "evidence",
- any extra context (e.g. query_time_us, missing sources).

If you have enough information to answer the question accurately and helpfully, you should provide a final answer.
Even when no anomalies or events are detected, you **must still describe the data behavior** (e.g., value range, consistency, change points). Use `summarize_field`, `get_change_points`, or `resample_evidence` as needed to provide useful context.

If you cannot answer confidently due to:
- Missing information,
- Insufficient evidence,
- Need for more statistics or derived values,

then you may either:
1. Ask a clarification question, or
2. Request one or more tool calls.

You MUST respond with a valid JSON object in one of the following three formats:

// 1. Clarification needed
{{
  "clarification_needed": true,
  "clarification_question": "..."
}}

// 2. Tool calls needed
{{
  "clarification_needed": false,
  "tool_calls": [
    {{ "tool": "tool_name", "args": {{ "arg1": ..., "arg2": ... }} }}
  ]
}}

// 3. Final answer ready
{{
  "clarification_needed": false,
  "tool_calls": [],
  "final_answer": "..."
}}

Do NOT mix clarification, tool_calls, or final_answer in a single response.

IMPORTANT RULES:
- Do not include more than 20 message types in a single tool call.
- Only use the tools listed below.
- When using a tool that requires message_types, prefer those known to contain the target field.
- Keep argument names exactly as listed below (no camelCase or abbreviations).
- **Only use message types from this list:** {parser_data_keys}

Available tools:

1. summarize_field
   Args:
     - field (str)
     - message_types (list[str])

2. get_change_points
   Args:
     - field (str)
     - message_types (list[str])

3. get_values_near_time
   Args:
     - field (str)
     - message_types (list[str])
     - query_time_us (int)
     - tolerance (int, optional, default = 1000000)

4. compute_duration_above_threshold
   Args:
     - field (str)
     - message_types (list[str])
     - threshold (float)

5. highlight_anomalies
   Args:
     - field (str)
     - message_types (list[str])
     - z_thresh (float, optional, default = 3.0)

6. list_possible_fields
   Args: none

7. resample_evidence
   Args:
     - evidence (list[dict])
     - n_samples (int, optional, default = 10)

8. detect_event_instances
   Args:
     - field (str)
     - message_types (list[str])
     - trigger_value (int, optional, default = 1)
"""

    # === If continuing from clarification, messages will be passed in ===
    if messages is None:
        user_prompt = {
            "original_question": question,
            "intent": stage2.get("intent"),
            "field": stage2.get("field"),
            "candidate_messages": stage2.get("candidate_messages"),
            "evidence": stage2.get("evidence"),
            "extra_context": extra_context or {}
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, indent=2)}
        ]

    # === Strategy Tracking State ===
    attempted_fields = set()
    successful_summaries = 0
    round_count = 0
    available_fields = set(list_possible_fields(parsed_data).get("available_fields", []))

    for round_num in range(1, MAX_ROUNDS + 1):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"}
        )

        content = json.loads(response.choices[0].message.content)

        # Pretty print the content from this round
        pretty_print_stage3_content(content, round_num)

        # Log assistant response to message list
        messages.append({
            "role": "assistant",
            "content": json.dumps(content, indent=2)
        })

        # === CLARIFICATION ===
        if content.get("clarification_needed"):
            clarification_q = content.get("clarification_question", "Can you clarify your question?")
            print(f"[Stage 3 Agent] Clarification needed: {clarification_q}")
            result = {
                "status": "clarification_requested",
                "question": clarification_q,
                "messages": messages
            }
            pretty_print_stage3_result(result)
            return result

        # === TOOL CALLS ===
        elif content.get("tool_calls"):
            strategy_result = handle_tool_calls_with_strategies(
                tool_calls=content["tool_calls"],
                parsed_data=parsed_data,
                available_fields=available_fields,
                attempted_fields=attempted_fields,
                successful_summaries=successful_summaries,
                round_count=round_count
            )

            if strategy_result["status"] == "continue":
                # Inject tool results and loop again
                messages.append({
                    "role": "user",
                    "content": json.dumps({
                        "tool_results": strategy_result["result"]
                    }, indent=2)
                })

            elif strategy_result["status"] == "done_collecting":
                # Add results and prompt for final answer
                messages.append({
                    "role": "user",
                    "content": json.dumps({
                        "tool_results": strategy_result["result"],
                        "note": "Please provide your final answer based on these summaries."
                    }, indent=2)
                })

            elif strategy_result["status"] == "stopped":
                # Cannot proceed anymore
                messages.append({
                    "role": "user",
                    "content": json.dumps({
                        "reason": strategy_result["reason"]
                    }, indent=2)
                })
                return {
                    "status": "incomplete",
                    "message": f"Stopped early: {strategy_result['reason']}",
                    "messages": messages
                }


        # === FINAL ANSWER ===
        elif content.get("final_answer"):
            result = {
                "status": "answered",
                "answer": content["final_answer"],
                "messages": messages
            }
            pretty_print_stage3_result(result)
            return result

        else:
            raise ValueError("Invalid LLM response format. Missing required keys.")

    # === Fallback after max rounds ===
    result = {
        "status": "incomplete",
        "message": "Couldn't complete the reasoning chain in allotted steps.",
        "messages": messages
    }
    pretty_print_stage3_result(result)
    return result

def pretty_print_stage3_content(content, round_num=None):
    """Pretty print the content from run_stage_3."""
    if round_num:
        print(f"\n🔄 ROUND {round_num}")
        print("="*60)
    
    if content.get("clarification_needed"):
        print("❓ CLARIFICATION REQUESTED")
        print("="*60)
        print(f"Question: {content.get('clarification_question', 'No question provided')}")
        
    elif content.get("tool_calls"):
        print("🔧 TOOL CALLS REQUESTED")
        print("="*60)
        tool_calls = content["tool_calls"]
        print(f"Number of tool calls: {len(tool_calls)}")
        for i, call in enumerate(tool_calls):
            print(f"\nTool Call {i+1}:")
            print(f"  Tool: {call.get('tool', 'Unknown')}")
            print(f"  Args: {call.get('args', {})}")
            
    elif content.get("final_answer"):
        print("✅ FINAL ANSWER")
        print("="*60)
        print(f"Answer: {content['final_answer']}")
        
    else:
        print("⚠️  UNKNOWN RESPONSE FORMAT")
        print("="*60)
        print(f"Content: {content}")
    
    print("="*60 + "\n")

def pretty_print_stage3_result(result):
    """Pretty print the final result from run_stage_3."""
    print("\n" + "🎯" + "="*58)
    print("STAGE 3 FINAL RESULT")
    print("="*60)
    
    status = result.get("status", "unknown")
    print(f"Status: {status}")
    
    if status == "clarification_requested":
        print(f"Question: {result.get('question', 'No question provided')}")
        print(f"Messages exchanged: {len(result.get('messages', []))}")
        
    elif status == "answered":
        print(f"Answer: {result.get('answer', 'No answer provided')}")
        print(f"Total messages exchanged: {len(result.get('messages', []))}")
        
    elif status == "incomplete":
        print(f"Message: {result.get('message', 'No message provided')}")
        print(f"Messages exchanged: {len(result.get('messages', []))}")
        
    print("="*60 + "\n")
