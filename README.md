# UniThreat: OSINT Risk Profiling Tool

UniThreat is a modular Open Source Intelligence (OSINT) tool designed to generate risk profiles for individuals or entities by aggregating public information from various online sources.

## Project Structure

The project is divided into two main components:

- **Backend (`/backend`)**: A Flask-based REST API that orchestrates the data collection.
- **Frontend (`/frontend`)**: A React-based single-page application (SPA) for user interaction and result visualization.

### Backend

- **`app.py`**: The entry point for the Flask application. Defines API routes.
- **`risk_profiling/profiler.py`**: Contains the `RiskProfiler` class, which manages search strategies (dorks) and executes searches across registered engines.
- **`search_engines/`**: Contains modular search engine implementations.
  - **`google_engine.py`**: A Selenium-based scraper for Google Search results, equipped with basic anti-detection measures.

### Frontend

- **`src/App.jsx`**: Main application component managing state and layout.
- **`src/api/profiler.js`**: API client for communicating with the backend.
- **`src/components/`**: Reusable UI components (`SearchForm`, `ProfileResults`, etc.).

## Prerequisites

- **Python 3.10+**: For the backend.
- **Node.js 16+**: For the frontend.
- **Google Chrome**: Required for the Selenium-based scraper.

## Setup & Installation

### 1. Backend Setup

Navigate to the `backend` directory:

```bash
cd backend
```

Create and activate a virtual environment (recommended):

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Frontend Setup

Navigate to the `frontend` directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

## Running the Application

### Start the Backend

From the `backend` directory:

```bash
python app.py
```
The API will run on `http://localhost:5000`.

### Start the Frontend

From the `frontend` directory:

```bash
npm run dev
```
The application will be accessible at `http://localhost:5173` (or the port shown in your terminal).

## Usage

1.  Open the web interface.
2.  Enter the name of the target you wish to profile.
3.  Select the desired search modules (Social, Work, Files, Web).
4.  Click "EXECUTE".
5.  View the aggregated results, sorted by relevance.

## Disclaimer

This tool is for educational and authorized testing purposes only. misuse of this tool for malicious activities is strictly prohibited. Ensure you have permission to profile the target.
