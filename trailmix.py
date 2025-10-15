
import streamlit as st
import openai
import json
import os
import re

# ---------------------------- PAGE ----------------------------
st.set_page_config(page_title="TRAILMIX", page_icon="🥗", layout="centered")
st.title("🥗 TRAILMIX")
st.caption("*Your AI meal planner – plan smart, eat better*")

# ---------------------------- USER INPUT ----------------------------
st.header("Tell us about you")
body_weight = st.slider("Body weight (kg):", 20.0, 200.0, 70.0, 0.5)
activity_level = st.selectbox("Activity level:", [
    "Sedentary","Lightly active","Moderately active","Very active","Extra active"])
goals = st.multiselect("Your goals:", [
    "Lose weight","Build muscle","Maintain muscle mass",
    "Reduce meat consumption","Discover new recipes","Reduce processed food consumption"])
budget = st.number_input("Weekly food budget (CHF):", 20, 500, 80, 5)
daily_calories = st.number_input("Target daily calories (kcal):", 1200, 4500, 2400, 100)
dietary_restrictions = st.text_area("Any dietary restrictions or allergies:")
diet_type = st.selectbox("Diet type:", [
    "Omnivore","Vegetarian","Keto","Vegan","Pescatarian","Gluten free","Other"])
location = st.text_input("Location (city or region):", "Lausanne")

user_data = dict(
    body_weight=body_weight, activity_level=activity_level, goals=goals,
    budget=budget, daily_calories=daily_calories,
    dietary_restrictions=dietary_restrictions, diet_type=diet_type, location=location
)

# ---------------------------- PROMPT ----------------------------
SYSTEM_PROMPT = """
You are TRAILMIX, a precise and practical AI meal planner.

Your output must be VALID JSON ONLY.

Include:
- A 7-day meal plan with Breakfast, Lunch, and Dinner.
- Each meal includes: name, ingredients (as dict), calories, and a short recipe (2–3 sentences).
- Total calories per day should match the user's target within ±5%.
- A grocery_list section that combines all ingredients by item name, summed quantities, and category.
- A summary with total weekly calories and estimated cost.

Example structure:
{
  "meal_plan": {
    "day_1": {
      "breakfast": {"meal": "...", "ingredients": {...}, "calories": 500, "recipe": "..."},
      "lunch": {...},
      "dinner": {...}
    },
    ...
  },
  "grocery_list": [
    {"item": "chicken breast", "quantity": "1.2 kg", "category": "protein"},
    ...
  ],
  "summary": {
    "average_daily_calories": 2400,
    "estimated_weekly_cost": "80 CHF",
    "nutrition_focus": "high protein, balanced carbs"
  }
}
"""

openai.api_key = 

# ---------------------------- HELPERS ----------------------------
def numeric_scale(qty: str, scale: float) -> str:
    nums = re.findall(r"[0-9]+\.?[0-9]*", qty)
    if not nums:
        return qty
    for num in nums:
        new_val = round(float(num) * scale, 1)
        qty = qty.replace(num, str(new_val), 1)
    return qty

def rescale_day(day_dict, target):
    meals = ["breakfast","lunch","dinner"]
    total = sum(day_dict[m].get("calories", 0) for m in meals if m in day_dict)
    if total <= 0:
        return day_dict
    scale = target / total
    for m in meals:
        if m not in day_dict:
            continue
        meal = day_dict[m]
        meal["calories"] = round(meal.get("calories", 0) * scale)
        ings = meal.get("ingredients", {})
        if isinstance(ings, dict):
            for k, v in ings.items():
                ings[k] = numeric_scale(v, scale)
    return day_dict

def normalize_mealplan(mp):
    if isinstance(mp, list):
        return [(d.get("day", f"Day {i+1}"), d.get("meals", d)) for i, d in enumerate(mp)]
    if isinstance(mp, dict):
        return [(k.replace("_", " ").title(), v) for k, v in mp.items()]
    return []

# ---------------------------- MAIN ----------------------------
if st.button("Generate My Weekly Plan 🧑‍🍳"):
    with st.spinner("Creating your personalized plan..."):
        user_prompt = f"""
        Create a 7-day meal plan for:
        - Body weight: {user_data['body_weight']} kg
        - Activity: {user_data['activity_level']}
        - Goals: {', '.join(user_data['goals']) or 'None'}
        - Diet: {user_data['diet_type']}
        - Restrictions: {user_data['dietary_restrictions'] or 'None'}
        - Target calories: {user_data['daily_calories']} kcal/day
        - Budget: {user_data['budget']} CHF
        - Location: {user_data['location']}
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.6,
            )

            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
            plan = json.loads(raw)

            target = user_data["daily_calories"]
            days = normalize_mealplan(plan.get("meal_plan"))

            # ✅ Weekly plan
            st.success("✅ Your personalized plan is ready!")
            st.header("Your Weekly Meal Plan 🍲")

            for day_name, day_dict in days:
                day_dict = rescale_day(day_dict, target)
                total = sum(day_dict[m].get("calories", 0) for m in ["breakfast","lunch","dinner"] if m in day_dict)
                st.subheader(day_name)
                st.caption(f"Total: {round(total)} kcal (Target: {target})")

                for m in ["breakfast","lunch","dinner"]:
                    if m not in day_dict:
                        continue
                    meal = day_dict[m]
                    name = meal.get("meal") or meal.get("name") or m
                    st.markdown(f"**{m.capitalize()} – {name}**")

                    ings = meal.get("ingredients", {})
                    if isinstance(ings, dict):
                        for ing_name, qty in ings.items():
                            st.write(f"- {ing_name}: {qty}")
                    elif isinstance(ings, list):
                        for ing in ings:
                            st.write(f"- {ing.get('item','?')}: {ing.get('quantity','?')}")
                    st.caption(f"~{meal.get('calories','?')} kcal")
                    if "recipe" in meal:
                        st.markdown(f"🧑‍🍳 *Recipe:* {meal['recipe']}")
                st.markdown("---")

            # ✅ Grocery List
            grocery = plan.get("grocery_list", [])
            if grocery:
                st.header("🛒 Grocery List")
                for g in grocery:
                    item = g.get("item", "?")
                    qty = g.get("quantity", "?")
                    cat = g.get("category", "?")
                    st.write(f"- **{item}** ({cat}) — {qty}")

            # ✅ Summary
            st.header("📋 Summary")
            summary = plan.get("summary", {})
            st.write(f"**Average daily calories:** {summary.get('average_daily_calories', '?')} kcal")
            st.write(f"**Estimated weekly cost:** {summary.get('estimated_weekly_cost', '?')}")
            st.write(f"**Nutrition focus:** {summary.get('nutrition_focus', '?')}")

        except Exception as e:
            st.error(f"⚠️ Error: {type(e).__name__} – {e}")
