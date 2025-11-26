from dash import Dash, Input, Output, State, html
import dash_bootstrap_components as dbc

from layout import layout
from recipes import sample_recipes, days, meal_times
from helpers import create_recipe_widget, rescale_day, normalize_mealplan

import os
import json
import re
import openai

# -------------------- OPENAI SETUP --------------------

# Uses env var: export OPENAI_API_KEY="sk-..."
openai.api_key = ""

SYSTEM_PROMPT = """
You are CULINAIRE, a precise and practical AI meal planner.

You MUST respond with VALID JSON ONLY. No Markdown, no backticks, no commentary.

Return an object with the following top-level keys:

- "meal_plan": a 7-day plan. Either:
    - a dict like {
        "Monday": {
          "breakfast": {...},
          "lunch": {...},
          "dinner": {...}
        },
        "Tuesday": { ... },
        ...
      }
      OR a list of day objects like:
      [
        {
          "day": "Monday",
          "meals": {
            "breakfast": {...},
            "lunch": {...},
            "dinner": {...}
          }
        },
        ...
      ]

  Each meal object MUST have:
    - "meal": short human-readable meal name
    - "ingredients": dict mapping ingredient name -> quantity string
    - "calories": numeric kcal for the meal
    - "recipe": 2–4 concise sentences describing the steps

- "grocery_list": a list of objects:
    [
      {
        "item": "Rolled oats",
        "quantity": "350 g",
        "category": "Grains"
      },
      ...
    ]

- "summary": an object with:
    {
      "average_daily_calories": number,
      "estimated_weekly_cost": string,
      "nutrition_focus": string
    }
"""


app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "CULINAIRE 🥗"
app.layout = layout

# -------------------- GOOGLE ANALYTICS --------------------

GA_TAG = "G-3R4901JN3H"

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
        if (elem.className) elementInfo += ' .' + elem.className.toString().replace(/\\s+/g, '.');
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

# ---------------------- LLM MEAL PLAN LOGIC ----------------------


def call_openai_mealplan(
    body_weight,
    activity,
    goals,
    budget,
    daily_calories,
    restrictions,
    diet_type,
    location,
):
    """Call OpenAI and return (plan_dict, target_calories, raw_text)."""
    if not daily_calories or daily_calories <= 0:
        daily_calories = 2000

    goals_str = ", ".join(goals or []) if isinstance(goals, list) else ""

    user_prompt = f"""
Create a 7-day meal plan with breakfast, lunch, and dinner for each day.

User profile:
- Body weight: {body_weight or "unknown"} kg
- Activity level: {activity or "unknown"}
- Goals: {goals_str or "general health"}
- Diet type: {diet_type or "Omnivore"}
- Restrictions / allergies: {restrictions or "None"}
- Target calories per day: {daily_calories} kcal
- Weekly budget: {budget} CHF
- Location: {location or "not specified"}

Make meals realistic, structured, and consistent across days. Vary proteins and vegetables.
"""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.5,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Try to extract pure JSON (defensive)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    raw_json = match.group(0) if match else raw

    plan = json.loads(raw_json)
    return plan, daily_calories, raw


def render_mealplan(plan_dict, target_calories):
    """Render the JSON meal plan in a nice HTML structure (defensive)."""
    blocks = []

    meal_plan = plan_dict.get("meal_plan")
    grocery_list = plan_dict.get("grocery_list", [])
    summary = plan_dict.get("summary", {})

    if meal_plan is None:
        return html.Div(
            "Model response does not contain 'meal_plan'.",
            style={"color": "red"},
        )

    # Normalize into list of (day_name, day_meals_dict)
    normalized = {}
    if isinstance(meal_plan, dict):
        # {"Monday": {...}, "Tuesday": {...}}
        for day_name, day_obj in meal_plan.items():
            if isinstance(day_obj, dict):
                meals = day_obj.get("meals", day_obj)
                normalized[day_name] = meals
    elif isinstance(meal_plan, list):
        # [{"day": "Monday", "meals": {...}}, ...]
        for i, day_obj in enumerate(meal_plan):
            if not isinstance(day_obj, dict):
                continue
            day_name = day_obj.get("day", f"Day {i+1}")
            meals = day_obj.get("meals", day_obj)
            normalized[day_name] = meals
    else:
        return html.Div(
            "Unexpected 'meal_plan' structure.",
            style={"color": "red"},
        )

    blocks.append(html.H3("Your Weekly Meal Plan 🍲"))

    for day_name, meals in normalized.items():
        blocks.append(
            html.H4(
                f"{day_name} (target: {target_calories} kcal/day)",
                style={"marginTop": "20px"},
            )
        )

        if not isinstance(meals, dict):
            blocks.append(html.P("Invalid meals structure for this day."))
            continue

        for meal_name in ["breakfast", "lunch", "dinner"]:
            if meal_name not in meals:
                continue
            meal = meals[meal_name]

            title = meal.get("meal", meal_name.capitalize())
            calories = meal.get("calories", "?")
            recipe_text = meal.get("recipe", "")
            ingredients = meal.get("ingredients", {})

            blocks.append(
                html.H5(
                    f"{meal_name.capitalize()} – {title} (~{calories} kcal)",
                    style={"marginTop": "10px"},
                )
            )

            if isinstance(ingredients, dict):
                blocks.append(
                    html.Ul([html.Li(f"{k}: {v}") for k, v in ingredients.items()])
                )
            else:
                blocks.append(html.P("No ingredients list."))

            blocks.append(html.P(recipe_text))

        blocks.append(html.Hr())

    # Grocery list
    if grocery_list:
        blocks.append(html.H3("🛒 Grocery List"))
        if isinstance(grocery_list, list):
            blocks.append(
                html.Ul(
                    [
                        html.Li(
                            f"{g.get('item')} ({g.get('category')}): {g.get('quantity')}"
                        )
                        for g in grocery_list
                        if isinstance(g, dict)
                    ]
                )
            )
        else:
            blocks.append(html.P("Unexpected grocery_list format."))

    # Summary
    blocks.append(html.H3("📋 Summary"))
    blocks.append(
        html.P(
            f"Average daily calories: {summary.get('average_daily_calories', '?')} kcal"
        )
    )
    blocks.append(
        html.P(
            f"Estimated weekly cost: {summary.get('estimated_weekly_cost', '?')}"
        )
    )
    blocks.append(
        html.P(f"Nutrition focus: {summary.get('nutrition_focus', '?')}")
    )

    return html.Div(blocks)


# ---------------------- CALLBACKS ----------------------


@app.callback(
    Output("budget_slider_container", "style"),
    Input("budget_ignore", "value"),
)
def toggle_budget_visibility(ignore_values):
    if ignore_values and "ignore" in ignore_values:
        return {"display": "none"}
    return {"display": "block"}


@app.callback(
    Output("calories_slider_container", "style"),
    Input("calories_ignore", "value"),
)
def toggle_calories_visibility(ignore_values):
    if ignore_values and "ignore" in ignore_values:
        return {"display": "none"}
    return {"display": "block"}


@app.callback(
    Output("plan_output", "children"),
    Input("generate", "n_clicks"),
    State("body_weight", "value"),
    State("activity", "value"),
    State("goals", "value"),
    State("budget", "value"),
    State("dayly_calories", "value"),
    State("restrictions", "value"),
    State("diet_type", "value"),
    State("location", "value"),
)
def on_generate_click(
    n_clicks,
    body_weight,
    activity,
    goals,
    budget,
    daily_calories,
    restrictions,
    diet_type,
    location,
):
    if not n_clicks:
        return ""

    if not openai.api_key:
        return html.Div(
            "Error: OPENAI_API_KEY is not set in the environment.",
            style={"color": "red"},
        )

    try:
        plan_dict, target, raw = call_openai_mealplan(
            body_weight,
            activity,
            goals,
            budget,
            daily_calories,
            restrictions,
            diet_type,
            location,
        )
        return render_mealplan(plan_dict, target)

    except json.JSONDecodeError as e:
        return html.Div(
            [
                html.P(
                    f"Error parsing model output as JSON: {e}",
                    style={"color": "red"},
                ),
                html.Hr(),
                html.P("Raw model output (truncated):"),
                html.Pre(raw[:3000]),
            ]
        )
    except Exception as e:
        return html.Div(
            f"Error calling OpenAI: {type(e).__name__} – {e}",
            style={"color": "red"},
        )


# Test Recipes – still uses your hard-coded recipes
@app.callback(
    Output("test_recipes_output", "children"),
    Input("test_recipes", "n_clicks"),
)
def display_test_recipes(n_clicks):
    if not n_clicks:
        return ""

    blocks = []
    # 14 recipes: Monday breakfast/dinner, Tuesday breakfast/dinner, ...
    for i in range(len(sample_recipes)):
        day_idx = i // 2
        meal_idx = i % 2
        day = days[day_idx]
        meal = meal_times[meal_idx]

        blocks.append(
            html.H4(
                f"{day} {meal}",
                style={"marginTop": "20px", "marginBottom": "10px"},
            )
        )
        blocks.append(create_recipe_widget(sample_recipes[i]))

    return blocks


# -------------------- MAIN --------------------
if __name__ == "__main__":
    app.run(debug=True)
