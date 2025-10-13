import streamlit as st

st.write("""
# TRAILMIX
*Meet your AI meal planner*
""")

# Onboarding questionnaire

body_weight = st.slider("Enter your body weight (kg):", 
    min_value=20.0, 
    max_value=200.0, 
    step=0.5,
    value=70.0
)

activity_level = st.selectbox("Select your activity level:",[
    "Sedentary", 
    "Lightly active", 
    "Moderately active", 
    "Very active", 
    "Extra active"
])

goals = st.multiselect("Select your goals:", [
    "Lose weight",
    "Build muscle",
    "Maintain muscle mass",
    "Reduce meat consumption",
    "Discover new recipes",
    "Reduce my proccessed food consumption",
])

dietary_restrictions = st.text_area("List any dietary restrictions & allergies:")

diet_type = st.selectbox("Select your diet type:", [
    "Omnivore", 
    "Vegetarian", 
    "Keto", 
    "Vegan", 
    "Pescatarian", 
    "Gluten free",
    "Other"
])


# Save data as variables
user_data = {
    "body_weight": body_weight,
    "activity_level": activity_level,
    "goals": goals,
    "dietary_restrictions": dietary_restrictions,
    "diet_type": diet_type,
}

st.write("Your entered data:")
st.write(user_data)
