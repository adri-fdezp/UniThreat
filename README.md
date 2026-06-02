# UniThreat

> **Open Source Intelligence (OSINT) risk-profiling platform** — aggregate, analyze, and visualize public threat data for authorized security assessments.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask)
![License](https://img.shields.io/badge/License-Educational-orange?style=flat-square)



## Overview

UniThreat is a modular OSINT platform built for security researchers. It runs multiple intelligence-gathering modules in parallel, streams results to the UI in real time via Server-Sent Events, and feeds curated findings into an AI-powered attack-vector analyzer.

```
┌─────────────────────────────────────────────────────┐
│                    React Frontend                    │
│          (Vite · SSE · Real-time results)           │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP / SSE
┌───────────────────────▼─────────────────────────────┐
│                   Flask Backend                      │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │  Search  │ │  Social  │ │     AI / Analysis  │  │
│  │ Google   │ │Instagram │ │  Claude Research   │  │
│  │DuckDuckGo│ │ LinkedIn │ │  Gemini Research   │  │
│  └──────────┘ └──────────┘ │  Attack Analyzer   │  │
│  ┌──────────┐ ┌──────────┐ │  SpamAssassin      │  │
│  │Username  │ │  Email   │ └────────────────────┘  │
│  │Enumerator│ │   HIBP   │                          │
│  └──────────┘ └──────────┘                          │
└─────────────────────────────────────────────────────┘
```


## Features

| Module | Description |
|---|---|
| **Google** | Selenium-based Google dorking with anti-detection |
| **DuckDuckGo** | Privacy-respecting search via `ddgs` |
| **Instagram** | Profile and post scraping via Instaloader |
| **LinkedIn** | Public profile and post collection |
| **Username Enumerator** | Cross-platform username presence check (Holehe) |
| **Email OSINT / HIBP** | Have I Been Pwned breach lookup |
| **Claude Research** | Anthropic-powered deep OSINT synthesis |
| **Gemini Research** | Google Gemini-powered intelligence gathering |
| **Attack Vector Analyzer** | AI-generated threat assessment from curated findings |
| **SpamAssassin Scorer** | Email header/body phishing analysis |



## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| Google Chrome | Latest stable (for Selenium modules) |



## Installation

### 1 — Clone the repository

```bash
git clone https://github.com/adri-fdezp/UniThreat.git
cd UniThreat
```

### 2 — Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3 — Environment variables

Copy the example env file and fill in your API keys:

```bash
cp backend/.env.example backend/.env
```

```ini
# backend/.env

# Required for Claude Research and Attack Analyzer (claude provider)
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional — enables Gemini Research and Attack Analyzer (gemini provider)
GOOGLE_API_KEY=your_google_key_here
```

> **Never commit your `.env` file.** It is already listed in `.gitignore`.

### 4 — Frontend

```bash
cd frontend
npm install
```



## Running the App

Open two terminals (or two tabs):

**Terminal 1 — Backend**

```bash
cd backend
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

python app.py
# → http://localhost:5000
```

**Terminal 2 — Frontend**

```bash
cd frontend
npm run dev
# → http://localhost:5173
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.



## Usage

1. Enter the **target name** (required) and optionally a username, email, or LinkedIn URL.
2. Select the **modules** you want to run.
3. Click **Execute** — results stream in as each module completes.
4. Curate interesting findings and click **Analyze** to generate an AI threat assessment.
5. Use the **Email Scorer** tab to test phishing email payloads against SpamAssassin.


## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/gather` | Start a new OSINT session |
| `GET` | `/api/stream/:id` | SSE stream for live module updates |
| `GET` | `/api/results/:id` | Polling fallback — full results snapshot |
| `POST` | `/api/analyze` | Run AI attack-vector analysis |
| `POST` | `/api/score-email` | Score an email through SpamAssassin |
| `GET` | `/health` | Health check |


## Disclaimer

> This tool is intended **exclusively** for educational purposes and authorized security assessments. Always obtain explicit written permission before profiling any individual or organization. Misuse of this tool may violate local, national, or international law. The authors accept no liability for unauthorized or malicious use.


*Master's Thesis project — Aarhus University, 2026*
