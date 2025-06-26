from flask import jsonify
import os
from dotenv import load_dotenv
import openai
import json

# Load environment variables
load_dotenv('secret.env')

# Set OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
openai.api_key = api_key

# Load field-to-messages mapping once
with open("field_to_messages.json", "r") as f:
    field_to_messages = json.load(f)

# Load message definitions once
with open("message_definitions.json", "r") as f:
    message_definitions = json.load(f)

def fallback_response(error_msg, original_query=None):
    return jsonify({
        "intent": "fallback",
        "target": "",
        "target_type": "",
        "candidate_messages": None,
        "error": error_msg,
        "original_query": original_query
    })

# LLM call
def call_intent_classifier(user_query):
    system_prompt = """You are a telemetry intent classifier for drone flight logs.

Your job is to extract:
1. intent — one of:
   [max_value, min_value, event_detection, time_duration, value_at_time, summary, change_detection, anomaly_detection]

2. target — the most relevant telemetry message or field that helps detect or answer the query. If the query refers to a system event (e.g., GPS loss, signal dropout, arming, mode changes, failsafes), return the message type that contains the clearest evidence — such as 'ERR' or 'MODE'.

3. target_type — one of:
   - "message" — for discrete events, states, or logs (e.g., GPS, ARM, MODE, ERR)
   - "field" — for continuous measurements or numerical values (e.g., Alt, Curr, Volt, Temp)

4. query_time_us (optional) — if the user asks for the value **at a specific time**, return the time in microseconds (1 second = 1,000,000 us). Otherwise, omit.

Guidelines:
- Use only valid telemetry field or message names from ArduPilot logs (e.g., "GPS", "Alt", "Spd", "Volt", "Curr", "ERR", etc.).
- Do not invent field or message names. Avoid combined names like "gps_speed", "battery_voltage", or "rc_signal_strength".
- Choose the best available telemetry source. For example:
  - "gps speed" → "Spd"
  - "battery voltage" → "Volt"
  - "signal strength" → "RSSI"
  - "rc signal lost" → "ERR" or "STAT"
- When in doubt about signal losses or system issues, prefer 'ERR' messages.

Respond strictly in JSON format.

---

Examples:

Q: "What was the highest altitude reached during the flight?"
→ { "intent": "max_value", "target": "Alt", "target_type": "field" }

Q: "When did the GPS signal first get lost?"
→ { "intent": "event_detection", "target": "GPS", "target_type": "message" }

Q: "What was the maximum battery temperature?"
→ { "intent": "max_value", "target": "Temp", "target_type": "field" }

Q: "How long was the total flight time?"
→ { "intent": "time_duration", "target": "TimeUS", "target_type": "field" }

Q: "List all critical errors that happened mid-flight."
→ { "intent": "event_detection", "target": "ERR", "target_type": "message" }

Q: "When was the first instance of RC signal loss?"
→ { "intent": "event_detection", "target": "ERR", "target_type": "message" }

Q: "What was the altitude at 10 seconds into the flight?"
→ { "intent": "value_at_time", "target": "Alt", "target_type": "field", "query_time_us": 10000000 }
"""

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
    )

    return response.choices[0].message.content

def classify(query):
    try:
        llm_raw = call_intent_classifier(query)
        print(llm_raw)
        parsed = json.loads(llm_raw)

        intent = parsed.get("intent")
        target = parsed.get("target")
        target_type = parsed.get("target_type")
        query_time_us = parsed.get("query_time_us")  # optional, but include if present

        if not intent or not target or not target_type:
            raise ValueError("Missing intent, target, or target_type.")

        # Normalize key
        target_norm = target.lower()

        response = {
            "intent": intent,
            "target": target_norm,
            "target_type": target_type,
        }

        # Always include extra_params if available
        extra_params = {}
        if query_time_us is not None:
            extra_params["query_time_us"] = query_time_us
        if extra_params:
            response["extra_params"] = extra_params

        if target_type == "message":
            if target_norm in message_definitions:
                response["candidate_messages"] = None
                return jsonify(response)
            else:
                return fallback_response(f"Message '{target_norm}' not found", query)

        elif target_type == "field":
            candidate_messages = field_to_messages.get(target_norm)
            if candidate_messages:
                response["candidate_messages"] = candidate_messages
                return jsonify(response)
            else:
                return fallback_response(f"Field '{target_norm}' not found", query)

        else:
            return fallback_response(f"Invalid target_type: {target_type}", query)

    except Exception as e:
        return fallback_response(str(e), query)
