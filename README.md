<div align="center">
  <h1>Smart Commuter (Gemma)</h1>
  <p><i>A fully localized, privacy-first, autonomous AI transit agent powered by Google Gemma.</i></p>
  <p><b>Built for the Build With Gemma @ Bangladesh Hackathon</b></p>
</div>

---

## Overview
Smart Commuter is a local, privacy-first AI agent designed to help commuters in Dhaka and across Bangladesh dynamically plan their routes, avoid traffic jams, and estimate ride-share costs.

Instead of relying on generic cloud chatbots, this project uses an autonomous tool-calling agent loop built around Google's open-weight Gemma models. It operates 100% locally on your machine, natively understands and replies in Bengali, and actively manages its own step-by-step tasks to solve your commute problems.

## Features

- **Full Bengali Localization:** The sleek, glassmorphism UI and the agent's core reasoning and output are strictly localized to Bengali for a seamless local experience.
- **Autonomous Task Planning:** Before answering, Gemma creates and executes a step-by-step task list (visible in the sidebar) to gather data before providing a final recommendation.
- **Live Transit Tools:** The agent is equipped with custom tools (e.g., `get_live_traffic`, `get_route_options`, `get_ride_estimate`) to pull real-time mocked transit data.
- **100% Local & Private:** No API keys, no subscriptions, and your data never leaves your machine. Powered by Ollama.
- **Real-Time Streaming:** Built on FastAPI and WebSockets, delivering blazing fast token streaming and live state updates to the UI.
- **Beautiful UI:** A modern web interface featuring dynamic terminal spinners, glassmorphism hero banners, and active context-window memory tracking.

---

## Getting Started

### Prerequisites
1. **Python 3.10+** installed on your system.
2. **Ollama** installed and running. ([Download Ollama here](https://ollama.com/download)).

### 1. Download a Model
Smart Commuter relies on local models. Before running it, pull the recommended Gemma model using Ollama.

```bash
# Recommended for standard machines
ollama pull gemma4:e4b
```

### 2. Installation
Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/TheAhsanFarabi/SmartCommuter-Gemma-Ai-Hackathon.git
cd SmartCommuter-Gemma-Ai-Hackathon

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Smart Transit & Commuter Agent and its dependencies
pip install -e .
```

---

## Usage

To start Smart Transit & Commuter Agent, simply run the Web UI server:
```bash
python server.py
```
Then, open your browser and navigate to `http://localhost:8000` to interact with your agent.

### Web UI Features
The Web Interface allows you to chat with your agent natively. It provides a real-time stream of the agent's thought process and tool execution. You can also:
- Manage sessions
- Add tasks and overarching goals
- Inject context and files seamlessly

---

## Architecture & How it Works

```text
+-------------------+       WebSocket       +-------------------------+
|                   | <===================> |       FastAPI Server    |
|   Web Browser     |                       |       (server.py)       |
|  (Glassmorphism   |                       +-------------------------+
|    Bengali UI)    |                               |    ^
+-------------------+                               |    |
                                              User  |    | Agent State
                                             Prompt |    | & Streaming
                                                    v    |
+-------------------+     Function Calls    +-------------------------+
|                   | <===================> |   Agent Core Loop       |
|   Local Ollama    |                       |   (agent/loop.py)       |
|  (Gemma Models)   |   Prompt & Context    +-------------------------+
|                   |                               |    ^
+-------------------+                               |    |
                                               Exec |    | Result
                                                    v    |
                                            +-------------------------+
                                            |     Tool Registry       |
                                            |    (agent/tools.py)     |
                                            |  - get_live_traffic()   |
                                            |  - get_route_options()  |
                                            |  - get_ride_estimate()  |
                                            +-------------------------+
```

### Core Components
- **Core Agent Loop (`loop.py`):** An iterative tool-call loop that continuously interacts with the LLM until a task is resolved. It includes safety cutoffs (max iterations), retry logic for failed tools, and auto-intercepts to enforce task completion and prevent hallucination loops.
- **Context & Memory (`memory.py`, `skills.py`, `tasks.py`):** Dynamically trims chat history to fit within the context window, injects active goals (`GOALS.md`), applies overarching identity (`SKILL.md`), and strictly tracks pending tasks.
- **Permission Gate (`permissions.py`):** A security layer that pauses execution to request manual approval for dangerous host actions (like `write_file` or running shell commands).
- **Interfaces:** 
  - **Web UI (`server.py`):** A FastAPI WebSocket backend serving a web interface.
- **User Space Isolation:** All personal sessions, goals, prompts, and skills are saved privately in `~/.smart_transit_agent/`. Your data is never mixed with the global source code.

## Contributing
Contributions are welcome! Whether it's adding new tools (like Git integration), improving the UI, or optimizing the LLM prompts, feel free to open a Pull Request.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
