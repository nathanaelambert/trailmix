from recipes import Recipe
from dash import html, dcc
import dash_bootstrap_components as dbc
import re


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
                html.Div(f"{ing.amount} {ing.amount_type}"),
                dbc.Button("Order", id=f"order_{ing.name}", color="secondary", size="sm", n_clicks=0, style={"marginBottom": "5px", "float": "right"}),

            ], style={
                "backgroundColor": "white",
                "borderRadius": "6px",
                "border": "1px solid grey",
                "textAlign": "left",
                "padding": "10px",
                "margin": "5px",
                "width": "260px",
                "display": "inline-block",
                "verticalAlign": "top",
                "fontSize": "14px",
                
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
            dbc.Button("Show/Hide Steps", id=f"toggle-{steps_id}", color="secondary", size="sm", n_clicks=0, style={"marginBottom": "5px"}),
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
    ], style={"borderRadius": "15px", "border": "1px solid grey", "marginBottom": "20px", "padding": "10px"})

