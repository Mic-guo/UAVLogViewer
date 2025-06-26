import gzip
import json
import random
import numpy as np
import math

# # Load the compressed JSON file
# file_path = "parsed_arenaTest.json.gz"

# with gzip.open(file_path, "rt", encoding="utf-8") as f:
#     test_parsed_data = json.load(f)

# Load message definitions once
with open("message_definitions.json", "r") as f:
    message_definitions = json.load(f)

def run_stage_2(classified: dict, parsed_data: dict): #, parsed_data: dict
    intent = classified.get("intent")
    target_type = classified.get("target_type")
    target = classified.get("target")
    candidate_messages = classified.get("candidate_messages", [])
    extra_params = classified.get("extra_params", {})

    # Crosscheck candidate_messages against parsed_data keys
    available_keys = set(parsed_data.keys())
    if candidate_messages:
        candidate_messages = [msg for msg in candidate_messages if msg in available_keys]

    if not candidate_messages:
        return dispatch_intent("fallback", target, [], parsed_data, extra_params)


    def is_field_based_intent(intent):
        return intent in {
            "anomaly_detection", "summary", "change_detection",
            "value_at_time", "max_value", "min_value", "event_detection"
        }

    if target_type == "field":
        return dispatch_intent(intent, target, candidate_messages, parsed_data, extra_params)

    elif target_type == "message":
        if target not in message_definitions:
            return build_response(intent, target, [], None, error=f"Unknown message type '{target}'.")

        if is_field_based_intent(intent):
            fields = message_definitions[target].get("fields", [])
            valid_fields = [
                f for f in fields
                if f.lower() not in {"timeus", "mavpackettype"}
            ]
            print(f"Valid fields: {valid_fields}")

            evidence_by_field = {}
            for field in valid_fields:
                result = dispatch_intent(intent, field, [target], parsed_data, extra_params)
                if result.get("evidence"):
                    evidence_by_field[field] = result["evidence"]

            return build_response(
                intent=intent,
                field=None,
                candidate_messages=[target],
                evidence=evidence_by_field
            )

        else:
            return dispatch_intent(intent, None, [target], parsed_data, extra_params)

    elif intent == "fallback":
        return dispatch_intent("fallback", target, [], parsed_data, extra_params)

    else:
        return build_response(intent or "unknown", target, candidate_messages, None, error="Invalid or missing target_type")


def dispatch_intent(intent, target_field, candidate_messages, parsed_data, extra_params=None):
    extra_params = extra_params or {}

    if intent == "max_value":
        return handle_max_value(target_field, candidate_messages, parsed_data)
    elif intent == "min_value":
        return handle_min_value(target_field, candidate_messages, parsed_data)
    elif intent == "event_detection":
        return handle_event_detection(target_field, candidate_messages, parsed_data)
    elif intent == "time_duration":
        return handle_time_duration(target_field, candidate_messages, parsed_data)
    elif intent == "value_at_time":
        query_time_us = extra_params.get("query_time_us")
        if query_time_us is None:
            return build_response(
                intent="value_at_time",
                field=target_field,
                candidate_messages=candidate_messages,
                evidence=None,
                error="Missing query_time_us for value_at_time intent"
            )
        return handle_value_at_time(target_field, candidate_messages, parsed_data, query_time_us)
    elif intent == "summary":
        return handle_summary(target_field, candidate_messages, parsed_data)
    elif intent == "change_detection":
        return handle_change_detection(target_field, candidate_messages, parsed_data)
    elif intent == "anomaly_detection":
        return handle_anomaly_detection(target_field, candidate_messages, parsed_data)
    elif intent == "fallback":
        return handle_fallback(parsed_data)
    else:
        return build_response("unknown", target_field, candidate_messages, None, error=f"Unhandled intent: {intent}")


def build_response(intent, field, candidate_messages, evidence, **optional):
    response = {
        "intent": intent,
        "field": field,
        "candidate_messages": candidate_messages,
        "evidence": evidence if evidence else None
    }

    response.update({k: v for k, v in optional.items() if v is not None})
    
    # Ensure all values are JSON serializable by handling NaN values
    return handle_nan_values(response)


def handle_max_value(field, candidate_messages, parsed_data):
    max_values = []

    for msg in candidate_messages:
        max_entry = None
        for row in parsed_data.get(msg, []):
            if field in row:
                if max_entry is None or row[field] > max_entry["value"]:
                    max_entry = {
                        "message_type": msg,
                        "value": row[field],
                        "time": row.get("timeus"),
                        "full_row": row
                    }
        if max_entry:
            max_values.append(max_entry)

    return build_response("max_value", field, candidate_messages, max_values or None)


def handle_min_value(field, candidate_messages, parsed_data):
    min_values = []

    for msg in candidate_messages:
        min_entry = None
        for row in parsed_data.get(msg, []):
            if field in row:
                if min_entry is None or row[field] < min_entry["value"]:
                    min_entry = {
                        "message_type": msg,
                        "value": row[field],
                        "time": row.get("timeus"),
                        "full_row": row
                    }
        if min_entry:
            min_values.append(min_entry)

    return build_response("min_value", field, candidate_messages, min_values or None)


def handle_event_detection(field, candidate_messages, parsed_data, max_transitions=10):
    transitions = []

    for msg in candidate_messages:
        rows = parsed_data.get(msg, [])
        prev_value = None

        field_values = [row[field] for row in rows if field in row]
        if len(set(field_values)) <= 1:
            continue  # skip fields that never change

        for row in rows:
            if field not in row:
                continue
            current_value = row[field]
            time = row.get("timeus")

            if prev_value is not None and current_value != prev_value:
                transitions.append({
                    "message_type": msg,
                    "field": field,
                    "old_value": prev_value,
                    "new_value": current_value,
                    "time": time,
                    "full_row": row
                })

            prev_value = current_value

    # Cap transitions to avoid overwhelming Stage 3
    # transitions = transitions[:max_transitions]
    transitions = transitions # TODO: Turn off max transitions for now

    return build_response(
        intent="event_detection",
        field=field,
        candidate_messages=candidate_messages,
        evidence=transitions or None
    )


def handle_time_duration(field, candidate_messages, parsed_data):
    durations = []

    for msg in candidate_messages:
        timestamps = [row["timeus"] for row in parsed_data.get(msg, []) if "timeus" in row]
        if not timestamps:
            continue

        start_time = min(timestamps)
        end_time = max(timestamps)
        duration_us = end_time - start_time
        duration_s = duration_us / 1e6

        durations.append({
            "message_type": msg,
            "start_time": start_time,
            "end_time": end_time,
            "duration_us": duration_us,
            "duration_s": duration_s
        })

    return build_response("time_duration", field, candidate_messages, durations or None)


def handle_value_at_time(field, candidate_messages, parsed_data, query_time_us, window_us=500_000, max_per_msg=5):
    def get_matching_field(row, target_field):
        for key in row:
            if key.lower() == target_field.lower():
                return key
        return None

    results = []
    availability_report = []

    for msg in candidate_messages:
        message_rows = parsed_data.get(msg, [])

        if not message_rows:
            availability_report.append({
                "message_type": msg,
                "status": "no_data"
            })
            continue

        sample_row = next((r for r in message_rows if "timeus" in r), None)
        available_fields = list(sample_row.keys()) if sample_row else []

        matched_rows = []
        for row in message_rows:
            if "timeus" not in row:
                continue
            matching_field = get_matching_field(row, field)
            if matching_field is None:
                continue
            diff = abs(row["timeus"] - query_time_us)
            if diff <= window_us:
                matched_rows.append({
                    "message_type": msg,
                    "value": row[matching_field],
                    "timestamp": row["timeus"],
                    "difference_us": diff,
                    "full_row": row
                })

        if matched_rows:
            results.extend(sorted(matched_rows, key=lambda r: r["difference_us"])[:max_per_msg])
            availability_report.append({
                "message_type": msg,
                "status": "matched_rows",
                "count": len(matched_rows)
            })
        else:
            has_field_anywhere = any(get_matching_field(r, field) for r in message_rows)
            if has_field_anywhere:
                closest = min(
                    ((abs(r["timeus"] - query_time_us), r["timeus"])
                     for r in message_rows if "timeus" in r),
                    default=(None, None)
                )
                availability_report.append({
                    "message_type": msg,
                    "status": "field_present_but_out_of_window",
                    "closest_timeus": closest[1],
                    "time_diff_us": closest[0]
                })
            else:
                availability_report.append({
                    "message_type": msg,
                    "status": "field_not_present",
                    "available_fields_sample": available_fields
                })

    return build_response(
        "value_at_time",
        field,
        candidate_messages,
        sorted(results, key=lambda r: r["difference_us"]),
        query_time_us=query_time_us,
        unavailable_sources=availability_report
    )


def handle_nan_values(obj):
    """Recursively replace NaN values with None and truncate floats to 4 decimal places for JSON serialization."""
    if isinstance(obj, dict):
        return {k: handle_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [handle_nan_values(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        else:
            return round(obj, 4)
    else:
        return obj


def handle_summary(target, candidate_messages, parsed_data, sample_size=5):
    summary = {}

    for msg in candidate_messages:
        entries = parsed_data.get(msg, [])
        if not entries:
            summary[msg] = {"entry_count": 0, "fields": []}
            continue

        sample_rows = entries[:sample_size]
        field_values = {}

        for field in entries[0].keys():
            values = [row[field] for row in entries if field in row]
            numeric_values = [v for v in values if isinstance(v, (int, float))]

            field_summary = {
                "sample_values": values[:3]  # adjust as needed
            }

            if numeric_values:
                # Handle potential NaN values from numpy operations
                min_val = np.min(numeric_values)
                max_val = np.max(numeric_values)
                mean_val = np.mean(numeric_values)
                
                field_summary.update({
                    "min": float(min_val) if not math.isnan(min_val) else None,
                    "max": float(max_val) if not math.isnan(max_val) else None,
                    "mean": float(mean_val) if not math.isnan(mean_val) else None
                })

            field_values[field] = field_summary

        summary[msg] = {
            "entry_count": len(entries),
            "field_summary": field_values,
            "sample_rows": sample_rows
        }

    return build_response(
        intent="summary",
        field=target,
        candidate_messages=candidate_messages,
        evidence=summary
    )


def handle_change_detection(field, candidate_messages, parsed_data, max_changes=30):
    all_changes = []
    last_value = None

    for msg in candidate_messages:
        for row in parsed_data.get(msg, []):
            if field in row:
                current = row[field]
                if last_value is not None and current != last_value:
                    all_changes.append({
                        "message_type": msg,
                        "time": row.get("timeus"),
                        "from": last_value,
                        "to": current,
                        "full_row": row
                    })
                last_value = current

    total_changes = len(all_changes)

    if total_changes <= max_changes:
        sampled_changes = all_changes
    else:
        # Sort by time and sample evenly across the flight
        all_changes.sort(key=lambda x: x["time"] or 0)
        indices = np.linspace(0, total_changes - 1, max_changes, dtype=int)
        sampled_changes = [all_changes[i] for i in indices]

    result = {
        "intent": "change_detection",
        "field": field,
        "candidate_messages": candidate_messages,
        "evidence": sampled_changes,
        "summary": {
            "total_changes_detected": total_changes,
            "sampled_changes_returned": len(sampled_changes),
            "note": f"Sampled {len(sampled_changes)} changes evenly across {total_changes} total changes."
        }
    }

    return result


def handle_anomaly_detection(field, candidate_messages, parsed_data, sample_size=5):
    evidence = []

    for msg in candidate_messages:
        rows = parsed_data.get(msg, [])
        print(f"Testing {msg} with {len(rows)} number of rows")
        values = [
            (row.get("timeus"), row[field], row)
            for row in rows
            if field in row and isinstance(row[field], (int, float))
        ]

        print("\tvalues: ", values)

        if len(values) < 2:
            continue

        sorted_by_value = sorted(values, key=lambda x: x[1])

        # Take bottom N and top N to expose extremes
        samples = sorted_by_value[:sample_size] + sorted_by_value[-sample_size:]

        for t, v, row in samples:
            evidence.append({
                "message_type": msg,
                "time": t,
                "value": v,
                "full_row": row
            })

    return build_response(
        intent="anomaly_detection",
        field=field,
        candidate_messages=candidate_messages,
        evidence=evidence
    )


def handle_fallback(parsed_data, rows_per_message=10, seed=42):
    random.seed(seed)
    evidence = []
    candidate_messages = [
        "err",     # Critical events
        "arm",     # Arm/disarm status
        "ctun",    # Control tuning (pitch/roll/throttle)
        "vfr_hud", # Airspeed, altitude, climb rate ****  ONLY AVAILABLE IN MAVLINK (.tlog) not in ArduPilot (.bin)   *****
        "bat",     # Battery status
        "gps",     # Position and fix info
        "ahr2",    # Attitude info
        "att",     # Attitude from AHRS
        "pos",     # Position estimate
    ]

    for msg in candidate_messages:
        rows = parsed_data.get(msg, [])
        if not rows:
            continue

        if len(rows) <= rows_per_message:
            sample_rows = rows
        elif len(rows) < 3 * rows_per_message:
            sample_rows = random.sample(rows, rows_per_message)
        else:
            third = len(rows) // 3
            sample_rows = (
                rows[:rows_per_message // 3] +
                rows[third:third + rows_per_message // 3] +
                rows[-(rows_per_message - 2 * (rows_per_message // 3)):]
            )

        for row in sample_rows:
            evidence.append({
                "message_type": msg,
                "row": row
            })

    return build_response(
        intent="fallback",
        field=None,
        candidate_messages=candidate_messages,
        evidence=evidence
    )