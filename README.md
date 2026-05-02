# Calendar Briefing Agent

Calendar Briefing Agent is a Python MVP for analyzing a user's daily calendar data, classifying the user's planning persona, and generating a personalized daily briefing. It is intentionally local-first and rule-based so the core product logic is easy to inspect before adding LLM, agent, observability, or retrieval layers.

## Architecture

```text
app/main.py       Orchestrates input loading, analysis, persona classification, briefing generation, and JSON output.
app/schema.py     Defines schedule data structures and input parsing.
app/analyzer.py   Computes schedule statistics, category distribution, conflicts, and buffer risks.
app/persona.py    Classifies the user's planning persona from analyzed calendar patterns.
app/briefing.py   Produces the user-facing daily briefing payload.
data/             Stores sample calendar input.
logs/             Stores generated output such as result.json.
```

The code is modular by design. Future agent capabilities can be introduced without rewriting the schedule analysis layer.

## Features

- Loads schedule data from `data/sample_schedule.json`
- Calculates total schedule count and total scheduled hours
- Computes category distribution
- Detects overlapping schedule conflicts
- Detects insufficient buffer time between events
- Classifies one of four personas:
  - Work-Focused Planner
  - Growth-Oriented Planner
  - Life-Balanced Planner
  - Light Scheduler
- Generates a daily briefing with:
  - summary
  - persona rationale
  - schedule list
  - risk message
  - recommended actions
- Saves the result to `logs/result.json`

## How To Run

From the project root:

```bash
python3 app/main.py
```

The generated briefing will be written to:

```text
logs/result.json
```

No external packages are required for this MVP.

## Example Output

The result JSON includes two top-level sections:

- `analysis`: structured metrics and detected scheduling risks
- `briefing`: user-facing summary, persona, schedule list, risk message, and recommendations

## Future Improvements

- Add OpenAI API integration for natural-language briefing generation
- Add LangGraph to model the workflow as explicit agent nodes
- Add VectorDB support for retrieving user preferences, past briefings, and meeting notes
- Add Langfuse tracing for prompt, tool-call, and output observability
- Add calendar provider integrations such as Google Calendar or Outlook Calendar
- Add evaluation datasets for persona accuracy and recommendation quality
- Add a lightweight web UI for reviewing schedule risks and briefing history

## Relevance To AI/Agent Product Roles

This project demonstrates core AI product thinking without hiding behind an LLM call. It separates product logic into observable stages: input parsing, deterministic analysis, persona classification, and briefing generation. That makes it easier to explain agent workflow design, identify where AI should add value, and define evaluation points before introducing LangGraph, retrieval, or observability tooling.

For an AI/Agent product role, the MVP highlights skills in scoping, user-context modeling, agent-ready architecture, risk detection, recommendation design, and roadmap thinking.
