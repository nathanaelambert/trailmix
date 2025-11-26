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
        html.H3("Your profile"),
        html.P("Save your info once to reuse it next time you visit.", style={"color": "#6c757d"}),
        html.Label("Email"),
        dcc.Input(id="user_email", type="email", placeholder="you@example.com", style={"width": "100%", "marginBottom": "10px"}),
        html.Label("Name"),
        dcc.Input(id="user_name", type="text", placeholder="Sam C.", style={"width": "100%", "marginBottom": "10px"}),
        html.Label("Notes or preferences"),
        dcc.Textarea(id="user_notes", placeholder="E.g., lactose intolerant, prefers quick breakfasts", style={"width": "100%", "height": "70px", "marginBottom": "10px"}),
        html.Div([
            html.Button("Save profile", id="save_profile", n_clicks=0, style={
                "backgroundColor": "#17a2b8", "color": "white", "border": "none", "padding": "8px 12px", "borderRadius": "5px"
            }),
            html.Button("Load saved info", id="load_profile", n_clicks=0, style={
                "backgroundColor": "#6c757d", "color": "white", "border": "none", "padding": "8px 12px",
                "borderRadius": "5px", "marginLeft": "10px"
            })
        ], style={"marginBottom": "10px"}),
        html.Div(id="profile_message", style={"marginTop": "5px", "color": "#0d6efd"}),
        html.Div(id="profile_dashboard", style={"marginTop": "10px"}),
    ], style={"maxWidth": "600px", "margin": "auto", "marginBottom": "30px", "padding": "15px", "border": "1px solid #dee2e6", "borderRadius": "8px", "backgroundColor": "#f8f9fa"}),

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
        html.Button("Generate with HuggingFace 🤗", id="generate_hf", n_clicks=0, style={
            "backgroundColor": "#6f42c1",
            "color": "white",
            "border": "none",
            "padding": "10px 15px",
            "borderRadius": "5px",
            "marginLeft": "10px"
        }),
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

    html.Div(id="plan_output", style={"marginTop": "40px", "maxWidth": "600px", "margin": "auto"}),
    html.Hr(),
    html.Div([
        html.H3("Chat with CULINAIRE"),
        html.P("Ask about meal ideas, grocery tips, or nutrition. The assistant can search the web and cite sources.", style={"color": "#6c757d"}),
        dcc.Textarea(
            id="chat_input",
            placeholder="Ask anything about meals, groceries, nutrition...",
            style={"width": "100%", "height": "80px", "marginBottom": "10px"}
        ),
        html.Button("Send", id="send_chat", n_clicks=0, style={
            "backgroundColor": "#fd7e14",
            "color": "white",
            "border": "none",
            "padding": "8px 12px",
            "borderRadius": "5px"
        }),
        html.Div(id="chat_output", style={"marginTop": "15px", "maxWidth": "800px", "margin": "20px auto"}),
    ], style={"maxWidth": "800px", "margin": "auto", "padding": "15px", "border": "1px solid #dee2e6", "borderRadius": "8px", "backgroundColor": "#f8f9fa"}),

    dcc.Store(id="latest_plan_data"),
    dcc.Store(id="chat_history"),
])
