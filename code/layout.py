from dash import html, dcc
import dash_bootstrap_components as dbc
from helpers import create_recipe_widget

layout = html.Div([
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
        dcc.Dropdown(
            ["Sedentary","Lightly active","Moderately active","Very active","Extra active"],
            "Moderately active",
            id="activity",
            style={"marginBottom": "20px"}
        ),

        html.Label("Diet type"),
        dcc.Dropdown(
            ["Omnivore","Vegetarian","Keto","Vegan","Pescatarian","Gluten free","Other"],
            "Omnivore",
            id="diet_type",
            style={"marginBottom": "20px"}
        ),

        html.Label("Location"),
        dcc.Input(id="location", placeholder="Lausanne", style={"width": "100%", "marginBottom": "20px"}),

        html.Label("Your goals (multi-select)"),
        dcc.Dropdown(
            id="goals",
            multi=True,
            options=[{"label": g, "value": g} for g in
                     ["Lose weight","Build muscle","Maintain muscle mass",
                      "Reduce meat consumption","Discover new recipes","Reduce processed food consumption"]],
            placeholder="Your goals...",
            style={"marginBottom": "20px"}
        ),

        html.Label("Any dietary restrictions or allergies?"),
        dcc.Textarea(
            id="restrictions",
            placeholder="egg, peanut",
            style={"width": "100%", "height": "80px", "marginBottom": "20px"}
        ),

        html.Button(
            "Generate My Weekly Plan 🧑‍🍳",
            id="generate",
            n_clicks=0,
            style={
                "backgroundColor": "#28a745",
                "color": "white",
                "border": "none",
                "padding": "10px 15px",
                "borderRadius": "5px"
            }
        ),
        html.Button(
            "Test Recipes",
            id="test_recipes",
            n_clicks=0,
            style={
                "backgroundColor": "#007bff",
                "color": "white",
                "border": "none",
                "padding": "10px 15px",
                "borderRadius": "5px",
                "marginLeft": "10px"
            }
        ),
    ], style={"maxWidth": "600px", "margin": "auto"}),

    html.Div(
        id="test_recipes_output",
        style={"maxWidth": "600px", "margin": "40px auto"}
    ),

    # 🔥 Wrap the plan output in a Loading spinner
    dcc.Loading(
        id="plan_loading",
        type="default",
        children=html.Div(
            id="plan_output",
            style={"marginTop": "40px", "maxWidth": "600px", "margin": "auto"}
        ),
    ),
])
