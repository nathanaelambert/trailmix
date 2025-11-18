from dash import callback_context, Dash, html, dcc, Input, Output, State
import json, re, openai
import dash_bootstrap_components as dbc
import smtplib
from email.message import EmailMessage


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
# -------------------- RECIPES --------------------
class Ingredient:
    def __init__(self, name, amount, amount_type):
        self.name = name
        self.amount = amount
        self.amount_type = amount_type

class Recipe:
    def __init__(self, name, prep_time, calories, ingredients, steps):
        self.name = name
        self.prep_time = prep_time 
        self.calories = calories
        self.ingredients = ingredients 
        self.steps = steps

days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
meal_times = ["Breakfast", "Dinner"]

# Sample 14 recipes
sample_recipes = [
    # 1
    Recipe(
        "Greek Yogurt Parfait",
        "10 min",
        320,
        [
            Ingredient("Greek Yogurt", 200, "g"),
            Ingredient("Granola", 30, "g"),
            Ingredient("Mixed Berries", 80, "g"),
            Ingredient("Honey", 10, "g"),
        ],
        [
            "Spoon the Greek yogurt into a bowl or glass.",
            "Layer granola and mixed berries on top.",
            "Drizzle with honey and serve immediately."
        ]
    ),

    # 2
    Recipe(
        "Baked Salmon with Quinoa",
        "30 min",
        520,
        [
            Ingredient("Salmon Fillet", 180, "g"),
            Ingredient("Quinoa (dry)", 70, "g"),
            Ingredient("Broccoli Florets", 120, "g"),
            Ingredient("Olive Oil", 10, "g"),
            Ingredient("Lemon Juice", 10, "g"),
        ],
        [
            "Season the salmon with salt, pepper, and a drizzle of olive oil, then bake at 180°C for 15–18 minutes.",
            "Cook quinoa according to package instructions.",
            "Steam broccoli until tender and serve with salmon and quinoa, finishing with lemon juice."
        ]
    ),

    # 3
    Recipe(
        "Veggie Omelette",
        "15 min",
        310,
        [
            Ingredient("Egg", 2, "unit"),
            Ingredient("Egg White", 60, "g"),
            Ingredient("Spinach", 40, "g"),
            Ingredient("Cherry Tomato", 50, "g"),
            Ingredient("Feta Cheese", 20, "g"),
        ],
        [
            "Whisk eggs and egg whites with a pinch of salt and pepper.",
            "Sauté spinach and halved cherry tomatoes in a non-stick pan, then pour the eggs over.",
            "Sprinkle with feta and cook until set, folding in half before serving."
        ]
    ),

    # 4
    Recipe(
        "Turkey Stir-Fry with Brown Rice",
        "25 min",
        540,
        [
            Ingredient("Turkey Breast Strips", 160, "g"),
            Ingredient("Brown Rice (dry)", 70, "g"),
            Ingredient("Bell Pepper", 60, "g"),
            Ingredient("Carrot", 50, "g"),
            Ingredient("Soy Sauce (reduced salt)", 10, "g"),
            Ingredient("Olive Oil", 8, "g"),
        ],
        [
            "Cook brown rice according to package instructions.",
            "Stir-fry turkey strips in olive oil until browned, then add sliced bell pepper and carrot.",
            "Add soy sauce and cook until vegetables are tender, then serve over brown rice."
        ]
    ),

    # 5
    Recipe(
        "Overnight Oats with Apple",
        "5 min + overnight",
        290,
        [
            Ingredient("Rolled Oats", 50, "g"),
            Ingredient("Milk or Plant Milk", 150, "ml"),
            Ingredient("Apple", 80, "g"),
            Ingredient("Chia Seeds", 10, "g"),
            Ingredient("Cinnamon", 2, "g"),
        ],
        [
            "Combine oats, milk, chia seeds, and cinnamon in a jar and stir well.",
            "Refrigerate overnight.",
            "In the morning, top with chopped apple and serve."
        ]
    ),

    # 6
    Recipe(
        "Lentil and Veggie Bowl",
        "30 min",
        480,
        [
            Ingredient("Cooked Lentils", 150, "g"),
            Ingredient("Sweet Potato", 120, "g"),
            Ingredient("Spinach", 40, "g"),
            Ingredient("Cherry Tomato", 60, "g"),
            Ingredient("Olive Oil", 10, "g"),
            Ingredient("Balsamic Vinegar", 10, "g"),
        ],
        [
            "Roast cubed sweet potato with a little olive oil and salt at 200°C for 20 minutes.",
            "Warm the lentils in a pan and add spinach and halved cherry tomatoes.",
            "Serve lentils and vegetables in a bowl with roasted sweet potato and drizzle with balsamic vinegar."
        ]
    ),

    # 7
    Recipe(
        "Avocado Toast with Egg",
        "12 min",
        340,
        [
            Ingredient("Wholegrain Bread Slice", 2, "unit"),
            Ingredient("Avocado", 70, "g"),
            Ingredient("Egg", 1, "unit"),
            Ingredient("Cherry Tomato", 40, "g"),
            Ingredient("Lemon Juice", 5, "g"),
        ],
        [
            "Toast the bread slices until crisp.",
            "Mash the avocado with lemon juice, salt, and pepper, then spread over the toast.",
            "Top with a fried or poached egg and sliced cherry tomatoes."
        ]
    ),

    # 8
    Recipe(
        "Tofu and Vegetable Curry",
        "30 min",
        510,
        [
            Ingredient("Firm Tofu", 150, "g"),
            Ingredient("Coconut Milk (light)", 150, "ml"),
            Ingredient("Mixed Vegetables (e.g., bell pepper, zucchini, carrot)", 150, "g"),
            Ingredient("Curry Paste", 15, "g"),
            Ingredient("Brown Rice (dry)", 60, "g"),
        ],
        [
            "Cook brown rice according to package instructions.",
            "Sauté cubed tofu and chopped vegetables in a pan until lightly browned.",
            "Stir in curry paste and coconut milk and simmer until vegetables are tender, then serve over rice."
        ]
    ),

    # 9
    Recipe(
        "Berry Smoothie Bowl",
        "8 min",
        300,
        [
            Ingredient("Frozen Berries", 120, "g"),
            Ingredient("Banana", 70, "g"),
            Ingredient("Greek Yogurt", 120, "g"),
            Ingredient("Milk or Plant Milk", 80, "ml"),
            Ingredient("Granola", 20, "g"),
        ],
        [
            "Blend frozen berries, banana, yogurt, and milk until thick and smooth.",
            "Pour into a bowl.",
            "Top with granola and extra berries if desired."
        ]
    ),

    # 10
    Recipe(
        "Baked Cod with Vegetables",
        "28 min",
        430,
        [
            Ingredient("Cod Fillet", 170, "g"),
            Ingredient("Cherry Tomato", 80, "g"),
            Ingredient("Zucchini", 80, "g"),
            Ingredient("Olive Oil", 10, "g"),
            Ingredient("Lemon", 40, "g"),
        ],
        [
            "Place cod on a baking tray and surround with sliced zucchini and cherry tomatoes.",
            "Drizzle with olive oil, season with salt and pepper, and bake at 190°C for 18–20 minutes.",
            "Serve with lemon wedges."
        ]
    ),

    # 11
    Recipe(
        "Cottage Cheese & Fruit Bowl",
        "7 min",
        280,
        [
            Ingredient("Cottage Cheese", 150, "g"),
            Ingredient("Pear", 80, "g"),
            Ingredient("Walnuts", 15, "g"),
            Ingredient("Honey", 8, "g"),
            Ingredient("Cinnamon", 2, "g"),
        ],
        [
            "Place cottage cheese in a bowl.",
            "Top with sliced pear and chopped walnuts.",
            "Finish with honey and a sprinkle of cinnamon."
        ]
    ),

    # 12
    Recipe(
        "Wholegrain Pasta with Tomato & Spinach",
        "25 min",
        520,
        [
            Ingredient("Wholegrain Pasta (dry)", 70, "g"),
            Ingredient("Tomato Passata", 120, "g"),
            Ingredient("Spinach", 50, "g"),
            Ingredient("Olive Oil", 8, "g"),
            Ingredient("Parmesan Cheese", 15, "g"),
        ],
        [
            "Cook wholegrain pasta according to package instructions.",
            "Warm tomato passata in a pan with olive oil and wilt the spinach in the sauce.",
            "Toss cooked pasta in the sauce and serve with grated Parmesan."
        ]
    ),

    # 13
    Recipe(
        "Chia Pudding with Mango",
        "5 min + chilling",
        260,
        [
            Ingredient("Chia Seeds", 25, "g"),
            Ingredient("Milk or Plant Milk", 200, "ml"),
            Ingredient("Mango", 80, "g"),
            Ingredient("Vanilla Extract", 2, "g"),
        ],
        [
            "Mix chia seeds with milk and vanilla extract in a jar and stir well.",
            "Refrigerate for at least 2 hours or overnight, stirring once after 15 minutes.",
            "Top with diced mango before serving."
        ]
    ),

    # 14
    Recipe(
        "Stuffed Bell Peppers with Turkey",
        "35 min",
        500,
        [
            Ingredient("Bell Pepper", 2, "unit"),
            Ingredient("Ground Turkey", 150, "g"),
            Ingredient("Cooked Brown Rice", 70, "g"),
            Ingredient("Tomato Sauce", 80, "g"),
            Ingredient("Onion", 40, "g"),
        ],
        [
            "Cut the tops off the bell peppers and remove the seeds.",
            "Sauté chopped onion and ground turkey until cooked, then mix with cooked rice and tomato sauce.",
            "Stuff the peppers with the mixture and bake at 190°C for 20–25 minutes."
        ]
    ),
]



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


def create_recipe_widget(recipe: Recipe):
    ingredient_squares = []
    for ing in recipe.ingredients:
        ingredient_squares.append(
            html.Div([
                html.Div(ing.name, style={"fontWeight": "bold"}),
                html.Div(f"{ing.amount} {ing.amount_type}")
            ], style={
                "backgroundColor": "#d0e1f9",
                "borderRadius": "6px",
                "textAlign": "center",
                "padding": "5px",
                "margin": "5px",
                "width": "90px",
                "display": "inline-block",
                "verticalAlign": "top",
                "fontSize": "14px"
            })
        )
    # Create expandable steps section with a collapsible toggle
    steps_id = f"steps-{recipe.name.replace(' ', '-')}"
    rate_id = f"rate-{recipe.name.replace(' ', '-')}"

    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div(recipe.name, style={"width": "60%", "fontWeight": "bold", "fontSize": "18px"}),
                html.Div(recipe.prep_time, style={"width": "20%", "textAlign": "center"}),
                html.Div(f"{recipe.calories} kcal", style={"width": "20%", "textAlign": "center"}),
            ], style={"display": "flex", "marginBottom": "10px"}),
            html.Div(ingredient_squares, style={"display": "flex", "flexWrap": "wrap", "marginBottom": "10px"}),
            # Collapsible steps
            dbc.Button("Show/Hide Steps", id=f"toggle-{steps_id}", color="primary", size="sm", n_clicks=0, style={"marginBottom": "5px"}),
            dbc.Collapse(
                html.Ol([html.Li(step) for step in recipe.steps]),
                id=steps_id,
                is_open=False
            ),
            # Rate this recipe stars
            html.Div([
                html.Span("Rate this recipe: ", style={"marginRight": "10px"}),
                *[html.Span("☆", id=f"{rate_id}-star-{i}", style={"cursor": "pointer", "fontSize": "20px", "color": "#ccc"}) for i in range(1,6)]
            ], style={"marginTop": "10px"}),
        ]),
    ], style={"borderRadius": "15px", "marginBottom": "20px", "padding": "10px"})


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
        dcc.Slider(
          id="body_weight",
          min=0, max=200, step=1,
            value=69,
            marks={i: str(i) for i in range(0, 201, 20)},
            tooltip={"placement": "bottom"},
            updatemode='drag',
        ),

        html.Label("Weekly food budget (CHF)"),
        html.Div(
          dcc.Slider(
              id='budget',
              min=0, max=200, step=1,
              value=80,
              marks={i: str(i) for i in range(0, 201, 20)},
              tooltip={"placement": "bottom"},
              updatemode='drag',
          ),
          id="budget_slider_container"
        ),
        dcc.Checklist(
            options=[{"label": "Ignore for now", "value": "ignore"}],
            value=[],
            id="budget_ignore",
            style={"marginBottom": "20px"}
        ),

        html.Label("Target (Calories/day)"),
        html.Div(
          dcc.Slider(
              id='dayly_calories',
              min=0, max=5000, step=5,
              value=2400,
              marks={i: str(i) for i in range(0, 5001, 500)},
              tooltip={"placement": "bottom"},
              updatemode='drag',
          ),
          id="calories_slider_container"

        ),
        dcc.Checklist(
            options=[{"label": "Compute for me", "value": "ignore"}],
            value=[],
            id="calories_ignore",
            style={"marginBottom": "20px"}
        ),
        
        html.Label("Activity level"),
        dcc.Dropdown(["Sedentary","Lightly active","Moderately active","Very active","Extra active"],
                     "Moderately active", id="activity", style={"marginBottom": "20px"}),

        html.Label("Diet type"),
        dcc.Dropdown(["Omnivore","Vegetarian","Keto","Vegan","Pescatarian","Gluten free","Other"],
                     "Omnivore", id="diet_type", style={"marginBottom": "20px"}),

        html.Label("Location"),
        dcc.Input(id="location", placeholder="Lausanne", style={"width": "100%", "marginBottom": "20px"}),

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
        dcc.Textarea(id="restrictions", placeholder="egg, peanut", style={"width": "100%", "height": "80px", "marginBottom": "20px"}),

        html.Button("Generate My Weekly Plan 🧑‍🍳", id="generate", n_clicks=0, style={"backgroundColor": "#28a745", "color": "white", "border": "none", "padding": "10px 15px", "borderRadius": "5px"}),
        html.Button("Test Recipes", id="test_recipes", n_clicks=0, style={
            "backgroundColor": "#007bff",
            "color": "white",
            "border": "none",
            "padding": "10px 15px",
            "borderRadius": "5px",
            "marginLeft": "10px"
        }),
    ], style={"maxWidth": "600px", "margin": "auto"}),
    html.Div(id="test_recipes_output", style={"maxWidth": "600px", "margin": "40px auto"}),

    html.Div(id="plan_output", style={"marginTop": "40px", "maxWidth": "600px", "margin": "auto"})
])


# (Keep your helper functions numeric_scale, rescale_day, normalize_mealplan unchanged here)

# -------------------- CALLBACK --------------------
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
# Callback to render test recipes with alternating day/meal headers and the recipe widgets
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