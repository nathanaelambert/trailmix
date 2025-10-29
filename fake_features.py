import streamlit as st
## onboarding questionnaire

## recipe generation button 
print("fake recipe:\n- ingredient 1 (200g)\n- ingedient 2(100g)")
# display "order"

import streamlit as st

st.title("TRAILMIX")
st.write("##insert onboarding questionnaire")

# Session state controls button visibility
if 'recipe_shown' not in st.session_state:
    st.session_state.recipe_shown = False

def show_recipe():
    st.session_state.recipe_shown = True

# Main button
if st.button("Generate Recipe", on_click=show_recipe):
    pass  # The callback updates session state

# Show recipe and extra buttons only after main button clicked
if st.session_state.recipe_shown:
    st.subheader("Your Recipe")
    st.write("Example Recipe: Spaghetti with Tomato Sauce.\nIngredients: Spaghetti, tomatoes, garlic, olive oil, salt.\nInstructions: Boil pasta, cook sauce, mix together.")

    # Reveal other buttons
    st.button("Order missing ingredients")
    st.button("Find place to buy missing ingredient")
