from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, datetime, re
from stage1 import classify
from stage2 import run_stage_2
from stage3 import run_stage_3

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variable to store parser data
parser_data = None

def log_stage_output(stage_name, input_data, output_data, error=None, timestamp=None):
    """
    Log stage outputs to a file for debugging purposes.
    
    Args:
        stage_name (str): Name of the stage (stage1, stage2, stage3)
        input_data: Input data to the stage
        output_data: Output data from the stage
        error (str, optional): Error message if any
        timestamp (str, optional): Timestamp for the log entry
    """
    if timestamp is None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "timestamp": timestamp,
        "stage": stage_name,
        "input": input_data,
        "output": output_data,
        "error": error
    }
    
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Write to stage-specific log file
    log_filename = f"{logs_dir}/{stage_name}_debug.log"
    
    try:
        with open(log_filename, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, indent=2, ensure_ascii=False, default=str)
        print(f"Stage {stage_name} output logged to {log_filename}")
    except Exception as e:
        print(f"Error writing to log file {log_filename}: {str(e)}")


def normalize_message_type(key):
    return re.sub(r'\[\d+\]$', '', key).lower()

def make_json_safe(obj):
    import numpy as np
    if isinstance(obj, bytes):
        return obj.decode(errors="ignore")
    elif isinstance(obj, (list, tuple)):
        return [make_json_safe(i) for i in obj]
    elif isinstance(obj, dict):
        return {k.lower(): make_json_safe(v) for k, v in obj.items()}
    elif hasattr(obj, 'tolist'):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    return obj

def convert_frontend_to_backend_format(frontend_data):
    backend_data = {}

    if 'messages' not in frontend_data:
        return frontend_data

    for original_key, message_data in frontend_data['messages'].items():
        msg_type = normalize_message_type(original_key)

        if isinstance(message_data, dict):
            field_names = list(message_data.keys())

            # Check if it's field-array format: each field is a list
            if field_names and any(isinstance(message_data[f], list) for f in field_names):
                length = max((len(message_data[f]) for f in field_names if isinstance(message_data[f], list)), default=0)
                message_array = []

                for i in range(length):
                    entry = {}
                    for field in field_names:
                        if i < len(message_data[field]):
                            field_name = field.lower()
                            value = make_json_safe(message_data[field][i])
                            if field_name == "time_boot_ms":
                                field_name = "timeus"
                                value = value * 1000  # Convert milliseconds to microseconds
                            entry[field_name] = value
                    message_array.append(entry)

                backend_data[msg_type] = message_array

            else:
                # Treat as single-row dict of scalar values
                entry = {}
                for field in field_names:
                    field_name = field.lower()
                    value = message_data[field]
                    if field_name == "time_boot_ms":
                        field_name = "timeus"
                        value = value * 1000  # Convert milliseconds to microseconds
                    entry[field_name] = make_json_safe(value)
                backend_data[msg_type] = [entry]

        elif isinstance(message_data, list):
            # Likely already list of dicts
            message_array = []
            for row in message_data:
                if isinstance(row, dict):
                    entry = {}
                    for k, v in row.items():
                        field_name = k.lower()
                        value = make_json_safe(v)
                        if field_name == "time_boot_ms":
                            field_name = "timeus"
                            value = value * 1000  # Convert milliseconds to microseconds
                        entry[field_name] = value
                    message_array.append(entry)
            backend_data[msg_type] = message_array

        else:
            print(f"[Warning] Unexpected format for message '{msg_type}': {type(message_data)} — skipped.")
            backend_data[msg_type] = []

    return backend_data


@app.route('/api/parser', methods=['POST'])
def receive_parser():
    global parser_data
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No parser data received'}), 400
        
        # Convert frontend format to backend format
        parser_data = convert_frontend_to_backend_format(data)
        
        print("Parser data received and converted to backend format.")
        return jsonify({'status': 'success'})
    except Exception as e:
        print("Error in /api/parser:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    global parser_data
    if parser_data is None:
        return jsonify({'error': 'Parser data not set. Please upload parser data first.'}), 400
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        messages = data.get('messages', [])
        if not messages:
            return jsonify({'error': 'No messages in request'}), 400
            
        # Get the last message from the user
        last_message = messages[-1]['content'] if messages else ""
        print("Processing message:", last_message)
        
        # Stage 1: Classification
        try:
            stage1_response = classify(last_message)
            stage1_data = stage1_response.get_json()
            # log_stage_output("stage1", {"message": last_message}, stage1_data)
            print("Stage 1 completed!")
        except Exception as e:
            error_msg = f"Stage 1 error: {str(e)}"
            # log_stage_output("stage1", {"message": last_message}, None, error_msg)
            print(error_msg)
            return jsonify({'error': error_msg}), 500
        
        # Stage 2: Data Processing
        try:
            stage2_response = run_stage_2(stage1_data, parser_data)
            # log_stage_output("stage2", {"stage1_data": stage1_data, "parser_data_keys": list(parser_data.keys()) if parser_data else None}, stage2_response)
            print("Stage 2 completed!")
        except Exception as e:
            error_msg = f"Stage 2 error: {str(e)}"
            # log_stage_output("stage2", {"stage1_data": stage1_data, "parser_data_keys": list(parser_data.keys()) if parser_data else None}, None, error_msg)
            print(error_msg)
            return jsonify({'error': error_msg}), 500

        extra_context = {}
        for k in ['query_time_us', 'unavailable_sources', 'summary', 'note', 'warning', 'error']:
            if k in stage2_response:
                extra_context[k] = stage2_response[k]
        
        # Stage 3: Final Processing
        try:
            stage3_response = run_stage_3(
                parsed_data=parser_data,
                question=last_message,
                # stage1=stage1_data,
                stage2=stage2_response,
                extra_context=extra_context
            )
            # log_stage_output("stage3", {
            #     "question": last_message,
            #     # "stage1_data": stage1_data,
            #     "stage2_response": stage2_response,
            #     "extra_context": extra_context
            # }, stage3_response)
            print("Stage 3 completed!")
        except Exception as e:
            error_msg = f"Stage 3 error: {str(e)}"
            # log_stage_output("stage3", {
            #     "question": last_message,
            #     # "stage1_data": stage1_data,
            #     "stage2_response": stage2_response,
            #     "extra_context": extra_context
            # }, None, error_msg)
            print(error_msg)
            return jsonify({'error': error_msg}), 500

        if stage3_response.get("status") == "clarification_requested":
            return jsonify({
                "message": stage3_response["question"],
                "expecting_clarification": True,
                "stage3Context": {
                    "messages": stage3_response["messages"],  # captured inside run_stage_3
                    # "stage1": stage1_data,
                    "stage2": stage2_response,
                    "extra_context": extra_context
                }
            })

        elif stage3_response.get("status") == "answered":
            return jsonify({
                "message": stage3_response["answer"],
                "expecting_clarification": False
            })

        return jsonify({
            "message": stage3_response.get("message", "Could not complete reasoning."),
            "expecting_clarification": False
        })

    except Exception as e:
        print("Error in /api/chat:", str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/clarify', methods=['POST'])
def clarify():
    global parser_data
    if parser_data is None:
        return jsonify({'error': 'Parser data not set. Please upload parser data first.'}), 400
    try:
        print("Clarify route called!")
        data = request.get_json()
        clarification = data.get("clarification")
        context = data.get("stage3Context", {})

        if not clarification or not context:
            return jsonify({'error': 'Missing clarification or context'}), 400

        messages = context.get("messages", [])
        messages.append({"role": "user", "content": clarification})

        # Log the clarification attempt
        try:
            stage3_response = run_stage_3(
                parsed_data=parser_data,
                messages=messages,
                # stage1=context.get("stage1"),
                stage2=context.get("stage2"),
                extra_context=context.get("extra_context")
            )
            # log_stage_output("stage3_clarify", {
            #     "clarification": clarification,
            #     "messages": messages,
            #     # "stage1": context.get("stage1"),
            #     "stage2": context.get("stage2"),
            #     "extra_context": context.get("extra_context")
            # }, stage3_response)
        except Exception as e:
            error_msg = f"Stage 3 clarification error: {str(e)}"
            # log_stage_output("stage3_clarify", {
            #     "clarification": clarification,
            #     "messages": messages,
            #     # "stage1": context.get("stage1"),
            #     "stage2": context.get("stage2"),
            #     "extra_context": context.get("extra_context")
            # }, None, error_msg)
            print(error_msg)
            return jsonify({'error': error_msg}), 500

        if stage3_response.get("status") == "clarification_requested":
            return jsonify({
                "message": stage3_response["question"],
                "expecting_clarification": True,
                "stage3Context": {
                    "messages": stage3_response["messages"],
                    # "stage1": context.get("stage1"),
                    "stage2": context.get("stage2"),
                    "extra_context": context.get("extra_context")
                }
            })

        elif stage3_response.get("status") == "answered":
            return jsonify({
                "message": stage3_response["answer"],
                "expecting_clarification": False
            })

        return jsonify({
            "message": stage3_response.get("message", "Could not complete reasoning."),
            "expecting_clarification": False
        })

    except Exception as e:
        print("Error in /api/chat/clarify:", str(e))
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
