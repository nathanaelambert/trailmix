from dash import Dash, Input, Output, State, html, dcc, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import os
from dotenv import load_dotenv

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.title = "CULINAIRE 🥗"

from layout import layout
app.layout = layout
load_dotenv()  # load env vars from .env if present

# -------------------- GOOGLE ANALYTICS --------------------

GA_TAG = 'G-3R4901JN3H'

app.index_string = """
<!DOCTYPE html>
<html>
  <head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-3R4901JN3H"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-3R4901JN3H');

      document.addEventListener('click', function(event) {
        var elem = event.target;
        var elementInfo = elem.tagName;
        if (elem.id) elementInfo += ' #' + elem.id;
        if (elem.className) elementInfo += ' .' + elem.className.toString().replace(/\s+/g, '.');
        var timestamp = new Date().toISOString();

        gtag('event', 'user_click', {
            'event_category': 'User Interaction',
            'event_label': elementInfo,
            'event_timestamp': timestamp
        });
      });

    </script>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
  </head>
  <body>
    {%app_entry%}
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>
  </body>
</html>
"""
# ---------------------Callbacks ---------------
from recipes import sample_recipes, days, meal_times
from helpers import rescale_day, normalize_mealplan, create_recipe_widget
import json, re
from openai import OpenAI
from functools import lru_cache

api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Please set OPENROUTER_API_KEY (or OPENAI_API_KEY) for the meal planner.")

default_headers = {"X-Title": os.getenv("OPENROUTER_APP_TITLE", "CULINAIRE")}
if os.getenv("OPENROUTER_SITE_URL"):
    default_headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL")

base_url = (
    os.getenv("OPENROUTER_BASE_URL")
    or os.getenv("OPENAI_API_BASE")
    or os.getenv("OPENAI_BASE_URL")
    or "https://openrouter.ai/api/v1"
)

client = OpenAI(
    base_url=base_url,
    api_key=api_key,
    default_headers=default_headers,
)

@lru_cache(maxsize=1)
def get_hf_pipeline():
    """Lazy-load the Hugging Face recipe generator pipeline."""
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    except ImportError:
        raise RuntimeError("transformers is required for the HuggingFace model. Please pip install transformers.")

    tokenizer = AutoTokenizer.from_pretrained("Ashikan/dut-recipe-generator")
    model = AutoModelForCausalLM.from_pretrained("Ashikan/dut-recipe-generator")
    return pipeline("text-generation", model=model, tokenizer=tokenizer)

def extract_json_block(raw_text: str) -> str:
    """Try to pull a JSON object out of a model response."""
    if raw_text is None:
        return ""
    if not isinstance(raw_text, str):
        try:
            return json.dumps(raw_text)
        except Exception:
            raw_text = str(raw_text)
    if not raw_text:
        return ""

    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw_text, re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
        if candidate:
            return candidate

    trimmed = raw_text.strip()
    if trimmed.startswith("{") and trimmed.endswith("}"):
        return trimmed

    # Prefer the first valid-looking JSON object; if multiple, take the first complete
    for m in re.finditer(r"\{.*\}", trimmed, re.DOTALL):
        candidate = m.group(0).strip()
        # quick heuristic: balanced braces
        if candidate.count("{") == candidate.count("}"):
            return candidate

    # If we got here, try to slice from first '{' to last '}'
    first_open = trimmed.find("{")
    last_close = trimmed.rfind("}")
    if first_open != -1 and last_close != -1 and last_close > first_open:
        return trimmed[first_open : last_close + 1].strip()

    # As a last resort, try to truncate at the last closing brace
    if last_close != -1:
        return trimmed[: last_close + 1]

    return trimmed


def clean_json_text(raw_text: str) -> str:
    """Light cleanup for common JSON mistakes (trailing commas, smart quotes)."""
    if raw_text is None:
        return ""
    if not isinstance(raw_text, str):
        try:
            raw_text = json.dumps(raw_text)
        except Exception:
            raw_text = str(raw_text)
    txt = raw_text
    # Replace smart quotes with regular quotes
    txt = txt.replace("“", "\"").replace("”", "\"")
    # Remove trailing commas before closing braces/brackets
    txt = re.sub(r",\s*([}\]])", r"\1", txt)
    return txt

SYSTEM_PROMPT = """
You are CULINAIRE, a precise and practical AI meal planner.

Your output must be VALID JSON ONLY.
Return a single JSON object with no code fences, markdown, or commentary.

Include:
- A 7-day meal plan with Breakfast, Lunch, and Dinner for EVERY day.
- Keys for each meal must be lowercase: breakfast, lunch, dinner.
- Each meal includes: meal (name), ingredients (as dict), calories (number), and a short recipe (1 sentence).
- Total calories per day should match the user's target within ±5%.
- A grocery_list section that combines all ingredients by item name, summed quantities, and category.
- A summary with total weekly calories and estimated cost.
- Do not use placeholder values like "None", "?", or "N/A". Provide realistic items and quantities.
- Grocery list entries must have item, category, and quantity; category should be something like Produce, Dairy, Meat, Pantry, Bakery, Frozen, Beverages, etc.

Recipe description style (for the recipe field):
- Describe only what is visibly present; do not mention anything unidentifiable.
- Include color features (dominant colors; interwoven vs. unified), shape/texture (shredded, granular, smooth, rough), spatial arrangement (mixed, stacked, layered, wrapped), and fusion state (distinguishable, fully fused, placed on top).
- Start with a step number (1., 2., etc.) and keep it to one sentence on one line.
- Choose one interaction type and weave it into the sentence: Mix up, Blend, Put on, Cover, or No relationship.
- Avoid extra commentary; keep it concise and vivid.
"""

@app.callback(
    Output("budget_slider_container", "style"),
    Input("budget_ignore", "value")
)
def toggle_budget_visibility(ignore_values):
    if "ignore" in ignore_values:
        return {"display": "none"}
    else:
        return {"display": "block"}

@app.callback(
    Output("calories_slider_container", "style"),
    Input("calories_ignore", "value")
)
def toggle_calories_visibility(ignore_values):
    if "ignore" in ignore_values:
        return {"display": "none"}
    else:
        return {"display": "block"}

def load_plan(json_text: str) -> dict:
    """Load JSON and normalize nested string JSON."""
    obj = json.loads(json_text)
    if isinstance(obj, str):
        obj = json.loads(obj)
    if not isinstance(obj, dict):
        raise ValueError("Meal plan response must be a JSON object")
    return obj


def render_plan_view(plan: dict, target: float):
    days = normalize_mealplan(plan.get("meal_plan"))
    blocks = []

    blocks.append(html.H3("Your Weekly Meal Plan 🍲"))
    day_totals = []
    for day_name, day_dict in days:
        if not isinstance(day_dict, dict):
            continue
        day_dict = rescale_day(day_dict, target)
        total = sum(day_dict[m].get("calories",0) for m in ["breakfast","lunch","dinner"] if m in day_dict)
        day_totals.append(total)
        meals_section = [html.H4(f"{day_name} — {round(total)} kcal (Target: {target})")]
        for m in ["breakfast","lunch","dinner"]:
            if m not in day_dict: continue
            meal = day_dict[m]
            meals_section.append(html.H5(f"{m.capitalize()} – {meal.get('meal', m)}"))
            ing_list = [html.Li(f"{k}: {v}") for k,v in meal.get("ingredients", {}).items()]
            meals_section.append(html.Ul(ing_list))
            meals_section.append(html.P(f"{meal.get('recipe','')} (~{meal.get('calories','?')} kcal)"))
        blocks.extend(meals_section)
        blocks.append(html.Hr())

    grocery = plan.get("grocery_list") or []
    if isinstance(grocery, dict):
        grocery = list(grocery.values())
    if grocery:
        blocks.append(html.H3("🛒 Grocery List"))
        blocks.extend(
            html.Li(f"{g.get('item')} ({g.get('category')}): {g.get('quantity')}")
            for g in grocery
            if isinstance(g, dict) and g.get("item")
        )

    summary = plan.get("summary") or {}
    if not isinstance(summary, dict):
        summary = {}
    if not summary.get("average_daily_calories") and day_totals:
        summary["average_daily_calories"] = round(sum(day_totals)/len(day_totals))
    blocks.append(html.H3("📋 Summary"))
    blocks.append(html.P(f"Average daily calories: {summary.get('average_daily_calories','?')} kcal"))
    blocks.append(html.P(f"Estimated weekly cost: {summary.get('estimated_weekly_cost','?')}"))
    blocks.append(html.P(f"Nutrition focus: {summary.get('nutrition_focus','?')}"))

    return html.Div(blocks)


def generate_plan(n, weight, activity, goals, budget, calories, restrictions, diet, location):
    user_prompt = f"""
    Create a 7-day meal plan for:
    - Body weight: {weight} kg
    - Activity: {activity}
    - Goals: {', '.join(goals or [])}
    - Diet: {diet}
    - Restrictions: {restrictions or 'None'}
    - Target calories: {calories} kcal/day
    - Budget: {budget} CHF
    - Location: {location}
    """

    raw_content = ""
    json_text = ""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":SYSTEM_PROMPT},
                      {"role":"user","content":user_prompt}],
            response_format={"type": "json_object"},
        )
        raw_content = (response.choices[0].message.content or "").strip()
        json_text = extract_json_block(raw_content)
        plan = load_plan(json_text)
        return render_plan_view(plan, calories)
    except json.JSONDecodeError as je:
        cleaned_text = clean_json_text(json_text)
        if cleaned_text != json_text:
            try:
                plan = load_plan(cleaned_text)
                return render_plan_view(plan, calories)
            except json.JSONDecodeError:
                pass

        snippet = (raw_content or cleaned_text or "")[:1000]
        return html.Div(
            [
                html.P(f"Error: JSON parsing failed – {je}", style={"color": "red", "fontWeight": "bold"}),
                html.Pre(snippet, style={"whiteSpace": "pre-wrap", "background": "#f8f9fa", "padding": "10px"}),
            ]
        )
    except Exception as e:
        return html.Div(f"Error: {type(e).__name__} – {e}", style={"color": "red"})


def generate_plan_hf(n, weight, activity, goals, budget, calories, restrictions, diet, location):
    user_prompt = f"""
    You are CULINAIRE. Create a 7-day meal plan as pure JSON only.
    Do NOT include the prompt or any text outside the JSON. No ellipses.
    - Body weight: {weight} kg
    - Activity: {activity}
    - Goals: {', '.join(goals or [])}
    - Diet: {diet}
    - Restrictions: {restrictions or 'None'}
    - Target calories: {calories} kcal/day
    - Budget: {budget} CHF
    - Location: {location}

    Return exactly this shape (no extra keys):
    {{
      "meal_plan": [
        {{"day": "Monday", "meals": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}}}}},
        {{"day": "Tuesday", "meals": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}}}}},
        {{"day": "Wednesday", "meals": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}}}}},
        {{"day": "Thursday", "meals": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}}}}},
        {{"day": "Friday", "meals": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}}}}},
        {{"day": "Saturday", "meals": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}}}}},
        {{"day": "Sunday", "meals": {{"breakfast": {{}}, "lunch": {{}}, "dinner": {{}}}}}}
      ],
      "grocery_list": [{{"item": "Bananas", "quantity": "6", "category": "Produce"}}],
      "summary": {{"average_daily_calories": 0, "estimated_weekly_cost": "CHF 0", "nutrition_focus": "balanced"}}
    }}
    Each meal object must include: "meal", "ingredients" (dict), "calories" (number), "recipe" (1 sentence).
    Make calorie totals close to target.
    """
    raw_content = ""
    json_text = ""
    try:
        pipe = get_hf_pipeline()
        raw_output = pipe(
            user_prompt,
            max_length=900,
            temperature=0.2,
            do_sample=True,
            truncation=True,
            return_full_text=False,
        )[0]
        raw_content = raw_output.get("generated_text") or ""
        json_text = extract_json_block(raw_content)
        plan = load_plan(json_text)
        return render_plan_view(plan, calories)
    except Exception as e:
        return html.Div(
            [
                html.P(f"Error using HuggingFace model: {type(e).__name__} – {e}", style={"color": "red", "fontWeight": "bold"}),
                html.Pre((raw_content or "")[:800], style={"whiteSpace": "pre-wrap", "background": "#f8f9fa", "padding": "10px"}),
            ]
        )


@app.callback(
    Output("plan_output", "children"),
    Input("generate", "n_clicks"),
    Input("generate_hf", "n_clicks"),
    State("body_weight", "value"),
    State("activity", "value"),
    State("goals", "value"),
    State("budget", "value"),
    State("dayly_calories", "value"),
    State("restrictions", "value"),
    State("diet_type", "value"),
    State("location", "value"),
    State("budget_ignore", "value"),
    State("calories_ignore", "value"),
)
def handle_generate_plan(n_clicks, n_clicks_hf, weight, activity, goals, budget, calories, restrictions, diet, location, budget_ignore, calories_ignore):
    if not n_clicks and not n_clicks_hf:
        raise PreventUpdate

    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    budget_value = budget if "ignore" not in (budget_ignore or []) else "Not specified"
    calorie_target = calories if "ignore" not in (calories_ignore or []) else 2400

    if trigger == "generate_hf":
        return generate_plan_hf(
            n_clicks_hf,
            weight,
            activity,
            goals or [],
            budget_value,
            calorie_target,
            restrictions or "None",
            diet,
            location or "Not specified",
        )

    return generate_plan(
        n_clicks,
        weight,
        activity,
        goals or [],
        budget_value,
        calorie_target,
        restrictions or "None",
        diet,
        location or "Not specified",
    )

@app.callback(
    Output("test_recipes_output", "children"),
    Input("test_recipes", "n_clicks")
)
def display_test_recipes(n_clicks):
    if n_clicks == 0:
        return ""

    blocks = []
    # We have 14 recipes, ordered as Monday breakfast, Monday dinner, Tuesday breakfast, etc.
    for i in range(14):
        day_idx = i // 2
        meal_idx = i % 2
        day = days[day_idx]
        meal = meal_times[meal_idx]
        # Add header for each recipe pair (day and meal)
        blocks.append(html.H4(f"{day} {meal}", style={"marginTop": "20px", "marginBottom": "10px"}))
        # Add recipe widget
        blocks.append(create_recipe_widget(sample_recipes[i]))

    return blocks


# Callback for collapsible steps toggling (expand/collapse) for all recipes
for recipe in sample_recipes:
    steps_id = f"steps-{recipe.name.replace(' ', '-')}"
    toggle_id = f"toggle-{steps_id}"

    @app.callback(
        Output(steps_id, "is_open"),
        Input(toggle_id, "n_clicks"),
        State(steps_id, "is_open")
    )
    def toggle_collapse(n, is_open):
        if n:
            return not is_open
        return is_open

# Callback for rating stars to enable clicking and highlighting stars
# (simplified version: each star toggles rating up to that star)

for recipe in sample_recipes:
    rate_id = f"rate-{recipe.name.replace(' ', '-')}"
    for i in range(1,6):
        star_id = f"{rate_id}-star-{i}"

        @app.callback(
            Output(star_id, "children"),
            Input(star_id, "n_clicks"),
            State(star_id, "children"),
            prevent_initial_call=True
        )
        def toggle_star(n_clicks, current_star, star_number=i, r_id=rate_id):
            # Logic to toggle star "filled" or "empty"
            # For demonstration: on click fill stars up to the clicked one, otherwise empty
            # This requires state for all stars; better handled with pattern matching callbacks but limited here
            # So keep this a placeholder or consider a JS front-end implementation for fully interactive stars
            return "★"  # filled star on click for user feedback


# -------------------- MAIN --------------------
if __name__ == '__main__':
    app.run(debug=False)
