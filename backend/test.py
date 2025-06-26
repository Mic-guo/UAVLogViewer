import requests
import json
import os
import time
from datetime import datetime

# Test server configuration
BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/chat"

# Create test questions organized by intent
TEST_QUESTIONS = {
    "max_value": [
        "What was the maximum altitude reached?",
        "What was the highest battery temperature recorded?",
        "What was the peak GPS speed during the flight?",
        "What was the maximum current draw?",
        "What was the highest voltage recorded?"
    ],
    "min_value": [
        "What was the lowest voltage during the flight?",
        "When was the battery temperature at its minimum?",
        "What was the minimum altitude reached?",
        "What was the lowest GPS speed?",
        "What was the minimum current draw?"
    ],
    "event_detection": [
        "When did the RC signal first get lost?",
        "Did the drone ever enter failsafe mode?",
        "When was the first GPS fix acquired?",
        "When did the drone arm?",
        "When did the flight mode change to AUTO?",
        "Were there any critical errors during the flight?"
    ],
    "time_duration": [
        "How long was the drone airborne?",
        "What was the duration between takeoff and landing?",
        "How long was the total flight time?",
        "What was the duration of the mission?",
        "How long did the GPS signal remain stable?"
    ],
    "value_at_time": [
        "What was the altitude at timestamp 70000000?",
        "What was the GPS speed at 12:05:00?",
        "What was the battery voltage at 50000000 microseconds?",
        "What was the current draw at 30000000?",
        "What was the temperature at 10000000?"
    ],
    "summary": [
        "Can you summarize the flight?",
        "Give me a high-level overview of the battery performance.",
        "What's a summary of the GPS performance?",
        "Summarize the flight statistics.",
        "Give me an overview of the mission."
    ],
    "change_detection": [
        "When did the flight mode change?",
        "Show all points where the altitude changed drastically.",
        "When did the battery voltage drop significantly?",
        "Show me when the GPS fix status changed.",
        "When did the RC signal strength change?"
    ],
    "anomaly_detection": [
        "Were there any anomalies in the GPS signal?",
        "Did the battery voltage drop unexpectedly at any point?",
        "Were there any unusual altitude readings?",
        "Did the current draw spike abnormally?",
        "Were there any temperature anomalies?"
    ],
    "fallback": [
        "Tell me what you can about this flight.",
        "Was everything normal during the flight?",
        "What happened during this mission?",
        "Give me any interesting information about this flight.",
        "What can you tell me about the drone's performance?"
    ]
}

def create_folder_structure():
    """Create the testAnswers folder structure"""
    base_folder = "testAnswers"
    
    # Create main folder
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
    
    # Create subfolders for each intent
    for intent in TEST_QUESTIONS.keys():
        intent_folder = os.path.join(base_folder, intent)
        if not os.path.exists(intent_folder):
            os.makedirs(intent_folder)
    
    print(f"Created folder structure: {base_folder}/")
    for intent in TEST_QUESTIONS.keys():
        print(f"  └── {intent}/")

def make_chat_request(question):
    """Make a request to the chat endpoint"""
    payload = {
        "messages": [
            {"role": "user", "content": question}
        ]
    }
    
    try:
        response = requests.post(CHAT_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None

def save_test_result(intent, question_number, question, response):
    """Save the test result to the appropriate folder"""
    base_folder = "testAnswers"
    intent_folder = os.path.join(base_folder, intent)
    
    # Create filename with question number and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{question_number:02d}_{timestamp}.json"
    filepath = os.path.join(intent_folder, filename)
    
    # Prepare the data to save
    result_data = {
        "timestamp": timestamp,
        "question": question,
        "stage1_response": response.get('stage1', {}),
        "stage2_response": response.get('stage2', {}),
        "intent": intent,
        "question_number": question_number
    }
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved: {filepath}")
        return filepath
    except Exception as e:
        print(f"  ✗ Error saving {filepath}: {e}")
        return None

def run_tests():
    """Run all tests and save results"""
    print("🚀 Starting comprehensive test suite...")
    print(f"Target endpoint: {CHAT_ENDPOINT}")
    print()
    
    # Create folder structure
    create_folder_structure()
    print()
    
    total_questions = sum(len(questions) for questions in TEST_QUESTIONS.values())
    current_question = 0
    
    for intent, questions in TEST_QUESTIONS.items():
        print(f"📋 Testing Intent: {intent}")
        print(f"   Questions: {len(questions)}")
        print("-" * 50)
        
        for i, question in enumerate(questions, 1):
            current_question += 1
            print(f"[{current_question}/{total_questions}] Testing: {question}")
            
            # Make the request
            response = make_chat_request(question)
            
            if response:
                # Save the result
                filepath = save_test_result(intent, i, question, response)
                
                # Print a brief summary of the response
                stage1 = response.get('stage1', {})
                stage2 = response.get('stage2', {})
                
                if 'intent' in stage1:
                    print(f"  Stage1 Intent: {stage1['intent']}")
                if 'intent' in stage2:
                    print(f"  Stage2 Intent: {stage2['intent']}")
                if 'error' in stage1:
                    print(f"  Stage1 Error: {stage1['error']}")
                if 'error' in stage2:
                    print(f"  Stage2 Error: {stage2['error']}")
                
                # Check for evidence in stage2
                if 'evidence' in stage2 and stage2['evidence']:
                    evidence_count = len(stage2['evidence']) if isinstance(stage2['evidence'], list) else 1
                    print(f"  Stage2 Evidence: {evidence_count} items found")
                
                # Add a small delay to avoid overwhelming the server
                time.sleep(0.5)
            else:
                print(f"  ✗ Failed to get response")
            
            print()
    
    print("✅ Test suite completed!")
    print(f"Results saved in: testAnswers/")

def test_server_connection():
    """Test if the server is running and accessible"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✓ Server is accessible at {BASE_URL}")
        return True
    except requests.exceptions.RequestException:
        print(f"✗ Cannot connect to server at {BASE_URL}")
        print("Make sure the Flask app is running with: python app.py")
        return False

if __name__ == "__main__":
    print("🧪 Drone Telemetry Chat Test Suite")
    print("=" * 50)
    
    # Check server connection first
    if not test_server_connection():
        exit(1)
    
    print()
    
    # Run the tests
    run_tests()
