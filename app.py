from dash import Dash, html, dcc, Input, Output, State
import json, re, openai
import dash_bootstrap_components as dbc


# -------------------- APP & CONFIG --------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.title = "CULINAIRE 🥗"

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


# -------------------- HELPERS --------------------
def numeric_scale(qty, scale):
    nums = re.findall(r"[0-9]+\\.?[0-9]*", qty)
    if not nums:
        return qty
    for num in nums:
        new_val = round(float(num) * scale, 1)
        qty = qty.replace(num, str(new_val), 1)
    return qty

def rescale_day(day_dict, target):
    meals = ["breakfast","lunch","dinner"]
    total = sum(day_dict[m].get("calories", 0) for m in meals if m in day_dict)
    if total <= 0: return day_dict
    scale = target / total
    for m in meals:
        if m not in day_dict: continue
        meal = day_dict[m]
        meal["calories"] = round(meal.get("calories", 0) * scale)
        for k,v in meal.get("ingredients", {}).items():
            meal["ingredients"][k] = numeric_scale(v, scale)
    return day_dict

def normalize_mealplan(mp):
    if isinstance(mp, list):
        return [(d.get("day", f"Day {i+1}"), d.get("meals", d)) for i, d in enumerate(mp)]
    if isinstance(mp, dict):
        return [(k.replace("_", " ").title(), v) for k,v in mp.items()]
    return []

# -------------------- LAYOUT --------------------
app.layout = html.Div([
    html.H1([
        "🥗 CULIN",
        html.B("AI"),
        "RE"
    ], style={"textAlign": "center", "marginTop": "20px"}),

    html.P("Your AI meal planner – plan smart, eat better", style={"textAlign": "center", "color": "gray", "marginBottom": "20px"}),

    html.Div([
        html.Label("Weight (kg)"),
        dcc.Input(id="body_weight", type="number", value=70, style={"width": "100%", "marginBottom": "10px"}),

        html.Label("Weekly food budget (CHF)"),
        dcc.Slider(
            id='budget',
            min=0, max=200, step=1,
            value=80,
            marks={i: str(i) for i in range(0, 201, 20)},
            tooltip={"placement": "bottom"},
            updatemode='drag',
        ),
        dcc.Checklist(
            options=[{"label": "ignore for now", "value": "ignore"}],
            value=[],
            id="budget_ignore",
            style={"marginBottom": "20px"}
        ),

        html.Label("Target (Calories/day)"),
        dcc.Input(id="daily_calories", type="number", value=2400, style={"width": "100%", "marginBottom": "20px"}),

        html.Label("Activity level"),
        dcc.Dropdown(["Sedentary","Lightly active","Moderately active","Very active","Extra active"],
                     "Moderately active", id="activity", style={"marginBottom": "20px"}),

        html.Label("Diet type"),
        dcc.Dropdown(["Omnivore","Vegetarian","Keto","Vegan","Pescatarian","Gluten free","Other"],
                     "Omnivore", id="diet_type", style={"marginBottom": "20px"}),

        html.Label("Location (e.g. Lausanne)"),
        dcc.Input(id="location", placeholder="Location (e.g. Lausanne)", value="Lausanne", style={"width": "100%", "marginBottom": "20px"}),

        html.Label("Your goals (multi-select)"),
        dcc.Dropdown(
            id="goals", multi=True,
            options=[{"label": g, "value": g} for g in
                     ["Lose weight","Build muscle","Maintain muscle mass",
                      "Reduce meat consumption","Discover new recipes","Reduce processed food consumption"]],
            placeholder="Your goals...",
            style={"marginBottom": "20px"}
        ),

        html.Label("Any dietary restrictions or allergies?"),
        dcc.Textarea(id="restrictions", placeholder="Any dietary restrictions or allergies?", style={"width": "100%", "height": "80px", "marginBottom": "20px"}),

        html.Button("Generate My Weekly Plan 🧑‍🍳", id="generate", n_clicks=0, style={"backgroundColor": "#28a745", "color": "white", "border": "none", "padding": "10px 15px", "borderRadius": "5px"}),
    ], style={"maxWidth": "600px", "margin": "auto"}),

    html.Div(id="plan_output", style={"marginTop": "40px", "maxWidth": "600px", "margin": "auto"})
])

# (Keep your helper functions numeric_scale, rescale_day, normalize_mealplan unchanged here)

# -------------------- CALLBACK --------------------
@app.callback(
    Output("plan_output", "children"),
    Input("generate", "n_clicks"),
    [
        State("body_weight", "value"),
        State("activity", "value"),
        State("goals", "value"),
        State("budget", "value"),
        State("daily_calories", "value"),
        State("restrictions", "value"),
        State("diet_type", "value"),
        State("location", "value"),
    ],
    prevent_initial_call=True
)
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

# -------------------- MAIN --------------------
if __name__ == '__main__':
    app.run(debug=False)