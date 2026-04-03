# Data Summarization Agent

[![Fetch.ai](https://img.shields.io/badge/Fetch.ai-uAgents-purple)](https://fetch.ai)
[![Daytona](https://img.shields.io/badge/Daytona-Sandbox-orange)](https://www.daytona.io)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
![innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:uagents](https://img.shields.io/badge/tag-uagents-blue)

An AI-powered data summarization assistant built with Fetch.ai uAgents and Daytona sandboxes. Send a CSV, JSON, or Google Sheets URL via chat and receive a comprehensive statistical report with auto-generated visualizations.

## Features

- **Automatic Data Analysis** — Downloads and analyzes CSV/JSON data from URLs or raw text input
- **Google Sheets Support** — Direct integration with Google Sheets CSV export URLs
- **Visualizations** — Generates histograms, bar charts, and correlation heatmaps via matplotlib/seaborn
- **Summary Reports** — Comprehensive statistics with key insights powered by ASI LLM
- **Secure Execution** — All code runs in isolated Daytona sandbox environments
- **Web Preview** — Beautiful HTML report served via Flask inside the sandbox
- **Chat Protocol** — Integrates with uAgents chat protocol for agent-to-agent communication

## Architecture

```
User Chat → uAgent → Daytona Sandbox
                          ├── Download data (CSV/JSON/Google Sheets)
                          ├── Analyze with pandas + seaborn
                          ├── Generate visualizations
                          ├── Build Flask report app
                          └── Return preview URL
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | Fetch.ai uAgents + Chat Protocol |
| Sandbox | Daytona |
| Data Analysis | pandas, numpy, seaborn, matplotlib |
| Web Preview | Flask |
| AI Summary | ASI:One LLM |

## Getting Started

### Prerequisites

- Python 3.10+
- Daytona API key
- (Optional) ASI:One API key for AI-enhanced summaries

### Installation

```bash
git clone https://github.com/gautammanak1/Data-Summarization-fetchai-daytona.git
cd Data-Summarization-fetchai-daytona
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
DAYTONA_API_KEY=your_daytona_api_key
```

### Run

```bash
python agent.py
```

### Example Usage

Send a message to the agent via chat protocol:

```
https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv
```

The agent will analyze the data and return a URL to a live Flask dashboard with charts and statistics.

## Project Structure

```
├── agent.py           # uAgents chat agent (message handling)
├── data_analyzer.py   # Core analysis logic (download, analyze, visualize, sandbox)
├── requirements.txt   # Python dependencies
├── sample_data.csv    # Example dataset for testing
└── README.md
```

## License

MIT
