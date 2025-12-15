# CULINAIRE
CULIN**AI**RE is a Dash + Flask meal-planning app that generates weekly plans, groceries, PDF summaries, and chat guidance using OpenAI/OpenRouter LLMs (with a Hugging Face fallback). It stores user profiles locally, respects per-meal portions, and can enrich grocery items with Migros pricing.

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py               # starts Dash on 0.0.0.0:8050 (PORT env respected)
```

## Core Features
- Profile capture & persistence: email-keyed SQLite (`user_profiles.db`) stores name, weight, goals, budget, calories, diet, restrictions, location, cravings/avoids, cuisines, complexity, per-day/meal portions, and last plan JSON. GDPR delete supported.
- Plan generation (OpenAI/OpenRouter): strict JSON prompt for 7-day plans; fixed calorie model (25/35/40% breakfast/lunch/dinner per person); portion-aware rendering; per-meal “Change” regeneration keeps plan and grocery list in sync.
- Hugging Face fallback: flax-community/t5-recipe-generation (requires `transformers[flax]` + `jax`) for offline-ish recipe ideas with the same calorie overrides.
- Grocery list: aggregated from all meals (skipping zero-portion meals), categorized heuristically, editable (add/remove), stored in `grocery-list-store` and used for PDF/export.
- Pricing enrichment (Migros): optional node helper `migros_price_helper.js` + HTTP search to attach prices/energy per ingredient and total estimate; capped to ~20 unique items.
- PDF export: ReportLab calendar-style PDF with per-day meals/portions/calories and categorized grocery list; downloaded via `Download PDF Summary` button.
- Chat assistant: llama-index ReAct agent (gpt-4o-mini) with DuckDuckGo search tool; uses live form/profile/plan context and cites URLs; premium-gated.
- Premium flow: modal + EPFL email verification unlocks chat, save/like recipe buttons, and order-groceries CTA; badge updates when active.

## App Layout (layout.py)
- Tabs: User Info (profile + save/load/delete), Recipes (plan generation buttons + output), Grocery List (editable list). Chat panel is always visible.
- Stores: `plan-data-store` (plan JSON + metadata), `grocery-list-store`, `latest_plan_data`, `chat_history`, `premium_status`.

## Environment & Secrets
- Primary (OpenRouter): `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` (default https://openrouter.ai/api/v1), `OPENROUTER_SITE_URL`, `OPENROUTER_APP_TITLE`.
- Alternative (OpenAI style): `OPENAI_API_KEY`, `OPENAI_API_BASE` or `OPENAI_BASE_URL`. `OPENROUTER_API_KEY` takes precedence if both exist.
- Database: `USER_DB_PATH` (defaults to `user_profiles.db`).
- Migros: `MIGROS_API_TOKEN`/`MIGROS_LESHOP_TOKEN`/`MIGROS_API_KEY` (optional), `MIGROS_API_WRAPPER_USERAGENT`, `MIGROS_NODE_BIN`.
- PORT: server port (default 8050).

## Data & Privacy
- SQLite schema: `user_profiles(email PK, name, weight, activity, goals JSON, budget, calories, restrictions, diet, location, avoid_ingredients, cravings, complexity, cuisines JSON, portions_json, last_plan, updated_at)`.
- Clearing data: “🗑️ Clear my data” deletes the email row; `clear_user_data` also available programmatically.
- Last plan snapshot saved with the profile for continuity; removable via the delete flow.

## Plan Generation Details
- Prompt enforces: 7 named days, breakfast/lunch/dinner keys, ingredients dict, rounded quantities, 5–7 step recipes, grocery_list with categories, summary section. Calories per meal are overridden in code to fixed per-person targets; zero portions set to 0 kcal and “Skipped” meals.
- Per-meal regeneration: `change_single_meal` targets one meal, respects portions/diet/restrictions, recalculates grocery list via `aggregate_grocery_list_from_plan`, and preserves existing list on failure.
- Grocery aggregation: deduplicates ingredients (case-insensitive), assigns categories (Produce/Dairy/Meat/Pantry/etc.), sorts by category then name.

## Hugging Face Path
- `generate_plan_hf` builds ingredient prompts, parses T5 text to title/ingredients/directions, applies the same calorie overrides, and aggregates groceries (quantities concatenated). Requires `transformers[flax]` and `jax` installed; otherwise prefer the default OpenRouter/OpenAI path.

## Pricing (Migros) Flow
- Collect up to ~20 unique ingredient names from grocery/ingredients.
- Try node helper (`migros_price_helper.js`) first; cache token; fall back to HTTP search (`search_migros_product`).
- Attach `migros_pricing` (items, estimated_total, currency, note) to `plan_data` when available.

## PDF Export
- `generate_meal_plan_pdf` renders per-day tables (meal names, portions, calories) and categorized grocery list, then returns bytes via `dcc.send_bytes` for download.

## Chat Assistant
- Context: live form values, saved profile digest, plan digest (`plan_digest` / `plan_full_context`), and any Migros pricing summary.
- Behaviour: concise, source-citing answers with DuckDuckGo via llama-index FunctionTool; gated by premium status (non-premium opens modal).

## Premium Gating
- “Go Premium” button opens modal; EPFL email regex enables premium in-session. Chat send, order-groceries, and like/save recipe buttons are gated and will open the modal if not premium.

## Development Notes
- Styles: Dash + Bootstrap FLATLY theme; GA snippet present but disabled.
- Debug logging: numerous stdout/stderr prints for callback triggers, parsing, and grocery recomputation to aid troubleshooting.
- Node binary selection: `_get_node_bin` prefers `MIGROS_NODE_BIN` or latest nvm install, else `node` on PATH.

