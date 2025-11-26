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
        html.Label("Weight (kg)", style={"marginBottom": "5px", "display": "block"}),
        dcc.Input(
            id="body_weight",
            type="number",
            min=0,
            max=300,
            step=0.5,
            value=69,
            style={"width": "100%", "marginBottom": "15px"}
        ),

        html.Label("Weekly food budget (CHF)", style={"marginBottom": "5px", "display": "block"}),
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
            style={"marginBottom": "15px"}
        ),

        html.Label("Target (Calories/day)", style={"marginBottom": "5px", "display": "block"}),
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
            style={"marginBottom": "15px"}
        ),
        
        html.Label("Activity (hours/week)", style={"marginBottom": "5px", "display": "block"}),
        dcc.Input(
            id="activity_hours",
            type="number",
            min=0,
            max=40,
            step=0.5,
            value=5,
            style={"width": "100%", "marginBottom": "15px"}
        ),

        html.Label("Diet type", style={"marginBottom": "5px", "display": "block"}),
        dcc.Dropdown(["Omnivore","Vegetarian","Keto","Vegan","Pescatarian","Gluten free","Other"],
                     "Omnivore", id="diet_type", style={"marginBottom": "15px"}),

        html.Label("Location", style={"marginBottom": "5px", "display": "block"}),
        dcc.Input(id="location", placeholder="Lausanne", style={"width": "100%", "marginBottom": "15px"}),

        html.Label("Your goals", style={"marginBottom": "5px", "display": "block"}),
        dcc.Checklist(
            id="goals",
            options=[{"label": g, "value": g} for g in
                     ["Lose weight","Build muscle","Maintain muscle mass",
                      "Reduce meat consumption","Discover new recipes","Reduce processed food consumption"]],
            value=["Lose weight"],
            inputStyle={"marginRight": "8px"},
            style={"marginBottom": "15px"}
        ),

        html.Label("Any dietary restrictions or allergies?", style={"marginBottom": "5px", "display": "block"}),
        dcc.Textarea(id="restrictions", placeholder="egg, peanut", style={"width": "100%", "height": "60px", "marginBottom": "15px"}),

        html.Label("Ingredients to avoid", style={"marginBottom": "5px", "display": "block"}),
        dcc.Textarea(id="avoid_ingredients", placeholder="e.g., mushrooms, olives, cilantro", style={"width": "100%", "height": "50px", "marginBottom": "15px"}),

        html.Label("Foods you're craving this week", style={"marginBottom": "5px", "display": "block"}),
        dcc.Textarea(id="cravings", placeholder="e.g., pasta, salmon, chocolate", style={"width": "100%", "height": "50px", "marginBottom": "15px"}),

        html.Label("Meal complexity / cooking time", style={"marginBottom": "5px", "display": "block"}),
        dcc.Dropdown(
            id="complexity",
            options=[
                {"label": "Quick (<20 min)", "value": "quick"},
                {"label": "Medium (20-40 min)", "value": "medium"},
                {"label": "Elaborate (>40 min)", "value": "elaborate"},
                {"label": "Mixed (variety)", "value": "mixed"}
            ],
            value="medium",
            style={"marginBottom": "15px"}
        ),

        html.Label("Preferred cuisines", style={"marginBottom": "5px", "display": "block"}),
        dcc.Checklist(
            id="cuisines",
            options=[
                {"label": "Italian", "value": "Italian"},
                {"label": "French", "value": "French"},
                {"label": "Asian (Chinese, Japanese, Thai)", "value": "Asian"},
                {"label": "Mediterranean", "value": "Mediterranean"},
                {"label": "Mexican", "value": "Mexican"},
                {"label": "Indian", "value": "Indian"},
                {"label": "Middle Eastern", "value": "Middle Eastern"},
                {"label": "American", "value": "American"},
                {"label": "Latin American", "value": "Latin American"},
                {"label": "African", "value": "African"}
            ],
            value=[],
            inputStyle={"marginRight": "8px"},
            style={"marginBottom": "15px"}
        ),

        html.Label("Portions per meal (0 = skip, 1 = solo, 2+ = with others)", style={"marginBottom": "10px", "display": "block", "fontWeight": "bold"}),
        html.Div([
            # Create a compact table-like layout for portions
            html.Div([
                html.Div("", style={"width": "80px", "display": "inline-block", "fontWeight": "bold"}),
                html.Div("Mon", style={"width": "60px", "display": "inline-block", "textAlign": "center", "fontWeight": "bold", "fontSize": "12px"}),
                html.Div("Tue", style={"width": "60px", "display": "inline-block", "textAlign": "center", "fontWeight": "bold", "fontSize": "12px"}),
                html.Div("Wed", style={"width": "60px", "display": "inline-block", "textAlign": "center", "fontWeight": "bold", "fontSize": "12px"}),
                html.Div("Thu", style={"width": "60px", "display": "inline-block", "textAlign": "center", "fontWeight": "bold", "fontSize": "12px"}),
                html.Div("Fri", style={"width": "60px", "display": "inline-block", "textAlign": "center", "fontWeight": "bold", "fontSize": "12px"}),
                html.Div("Sat", style={"width": "60px", "display": "inline-block", "textAlign": "center", "fontWeight": "bold", "fontSize": "12px"}),
                html.Div("Sun", style={"width": "60px", "display": "inline-block", "textAlign": "center", "fontWeight": "bold", "fontSize": "12px"}),
            ], style={"marginBottom": "5px"}),
            
            # Breakfast row
            html.Div([
                html.Div("Breakfast", style={"width": "80px", "display": "inline-block", "fontWeight": "500", "fontSize": "13px"}),
            ] + [
                dcc.Input(
                    id={"type": "portion", "day": day, "meal": "breakfast"},
                    type="number",
                    min=0,
                    max=10,
                    value=1,
                    style={"width": "50px", "marginRight": "10px", "padding": "3px", "textAlign": "center"}
                )
                for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            ], style={"marginBottom": "5px"}),
            
            # Lunch row
            html.Div([
                html.Div("Lunch", style={"width": "80px", "display": "inline-block", "fontWeight": "500", "fontSize": "13px"}),
            ] + [
                dcc.Input(
                    id={"type": "portion", "day": day, "meal": "lunch"},
                    type="number",
                    min=0,
                    max=10,
                    value=1,
                    style={"width": "50px", "marginRight": "10px", "padding": "3px", "textAlign": "center"}
                )
                for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            ], style={"marginBottom": "5px"}),
            
            # Dinner row
            html.Div([
                html.Div("Dinner", style={"width": "80px", "display": "inline-block", "fontWeight": "500", "fontSize": "13px"}),
            ] + [
                dcc.Input(
                    id={"type": "portion", "day": day, "meal": "dinner"},
                    type="number",
                    min=0,
                    max=10,
                    value=1,
                    style={"width": "50px", "marginRight": "10px", "padding": "3px", "textAlign": "center"}
                )
                for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            ], style={"marginBottom": "5px"}),
        ], style={"marginBottom": "15px", "padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "overflowX": "auto"}),

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
    
    dcc.Loading(
        id="loading-plan",
        type="default",
        children=html.Div(id="plan_output", style={"marginTop": "40px", "maxWidth": "600px", "margin": "auto"}),
        style={"marginTop": "40px"}
    ),
    
    # Store for plan data (for PDF export)
    dcc.Store(id="plan-data-store"),
    dcc.Download(id="download-pdf"),
    
    dcc.Loading(
        id="loading-test-recipes",
        type="default",
        children=html.Div(id="test_recipes_output", style={"maxWidth": "600px", "margin": "40px auto"}),
    ),
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
