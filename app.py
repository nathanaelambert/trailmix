from dash import Dash, Input, Output, State, html, dcc, callback_context, no_update, ALL, MATCH
from flask import send_file
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import os
import sqlite3
import json
import re
from dotenv import load_dotenv
from datetime import datetime
import requests
from duckduckgo_search import DDGS
import subprocess
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import tempfile

# Load environment variables FIRST before anything else
load_dotenv()

from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
server = app.server  
app.title = "CULINAIRE 🥗"

from layout import layout
app.layout = layout

ACTIVITY_OPTIONS = ["Sedentary","Lightly active","Moderately active","Very active","Extra active"]
DIET_OPTIONS = ["Omnivore","Vegetarian","Keto","Vegan","Pescatarian","Gluten free","Other"]
GOALS_OPTIONS = [
    "Lose weight","Build muscle","Maintain weight",
    "Reduce meat consumption","Discover new recipes","Reduce processed food consumption",
]

# -------------------- USER DATA STORAGE --------------------

DB_PATH = os.getenv("USER_DB_PATH", "user_profiles.db")


def init_db():
    """Ensure the local SQLite database and table exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            email TEXT PRIMARY KEY,
            name TEXT,
            weight REAL,
            activity TEXT,
            goals TEXT,
            budget REAL,
            calories REAL,
            restrictions TEXT,
            diet TEXT,
            location TEXT,
            avoid_ingredients TEXT,
            cravings TEXT,
            complexity TEXT,
            cuisines TEXT,
            last_plan TEXT,
            updated_at TEXT
        )
        """
    )
    
    # Add new columns if they don't exist (for existing databases)
    try:
        conn.execute("ALTER TABLE user_profiles ADD COLUMN avoid_ingredients TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        conn.execute("ALTER TABLE user_profiles ADD COLUMN cravings TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        conn.execute("ALTER TABLE user_profiles ADD COLUMN complexity TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        conn.execute("ALTER TABLE user_profiles ADD COLUMN cuisines TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        conn.execute("ALTER TABLE user_profiles ADD COLUMN portions_json TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.commit()
    conn.close()


def serialize_goals(goals):
    if not goals:
        return "[]"
    try:
        return json.dumps(goals)
    except TypeError:
        return json.dumps([str(g) for g in goals])


def parse_goals(goals_text):
    if not goals_text:
        return []
    try:
        parsed = json.loads(goals_text)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def save_user_profile(email, name, weight, activity_hours, goals, budget, calories, restrictions, diet, location, avoid_ingredients, cravings, complexity, cuisines, last_plan, portions=None):
    """Insert or update a user profile along with the latest plan snapshot."""
    if not email:
        return
    init_db()
    timestamp = datetime.utcnow().isoformat()
    
    # Serialize portions dict to JSON
    portions_json = json.dumps(portions) if portions else None
    
    payload = (
        email.strip().lower(),
        name.strip() if name else None,
        safe_float(weight),
        activity_hours,
        serialize_goals(goals),
        safe_float(budget),
        safe_float(calories),
        restrictions,
        diet,
        location,
        avoid_ingredients,
        cravings,
        complexity,
        serialize_goals(cuisines),  # Reuse serialize_goals for cuisines list
        portions_json,
        last_plan,
        timestamp,
    )

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO user_profiles
        (email, name, weight, activity, goals, budget, calories, restrictions, diet, location, avoid_ingredients, cravings, complexity, cuisines, portions_json, last_plan, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            name=excluded.name,
            weight=excluded.weight,
            activity=excluded.activity,
            goals=excluded.goals,
            budget=excluded.budget,
            calories=excluded.calories,
            restrictions=excluded.restrictions,
            diet=excluded.diet,
            location=excluded.location,
            avoid_ingredients=excluded.avoid_ingredients,
            cravings=excluded.cravings,
            complexity=excluded.complexity,
            cuisines=excluded.cuisines,
            portions_json=excluded.portions_json,
            last_plan=excluded.last_plan,
            updated_at=excluded.updated_at
        """,
        payload,
    )
    conn.commit()
    conn.close()


def get_user_profile(email):
    if not email:
        return None
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM user_profiles WHERE email = ?", (email.strip().lower(),)).fetchone()
    conn.close()
    if not row:
        return None
    profile = dict(row)
    profile["goals"] = parse_goals(profile.get("goals"))
    profile["cuisines"] = parse_goals(profile.get("cuisines"))  # Parse cuisines list
    
    # Parse portions_json
    portions_json = profile.get("portions_json")
    if portions_json:
        try:
            profile["portions"] = json.loads(portions_json)
        except:
            profile["portions"] = None
    else:
        profile["portions"] = None
    
    return profile


def clear_user_data(email):
    """Delete all user data from the database (GDPR compliance)."""
    if not email:
        return False
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM user_profiles WHERE email = ?", (email.strip().lower(),))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error clearing user data: {e}")
        return False


def render_profile_dashboard(profile):
    """Create a simple dashboard view from a stored profile."""
    if not profile:
        return html.Div("No saved data yet. Add your email and click Save profile.", style={"color": "#6c757d"})

    rows = []
    items = [
        ("Name", profile.get("name") or "—"),
        ("Email", profile.get("email") or "—"),
        ("Weight", f"{profile.get('weight')} kg" if profile.get("weight") else "—"),
        ("Activity", f"{profile.get('activity')} hrs/week" if profile.get("activity") else "—"),
        ("Diet", profile.get("diet") or "—"),
        ("Goals", ", ".join(profile.get("goals") or []) or "—"),
        ("Budget", f"{profile.get('budget')} CHF" if profile.get("budget") is not None else "—"),
        ("Calories", f"{profile.get('calories')} kcal" if profile.get("calories") is not None else "—"),
        ("Restrictions", profile.get("restrictions") or "—"),
        ("Location", profile.get("location") or "—"),
        ("Avoid Ingredients", profile.get("avoid_ingredients") or "—"),
        ("Cravings", profile.get("cravings") or "—"),
        ("Complexity", profile.get("complexity") or "—"),
        ("Cuisines", ", ".join(profile.get("cuisines") or []) or "—"),
        ("Portions", "Custom per-meal settings saved" if profile.get("portions") else "Default (1 per meal)"),
        ("Updated", profile.get("updated_at") or "—"),
    ]
    for label, value in items:
        rows.append(
            html.Div(
                [
                    html.Div(label, style={"fontWeight": "bold", "width": "30%"}),
                    html.Div(value, style={"width": "70%"}),
                ],
                style={"display": "flex", "marginBottom": "6px"},
            )
        )

    plan_preview = None
    last_plan = profile.get("last_plan")
    if last_plan:
        plan_preview = html.Details(
            [
                html.Summary("Last saved plan JSON"),
                html.Pre(last_plan[:1200], style={"whiteSpace": "pre-wrap", "background": "#f8f9fa", "padding": "10px"}),
            ],
            open=False,
        )

    return html.Div(
        [
            html.H4("Profile Dashboard"),
            html.Div(rows, style={"padding": "10px", "border": "1px solid #dee2e6", "borderRadius": "8px", "background": "#fff"}),
            plan_preview if plan_preview else html.Div("No plan saved yet.", style={"marginTop": "10px"}),
        ],
        style={"marginTop": "10px"},
    )

# Initialize storage on startup
init_db()

# -------------------- GOOGLE ANALYTICS --------------------
# Temporarily disabled to test if it's causing issues
# GA_TAG = 'G-3R4901JN3H'

# app.index_string = """
# <!DOCTYPE html>
# <html>
#   <head>
#     <script async src="https://www.googletagmanager.com/gtag/js?id=G-3R4901JN3H"></script>
#     <script>
#       window.dataLayer = window.dataLayer || [];
#       function gtag(){dataLayer.push(arguments);}
#       gtag('js', new Date());
#       gtag('config', 'G-3R4901JN3H');
#
#       document.addEventListener('click', function(event) {
#         var elem = event.target;
#         var elementInfo = elem.tagName;
#         if (elem.id) elementInfo += ' #' + elem.id;
#         if (elem.className) elementInfo += ' .' + elem.className.toString().replace(/\s+/g, '.');
#         var timestamp = new Date().toISOString();
#
#         gtag('event', 'user_click', {
#             'event_category': 'User Interaction',
#             'event_label': elementInfo,
#             'event_timestamp': timestamp
#         });
#       });
#
#     </script>
#     {%metas%}
#     <title>{%title%}</title>
#     {%favicon%}
#     {%css%}
#   </head>
#   <body>
#     {%app_entry%}
#     <footer>
#       {%config%}
#       {%scripts%}
#       {%renderer%}
#     </footer>
#   </body>
# </html>
# """
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

# Determine base URL based on which key is set
if os.getenv("OPENROUTER_API_KEY"):
    # Using OpenRouter
    base_url = os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
else:
    # Using OpenAI directly
    base_url = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    default_headers = {}  # OpenAI doesn't need custom headers

MIGROS_API_TOKEN = (
    os.getenv("MIGROS_API_TOKEN")
    or os.getenv("MIGROS_LESHOP_TOKEN")
    or os.getenv("MIGROS_API_KEY")
)
MIGROS_DEFAULT_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "User-Agent": os.getenv(
        "MIGROS_API_WRAPPER_USERAGENT",
        "Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0",
    ),
}

MIGROS_HELPER_PATH = os.path.join(os.path.dirname(__file__), "migros_price_helper.js")

def _get_node_bin():
    """Pick a Node binary, preferring env override or newest nvm install."""
    env_bin = os.getenv("MIGROS_NODE_BIN")
    if env_bin and os.path.exists(env_bin):
        return env_bin
    nvm_dir = os.path.expanduser("~/.nvm/versions/node")
    if os.path.isdir(nvm_dir):
        try:
            versions = sorted(os.listdir(nvm_dir))
            if versions:
                return os.path.join(nvm_dir, versions[-1], "bin", "node")
        except Exception:
            pass
    return "node"

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


def parse_text_meal_plan(text: str, base_calories: dict) -> dict:
    """
    Parse a simple text format meal plan into the JSON structure expected by the app.
    
    Expected format:
    DAY: Monday
    BREAKFAST: Meal Name
      Calories: 600
      Ingredients: Ingredient1 quantity1, Ingredient2 quantity2
      Recipe: 1. Step one. 2. Step two. 3. Step three.
    """
    import sys
    print(f"🔍 DEBUG parse_text_meal_plan: Input text length: {len(text)} chars", file=sys.stderr, flush=True)
    print(f"🔍 DEBUG parse_text_meal_plan: First 500 chars: {text[:500]}", file=sys.stderr, flush=True)
    
    plan = {
        "meal_plan": [],
        "grocery_list": [],
        "summary": {
            "average_daily_calories": 0,
            "estimated_weekly_cost": "CHF 0",
            "nutrition_focus": "balanced"
        }
    }
    
    current_day = None
    current_meal_type = None
    current_meal = {}
    
    lines = text.split('\n')
    print(f"🔍 DEBUG parse_text_meal_plan: Split into {len(lines)} lines", file=sys.stderr, flush=True)
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for day header - be flexible with format
        if line.upper().startswith('DAY:') or line.upper().startswith('DAY ') or (line.upper().startswith('MONDAY') or line.upper().startswith('TUESDAY') or line.upper().startswith('WEDNESDAY') or line.upper().startswith('THURSDAY') or line.upper().startswith('FRIDAY') or line.upper().startswith('SATURDAY') or line.upper().startswith('SUNDAY')):
            # If it's just a day name without "DAY:", extract it
            if not line.upper().startswith('DAY'):
                # It's just the day name
                day_name = line.strip()
            else:
                day_name = line.split(':', 1)[1].strip() if ':' in line else line.replace('DAY', '').strip()
            
            # Save previous meal if exists
            if current_day and current_meal_type and current_meal:
                day_entry = next((d for d in plan["meal_plan"] if d.get("day") == current_day), None)
                if day_entry:
                    day_entry["meals"][current_meal_type] = current_meal
                    current_meal = {}
            
            # Start new day
            current_day = day_name
            current_meal_type = None
            current_meal = {}
            
            # Add day entry if not exists
            if current_day not in [d.get("day") for d in plan["meal_plan"]]:
                plan["meal_plan"].append({
                    "day": current_day,
                    "meals": {}
                })
            continue
        
        # Check for meal type header - be flexible
        elif line.upper().startswith(('BREAKFAST', 'LUNCH', 'DINNER')):
            # If we don't have a current day yet, create one (model might skip DAY: header)
            if not current_day:
                # Try to infer day from context or use a default
                if len(plan["meal_plan"]) == 0:
                    current_day = "Monday"
                else:
                    # Use the last day or increment
                    days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    last_day = plan["meal_plan"][-1].get("day") if plan["meal_plan"] else None
                    if last_day in days_list:
                        idx = days_list.index(last_day)
                        if idx < len(days_list) - 1:
                            current_day = days_list[idx + 1]
                        else:
                            current_day = "Monday"  # Wrap around
                    else:
                        current_day = "Monday"
                
                if current_day not in [d.get("day") for d in plan["meal_plan"]]:
                    plan["meal_plan"].append({
                        "day": current_day,
                        "meals": {}
                    })
            
            # Save previous meal if exists
            if current_day and current_meal_type and current_meal:
                day_entry = next((d for d in plan["meal_plan"] if d.get("day") == current_day), None)
                if day_entry:
                    day_entry["meals"][current_meal_type] = current_meal
                    import sys
                    print(f"🔍 DEBUG: Saved {current_meal_type} for {current_day}: {current_meal.get('meal', 'N/A')}", file=sys.stderr, flush=True)
            
            # Start new meal
            if ':' in line:
                meal_type = line.split(':', 1)[0].strip().lower()
                meal_name = line.split(':', 1)[1].strip()
            else:
                # No colon, try to extract meal type from start of line
                meal_type = line.strip().lower().split()[0] if line.strip() else ""
                meal_name = line.replace(meal_type, '').strip() if meal_type else ""
            
            # Normalize meal type
            if 'breakfast' in meal_type:
                current_meal_type = "breakfast"
            elif 'lunch' in meal_type:
                current_meal_type = "lunch"
            elif 'dinner' in meal_type:
                current_meal_type = "dinner"
            else:
                continue  # Skip if we can't identify meal type
            
            current_meal = {
                "meal": meal_name,
                "ingredients": {},
                "calories": base_calories.get(current_meal_type, 0),
                "recipe": ""
            }
            import sys
            print(f"🔍 DEBUG: Started new {current_meal_type} for {current_day}: {meal_name}", file=sys.stderr, flush=True)
        
        # Check for calories
        elif line.upper().startswith('CALORIES:'):
            if current_meal:
                try:
                    cal_text = line.split(':', 1)[1].strip()
                    cal_num = re.search(r'\d+', cal_text)
                    if cal_num:
                        current_meal["calories"] = int(cal_num.group())
                except:
                    pass
        
        # Check for ingredients
        elif line.upper().startswith('INGREDIENTS:'):
            if current_meal:
                ingredients_text = line.split(':', 1)[1].strip()
                ingredients = [i.strip() for i in ingredients_text.split(',')]
                for ing in ingredients:
                    parts = ing.rsplit(' ', 1)
                    if len(parts) == 2:
                        name, qty = parts
                        current_meal["ingredients"][name.strip()] = qty.strip()
                    else:
                        current_meal["ingredients"][ing] = ""
        
        # Check for recipe
        elif line.upper().startswith('RECIPE:'):
            if current_meal:
                recipe_text = line.split(':', 1)[1].strip()
                current_meal["recipe"] = recipe_text
        
        # Recipe continuation (indented lines or numbered steps)
        elif (line.startswith('  ') or line.startswith('\t') or re.match(r'^\d+\.', line)) and current_meal:
            if current_meal.get("recipe"):
                current_meal["recipe"] += " " + line.strip()
            else:
                current_meal["recipe"] = line.strip()
    
    # Save last meal
    if current_day and current_meal_type and current_meal:
        day_entry = next((d for d in plan["meal_plan"] if d.get("day") == current_day), None)
        if day_entry:
            day_entry["meals"][current_meal_type] = current_meal
            import sys
            print(f"🔍 DEBUG: Saved final {current_meal_type} for {current_day}: {current_meal.get('meal', 'N/A')}", file=sys.stderr, flush=True)
    
    import sys
    print(f"🔍 DEBUG parse_text_meal_plan: Final result - {len(plan['meal_plan'])} days", file=sys.stderr, flush=True)
    for day_entry in plan["meal_plan"]:
        meals_count = len(day_entry.get("meals", {}))
        print(f"🔍 DEBUG:   {day_entry.get('day')}: {meals_count} meals ({list(day_entry.get('meals', {}).keys())})", file=sys.stderr, flush=True)
    
    # Generate grocery list from ingredients
    ingredient_map = {}
    for day_entry in plan["meal_plan"]:
        meals = day_entry.get("meals", {})
        for meal_type in ["breakfast", "lunch", "dinner"]:
            if meal_type in meals:
                meal = meals[meal_type]
                for ing_name, ing_qty in meal.get("ingredients", {}).items():
                    if ing_name:
                        if ing_name.lower() not in ingredient_map:
                            ingredient_map[ing_name.lower()] = {
                                "item": ing_name,
                                "quantity": ing_qty or "1",
                                "category": "Other"
                            }
    
    plan["grocery_list"] = list(ingredient_map.values())
    
    # Calculate summary
    total_cals = 0
    day_count = 0
    for day_entry in plan["meal_plan"]:
        meals = day_entry.get("meals", {})
        day_cals = sum(meals.get(m, {}).get("calories", 0) for m in ["breakfast", "lunch", "dinner"])
        if day_cals > 0:
            total_cals += day_cals
            day_count += 1
    
    if day_count > 0:
        plan["summary"]["average_daily_calories"] = round(total_cals / day_count)
    
    return plan


def aggregate_grocery_list_from_plan(plan: dict) -> list:
    """
    Simple function to aggregate all ingredients from all meals in the plan.
    Just collects all unique ingredients - no complex quantity summing.
    """
    if not plan or not isinstance(plan, dict):
        return []
    
    meal_plan = plan.get("meal_plan", [])
    if not isinstance(meal_plan, list):
        return []
    
    # Collect all ingredients from all meals
    ingredient_map = {}  # {ingredient_name: {"quantity": quantity, "category": category}}
    
    for day_entry in meal_plan:
        if not isinstance(day_entry, dict):
            continue
        
        meals = day_entry.get("meals", {})
        if not isinstance(meals, dict):
            continue
        
        for meal_type in ["breakfast", "lunch", "dinner"]:
            if meal_type not in meals:
                continue
            
            meal = meals[meal_type]
            if not isinstance(meal, dict):
                continue
            
            # Skip skipped meals
            if meal.get('meal', '').lower() == 'skipped':
                continue
            
            ingredients = meal.get("ingredients", {})
            if not isinstance(ingredients, dict):
                continue
            
            # Add all ingredients to the map
            for ingredient, quantity in ingredients.items():
                if not ingredient or not quantity:
                    continue
                
                # Use ingredient name as key (case-insensitive for deduplication)
                ingredient_key = ingredient.lower().strip()
                
                if ingredient_key not in ingredient_map:
                    # Determine category
                    category = "Other"
                    if any(word in ingredient_key for word in ["milk", "cheese", "yogurt", "butter", "cream"]):
                        category = "Dairy"
                    elif any(word in ingredient_key for word in ["chicken", "beef", "pork", "fish", "meat", "turkey", "lamb"]):
                        category = "Meat"
                    elif any(word in ingredient_key for word in ["apple", "banana", "tomato", "onion", "pepper", "vegetable", "fruit", "lettuce", "carrot", "cucumber", "broccoli"]):
                        category = "Produce"
                    elif any(word in ingredient_key for word in ["flour", "sugar", "salt", "oil", "vinegar", "spice", "garlic", "herb"]):
                        category = "Pantry"
                    
                    # Store with original ingredient name
                    ingredient_map[ingredient_key] = {
                        "item": ingredient,
                        "quantity": quantity,
                        "category": category
                    }
    
    # Convert to list and sort
    grocery_list = []
    for data in ingredient_map.values():
        grocery_list.append({
            "item": data["item"],
            "quantity": data["quantity"],
            "category": data["category"]
        })
    
    # Sort by category, then by item name
    grocery_list.sort(key=lambda x: (x["category"], x["item"].lower()))
    
    return grocery_list


def format_recipe_with_line_breaks(recipe_text: str) -> list:
    """
    Split recipe text by numbered steps and return as a list of HTML elements with line breaks.
    Handles formats like "1. Step one. 2. Step two." or "1. Step one\n2. Step two"
    """
    if not recipe_text:
        return []
    
    # First, try splitting by newlines if they exist
    if '\n' in recipe_text:
        steps = [s.strip() for s in recipe_text.split('\n') if s.strip()]
    else:
        # Split by numbered patterns (1., 2., 3., etc.)
        # Use a more robust pattern that captures everything between numbers
        # Pattern: number followed by period and optional space, then capture everything until next number or end
        # This handles cases like "1. Step one. 2. Step two" or "1.Step one 2.Step two"
        
        # First, find all number positions
        number_positions = []
        for match in re.finditer(r'\d+\.\s*', recipe_text):
            number_positions.append(match.start())
        
        if number_positions:
            steps = []
            # Extract text between each number
            for i in range(len(number_positions)):
                start = number_positions[i]
                # Find the end: either next number position or end of string
                if i + 1 < len(number_positions):
                    end = number_positions[i + 1]
                else:
                    end = len(recipe_text)
                
                step_text = recipe_text[start:end].strip()
                if step_text:
                    steps.append(step_text)
        else:
            # No numbered steps found, try splitting by "number. " pattern
            parts = re.split(r'(\d+\.\s+)', recipe_text)
            steps = []
            # Combine number with following text
            i = 0
            while i < len(parts):
                if re.match(r'\d+\.\s+', parts[i]):
                    # This is a number, combine with next part
                    step_text = parts[i]
                    if i + 1 < len(parts):
                        step_text += parts[i + 1]
                    steps.append(step_text.strip())
                    i += 2
                else:
                    # This might be text before first number - include it
                    if parts[i].strip():
                        steps.append(parts[i].strip())
                    i += 1
            
            # If still no steps, just use the whole text
            if not steps:
                steps = [recipe_text]
    
    # Create HTML elements for each step
    recipe_elements = []
    for step in steps:
        step_clean = step.strip()
        if step_clean:
            recipe_elements.append(
                html.Div(
                    step_clean,
                    style={
                        "marginBottom": "8px",
                        "paddingLeft": "10px"
                    }
                )
            )
    
    return recipe_elements if recipe_elements else [html.Div(recipe_text)]


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

REQUIRED JSON STRUCTURE:
{
  "meal_plan": [
    {"day": "Monday", "meals": {"breakfast": {...}, "lunch": {...}, "dinner": {...}}},
    ... (7 days total)
  ],
  "grocery_list": [
    {"item": "Eggs", "quantity": "12", "category": "Dairy"},
    {"item": "Chicken breast", "quantity": "1 kg", "category": "Meat"},
    ... (all ingredients summed)
  ],
  "summary": {
    "average_daily_calories": 2400,
    "estimated_weekly_cost": "CHF 150",
    "nutrition_focus": "balanced"
  }
}

MEAL PLAN REQUIREMENTS:
- 7 days: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday (NOT Day 1, Day 2, etc.)
- Keys for each meal must be lowercase: breakfast, lunch, dinner
- Each meal includes: meal (name), ingredients (dict), calories (number), recipe (5-7 numbered steps)
- Total calories per day should match the user's target within ±10%

GROCERY LIST REQUIREMENTS (CRITICAL - DO NOT SKIP):
- MUST include a grocery_list array with ALL ingredients from the week
- Combine duplicate ingredients (e.g., if eggs appear in 5 meals, sum the quantities)
- Account for portion multipliers (2 portions = double the ingredients)
- Each entry MUST have: item, quantity, category
- Categories: Produce, Dairy, Meat, Pantry, Bakery, Frozen, Beverages, Spices, etc.
- Skip meals with 0 portions entirely from the grocery list

IMPORTANT - Ingredient Quantities:
- Use ROUNDED, practical quantities that are easy to measure (e.g., "200 g", "1 cup", "2 tbsp", "50 ml")
- Avoid precise decimals like "47.3 g" or "1.7 cups" - round to nice numbers
- Common rounded amounts: 50g, 100g, 150g, 200g, 250g, 1/2 cup, 1 cup, 1 tbsp, 2 tbsp, etc.
- It's acceptable for total calories to vary ±10% from target to achieve rounded quantities

Recipe instructions format (for the recipe field):
- Provide 5-7 numbered steps with clear, actionable instructions
- Each step should be specific (e.g., "Heat pan over medium heat for 2 minutes" not just "Heat pan")
- Include timing when relevant (e.g., "Cook for 5 minutes", "Let rest for 10 minutes")
- Include temperatures when relevant (e.g., "Preheat oven to 180°C")
- Use action verbs: chop, dice, heat, stir, mix, cook, bake, season, serve
- Format: "1. [action]. 2. [action]. 3. [action]..." all in one paragraph separated by spaces
"""

# Callback to handle tab switching
@app.callback(
    Output("user-info-content", "style"),
    Output("recipes-content", "style"),
    Output("grocery-list-content", "style"),
    Input("main-tabs", "active_tab")
)
def switch_tab(active_tab):
    """Show/hide tab content based on active tab."""
    if active_tab == "user-info":
        return {"display": "block"}, {"display": "none"}, {"display": "none"}
    elif active_tab == "recipes":
        return {"display": "none"}, {"display": "block"}, {"display": "none"}
    elif active_tab == "grocery-list":
        return {"display": "none"}, {"display": "none"}, {"display": "block"}
    else:
        return {"display": "block"}, {"display": "none"}, {"display": "none"}


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


# No callbacks needed for portion inputs - they're simple dcc.Input components


def load_plan(json_text: str) -> dict:
    """Load JSON and normalize nested string JSON."""
    obj = json.loads(json_text)
    if isinstance(obj, str):
        obj = json.loads(obj)
    if not isinstance(obj, dict):
        raise ValueError("Meal plan response must be a JSON object")
    return obj


def fix_calories_in_plan(plan: dict, daily_calorie_target: float, portions: dict = None) -> dict:
    """
    Override calories in the meal plan based on fixed per-meal, per-portion targets.
    This ensures calories are calculated correctly regardless of what the LLM generated.
    
    Rules:
    - Breakfast: 25% of daily target per portion
    - Lunch: 35% of daily target per portion
    - Dinner: 40% of daily target per portion
    - If a meal has 0 portions, set calories to 0
    - Calories are per portion, not total
    """
    if portions is None:
        portions = {}
    
    # Fixed per-portion calorie targets
    base_calories = {
        "breakfast": round(daily_calorie_target * 0.25),  # 25% of daily
        "lunch": round(daily_calorie_target * 0.35),      # 35% of daily
        "dinner": round(daily_calorie_target * 0.40),     # 40% of daily
    }
    
    # Get the meal plan array
    meal_plan = plan.get("meal_plan", [])
    if not isinstance(meal_plan, list):
        return plan
    
    days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Iterate through each day
    for day_entry in meal_plan:
        if not isinstance(day_entry, dict):
            continue
        
        day_name = day_entry.get("day", "")
        meals = day_entry.get("meals", {})
        
        if not isinstance(meals, dict):
            continue
        
        # Fix calories for each meal type
        for meal_type in ["breakfast", "lunch", "dinner"]:
            if meal_type not in meals:
                continue
            
            meal = meals[meal_type]
            if not isinstance(meal, dict):
                continue
            
            # Get portion count for this specific meal
            portion_key = f"{day_name}_{meal_type}"
            portion_count = portions.get(portion_key, 1)
            
            # If 0 portions, set calories to 0
            if portion_count == 0:
                meal["calories"] = 0
            else:
                # Set calories to the fixed per-portion target
                meal["calories"] = base_calories[meal_type]
    
    return plan


def render_plan_view(plan: dict, target: float, portions: dict = None):
    days = normalize_mealplan(plan.get("meal_plan"))
    blocks = []
    
    # Default portions if not provided
    if portions is None:
        portions = {}

    blocks.append(html.H3("Your Weekly Meal Plan 🍲", style={"marginBottom": "20px"}))
    day_totals = []
    
    for day_idx, (day_name, day_dict) in enumerate(days):
        if not isinstance(day_dict, dict):
            continue
        # DO NOT call rescale_day - calories are fixed per meal per portion in code
        # day_dict = rescale_day(day_dict, target)  # REMOVED - calories are now fixed in fix_calories_in_plan()
        total = sum(day_dict[m].get("calories",0) for m in ["breakfast","lunch","dinner"] if m in day_dict)
        day_totals.append(total)
        
        # Create meals content for this day - HORIZONTAL LAYOUT
        meal_cards = []
        for m in ["breakfast","lunch","dinner"]:
            if m not in day_dict: 
                continue
            meal = day_dict[m]
            
            # Get portion count for this specific meal
            portion_key = f"{day_name}_{m}"
            portion_count = portions.get(portion_key, 1)
            
            # If portions = 0 OR meal is marked as "Skipped", show "No meal planned" instead of full card
            if portion_count == 0 or meal.get('meal', '').lower() == 'skipped':
                meal_card = html.Div([
                    html.H5(m.capitalize(), style={"color": "#7f8c8d", "fontSize": "14px", "marginBottom": "8px", "textTransform": "uppercase", "letterSpacing": "0.5px"}),
                    html.Div("No meal planned", style={"fontSize": "14px", "color": "#95a5a6", "fontStyle": "italic", "padding": "20px", "textAlign": "center"})
                ], style={
                    "flex": "1 1 0",
                    "minWidth": "0",
                    "padding": "15px",
                    "backgroundColor": "#f8f9fa",
                    "border": "1px solid #e0e0e0",
                    "borderRadius": "8px",
                    "margin": "5px"
                })
                meal_cards.append(meal_card)
                continue
            
            # Meal header with name, portions, and calories (per portion)
            calories_per_portion = meal.get('calories', '?')
            if portion_count > 1:
                calorie_display = f"{calories_per_portion} kcal/portion (×{portion_count} = {int(calories_per_portion) * portion_count if calories_per_portion != '?' else '?'} kcal total)"
            else:
                calorie_display = f"{calories_per_portion} kcal"
            
            meal_header = html.Div([
                html.Span(meal.get('meal', m), style={"fontWeight": "bold", "fontSize": "16px", "color": "#2c3e50"}),
                html.Span(f" • {portion_count} portion{'s' if portion_count != 1 else ''}", style={"fontSize": "13px", "color": "#3498db", "marginLeft": "8px", "fontWeight": "500"}),
                html.Span(f" • {calorie_display}", style={"fontSize": "13px", "color": "#7f8c8d", "marginLeft": "8px"}),
            ], style={"marginBottom": "10px"})
            
            # Ingredients in card grid
            ingredient_cards = []
            for ingredient, quantity in meal.get("ingredients", {}).items():
                ingredient_cards.append(
                    html.Div([
                        html.Div(ingredient, style={"fontWeight": "bold", "fontSize": "13px", "color": "#2c3e50", "marginBottom": "4px"}),
                        html.Div(quantity, style={"fontSize": "12px", "color": "#7f8c8d"}),
                    ], style={
                        "backgroundColor": "white",
                        "border": "1px solid #ddd",
                        "borderRadius": "6px",
                        "padding": "10px",
                        "minWidth": "120px",
                        "display": "inline-block",
                        "margin": "4px",
                        "verticalAlign": "top"
                    })
                )
            
            ingredients_section = html.Div(ingredient_cards, style={"marginBottom": "12px"})
            
            # Recipe instructions
            recipe_section = None
            if meal.get('recipe'):
                recipe_steps = format_recipe_with_line_breaks(meal.get('recipe',''))
                recipe_section = html.Div(
                    recipe_steps,
                    style={
                        "fontSize": "13px",
                        "color": "#555", 
                        "lineHeight": "1.6",
                        "marginTop": "8px",
                        "padding": "10px",
                        "backgroundColor": "#f8f9fa",
                        "borderRadius": "6px",
                        "borderLeft": "3px solid #3498db"
                    }
                )
            
            # Create a card for this meal with unique ID
            meal_card_id = f"meal-card-{day_idx}-{m}"
            change_button_id = f"change-meal-{day_idx}-{m}"
            
            # Like button ID (premium feature) - using pattern matching
            like_button_id = {"type": "like-recipe", "day": day_idx, "meal": m}
            
            # Create a card for this meal
            meal_card = html.Div([
                html.Div([
                    html.H5(m.capitalize(), style={"color": "#7f8c8d", "fontSize": "14px", "marginBottom": "8px", "textTransform": "uppercase", "letterSpacing": "0.5px", "display": "inline-block"}),
                    html.Div([
                        dbc.Button(
                            "❤️ Save",
                            id=like_button_id,
                            color="danger",
                            size="sm",
                            n_clicks=0,
                            outline=True,
                            style={"fontSize": "12px", "padding": "4px 10px", "marginRight": "5px"}
                        ),
                        dbc.Button(
                            "🔀 Change",
                            id=change_button_id,
                            color="light",
                            size="sm",
                            n_clicks=0,
                            style={"fontSize": "12px", "padding": "4px 10px"}
                        ),
                    ], style={"float": "right"}),
                ], style={"marginBottom": "8px"}),
                meal_header,
                ingredients_section,
                recipe_section if recipe_section else html.Div(),
                # Store the meal data for regeneration
                dcc.Store(id=f"meal-data-{day_idx}-{m}", data={
                    "day_name": day_name,
                    "meal_type": m,
                    "target_calories": meal.get('calories', target // 3)
                })
            ], id=meal_card_id, style={
                "flex": "1 1 0",
                "minWidth": "0",
                "padding": "15px",
                "backgroundColor": "#fff",
                "border": "1px solid #e0e0e0",
                "borderRadius": "8px",
                "margin": "5px"
            })
            
            meal_cards.append(meal_card)
        
        # Horizontal container for all meals - FORCE HORIZONTAL LAYOUT
        meals_content = [
            html.Div(meal_cards, style={
                "display": "flex",
                "flexWrap": "nowrap",  # Never wrap to next line
                "gap": "10px",
                "justifyContent": "space-between",
                "width": "100%",
                "overflowX": "auto"  # Scroll if needed instead of wrapping
            })
        ]
        
        # Create collapsible card for this day
        blocks.append(
            dbc.Card([
                dbc.CardHeader(
                    html.Div([
                        html.H4(f"{day_name} — {round(total)} kcal", className="mb-0", style={"display": "inline-block", "marginRight": "10px"}),
                        html.Small(f"(Target: {target} kcal)", style={"color": "#666", "marginRight": "auto"}),
                        dbc.Button(
                            "Show/Hide",
                            id=f"plan-day-toggle-{day_idx}",
                            color="secondary",
                            size="sm",
                            n_clicks=0,
                        ),
                    ], style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "padding": "10px"}),
                ),
                dbc.Collapse(
                    dbc.CardBody(meals_content),
                    id=f"plan-day-collapse-{day_idx}",
                    is_open=True,  # First day open by default
                ),
            ], style={"marginBottom": "10px", "borderRadius": "8px", "border": "1px solid #ddd"})
        )

    # Grocery list is now in a separate tab - just initialize the store
    grocery = plan.get("grocery_list") or []
    if isinstance(grocery, dict):
        grocery = list(grocery.values())
    
    # Store grocery list data for editing (will be updated by callback)
    blocks.append(dcc.Store(id="grocery-list-store", data=grocery if grocery else []))

    # Summary Section
    summary = plan.get("summary") or {}
    if not isinstance(summary, dict):
        summary = {}
    if not summary.get("average_daily_calories") and day_totals:
        summary["average_daily_calories"] = round(sum(day_totals)/len(day_totals))
    
    blocks.append(
        dbc.Card([
            dbc.CardBody([
                html.H3("📋 Summary", style={"marginBottom": "15px"}),
                html.P([html.Strong("Average daily calories: "), f"{summary.get('average_daily_calories','?')} kcal"]),
                html.P([html.Strong("Estimated weekly cost: "), f"{summary.get('estimated_weekly_cost','?')}"]),
                html.P([html.Strong("Nutrition focus: "), f"{summary.get('nutrition_focus','?')}"]),
            ])
        ], style={"marginTop": "20px", "backgroundColor": "#f8f9fa", "border": "1px solid #dee2e6"})
    )
    
    # Download PDF button
    blocks.append(
        html.Div([
            dbc.Button(
                "📥 Download PDF Summary",
                id="download-pdf-button",
                color="primary",
                size="lg",
                style={"marginTop": "30px", "width": "100%", "maxWidth": "400px"}
            )
        ], style={"textAlign": "center", "marginTop": "30px", "marginBottom": "40px"})
    )

    return html.Div(blocks)


# Callbacks for collapsible day sections in meal plan (7 days = 7 callbacks)
for day_idx in range(7):
    @app.callback(
        Output(f"plan-day-collapse-{day_idx}", "is_open"),
        Input(f"plan-day-toggle-{day_idx}", "n_clicks"),
        State(f"plan-day-collapse-{day_idx}", "is_open"),
        prevent_initial_call=True
    )
    def toggle_plan_day(n_clicks, is_open):
        if not n_clicks:
            raise PreventUpdate
        return not is_open


# Callbacks for changing individual meals (7 days x 3 meals = 21 callbacks)
for day_idx in range(7):
    for meal_type in ["breakfast", "lunch", "dinner"]:
        @app.callback(
            Output(f"meal-card-{day_idx}-{meal_type}", "children"),
            Output("plan-data-store", "data", allow_duplicate=True),
            Output("grocery-list-store", "data", allow_duplicate=True),
            Input(f"change-meal-{day_idx}-{meal_type}", "n_clicks"),
            State(f"meal-data-{day_idx}-{meal_type}", "data"),
            State("body_weight", "value"),
            State("activity_hours", "value"),
            State("goals", "value"),
            State("restrictions", "value"),
            State("diet_type", "value"),
            State("plan-data-store", "data"),
            State("grocery-list-store", "data"),
            State({"type": "portion", "day": ALL, "meal": ALL}, "value"),
            prevent_initial_call=True
        )
        def change_single_meal(n_clicks, meal_data, weight, activity_hours, goals, restrictions, diet, plan_data, current_grocery_list, portion_values):
            if not n_clicks or not meal_data:
                raise PreventUpdate
            
            # Generate a new recipe for this specific meal
            day_name = meal_data.get("day_name", "Monday")
            meal_type = meal_data.get("meal_type", "breakfast")
            target_calories = meal_data.get("target_calories", 400)
            
            # Get portion count for this specific meal
            portion_count = 1
            if portion_values and len(portion_values) == 21:
                days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                meals_list = ["breakfast", "lunch", "dinner"]
                try:
                    # Find the index: meals are ordered as breakfast (all days), lunch (all days), dinner (all days)
                    meal_idx = meals_list.index(meal_type)
                    day_idx = days_list.index(day_name)
                    # Index calculation: meal_idx * 7 (days) + day_idx
                    idx = meal_idx * 7 + day_idx
                    if idx < len(portion_values):
                        val = portion_values[idx]
                        portion_count = int(val) if (val is not None and val != '') else 1
                except (ValueError, IndexError):
                    portion_count = 1
            
            # Calculate total calories for all portions
            total_calories = target_calories * portion_count
            
            prompt = f"""
            Generate a single {meal_type} recipe as JSON with this exact structure:
            {{
                "meal": "Recipe Name",
                "ingredients": {{"ingredient1": "quantity1", "ingredient2": "quantity2"}},
                "calories": {target_calories},
                "recipe": "1. Step one. 2. Step two. 3. Step three. 4. Step four. 5. Step five."
            }}
            
            Requirements:
            - For a {meal_type} meal
            - Number of portions: {portion_count} person{'s' if portion_count != 1 else ''}
            - Target calories per portion: {target_calories} kcal (±10% is okay)
            - Total calories for all portions: {total_calories} kcal
            - Diet: {diet}
            - Restrictions: {restrictions or 'None'}
            - IMPORTANT: Scale all ingredient quantities for {portion_count} portion{'s' if portion_count != 1 else ''}
            - Use rounded quantities (50g, 100g, 1 cup, 2 tbsp, etc.) - multiply by {portion_count} for the total
            - Provide 5-7 numbered steps with specific actions, timing, and temperatures
            - Return ONLY valid JSON, no markdown or extra text
            """
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"system","content":"You are a recipe generator. Return only valid JSON."},
                              {"role":"user","content":prompt}],
                    response_format={"type": "json_object"},
                )
                raw_content = (response.choices[0].message.content or "").strip()
                meal_data_new = json.loads(raw_content)
                
                # Render the new meal card
                calories_per_portion = meal_data_new.get('calories', target_calories)
                if portion_count > 1:
                    calorie_display = f"{calories_per_portion} kcal/portion (×{portion_count} = {int(calories_per_portion) * portion_count} kcal total)"
                else:
                    calorie_display = f"{calories_per_portion} kcal"
                
                meal_header = html.Div([
                    html.Span(meal_data_new.get('meal', meal_type), style={"fontWeight": "bold", "fontSize": "16px", "color": "#2c3e50"}),
                    html.Span(f" • {portion_count} portion{'s' if portion_count != 1 else ''}", style={"fontSize": "13px", "color": "#3498db", "marginLeft": "8px", "fontWeight": "500"}),
                    html.Span(f" • {calorie_display}", style={"fontSize": "13px", "color": "#7f8c8d", "marginLeft": "8px"}),
                ], style={"marginBottom": "10px"})
                
                # Ingredients
                ingredient_cards = []
                for ingredient, quantity in meal_data_new.get("ingredients", {}).items():
                    ingredient_cards.append(
                        html.Div([
                            html.Div(ingredient, style={"fontWeight": "bold", "fontSize": "13px", "color": "#2c3e50", "marginBottom": "4px"}),
                            html.Div(quantity, style={"fontSize": "12px", "color": "#7f8c8d"}),
                        ], style={
                            "backgroundColor": "white",
                            "border": "1px solid #ddd",
                            "borderRadius": "6px",
                            "padding": "10px",
                            "minWidth": "120px",
                            "display": "inline-block",
                            "margin": "4px",
                            "verticalAlign": "top"
                        })
                    )
                
                ingredients_section = html.Div(ingredient_cards, style={"marginBottom": "12px"})
                
                # Recipe with line breaks
                recipe_steps = format_recipe_with_line_breaks(meal_data_new.get('recipe',''))
                recipe_section = html.Div(
                    recipe_steps,
                    style={
                        "fontSize": "13px",
                        "color": "#555", 
                        "lineHeight": "1.6",
                        "marginTop": "8px",
                        "padding": "10px",
                        "backgroundColor": "#f8f9fa",
                        "borderRadius": "6px",
                        "borderLeft": "3px solid #3498db"
                    }
                )
                
                # Update the plan data with the new meal
                updated_plan = None
                updated_grocery = None
                
                if plan_data:
                    try:
                        # Parse the plan data
                        if isinstance(plan_data, str):
                            plan_dict = json.loads(plan_data)
                        elif isinstance(plan_data, dict):
                            plan_dict = plan_data
                        else:
                            plan_dict = {}
                        
                        # Find and update the specific meal in the plan
                        meal_plan = plan_dict.get("meal_plan", [])
                        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                        
                        for day_entry in meal_plan:
                            if isinstance(day_entry, dict) and day_entry.get("day") == day_name:
                                meals = day_entry.get("meals", {})
                                if meal_type in meals:
                                    # Update the meal with new data
                                    old_meal = meals[meal_type]
                                    meals[meal_type] = meal_data_new
                                    print(f"✅ Updated {day_name} {meal_type}: {old_meal.get('meal', 'old')} -> {meal_data_new.get('meal', 'new')}")
                                    break
                        
                        # Parse portions from portion_values
                        portions = {}
                        if portion_values and len(portion_values) == 21:
                            idx = 0
                            for meal in ["breakfast", "lunch", "dinner"]:
                                for day in days_list:
                                    val = portion_values[idx]
                                    portions[f"{day}_{meal}"] = int(val) if (val is not None and val != '') else 1
                                    idx += 1
                        else:
                            # Default: all meals = 1 portion
                            for day in days_list:
                                for meal in ["breakfast", "lunch", "dinner"]:
                                    portions[f"{day}_{meal}"] = 1
                        
                        # Aggregate grocery list from all meals in the updated plan
                        updated_grocery = aggregate_grocery_list_from_plan(plan_dict)
                        
                        # Ensure we have a valid grocery list (even if empty, it should be a list)
                        if not isinstance(updated_grocery, list) or len(updated_grocery) == 0:
                            # Fallback to existing grocery list if recalculation failed or returned empty
                            if current_grocery_list and isinstance(current_grocery_list, list) and len(current_grocery_list) > 0:
                                updated_grocery = current_grocery_list
                                print(f"⚠️ Grocery recalculation returned empty, using existing list with {len(updated_grocery)} items")
                            else:
                                updated_grocery = []
                                print(f"⚠️ No grocery list available, using empty list")
                        else:
                            print(f"✅ Updated meal {day_name} {meal_type}, grocery list has {len(updated_grocery)} items")
                        
                        # Update plan_data - keep the same format (string or dict)
                        if isinstance(plan_data, str):
                            updated_plan = json.dumps(plan_dict)
                        else:
                            updated_plan = plan_dict
                        
                    except Exception as e:
                        print(f"⚠️ Error updating plan/grocery list: {e}")
                        import traceback
                        traceback.print_exc()
                        # If update fails, preserve existing grocery list instead of clearing it
                        updated_plan = no_update
                        if current_grocery_list and isinstance(current_grocery_list, list):
                            updated_grocery = current_grocery_list
                        else:
                            updated_grocery = []
                else:
                    # No plan_data available, preserve existing grocery list
                    updated_plan = no_update
                    if current_grocery_list and isinstance(current_grocery_list, list):
                        updated_grocery = current_grocery_list
                    else:
                        updated_grocery = []
                    print(f"⚠️ No plan_data available, preserving existing grocery list")
                
                # Return new card content, updated plan, and updated grocery list
                # Recreate meal_data dict for the Store
                meal_data = {
                    "day_name": day_name,
                    "meal_type": meal_type,
                    "target_calories": calories_per_portion
                }
                
                meal_card_content = [
                    html.Div([
                        html.H5(meal_type.capitalize(), style={"color": "#7f8c8d", "fontSize": "14px", "marginBottom": "8px", "textTransform": "uppercase", "letterSpacing": "0.5px", "display": "inline-block"}),
                        html.Div([
                            dbc.Button(
                                "❤️ Save",
                                id={"type": "like-recipe", "day": day_idx, "meal": meal_type},
                                color="danger",
                                size="sm",
                                n_clicks=0,
                                outline=True,
                                style={"fontSize": "12px", "padding": "4px 10px", "marginRight": "5px"}
                            ),
                            dbc.Button(
                                "🔀 Change",
                                id=f"change-meal-{day_idx}-{meal_type}",
                                color="light",
                                size="sm",
                                n_clicks=0,
                                style={"fontSize": "12px", "padding": "4px 10px"}
                            ),
                        ], style={"float": "right"}),
                    ], style={"marginBottom": "8px"}),
                    meal_header,
                    ingredients_section,
                    recipe_section,
                    dcc.Store(id=f"meal-data-{day_idx}-{meal_type}", data=meal_data)
                ]
                
                return meal_card_content, updated_plan, updated_grocery
                
            except Exception as e:
                error_div = html.Div(f"Error regenerating recipe: {str(e)}", style={"color": "red"})
                return error_div, no_update, no_update


def generate_plan(n, weight, activity_hours, goals, budget, calories, restrictions, diet, location, avoid_ingredients="", cravings="", complexity="medium", cuisines=None, portions=None):
    # Default portions if not provided
    if portions is None:
        portions = {"breakfast": 1, "lunch": 1, "dinner": 1}
    
    # Build complexity description
    complexity_desc = {
        "quick": "Quick meals under 20 minutes",
        "medium": "Medium complexity, 20-40 minutes",
        "elaborate": "Elaborate recipes over 40 minutes",
        "mixed": "Mix of quick, medium, and elaborate recipes"
    }.get(complexity, "Medium complexity")
    
    # Build cuisine preference
    cuisine_pref = ""
    if cuisines and len(cuisines) > 0:
        cuisine_pref = f"- Preferred cuisines: {', '.join(cuisines)}"
    
    # Build portions info - just show which meals to cook, NO calorie totals
    portions_lines = ["Number of portions (people) to cook for each meal:"]
    days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Base calories per person per meal (for 1 portion) - FIXED
    base_calories = {
        "breakfast": round(calories * 0.25),  # 25% of daily
        "lunch": round(calories * 0.35),      # 35% of daily
        "dinner": round(calories * 0.40),     # 40% of daily
    }
    
    for day in days_list:
        day_portions = []
        
        # Just show portions, NO calorie calculations to avoid confusing LLM
        for meal in ["breakfast", "lunch", "dinner"]:
            key = f"{day}_{meal}"
            p = portions.get(key, 1)
            
            if p == 0:
                day_portions.append(f"{meal}: SKIP")
            else:
                day_portions.append(f"{meal}: {p} person{'s' if p != 1 else ''}")
        
        portions_lines.append(f"  {day}: {', '.join(day_portions)}")
    
    portions_info = "\n".join(portions_lines)
    
    user_prompt = f"""
    Create a 7-day meal plan for:
    - Body weight: {weight} kg
    - Activity: {activity_hours} hours/week
    - Goals: {', '.join(goals or [])}
    - Diet: {diet}
    - Restrictions: {restrictions or 'None'}
    - Budget: {budget} CHF
    - Location: {location}
    - Complexity: {complexity_desc}
    {f"- Ingredients to AVOID: {avoid_ingredients}" if avoid_ingredients else ""}
    {f"- Foods user is craving: {cravings}" if cravings else ""}
    {cuisine_pref}
    
    {portions_info}
    
    IMPORTANT:
    - Do NOT use any of these ingredients if specified: {avoid_ingredients or 'none'}
    - CRAVINGS: Incorporate these foods in ONLY 1-2 meals during the ENTIRE week (not every day): {cravings or 'none'}. Use them sparingly as special treats or highlights, not as a base for every meal.
    - Match the complexity level: {complexity_desc}
    {f"- Favor these cuisines: {', '.join(cuisines or [])}" if cuisines else ""}
    
    ⚠️ CALORIE TARGETS (CRITICAL - IGNORE DAILY TOTALS, FOCUS ON PER-MEAL):
    
    DO NOT try to balance daily calories. Instead, create EACH MEAL independently with these FIXED targets:
    
    FIXED CALORIES PER PERSON PER MEAL:
      * Every breakfast: {base_calories['breakfast']} kcal per person (always)
      * Every lunch: {base_calories['lunch']} kcal per person (always)
      * Every dinner: {base_calories['dinner']} kcal per person (always)
    
    CRITICAL RULES:
    - Generate each meal to hit its specific calorie target (breakfast={base_calories['breakfast']}, lunch={base_calories['lunch']}, dinner={base_calories['dinner']})
    - DO NOT look at daily totals
    - DO NOT adjust meals based on what other meals are that day
    - If a meal is SKIPPED, the other meals that day stay at their normal calories
    - The "calories" field in JSON = the per-person target ({base_calories['breakfast']} for breakfast, {base_calories['lunch']} for lunch, {base_calories['dinner']} for dinner)
    - Scale INGREDIENTS for the number of portions, but keep per-person calories the same
    
    Example: Monday breakfast SKIP, lunch 1 person, dinner 2 persons:
    - Breakfast: {{"meal": "Skipped", "calories": 0, "ingredients": {{}}, "recipe": "No meal planned"}}
    - Lunch: {{"meal": "...", "calories": {base_calories['lunch']}, "ingredients": {{...}}, "recipe": "..."}} (normal lunch, NOT increased)
    - Dinner: {{"meal": "...", "calories": {base_calories['dinner']}, "ingredients": {{... doubled quantities}}, "recipe": "..."}} (normal dinner per person, ingredients for 2)
    
    GROCERY LIST: Sum up ALL ingredients across the week, accounting for the portion multipliers. Skip meals with 0 portions entirely.
    """

    raw_content = ""
    json_text = ""
    plan_payload = None
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
        # Fix calories in code - override LLM's calorie values with correct per-portion targets
        plan = fix_calories_in_plan(plan, calories, portions)
        # Update the JSON payload with corrected calories
        plan_payload = json.dumps(plan)
        return render_plan_view(plan, calories, portions), plan_payload
    except json.JSONDecodeError as je:
        cleaned_text = clean_json_text(json_text)
        if cleaned_text != json_text:
            try:
                plan = load_plan(cleaned_text)
                # Fix calories in code - override LLM's calorie values with correct per-portion targets
                plan = fix_calories_in_plan(plan, calories, portions)
                # Update the JSON payload with corrected calories
                plan_payload = json.dumps(plan)
                return render_plan_view(plan, calories, portions), plan_payload
            except json.JSONDecodeError:
                pass

        snippet = (raw_content or cleaned_text or "")[:1000]
        return html.Div(
            [
                html.P(f"Error: JSON parsing failed – {je}", style={"color": "red", "fontWeight": "bold"}),
                html.Pre(snippet, style={"whiteSpace": "pre-wrap", "background": "#f8f9fa", "padding": "10px"}),
            ]
        ), plan_payload or cleaned_text or json_text
    except Exception as e:
        return html.Div(f"Error: {type(e).__name__} – {e}", style={"color": "red"}), plan_payload or json_text or raw_content


def generate_plan_hf(n, weight, activity_hours, goals, budget, calories, restrictions, diet, location, avoid_ingredients="", cravings="", complexity="medium", cuisines=None, portions=None):
    import sys
    print(f"🔍 DEBUG generate_plan_hf: Function called with calories={calories}, diet={diet}", file=sys.stderr, flush=True)
    
    # Default portions if not provided
    if portions is None:
        portions = {"breakfast": 1, "lunch": 1, "dinner": 1}
    
    complexity_desc = {
        "quick": "Quick meals under 20 minutes",
        "medium": "Medium complexity, 20-40 minutes",
        "elaborate": "Elaborate recipes over 40 minutes",
        "mixed": "Mix of quick, medium, and elaborate recipes"
    }.get(complexity, "Medium complexity")
    
    # Build portions info - detailed per day and meal with calorie calculations
    # Use realistic meal calorie distribution: Breakfast 25%, Lunch 35%, Dinner 40%
    portions_lines = ["Portions per meal with calorie targets (per portion):"]
    days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Base calories per person per meal (for 1 portion)
    base_calories = {
        "breakfast": round(calories * 0.25),  # 25% of daily
        "lunch": round(calories * 0.35),      # 35% of daily
        "dinner": round(calories * 0.40),     # 40% of daily
    }
    
    for day in days_list:
        day_portions = []
        
        # Build meal info with calorie targets
        for meal in ["breakfast", "lunch", "dinner"]:
            key = f"{day}_{meal}"
            p = portions.get(key, 1)
            
            if p == 0:
                day_portions.append(f"{meal}: SKIP (0 kcal)")
            else:
                # Calories = base_per_person × number_of_portions
                target_cals = base_calories[meal] * p
                day_portions.append(f"{meal}: {p}p (~{target_cals} kcal total)")
        
        portions_lines.append(f"  {day}: {', '.join(day_portions)}")
    
    portions_info = "\n".join(portions_lines)
    
    # Add explanation of the calorie model
    portions_info += "\n\nCalorie model: Each portion represents one person's meal. Base calories per person: Breakfast ~{} kcal, Lunch ~{} kcal, Dinner ~{} kcal.".format(
        base_calories["breakfast"],
        base_calories["lunch"],
        base_calories["dinner"]
    )
    
    # Use simple text format - SHORTENED prompt to avoid truncation
    user_prompt = f"""Create a 7-day meal plan.

User: {calories} cal/day, {diet} diet{f", avoid {avoid_ingredients}" if avoid_ingredients else ""}{f", likes {cravings}" if cravings else ""}

Format:
DAY: Monday
BREAKFAST: Meal Name
  Calories: {base_calories['breakfast']}
  Ingredients: Item1 qty1, Item2 qty2
  Recipe: 1. Step one. 2. Step two. 3. Step three.
LUNCH: Meal Name
  Calories: {base_calories['lunch']}
  Ingredients: Item1 qty1, Item2 qty2
  Recipe: 1. Step one. 2. Step two. 3. Step three.
DINNER: Meal Name
  Calories: {base_calories['dinner']}
  Ingredients: Item1 qty1, Item2 qty2
  Recipe: 1. Step one. 2. Step two. 3. Step three.

Repeat for all 7 days: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday."""
    raw_content = ""
    json_text = ""
    plan_payload = None
    try:
        pipe = get_hf_pipeline()
        tokenizer = pipe.tokenizer
        # Check for repetitive output and stop early if detected
        raw_output = pipe(
            user_prompt,
            max_new_tokens=1500,  # Reduced further to prevent excessive generation
            temperature=0.9,  # Higher temperature for more variety
            do_sample=True,
            truncation=True,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id if tokenizer.eos_token_id else None,
            repetition_penalty=2.0,  # Strong repetition penalty to prevent loops
            no_repeat_ngram_size=2,  # Prevent repeating 2-grams
        )
        
        # Handle pipeline output
        import sys
        if isinstance(raw_output, list) and len(raw_output) > 0:
            raw_output = raw_output[0]
            print(f"🔍 DEBUG: Extracted from list, type: {type(raw_output)}", file=sys.stderr, flush=True)
        
        if isinstance(raw_output, dict):
            raw_content = raw_output.get("generated_text", "")
            print(f"🔍 DEBUG: Got generated_text from dict, length: {len(raw_content)}", file=sys.stderr, flush=True)
        elif isinstance(raw_output, str):
            raw_content = raw_output
            print(f"🔍 DEBUG: Got string output, length: {len(raw_content)}", file=sys.stderr, flush=True)
        else:
            raw_content = str(raw_output) if raw_output else ""
            print(f"🔍 DEBUG: Converted to string, length: {len(raw_content)}", file=sys.stderr, flush=True)
        
        # If return_full_text=True, we need to extract just the generated part (after the prompt)
        # The generated_text includes the prompt, so we need to remove it
        if user_prompt in raw_content:
            # Find where the prompt ends and extract only the generated part
            prompt_end = raw_content.find(user_prompt) + len(user_prompt)
            raw_content = raw_content[prompt_end:].strip()
            print(f"🔍 DEBUG: Extracted generated part (after prompt), length: {len(raw_content)}", file=sys.stderr, flush=True)
        print(f"🔍 DEBUG: Raw output length: {len(raw_content)} chars", file=sys.stderr, flush=True)
        print(f"🔍 DEBUG: First 500 chars: {raw_content[:500]}", file=sys.stderr, flush=True)
        print(f"🔍 DEBUG: Last 500 chars: {raw_content[-500:]}", file=sys.stderr, flush=True)
        
        # Check for repetitive output (model stuck in loop)
        if raw_content and len(raw_content) > 100:
            # Check if output is mostly repetitive
            words = raw_content.split()
            if len(words) > 10:
                unique_words = len(set(words[:50]))  # Check first 50 words
                if unique_words < 5:  # Less than 5 unique words in first 50 = repetitive
                    raise ValueError(f"HuggingFace model generated repetitive output (only {unique_words} unique words in first 50). The model may not be suitable for this task. Please use the 'Generate My Weekly Plan' button instead.")
        
        if not raw_content or not raw_content.strip():
            raise ValueError("HuggingFace model returned empty output.")
        
        # Parse the text format instead of JSON
        print(f"🔍 DEBUG: Parsing text format meal plan...", file=sys.stderr, flush=True)
        print(f"🔍 DEBUG: Raw content (first 2000 chars):\n{raw_content[:2000]}", file=sys.stderr, flush=True)
        plan = parse_text_meal_plan(raw_content, base_calories)
        print(f"🔍 DEBUG: Successfully parsed! Found {len(plan.get('meal_plan', []))} days", file=sys.stderr, flush=True)
        if len(plan.get('meal_plan', [])) == 0:
            print(f"⚠️ WARNING: Parser found 0 days!", file=sys.stderr, flush=True)
            print(f"⚠️ WARNING: Full raw content:\n{raw_content}", file=sys.stderr, flush=True)
            print(f"⚠️ WARNING: Plan structure: {plan}", file=sys.stderr, flush=True)
        
        # Convert to JSON for compatibility
        json_text = json.dumps(plan)
        # Fix calories in code - override LLM's calorie values with correct per-portion targets
        plan = fix_calories_in_plan(plan, calories, portions)
        # Update the JSON payload with corrected calories
        plan_payload = json.dumps(plan)
        return render_plan_view(plan, calories, portions), plan_payload
    except Exception as e:
        return html.Div(
            [
                html.P(f"Error using HuggingFace model: {type(e).__name__} – {e}", style={"color": "red", "fontWeight": "bold"}),
                html.P("⚠️ The HuggingFace model sometimes generates invalid JSON. Try the 'Generate My Weekly Plan' button instead for better results!", style={"color": "#856404", "backgroundColor": "#fff3cd", "padding": "10px", "borderRadius": "5px", "marginTop": "10px"}),
                html.Details([
                    html.Summary("Show raw output", style={"cursor": "pointer", "marginTop": "10px"}),
                    html.Pre((raw_content or "")[:800], style={"whiteSpace": "pre-wrap", "background": "#f8f9fa", "padding": "10px"}),
                ]),
            ]
        ), plan_payload or json_text or raw_content


# -------------------- CHATBOT (LLamaIndex Agent) --------------------

CHAT_SYSTEM_PROMPT = """
You are CULINAIRE Chat, a helpful culinary assistant.
- Use the web_search tool whenever the user asks for current information, product options, or evidence. Cite URLs.
- Keep answers concise and organized; include short bullet references with source URLs.
- Blend in the user's profile or latest meal plan if provided.
"""


def web_search(query: str, max_results: int = 3) -> str:
    """Search the web and return a compact JSON-like string of results."""
    if not query:
        return "[]"
    results = []
    try:
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                if not item:
                    continue
                results.append(
                    {
                        "title": item.get("title"),
                        "url": item.get("href"),
                        "snippet": item.get("body"),
                    }
                )
    except Exception as e:
        return json.dumps([{"error": f"search_failed: {e}"}])
    return json.dumps(results)


def latest_plan_summary(plan_data):
    if not isinstance(plan_data, dict):
        return ""
    raw = plan_data.get("raw_json")
    if not raw:
        return ""
    snippet = raw if len(raw) < 1200 else raw[:1200] + "..."
    return f"Latest meal plan JSON (truncated): {snippet}"


def parse_plan_raw(plan_raw):
    if not plan_raw:
        return None
    try:
        data = json.loads(plan_raw)
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def plan_digest(plan_data, max_days=3):
    """Small, model-friendly digest of the plan for chat."""
    if not isinstance(plan_data, dict):
        return ""
    plan_raw = plan_data.get("raw_json")
    parsed = parse_plan_raw(plan_raw)
    if not parsed:
        return ""
    meal_plan = parsed.get("meal_plan")
    days = normalize_mealplan(meal_plan)
    lines = []
    for idx, (day_name, meals) in enumerate(days):
        if idx >= max_days:
            lines.append(f"...({len(days) - max_days} more days)")
            break
        lines.append(f"{day_name}:")
        for meal_name in ["breakfast", "lunch", "dinner"]:
            meal = meals.get(meal_name, {})
            title = meal.get("meal") or meal_name.title()
            cals = meal.get("calories")
            lines.append(f"- {meal_name.title()}: {title} ({cals} kcal)")
    grocery = parsed.get("grocery_list")
    if grocery:
        lines.append(f"Grocery items: {len(grocery)} entries.")
    summary = parsed.get("summary", {})
    if summary:
        lines.append(f"Summary: avg daily calories {summary.get('average_daily_calories')}, est weekly cost {summary.get('estimated_weekly_cost')}.")
    return "\n".join(lines)


def plan_full_context(plan_data, max_chars=8000):
    """Richer per-day overview so the agent can answer specific day questions."""
    if not isinstance(plan_data, dict):
        return ""
    parsed = parse_plan_raw(plan_data.get("raw_json"))
    if not parsed:
        return ""
    meal_plan = parsed.get("meal_plan")
    days = normalize_mealplan(meal_plan)
    lines = []
    for day_name, meals in days:
        lines.append(day_name + ":")
        for meal_name in ["breakfast", "lunch", "dinner"]:
            meal = meals.get(meal_name, {})
            title = meal.get("meal") or meal_name.title()
            cals = meal.get("calories")
            ing = meal.get("ingredients", {})
            ing_list = ", ".join(f"{k} {v}" for k, v in ing.items()) if ing else "ingredients not provided"
            lines.append(f"- {meal_name.title()}: {title} ({cals} kcal) | {ing_list}")
    summary = parsed.get("summary", {})
    if summary:
        lines.append(f"Summary: avg daily calories {summary.get('average_daily_calories')}, est weekly cost {summary.get('estimated_weekly_cost')}, focus {summary.get('nutrition_focus')}.")
    text = "\n".join(lines)
    if len(text) > max_chars:
        return text[:max_chars] + "... (truncated)"
    return text


def _extract_price_fields(product):
    """Best-effort price extraction from Migros product payload."""
    if not isinstance(product, dict):
        return {}
    price = None
    currency = "CHF"

    # Common locations
    if isinstance(product.get("price"), (int, float, str, dict)):
        price = product.get("price")
    prices = product.get("prices") or {}
    if isinstance(prices, dict):
        price = price or prices.get("defaultPrice") or prices.get("price")
        currency = prices.get("currency") or currency

    if isinstance(price, dict):
        currency = price.get("currency") or currency
        price = price.get("value") or price.get("amount") or price.get("price")

    try:
        price = float(price)
    except (TypeError, ValueError):
        price = None

    return {"price": price, "currency": currency}


def _extract_energy(product):
    """Attempt to extract calorie/energy info."""
    if not isinstance(product, dict):
        return None
    # Check common keys
    for key in ["calories", "energyKcal", "energy_kcal", "energy"]:
        val = product.get(key)
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    nutrients = product.get("nutrients") or product.get("nutritionFacts")
    if isinstance(nutrients, dict):
        for k in ["energyKcal", "energy_kcal", "calories", "kcal"]:
            if k in nutrients:
                try:
                    return float(nutrients[k])
                except (TypeError, ValueError):
                    pass
    return None


def fetch_migros_token():
    """Get Migros token from env or guest endpoint."""
    if MIGROS_API_TOKEN:
        return MIGROS_API_TOKEN
    try:
        resp = requests.get(
            "https://www.migros.ch/authentication/public/v1/api/guest",
            headers=MIGROS_DEFAULT_HEADERS,
            timeout=10,
        )
        token = resp.headers.get("leshopch")
        return token
    except Exception:
        return None


def run_node_migros_helper(names):
    """Call the Node helper to fetch a guest token and prices for a list of names."""
    if not os.path.exists(MIGROS_HELPER_PATH):
        return None
    try:
        payload = json.dumps(names)
    except Exception:
        return None
    env = os.environ.copy()
    env.setdefault("MIGROS_API_WRAPPER_USERAGENT", MIGROS_DEFAULT_HEADERS["User-Agent"])
    env.setdefault("MIGROS_API_WRAPPER_USECURL", "1")
    node_bin = _get_node_bin()
    try:
        result = subprocess.run(
            [node_bin, MIGROS_HELPER_PATH, payload],
            capture_output=True,
            text=True,
            env=env,
            timeout=45,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


def bulk_search_migros_via_node(names):
    data = run_node_migros_helper(names)
    if not data:
        return None
    token = data.get("token")
    if token:
        global MIGROS_API_TOKEN  # cache for later Python calls
        if not MIGROS_API_TOKEN:
            MIGROS_API_TOKEN = token
    return data.get("results") or []


@lru_cache(maxsize=128)
def search_migros_product(query: str):
    """Search Migros for a product; returns first product with price info."""
    if not query:
        return None
    token = fetch_migros_token()
    if not token:
        return None
    headers = dict(MIGROS_DEFAULT_HEADERS)
    headers["leshopch"] = token
    body = {"query": query, "language": "en", "regionId": 1000}
    try:
        resp = requests.post(
            "https://www.migros.ch/onesearch-oc-seaapi/public/v5/search",
            json=body,
            headers=headers,
            timeout=12,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        products = data.get("products") or []
        if not products:
            return None
        prod = products[0]
        price_info = _extract_price_fields(prod)
        energy = _extract_energy(prod)
        title = prod.get("displayName") or prod.get("name") or query
        return {
            "title": title,
            "price": price_info.get("price"),
            "currency": price_info.get("currency"),
            "energy_kcal": energy,
            "source": "migros",
            "raw": prod,
        }
    except Exception:
        return None


def enrich_plan_with_migros(plan_data):
    """Attach Migros pricing to plan_data if possible."""
    if not isinstance(plan_data, dict):
        return plan_data
    parsed = parse_plan_raw(plan_data.get("raw_json"))
    if not parsed:
        return plan_data

    grocery = parsed.get("grocery_list") or []
    if isinstance(grocery, dict):
        grocery = list(grocery.values())
    names = []
    if grocery:
        for g in grocery:
            if isinstance(g, dict) and g.get("item"):
                names.append(g.get("item"))
    # fallback: ingredient keys
    meal_plan = parsed.get("meal_plan")
    days = normalize_mealplan(meal_plan)
    for _, meals in days:
        for meal in meals.values():
            for ing_name in (meal.get("ingredients") or {}).keys():
                names.append(ing_name)

    unique_names = []
    seen = set()
    for n in names:
        key = str(n).strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique_names.append(n)
        if len(unique_names) >= 20:
            break  # cap to avoid long calls

    node_results = bulk_search_migros_via_node(unique_names)
    node_map = {}
    if node_results:
        for r in node_results:
            key = str(r.get("query", "")).lower()
            if key:
                node_map[key] = r

    priced_items = []
    total = 0.0
    currency = None
    for name in unique_names:
        key = str(name).strip().lower()
        info = None
        if node_map.get(key):
            r = node_map[key]
            info = {
                "title": r.get("title") or name,
                "price": r.get("price"),
                "currency": r.get("currency"),
                "energy_kcal": r.get("energy_kcal"),
                "source": "migros-node",
                "url": r.get("url"),
                "id": r.get("id"),
                "price_per_unit": r.get("pricePerUnit"),
                "price_per_unit_text": r.get("pricePerUnitText"),
            }
        if not info or info.get("price") is None:
            info = search_migros_product(str(name))
        if not info:
            continue
        priced_items.append({"query": name, **info})
        if info.get("price") is not None:
            total += float(info["price"])
            currency = info.get("currency") or currency

    if priced_items:
        plan_data["migros_pricing"] = {
            "items": priced_items,
            "estimated_total": round(total, 2),
            "currency": currency or "CHF",
            "note": "Estimated total from Migros search (first match per item).",
        }
    else:
        plan_data["migros_pricing"] = {"items": [], "note": "No Migros pricing found."}

    return plan_data


def build_user_context(email, profile, plan_data, fields):
    """Bundle profile + live form selections for the chat agent."""
    weight, budget, calories, activity, diet, location, goals, restrictions, budget_ignore, calories_ignore = fields
    context_lines = []
    if email:
        context_lines.append(f"Current email: {email}")
    if profile:
        context_lines.append("Saved profile available (already merged).")

    def fmt_val(label, value):
        if value is None or value == "":
            return f"{label}: Not specified"
        return f"{label}: {value}"

    context_lines.extend([
        fmt_val("Weight (kg)", weight),
        fmt_val("Weekly budget (CHF)", "Not specified" if ("ignore" in (budget_ignore or [])) else budget),
        fmt_val("Calories/day target", "Compute for me" if ("ignore" in (calories_ignore or [])) else calories),
        fmt_val("Activity", activity),
        fmt_val("Diet type", diet),
        fmt_val("Location", location),
        fmt_val("Goals", ", ".join(goals or [])),
        fmt_val("Restrictions", restrictions),
    ])

    # Include choice lists so the agent can guide users
    context_lines.append(f"Available activity options: {', '.join(ACTIVITY_OPTIONS)}")
    context_lines.append(f"Available diet options: {', '.join(DIET_OPTIONS)}")
    context_lines.append(f"Available goals (multi-select): {', '.join(GOALS_OPTIONS)}")

    plan_text = latest_plan_summary(plan_data)
    if plan_text:
        context_lines.append(plan_text)
    digest = plan_digest(plan_data)
    if digest:
        context_lines.append("Plan digest:")
        context_lines.append(digest)
    full_plan = plan_full_context(plan_data)
    if full_plan:
        context_lines.append("Plan details:")
        context_lines.append(full_plan)
    pricing = plan_data.get("migros_pricing") if isinstance(plan_data, dict) else None
    if pricing and pricing.get("items"):
        context_lines.append(
            f"Migros price estimate: {pricing.get('estimated_total')} {pricing.get('currency','CHF')} ({len(pricing.get('items',[]))} matched items)."
        )
        top_items = pricing.get("items", [])[:8]
        context_lines.append("Migros items:")
        for item in top_items:
            line = f"- {item.get('query')}: {item.get('price')} {item.get('currency','CHF')}"
            if item.get("url"):
                line += f" (url: {item.get('url')})"
            context_lines.append(line)
    elif pricing:
        context_lines.append("Migros price estimate unavailable for this plan.")

    return "\n".join(context_lines)


@lru_cache(maxsize=1)
def get_llama_agent():
    llm = LlamaOpenAI(
        model="gpt-4o-mini",
        api_key=api_key,
        base_url=base_url,
        default_headers=default_headers,
        temperature=0.3,
    )
    search_tool = FunctionTool.from_defaults(
        fn=web_search,
        name="web_search",
        description="Search the web and return a list of results with title, url, and snippet.",
    )
    return ReActAgent.from_tools(
        [search_tool],
        llm=llm,
        system_prompt=CHAT_SYSTEM_PROMPT,
        verbose=False,
    )


def render_chat(history):
    if not history:
        return html.Div("Ask me anything about meals, groceries, or nutrition.")
        blocks = []
    for msg in history:
        role = msg.get("role")
        content = msg.get("content")
        if not content:
            continue
        style = {
            "background": "#fff3cd" if role == "assistant" else "#e2e3e5",
            "padding": "10px",
            "borderRadius": "8px",
            "marginBottom": "8px",
            "border": "1px solid #dee2e6",
        }
        label = "AI" if role == "assistant" else "You"
        blocks.append(html.Div([html.Strong(f"{label}: "), html.Span(content)], style=style))
    return blocks


def chat_with_agent(user_message, history, plan_data, email, form_fields):
    agent = get_llama_agent()
    profile = get_user_profile(email) if email else None

    history_text = ""
    if history:
        # keep a generous window for continuity
        trimmed = history[-14:]  # up to 7 exchanges
        pairs = []
        for h in trimmed:
            role = h.get("role", "user")
            content = h.get("content", "")
            pairs.append(f"{role}: {content}")
        history_text = "\n".join(pairs)

    profile_text = ""
    if profile:
        profile_text = f"""
        Saved profile:
        - Name: {profile.get('name')}
        - Weight: {profile.get('weight')}
        - Activity: {profile.get('activity')}
        - Diet: {profile.get('diet')}
        - Goals: {', '.join(profile.get('goals') or [])}
        - Restrictions: {profile.get('restrictions')}
        - Location: {profile.get('location')}
        """

    form_context = build_user_context(email, profile, plan_data, form_fields)

    prompt = f"""
    {profile_text}
    {form_context}
    Ongoing conversation (chronological):
    {history_text}

    User question: {user_message}
    Remember: keep continuity with earlier answers, reuse user-provided details, use the plan digest above when talking about the meal plan, and cite sources with URLs. Use web_search tool for up-to-date or factual items.
    """

    response = agent.chat(prompt)
    return getattr(response, "response", str(response))


@app.callback(
    Output("plan_output", "children"),
    Output("latest_plan_data", "data"),
    Output("plan-data-store", "data"),
    Input("generate", "n_clicks"),
    State("body_weight", "value"),
    State("activity_hours", "value"),
    State("goals", "value"),
    State("budget", "value"),
    State("dayly_calories", "value"),
    State("restrictions", "value"),
    State("diet_type", "value"),
    State("location", "value"),
    State("budget_ignore", "value"),
    State("calories_ignore", "value"),
    State("user_email", "value"),
    State("user_name", "value"),
    State("avoid_ingredients", "value"),
    State("cravings", "value"),
    State("complexity", "value"),
    State("cuisines", "value"),
    State({"type": "portion", "day": ALL, "meal": ALL}, "value"),
)
def handle_generate_plan(n_clicks, weight, activity_hours, goals, budget, calories, restrictions, diet, location, budget_ignore, calories_ignore, email, name, avoid_ingredients, cravings, complexity, cuisines, portion_values):
    print(f"\n{'='*60}")
    print(f"🔥 GENERATE CALLBACK FIRED!")
    print(f"   n_clicks={n_clicks} (type: {type(n_clicks)})")
    print(f"   weight={weight}, activity_hours={activity_hours}")
    print(f"   goals={goals}")
    print(f"{'='*60}\n")
    
    if n_clicks is None:
        print("   ❌ PreventUpdate - n_clicks is None")
        raise PreventUpdate
    
    if (n_clicks or 0) == 0:
        print("   ❌ PreventUpdate - n_clicks is zero")
        raise PreventUpdate

    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    print(f"   ✅ Trigger: {trigger}")

    budget_value = budget if "ignore" not in (budget_ignore or []) else "Not specified"
    calorie_target = calories if "ignore" not in (calories_ignore or []) else 2400
    
    # Parse portions - portion_values is a list from pattern-matching callback
    # We need to reconstruct the portions dict with day and meal info
    # The order is: Mon-Breakfast, Tue-Breakfast, ..., Sun-Breakfast, Mon-Lunch, ..., Sun-Dinner
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    meals = ["breakfast", "lunch", "dinner"]
    
    print(f"   📊 Portion values received: {portion_values}")
    print(f"   📊 Length: {len(portion_values) if portion_values else 0}")
    
    portions = {}
    if portion_values and len(portion_values) == 21:  # 7 days × 3 meals
        idx = 0
        for meal in meals:
            for day in days:
                # Convert to int, default to 1 if None or empty
                val = portion_values[idx]
                portions[f"{day}_{meal}"] = int(val) if (val is not None and val != '') else 1
                idx += 1
    else:
        # Default: all meals = 1 portion
        for day in days:
            for meal in meals:
                portions[f"{day}_{meal}"] = 1
    
    print(f"   📊 Parsed portions: {portions}")

    # HuggingFace feature disabled - model not suitable for this task
    # if trigger == "generate_hf":
    #     ... (removed)

    plan_view, plan_raw = generate_plan(
        n_clicks,
        weight,
        activity_hours,
        goals or [],
        budget_value,
        calorie_target,
        restrictions or "None",
        diet,
        location or "Not specified",
        avoid_ingredients or "",
        cravings or "",
        complexity or "medium",
        cuisines or [],
        portions,
    )
    plan_data = {
        "raw_json": plan_raw,
        "provider": "openrouter",
        "generated_at": datetime.utcnow().isoformat(),
        "email": email,
        "name": name,
        "weight": weight,
        "calorie_target": calorie_target,
        "portions": portions,
    }
    plan_data = enrich_plan_with_migros(plan_data)
    return plan_view, plan_data, plan_data


@app.callback(
    Output("profile_dashboard", "children"),
    Output("profile_message", "children"),
    Output("main-tabs", "active_tab"),
    Input("latest_plan_data", "data"),
    Input("save_profile", "n_clicks"),
    Input("load_profile", "n_clicks"),
    State("user_email", "value"),
    State("user_name", "value"),
    State("body_weight", "value"),
    State("activity_hours", "value"),
    State("goals", "value"),
    State("budget", "value"),
    State("dayly_calories", "value"),
    State("restrictions", "value"),
    State("diet_type", "value"),
    State("location", "value"),
    State("avoid_ingredients", "value"),
    State("cravings", "value"),
    State("complexity", "value"),
    State("cuisines", "value"),
    State({"type": "portion", "day": ALL, "meal": ALL}, "value"),
    prevent_initial_call=True,
)
def persist_profile(plan_data, save_clicks, load_clicks, email, name, weight, activity_hours, goals, budget, calories, restrictions, diet, location, avoid_ingredients, cravings, complexity, cuisines, portion_values):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if not email:
        return no_update, html.Span("Add an email to save or load your profile.", style={"color": "#dc3545"}), no_update

    if trigger == "load_profile":
        profile = get_user_profile(email)
        if not profile:
            return render_profile_dashboard(None), html.Span("No saved profile found for that email yet.", style={"color": "#dc3545"}), no_update
        return render_profile_dashboard(profile), html.Span("Loaded saved profile.", style={"color": "#198754"}), no_update

    # Handle save_profile trigger
    last_plan = None
    if isinstance(plan_data, dict):
        last_plan = plan_data.get("raw_json")
    elif isinstance(plan_data, str):
        last_plan = plan_data
    
    # Parse portions from pattern-matching callback
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    meals = ["breakfast", "lunch", "dinner"]
    portions = {}
    if portion_values and len(portion_values) == 21:
        idx = 0
        for meal in meals:
            for day in days:
                # Handle 0 portions correctly - only default to 1 if None or empty string
                val = portion_values[idx]
                portions[f"{day}_{meal}"] = int(val) if (val is not None and val != '') else 1
                idx += 1

    save_user_profile(
        email=email,
        name=name,
        weight=weight,
        activity_hours=activity_hours,
        goals=goals or [],
        budget=budget,
        calories=calories,
        restrictions=restrictions,
        diet=diet,
        location=location,
        avoid_ingredients=avoid_ingredients,
        cravings=cravings,
        complexity=complexity,
        cuisines=cuisines or [],
        last_plan=last_plan,
        portions=portions if portions else None,
    )
    profile = get_user_profile(email)
    msg = "Profile auto-saved with your latest plan." if trigger == "latest_plan_data" else "Profile saved."
    
    # Switch to Recipes tab if save_profile button was clicked
    if trigger == "save_profile":
        return render_profile_dashboard(profile), html.Span(msg, style={"color": "#198754"}), "recipes"
    else:
        return render_profile_dashboard(profile), html.Span(msg, style={"color": "#198754"}), no_update


# -------------------- CLEAR USER DATA (GDPR COMPLIANCE) --------------------

@app.callback(
    Output("clear_data_message", "children"),
    Input("clear_data", "n_clicks"),
    State("user_email", "value"),
    prevent_initial_call=True,
)
def handle_clear_data(n_clicks, email):
    """Handle GDPR data deletion request."""
    if not n_clicks or n_clicks == 0:
        raise PreventUpdate
    
    if not email:
        return dbc.Alert(
            "Please enter your email address first to clear your data.",
            color="warning",
            style={"marginTop": "10px"}
        )
    
    # Clear the data
    success = clear_user_data(email)
    
    if success:
        return dbc.Alert(
            "✅ Your data has been successfully deleted from our database (GDPR compliant).",
            color="success",
            style={"marginTop": "10px"}
        )
    else:
        return dbc.Alert(
            "❌ An error occurred while clearing your data. Please try again or contact support.",
            color="danger",
            style={"marginTop": "10px"}
        )


@app.callback(
    Output("user_name", "value"),
    Output("body_weight", "value"),
    Output("activity_hours", "value"),
    Output("goals", "value"),
    Output("budget", "value"),
    Output("dayly_calories", "value"),
    Output("restrictions", "value"),
    Output("diet_type", "value"),
    Output("location", "value"),
    Output("avoid_ingredients", "value"),
    Output("cravings", "value"),
    Output("complexity", "value"),
    Output("cuisines", "value"),
    Output({"type": "portion", "day": ALL, "meal": ALL}, "value"),
    Input("load_profile", "n_clicks"),
    State("user_email", "value"),
    prevent_initial_call=True,
)
def populate_profile_fields(n_clicks, email):
    if not n_clicks or not email:
        raise PreventUpdate

    profile = get_user_profile(email)
    if not profile:
        return (no_update,) * 14  # 13 fields + portions list

    # Build portions list in the correct order
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    meals = ["breakfast", "lunch", "dinner"]
    portions_dict = profile.get("portions") or {}
    portion_values = []
    
    for meal in meals:
        for day in days:
            key = f"{day}_{meal}"
            portion_values.append(portions_dict.get(key, 1))

    return (
        profile.get("name"),
        profile.get("weight"),
        profile.get("activity"),
        profile.get("goals"),
        profile.get("budget"),
        profile.get("calories"),
        profile.get("restrictions"),
        profile.get("diet"),
        profile.get("location"),
        profile.get("avoid_ingredients"),
        profile.get("cravings"),
        profile.get("complexity"),
        profile.get("cuisines"),
        portion_values,
    )


# Chat callback disabled - now opens premium modal instead
@app.callback(
    Output("premium-modal", "is_open", allow_duplicate=True),
    Input("send_chat", "n_clicks"),
    prevent_initial_call=True
)
def open_premium_modal_from_chat(n_clicks):
    """Open premium modal when Send button in chat is clicked."""
    if n_clicks and n_clicks > 0:
        return True
    raise PreventUpdate

# Original chat callback disabled - chat is now a premium feature
# @app.callback(
#     Output("chat_output", "children"),
#     Output("chat_history", "data"),
#     Input("send_chat", "n_clicks"),
#     State("chat_input", "value"),
#     State("chat_history", "data"),
#     State("latest_plan_data", "data"),
#     State("user_email", "value"),
#     State("body_weight", "value"),
#     State("budget", "value"),
#     State("dayly_calories", "value"),
#     State("activity_hours", "value"),
#     State("diet_type", "value"),
#     State("location", "value"),
#     State("goals", "value"),
#     State("restrictions", "value"),
#     State("budget_ignore", "value"),
#     State("calories_ignore", "value"),
#     prevent_initial_call=True,
# )
# def handle_chat(n_clicks, user_message, history, plan_data, email, weight, budget, calories, activity_hours, diet, location, goals, restrictions, budget_ignore, calories_ignore):
#     if not n_clicks or not user_message:
#         raise PreventUpdate
#     ... (disabled - chat is now premium)


# -------------------- PROFILE SUMMARY FOR RECIPES TAB --------------------

@app.callback(
    [Output("profile-summary-recipes", "children"),
     Output("profile-info-message-recipes", "children")],
    Input("user_email", "value"),
    Input("user_name", "value"),
    Input("body_weight", "value"),
    Input("budget", "value"),
    Input("budget_ignore", "value"),
    Input("dayly_calories", "value"),
    Input("calories_ignore", "value"),
    Input("activity_hours", "value"),
    Input("diet_type", "value"),
    Input("location", "value"),
    Input("goals", "value"),
    Input("restrictions", "value"),
    Input("avoid_ingredients", "value"),
    Input("cravings", "value"),
    Input("complexity", "value"),
    Input("cuisines", "value"),
    State({"type": "portion", "day": ALL, "meal": ALL}, "value"),
)
def render_profile_summary_recipes(email, name, weight, budget, budget_ignore, calories, calories_ignore, 
                                   activity, diet, location, goals, restrictions, avoid_ingredients, 
                                   cravings, complexity, cuisines, portion_values):
    """Render a summary of the current profile settings for the Recipes tab and info message."""
    items = []
    
    if name:
        items.append(("Name", name))
    if email:
        items.append(("Email", email))
    if weight:
        items.append(("Weight", f"{weight} kg"))
    if budget and "ignore" not in (budget_ignore or []):
        items.append(("Weekly Budget", f"{budget} CHF"))
    if calories and "ignore" not in (calories_ignore or []):
        items.append(("Daily Calories", f"{calories} kcal"))
    if activity:
        items.append(("Physical Activity", f"{activity} hrs/week"))
    if diet:
        items.append(("Diet Type", diet))
    if location:
        items.append(("Location", location))
    if goals:
        items.append(("Goals", ", ".join(goals)))
    if restrictions:
        items.append(("Restrictions", restrictions))
    if avoid_ingredients:
        items.append(("Avoid Ingredients", avoid_ingredients))
    if cravings:
        items.append(("Cravings", cravings))
    if complexity:
        complexity_labels = {
            "quick": "Quick (<20 min)",
            "medium": "Medium (20-40 min)",
            "elaborate": "Elaborate (>40 min)",
            "mixed": "Mixed (variety)"
        }
        items.append(("Complexity", complexity_labels.get(complexity, complexity)))
    if cuisines:
        items.append(("Preferred Cuisines", ", ".join(cuisines)))
    
    # Check if custom portions are set
    if portion_values:
        has_custom_portions = any(v and int(v) != 1 for v in portion_values if v is not None and v != '')
        if has_custom_portions:
            items.append(("Portions", "Custom per-meal settings"))
    
    # Check if profile is complete enough (at least email is required)
    is_profile_complete = bool(email and email.strip())
    
    # Info message
    if not is_profile_complete:
        info_message = dbc.Alert(
            [
                html.Strong("⚠️ Profile Required: "),
                "Please fill out your profile information in the ",
                html.Strong("User Info"),
                " tab (at minimum, enter your email) or connect to a saved profile before generating recipes."
            ],
            color="warning",
            style={"marginBottom": "20px"}
        )
    else:
        info_message = html.Div()  # Empty div when profile is complete
    
    if not items:
        summary = html.Div([
            html.H4("📋 Profile Summary", style={"marginBottom": "15px"}),
            html.P("Fill in your profile information in the 'User Info' tab to see your summary here.", 
                   style={"color": "#6c757d", "fontStyle": "italic", "padding": "20px", "textAlign": "center"})
        ])
        return summary, info_message
    
    rows = []
    for label, value in items:
        rows.append(
            html.Div([
                html.Div(label, style={"fontWeight": "bold", "width": "30%", "color": "#495057"}),
                html.Div(str(value), style={"width": "70%", "color": "#212529"}),
            ], style={"display": "flex", "marginBottom": "8px", "padding": "8px", "backgroundColor": "#f8f9fa", "borderRadius": "4px"})
        )
    
    summary = html.Div([
        html.H4("📋 Profile Summary", style={"marginBottom": "15px", "color": "#2c3e50"}),
        html.Div(rows, style={
            "padding": "15px", 
            "border": "1px solid #dee2e6", 
            "borderRadius": "8px", 
            "backgroundColor": "#fff",
            "marginBottom": "20px"
        })
    ])
    
    return summary, info_message


# -------------------- PREMIUM MODAL CALLBACKS --------------------

# Simple callback for premium modal - handles all premium buttons
@app.callback(
    Output("premium-modal", "is_open"),
    Input("open-premium-modal", "n_clicks"),
    Input("close-premium-modal", "n_clicks"),
    prevent_initial_call=True
)
def toggle_premium_modal(open_clicks, close_clicks):
    """Open/close the premium modal."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]["prop_id"]
    
    # Close modal if close button is clicked
    if "close-premium-modal" in trigger_id:
        return False
    
    # Open modal for "Go Premium" button
    if "open-premium-modal" in trigger_id:
        if open_clicks and open_clicks > 0:
            return True
    
    raise PreventUpdate


# Callback for Order Groceries button (only exists after grocery list is generated)
@app.callback(
    Output("premium-modal", "is_open", allow_duplicate=True),
    Input("order-groceries-button", "n_clicks"),
    prevent_initial_call=True
)
def open_premium_modal_from_order(n_clicks):
    """Open premium modal when Order Groceries button is clicked."""
    if n_clicks and n_clicks > 0:
        return True
    raise PreventUpdate


# Callback for Save Recipe buttons (only exists after recipes are generated)
@app.callback(
    Output("premium-modal", "is_open", allow_duplicate=True),
    Input({"type": "like-recipe", "day": ALL, "meal": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def open_premium_modal_from_like(like_clicks):
    """Open premium modal when Save Recipe button is clicked."""
    if not like_clicks:
        raise PreventUpdate
    
    # Check if any like button was actually clicked (n_clicks > 0)
    if any(clicks and clicks > 0 for clicks in like_clicks if clicks is not None):
        return True
    
    raise PreventUpdate


# Test recipes callback removed - button no longer in UI
# @app.callback(
#     Output("test_recipes_output", "children"),
#     Input("test_recipes", "n_clicks")
# )
# def display_test_recipes(n_clicks):
#     if n_clicks == 0:
#         return ""
#     ...


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


# -------------------- GROCERY LIST EDITING CALLBACKS --------------------

@app.callback(
    Output("grocery-list-container", "children"),
    Input("grocery-list-store", "data"),
)
def render_grocery_list(grocery_data):
    """Render the editable grocery list with remove buttons in the grocery list tab."""
    if not grocery_data:
        return html.Div([
            html.H3("🛒 Grocery List", style={"marginBottom": "20px"}),
            html.P("No items in grocery list. Generate a meal plan to see your grocery list here.", 
                   style={"color": "#999", "fontStyle": "italic", "padding": "20px", "textAlign": "center"})
        ])
    
    # Group by category
    categorized = {}
    for item in grocery_data:
        if isinstance(item, dict) and item.get("item"):
            cat = item.get("category", "Other")
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(item)
    
    # Render items by category
    category_sections = []
    for category in sorted(categorized.keys()):
        items = categorized[category]
        item_elements = []
        
        for idx, item in enumerate(items):
            item_id = f"{category}_{idx}_{item['item'].replace(' ', '_')}"
            item_elements.append(
                html.Div([
                    html.Div([
                        html.Strong(item['item'], style={"fontSize": "14px"}),
                        html.Span(f" — {item['quantity']}", style={"fontSize": "13px", "color": "#666", "marginLeft": "8px"}),
                    ], style={"flex": "1"}),
                    dbc.Button(
                        "✕",
                        id={"type": "remove-grocery", "index": item_id},
                        color="danger",
                        size="sm",
                        outline=True,
                        style={"padding": "2px 8px", "fontSize": "12px"}
                    )
                ], style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "padding": "8px 12px",
                    "marginBottom": "5px",
                    "backgroundColor": "white",
                    "border": "1px solid #ddd",
                    "borderRadius": "4px"
                })
            )
        
        category_sections.append(
            html.Div([
                html.H6(category, style={"color": "#666", "fontSize": "12px", "textTransform": "uppercase", "marginBottom": "8px", "marginTop": "15px"}),
                html.Div(item_elements)
            ])
        )
    
    # Add Custom Item section
    add_item_section = dbc.Card([
        dbc.CardBody([
            html.H5("Add Custom Item", style={"marginBottom": "15px"}),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Item Name"),
                    dbc.Input(id="new-grocery-item", placeholder="e.g., Chocolate bars", type="text")
                ], width=4),
                dbc.Col([
                    dbc.Label("Quantity"),
                    dbc.Input(id="new-grocery-quantity", placeholder="e.g., 3 bars", type="text")
                ], width=3),
                dbc.Col([
                    dbc.Label("Category"),
                    dbc.Select(
                        id="new-grocery-category",
                        options=[
                            {"label": "Produce", "value": "Produce"},
                            {"label": "Dairy", "value": "Dairy"},
                            {"label": "Meat", "value": "Meat"},
                            {"label": "Pantry", "value": "Pantry"},
                            {"label": "Bakery", "value": "Bakery"},
                            {"label": "Frozen", "value": "Frozen"},
                            {"label": "Beverages", "value": "Beverages"},
                            {"label": "Snacks", "value": "Snacks"},
                            {"label": "Spices", "value": "Spices"},
                            {"label": "Other", "value": "Other"},
                        ],
                        value="Snacks"
                    )
                ], width=3),
                dbc.Col([
                    dbc.Label(" ", style={"display": "block"}),
                    dbc.Button("Add Item", id="add-grocery-item", color="success", style={"width": "100%"})
                ], width=2),
            ])
        ])
    ], style={"marginTop": "30px", "marginBottom": "20px", "backgroundColor": "#f8f9fa"})
    
    # Order button (premium feature)
    order_button = dbc.Button(
        "🛒 Order Groceries",
        id="order-groceries-button",
        color="success",
        size="lg",
        style={
            "width": "100%",
            "marginTop": "30px",
            "padding": "15px",
            "fontSize": "18px",
            "fontWeight": "bold"
        }
    )
    
    return html.Div([
        html.H3("🛒 Grocery List", style={"marginBottom": "20px"}),
        html.Div(category_sections),
        add_item_section,
        order_button
    ])


@app.callback(
    Output("grocery-list-store", "data", allow_duplicate=True),
    Input("add-grocery-item", "n_clicks"),
    State("new-grocery-item", "value"),
    State("new-grocery-quantity", "value"),
    State("new-grocery-category", "value"),
    State("grocery-list-store", "data"),
    prevent_initial_call=True
)
def add_grocery_item(n_clicks, new_item, new_qty, new_cat, grocery_data):
    """Add a new item to the grocery list."""
    if not n_clicks or not new_item or not new_qty:
        raise PreventUpdate
    
    if not grocery_data:
        grocery_data = []
    
    grocery_data.append({
        "item": new_item,
        "quantity": new_qty,
        "category": new_cat or "Other"
    })
    
    print(f"✅ Added item to grocery list: {new_item} - {new_qty}")
    return grocery_data


@app.callback(
    Output("grocery-list-store", "data", allow_duplicate=True),
    Input({"type": "remove-grocery", "index": ALL}, "n_clicks"),
    State("grocery-list-store", "data"),
    prevent_initial_call=True
)
def remove_grocery_item(remove_clicks, grocery_data):
    """Remove an item from the grocery list."""
    ctx = callback_context
    if not ctx.triggered or not grocery_data:
        raise PreventUpdate
    
    # Find which button was clicked
    triggered_id = ctx.triggered[0]["prop_id"]
    if "remove-grocery" not in triggered_id:
        raise PreventUpdate
    
    # Extract the item identifier from the button ID
    import json as json_lib
    button_id = json_lib.loads(triggered_id.split(".")[0])
    item_id = button_id["index"]
    
    # Parse the item_id to get category and item name
    parts = item_id.split("_", 2)
    if len(parts) >= 3:
        category = parts[0]
        item_name = parts[2].replace("_", " ")
        
        # Remove the item from grocery_data
        grocery_data = [
            item for item in grocery_data
            if not (item.get("category") == category and item.get("item") == item_name)
        ]
    
    return grocery_data


@app.callback(
    Output("new-grocery-item", "value"),
    Output("new-grocery-quantity", "value"),
    Input("add-grocery-item", "n_clicks"),
    prevent_initial_call=True
)
def clear_add_item_inputs(n_clicks):
    """Clear the add item inputs after adding."""
    return "", ""


# -------------------- PDF GENERATION --------------------

def generate_meal_plan_pdf(plan_data, grocery_list):
    """Generate a PDF with calendar view of meal plan and grocery list."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12,
        spaceBefore=20
    )
    
    # Title
    story.append(Paragraph("🍽️ CULINAIRE - Weekly Meal Plan", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Parse the plan
    try:
        if isinstance(plan_data, str):
            plan = json.loads(plan_data)
        elif isinstance(plan_data, dict):
            raw = plan_data.get("raw_json")
            if raw:
                plan = json.loads(raw) if isinstance(raw, str) else raw
            else:
                plan = plan_data
        else:
            plan = {}
        
        meal_plan = plan.get("meal_plan", [])
        portions = plan_data.get("portions", {}) if isinstance(plan_data, dict) else {}
        
        # Calendar view - 7 days
        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days_data = normalize_mealplan(meal_plan)
        
        for day_name, meals in days_data:
            story.append(Paragraph(f"<b>{day_name}</b>", heading_style))
            
            # Create table for the day's meals
            day_table_data = [["Meal", "Recipe", "Calories"]]
            
            for meal_type in ["breakfast", "lunch", "dinner"]:
                meal = meals.get(meal_type, {})
                portion_key = f"{day_name}_{meal_type}"
                portion_count = portions.get(portion_key, 1)
                
                if portion_count == 0 or meal.get('meal', '').lower() == 'skipped':
                    day_table_data.append([
                        meal_type.capitalize(),
                        "No meal planned",
                        "0 kcal"
                    ])
                else:
                    meal_name = meal.get('meal', meal_type.capitalize())
                    calories = meal.get('calories', '?')
                    portion_text = f" ({portion_count}p)" if portion_count > 1 else ""
                    day_table_data.append([
                        meal_type.capitalize(),
                        f"{meal_name}{portion_text}",
                        f"{calories} kcal"
                    ])
            
            day_table = Table(day_table_data, colWidths=[1.5*inch, 4*inch, 1.5*inch])
            day_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            story.append(day_table)
            story.append(Spacer(1, 0.2*inch))
        
        # Page break before grocery list
        story.append(PageBreak())
        
        # Grocery List
        story.append(Paragraph("🛒 Grocery List", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        if grocery_list:
            # Group by category
            categorized = {}
            for item in grocery_list:
                if isinstance(item, dict) and item.get("item"):
                    cat = item.get("category", "Other")
                    if cat not in categorized:
                        categorized[cat] = []
                    categorized[cat].append(item)
            
            for category in sorted(categorized.keys()):
                story.append(Paragraph(f"<b>{category}</b>", heading_style))
                items = categorized[category]
                
                grocery_table_data = []
                for item in items:
                    grocery_table_data.append([
                        f"• {item['item']}",
                        item.get('quantity', '')
                    ])
                
                grocery_table = Table(grocery_table_data, colWidths=[4.5*inch, 2.5*inch])
                grocery_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(grocery_table)
                story.append(Spacer(1, 0.15*inch))
        
    except Exception as e:
        story.append(Paragraph(f"Error generating PDF: {str(e)}", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


@app.callback(
    Output("download-pdf", "data"),
    Input("download-pdf-button", "n_clicks"),
    State("plan-data-store", "data"),
    State("grocery-list-store", "data"),
    prevent_initial_call=True
)
def download_pdf(n_clicks, plan_data, grocery_list):
    """Generate and download the PDF."""
    if not n_clicks or not plan_data:
        raise PreventUpdate
    
    print(f"📥 PDF Download - Grocery list items: {len(grocery_list) if grocery_list else 0}")
    print(f"📥 PDF Download - Grocery list: {grocery_list}")
    
    try:
        pdf_buffer = generate_meal_plan_pdf(plan_data, grocery_list)
        return dcc.send_bytes(pdf_buffer.getvalue(), "CULINAIRE_Meal_Plan.pdf")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        raise PreventUpdate

# -------------------- MAIN --------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)