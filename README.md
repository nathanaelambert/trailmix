# CULINAIRE
CULIN**AI**RE is an AI powered meal planning app focused on recommending **healthy** recipes, adapting plans to personal needs and health **goals**, integrating **local** retailers, while **reducing food waste**.

## Initial setup for devs
1. clone git repo
2. create a virtual environment
```python -m venv .venv```
3. activate virtual environment
```source .venv/bin/activate```
4. install requirements
```pip install -r requirements.txt```

## How to run the app for testing
```python app.py```

## Configure your API key
The meal planner works with OpenRouter-compatible keys (or standard OpenAI keys). Export one of the following:
```bash
export OPENROUTER_API_KEY="sk-or-..."
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"   # default already set
export OPENROUTER_SITE_URL="http://localhost:8050"          # optional referer header
export OPENROUTER_APP_TITLE="CULINAIRE"                     # optional title header

# Alternatively, for the OpenAI-style env vars you provided:
export OPENAI_API_KEY="sk-or-..."
export OPENAI_API_BASE="https://openrouter.ai/api/v1"       # OPENAI_BASE_URL also supported
```
`OPENROUTER_API_KEY` is preferred when using OpenRouter; `OPENAI_API_KEY` + `OPENAI_API_BASE` also work.

