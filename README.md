# Arena.ai UAV Log Analysis System

This project consists of a frontend UAV log viewer and a backend analysis system for processing and querying UAV log data.

## Prerequisites

- Docker installed on your system
- Python 3.13
- Virtual environment support (venv)
- OpenAI API key

### Setting up OpenAI API Key

Create a `secret.env` file in the root directory of the project and add your OpenAI API key:

```bash
# Create secret.env file
touch secret.env
```

Add your OpenAI API key to the `secret.env` file:

```
OPENAI_API_KEY="your-openai-api-key-here"
```

**Important**: Replace `"your-openai-api-key-here"` with your actual OpenAI API key. You can obtain an API key by signing up at [OpenAI's platform](https://platform.openai.com/).

## Python Dependencies

To install all required Python packages, create a virtual environment and install from the requirements file:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r backend/requirements.txt
```

## Quick Start

### 0. Set up OpenAI API Key

Before starting the application, make sure you have created the `secret.env` file with your OpenAI API key as described in the Prerequisites section above.

### 1. Start the Frontend (UAVLogViewer)

Run the Docker container to start the frontend application:

```bash
docker run \
  -e VUE_APP_CESIUM_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI4MmZlMzhiOC04MzZmLTQ1M2EtYTY5Ny0zMmE2ODEzODQyN2UiLCJpZCI6MzEyMTU4LCJpYXQiOjE3NDk5MTEzMjR9.H4UcrrWI76lHFc1Q-vLTf6GsamzUuzAWujoCY76bhM0 \
  -p 8080:8080 \
  -v ${PWD}:/usr/src/app \
  -v /usr/src/app/node_modules \
  -it uavlogviewer-dev
```

The frontend will be available at `http://localhost:8080`

### 2. Start the Backend Server

Open a new terminal window and navigate to the backend directory:

```bash
cd backend
```

Activate the virtual environment:

```bash
source ../venv/bin/activate
```

Start the Flask backend server:

```bash
python3 app.py
```

The backend API will be available at `http://localhost:8000`

## System Architecture

- **Frontend**: Vue.js application for viewing and uploading UAV log files
- **Backend**: Flask API server that processes log data and provides analysis capabilities

## API Endpoints

- `POST /api/parser` - Upload and parse UAV log data
- `POST /api/chat` - Send queries about the log data
- `POST /api/chat/clarify` - Provide clarification for ambiguous queries

## Usage

1. Start both the frontend and backend servers as described above
2. Open your browser and navigate to `http://localhost:8080`
3. Upload a UAV log file through the frontend interface
4. Use the chat interface to ask questions about your log data

## Troubleshooting

- Make sure both servers are running simultaneously
- Check that the ports 8080 (frontend) and 8000 (backend) are not already in use
- Ensure the virtual environment is properly activated before running the backend
- Verify that Docker is running and the `uavlogviewer-dev` image exists
