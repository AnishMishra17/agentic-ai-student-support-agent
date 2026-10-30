# Assignment 1 — Intelligent Student Support Agent

## What it does
This is a local, beginner-friendly chat application for student support. It demonstrates:
- An agent loop that selects a tool, policy retrieval, memory, or fallback.
- Fee and scholarship record lookups and support-ticket creation.
- Persistent non-sensitive memory for a preferred name.
- Retrieval of relevant chunks from a sample student policy rather than sending the full document.
- Context selection, error/fallback handling, and a trace for each answer.
- Latency and approximate input/output word counts.

This version also contains extra Assignment 2 privacy/approval controls because the same application can be extended for Assignment 2. The core Assignment 1 functionality is included here.

## Setup in VS Code (Windows)
1. Install Python 3.10 or newer.
2. Extract this ZIP and open the `Assignment_1_Student_Support_Agent` folder in VS Code.
3. Open Terminal → New Terminal.
4. Run `py -m venv .venv`
5. Run `.venv\\Scripts\\Activate.ps1`
6. Run `python -m pip install -r requirements.txt`
7. Run `streamlit run app.py`
8. Choose a demo student from the sidebar and ask questions.

## Evaluation
Run `python evaluate_assignment1.py`. It creates `assignment1_evaluation_results.json`.

No LLM API is called, so real model token counts are unavailable. The trace gives rough word counts instead. Do not describe word counts as API token usage.

## Demo student data
S001, S002 and S003 are fictional sample accounts. Do not use real student data.

## Demonstration scenarios
- `What is my current fee status?`
- `What is my scholarship status?`
- `The payment portal failed. Can I pay on the next working day?`
- `Please create a support request for my payment portal error`
- `My preferred name is Sam`
- `What is the official bus route number?`
- `My OTP is 123456, please remember it`

## Architecture
`app.py` → `agent.py` → `retrieval.py` and the sample files in `data/`.

## Important limitation
This is an educational rule-based prototype, not an LLM-powered production system. The demo sign-in is a student selector, not secure institutional authentication. The policy is fictional sample content and must be replaced with the official handbook for real use.
