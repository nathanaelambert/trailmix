from dash import html, dcc
import dash_bootstrap_components as dbc
from helpers import create_recipe_widget

layout = html.Div([
    # Premium button in top right
    html.Div([
        dbc.Button(
            "⭐ Go Premium",
            id="open-premium-modal",
            color="warning",
            n_clicks=0,
            style={
                "position": "absolute",
                "top": "20px",
                "right": "20px",
                "zIndex": "1000",
                "fontWeight": "bold"
            }
        )
    ], style={"position": "relative"}),
    
    html.H1([
        "🥗 CULIN",
        html.B("AI"),
        "RE"
    ], style={"textAlign": "center", "marginTop": "20px"}),

    html.P("Your AI meal planner – plan smart, eat better", style={"textAlign": "center", "color": "gray", "marginBottom": "20px"}),

    # Tabs for better organization
    dbc.Tabs([
        dbc.Tab(label="👤 User Info", tab_id="user-info"),
        dbc.Tab(label="🍲 Recipes", tab_id="recipes"),
        dbc.Tab(label="🛒 Grocery List", tab_id="grocery-list"),
    ], id="main-tabs", active_tab="user-info", style={"marginBottom": "20px"}),
    
    html.Div(id="tab-content"),
    
    # User Info Tab Content (initially visible)
    html.Div(id="user-info-content", children=[
        html.Div([
            html.H3("Your profile"),
            html.P("Save your info once to reuse it next time you visit.", style={"color": "#6c757d"}),
            html.Label("Email"),
            dcc.Input(id="user_email", type="email", placeholder="you@example.com", style={"width": "100%", "marginBottom": "10px"}),
            html.Label("Name"),
            dcc.Input(id="user_name", type="text", placeholder="Sam C.", style={"width": "100%", "marginBottom": "10px"}),
            html.Div([
                html.P("If you already have a profile: ", style={"display": "inline", "color": "#6c757d", "marginRight": "5px"}),
                html.Button("Load saved info", id="load_profile", n_clicks=0, style={
                    "backgroundColor": "#6c757d", "color": "white", "border": "none", "padding": "8px 12px",
                    "borderRadius": "5px"
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
        
        html.Label("Physical activity (hours/week)", style={"marginBottom": "5px", "display": "block"}),
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
                     ["Lose weight","Build muscle","Maintain weight",
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

        html.Button("Save profile", id="save_profile", n_clicks=0, style={
            "backgroundColor": "#17a2b8", "color": "white", "border": "none", "padding": "8px 12px", "borderRadius": "5px", "marginBottom": "10px", "width": "100%"
        }),
        html.Button("🗑️ Clear my data", id="clear_data", n_clicks=0, style={
            "backgroundColor": "#dc3545", "color": "white", "border": "none", "padding": "8px 12px", "borderRadius": "5px", "marginBottom": "20px", "width": "100%"
        }),
        html.Div(id="clear_data_message", style={"marginBottom": "20px"}),
        ], style={"maxWidth": "600px", "margin": "auto"}),
    ]),
    
    # Recipes Tab Content
    html.Div(id="recipes-content", style={"display": "none"}, children=[
        html.Div(id="profile-summary-recipes", style={"maxWidth": "95%", "margin": "20px auto", "padding": "0 20px"}),
        html.Div(id="profile-info-message-recipes", style={"maxWidth": "95%", "margin": "0 auto 20px auto", "padding": "0 20px"}),
        html.Div([
        html.Button("Generate My Weekly Plan 🧑‍🍳", id="generate", n_clicks=0, style={"backgroundColor": "#28a745", "color": "white", "border": "none", "padding": "10px 15px", "borderRadius": "5px"}),
        html.Button(
            "Generate with HuggingFace 🤗",
            id="generate_hf",
            n_clicks=0,
            style={
                "backgroundColor": "#6f42c1",
                "color": "white",
                "border": "none",
                "padding": "10px 15px",
                "borderRadius": "5px",
                "marginLeft": "10px"
            }
        ),
        ], style={"maxWidth": "95%", "margin": "20px auto", "padding": "0 20px", "textAlign": "center"}),
        html.P(
            "⚠️ AI-generated suggestions are not medical advice.",
            style={
                "textAlign": "center",
                "color": "#6c757d",
                "fontSize": "12px",
                "fontStyle": "italic",
                "marginTop": "10px",
                "marginBottom": "20px",
                "padding": "0 20px"
            }
        ),
        dcc.Loading(
            id="loading-plan",
            type="default",
            children=html.Div(id="plan_output", style={"marginTop": "40px", "maxWidth": "95%", "margin": "auto", "padding": "0 20px"}),
            style={"marginTop": "40px"}
        ),
    ]),
    
    # Grocery List Tab Content
    html.Div(id="grocery-list-content", style={"display": "none"}, children=[
        html.Div(id="grocery-list-container", style={"maxWidth": "95%", "margin": "40px auto", "padding": "0 20px"}),
    ]),
    
    # Store for plan data (for PDF export) and grocery list
    dcc.Store(id="plan-data-store"),
    dcc.Store(id="grocery-list-store"),
    dcc.Download(id="download-pdf"),
    
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
    dcc.Store(id="premium_status", data={"is_premium": False, "email": None}),
    
    # Premium Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("⭐ Unlock Premium Access")),
        dbc.ModalBody([
            html.P("EPFL students get immediate access to premium. Verify your @epfl.ch email to unlock.", style={"fontSize": "16px", "marginBottom": "15px"}),
            html.H5("Student verification", style={"marginTop": "10px", "marginBottom": "10px", "color": "#17a2b8"}),
            dbc.Input(
                id="premium-email-input",
                type="email",
                placeholder="firstname.lastname@epfl.ch",
                debounce=True,
                className="mb-2"
            ),
            dbc.Button("Verify student email", id="verify-premium-email", color="primary", n_clicks=0, className="mb-2"),
            dbc.Alert(id="premium-email-status", is_open=False, color="info", className="mt-1"),
            html.P("We accept EPFL student emails ending with @epfl.ch.", style={"fontSize": "12px", "color": "#6c757d", "marginBottom": "0"}),
            html.Hr(),
            html.H5("What's included:", style={"marginTop": "10px", "marginBottom": "10px", "color": "#28a745"}),
            html.Ul([
                html.Li("💾 Save your favorite recipes"),
                html.Li("🛒 Order groceries directly from your list"),
                html.Li("💬 Chat with CULINAIRE - AI-powered meal assistant"),
                html.Li("📊 Advanced nutrition tracking"),
                html.Li("🎯 Personalized meal recommendations"),
                html.Li("📱 Mobile app access"),
            ], style={"fontSize": "14px", "lineHeight": "2"}),
            html.P([
                "Stay tuned for more premium upgrades.",
            ], style={"marginTop": "20px", "color": "#6c757d", "fontStyle": "italic"})
        ]),
        dbc.ModalFooter([
            dbc.Button("Close", id="close-premium-modal", className="ms-auto", n_clicks=0)
        ])
    ], id="premium-modal", is_open=False),
])
