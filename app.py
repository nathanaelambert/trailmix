from dash import Dash, Input, Output, State, html, dcc
import dash_bootstrap_components as dbc

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.title = "CULINAIRE 🥗"

from layout import layout
app.layout = layout

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
import json, re, openai

openai.api_key = "YOUR_OPENAI_KEY"

SYSTEM_PROMPT = """
You are CULINAIRE, a precise and practical AI meal planner.

Your output must be VALID JSON ONLY.

Include:
- A 7-day meal plan with Breakfast, Lunch, and Dinner.
- Each meal includes: name, ingredients (as dict), calories, and a short recipe (2–3 sentences).
- Total calories per day should match the user's target within ±5%.
- A grocery_list section that combines all ingredients by item name, summed quantities, and category.
- A summary with total weekly calories and estimated cost.
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

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":SYSTEM_PROMPT},
                      {"role":"user","content":user_prompt}],
            temperature=0.6,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^``````$", "", raw.strip(), flags=re.MULTILINE)
        plan = json.loads(raw)
        days = normalize_mealplan(plan.get("meal_plan"))
        target = calories
        blocks = []

        blocks.append(html.H3("Your Weekly Meal Plan 🍲"))
        for day_name, day_dict in days:
            day_dict = rescale_day(day_dict, target)
            total = sum(day_dict[m].get("calories",0) for m in ["breakfast","lunch","dinner"] if m in day_dict)
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

        grocery = plan.get("grocery_list", [])
        if grocery:
            blocks.append(html.H3("🛒 Grocery List"))
            blocks.extend(html.Li(f"{g.get('item')} ({g.get('category')}): {g.get('quantity')}") for g in grocery)

        summary = plan.get("summary", {})
        blocks.append(html.H3("📋 Summary"))
        blocks.append(html.P(f"Average daily calories: {summary.get('average_daily_calories','?')} kcal"))
        blocks.append(html.P(f"Estimated weekly cost: {summary.get('estimated_weekly_cost','?')}"))
        blocks.append(html.P(f"Nutrition focus: {summary.get('nutrition_focus','?')}"))

        return html.Div(blocks)
    except Exception as e:
        return html.Div(f"Error: {type(e).__name__} – {e}", style={"color": "red"})

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