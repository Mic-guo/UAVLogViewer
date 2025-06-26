# Drone Telemetry Chat System - Test Suite

This test suite comprehensively tests the drone telemetry chat system by sending various questions to the `/api/chat` endpoint and organizing the results in a structured folder hierarchy. The system now captures both Stage 1 (intent classification) and Stage 2 (evidence gathering) responses.

## 🚀 Quick Start

### 1. Start the Flask Server

```bash
python app.py
```

The server will start on `http://localhost:8000`

### 2. Run the Test Suite

```bash
python test.py
```

### 3. Analyze Results

```bash
python analyze_tests.py
```

## 📁 Folder Structure

The test suite creates the following structure:

```
testAnswers/
├── max_value/
│   ├── 01_20241201_143022.json
│   ├── 02_20241201_143023.json
│   └── ...
├── min_value/
│   ├── 01_20241201_143025.json
│   └── ...
├── event_detection/
├── time_duration/
├── value_at_time/
├── summary/
├── change_detection/
├── anomaly_detection/
└── fallback/
```

## 🧪 Test Coverage

The test suite covers all 9 intent types with multiple questions each:

### ✅ Intent: max_value

- "What was the maximum altitude reached?"
- "What was the highest battery temperature recorded?"
- "What was the peak GPS speed during the flight?"
- "What was the maximum current draw?"
- "What was the highest voltage recorded?"

### ✅ Intent: min_value

- "What was the lowest voltage during the flight?"
- "When was the battery temperature at its minimum?"
- "What was the minimum altitude reached?"
- "What was the lowest GPS speed?"
- "What was the minimum current draw?"

### ✅ Intent: event_detection

- "When did the RC signal first get lost?"
- "Did the drone ever enter failsafe mode?"
- "When was the first GPS fix acquired?"
- "When did the drone arm?"
- "When did the flight mode change to AUTO?"
- "Were there any critical errors during the flight?"

### ✅ Intent: time_duration

- "How long was the drone airborne?"
- "What was the duration between takeoff and landing?"
- "How long was the total flight time?"
- "What was the duration of the mission?"
- "How long did the GPS signal remain stable?"

### ✅ Intent: value_at_time

- "What was the altitude at timestamp 70000000?"
- "What was the GPS speed at 12:05:00?"
- "What was the battery voltage at 50000000 microseconds?"
- "What was the current draw at 30000000?"
- "What was the temperature at 10000000?"

### ✅ Intent: summary

- "Can you summarize the flight?"
- "Give me a high-level overview of the battery performance."
- "What's a summary of the GPS performance?"
- "Summarize the flight statistics."
- "Give me an overview of the mission."

### ✅ Intent: change_detection

- "When did the flight mode change?"
- "Show all points where the altitude changed drastically."
- "When did the battery voltage drop significantly?"
- "Show me when the GPS fix status changed."
- "When did the RC signal strength change?"

### ✅ Intent: anomaly_detection

- "Were there any anomalies in the GPS signal?"
- "Did the battery voltage drop unexpectedly at any point?"
- "Were there any unusual altitude readings?"
- "Did the current draw spike abnormally?"
- "Were there any temperature anomalies?"

### ✅ Intent: fallback

- "Tell me what you can about this flight."
- "Was everything normal during the flight?"
- "What happened during this mission?"
- "Give me any interesting information about this flight."
- "What can you tell me about the drone's performance?"

## 📊 Result Files

Each test result is saved as a JSON file containing both Stage 1 and Stage 2 responses:

```json
{
  "timestamp": "20241201_143022",
  "question": "What was the maximum altitude reached?",
  "stage1_response": {
    "intent": "max_value",
    "target": "alt",
    "target_type": "field",
    "candidate_messages": ["gps", "vfr_hud"]
  },
  "stage2_response": {
    "intent": "max_value",
    "field": "alt",
    "candidate_messages": ["gps", "vfr_hud"],
    "evidence": [
      {
        "message_type": "gps",
        "value": 150.5,
        "time": 50000000,
        "full_row": {...}
      }
    ]
  },
  "intent": "max_value",
  "question_number": 1
}
```

## 📈 Analysis Report

The `analyze_tests.py` script generates a comprehensive report including:

- **Overall Statistics**: Total tests, intent types tested
- **Intent Classification Accuracy**: Separate accuracy for Stage 1 and Stage 2
- **Evidence Analysis**: How often evidence is found and how much
- **Error Analysis**: Common errors in both stages
- **Detailed Results**: Question-by-question breakdown with evidence counts

### Sample Report Output:

```
🎯 INTENT CLASSIFICATION ACCURACY
----------------------------------------------------------------------
Intent                | Stage1   | Stage2   | Stage1 % | Stage2 %
----------------------------------------------------------------------
max_value             |        5 |        5 |     100.0 |     100.0
min_value             |        4 |        4 |      80.0 |      80.0
event_detection       |        6 |        6 |     100.0 |     100.0
...
OVERALL               |       40 |       40 |      95.6 |      95.6

📊 EVIDENCE ANALYSIS
------------------------------------------------------------
Intent                | With Evidence | Total Items | Rate %
------------------------------------------------------------
max_value             |            5 |           8 |    100.0
min_value             |            4 |           6 |     80.0
...
```

## 🔧 Configuration

### Server Settings

- **Base URL**: `http://localhost:8000` (configurable in `test.py`)
- **Endpoint**: `/api/chat`
- **Timeout**: 30 seconds per request

### Test Settings

- **Delay between requests**: 0.5 seconds (to avoid overwhelming the server)
- **File naming**: `{question_number:02d}_{timestamp}.json`

## 🐛 Troubleshooting

### Server Connection Issues

```
✗ Cannot connect to server at http://localhost:8000
Make sure the Flask app is running with: python app.py
```

**Solution**: Start the Flask server first with `python app.py`

### Missing Dependencies

```bash
pip install requests flask flask-cors python-dotenv openai numpy
```

### Test Results Not Found

```
❌ Test results folder 'testAnswers' not found!
Run test.py first to generate test results.
```

**Solution**: Run `python test.py` to generate test results first

## 📝 Customization

### Adding New Test Questions

Edit the `TEST_QUESTIONS` dictionary in `test.py`:

```python
TEST_QUESTIONS = {
    "max_value": [
        "What was the maximum altitude reached?",
        # Add your new questions here
        "What was the highest speed recorded?"
    ],
    # Add new intent types here
}
```

### Modifying Server Configuration

Change the `BASE_URL` in `test.py`:

```python
BASE_URL = "http://your-server:port"
```

### Adjusting Test Parameters

Modify timing and other parameters in `test.py`:

```python
# Delay between requests (seconds)
time.sleep(0.5)

# Request timeout (seconds)
response = requests.post(CHAT_ENDPOINT, json=payload, timeout=30)
```

## 🎯 Expected Outcomes

After running the test suite, you should see:

1. **Folder Structure**: `testAnswers/` with subfolders for each intent
2. **Test Results**: JSON files with both Stage 1 and Stage 2 responses
3. **Analysis Report**: Comprehensive accuracy and error analysis for both stages
4. **Console Output**: Real-time progress and summary statistics

The system should correctly classify most questions into their intended categories and provide relevant evidence from the drone telemetry data in Stage 2.

## 🔄 System Flow

1. **Stage 1**: Intent classification and target identification
2. **Stage 2**: Evidence gathering and data analysis
3. **Test Suite**: Captures both stages and organizes results
4. **Analysis**: Compares expected vs actual intents and evidence quality
