import streamlit as st
import pathlib
from bs4 import BeautifulSoup
import logging
import shutil


def inject_google_analytics():
    GA_stream_id = 12364028308
    GA_measurement_id = "G-ETT9HS0JXE"
    GA_JS = """
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-ETT9HS0JXE"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-ETT9HS0JXE');
    </script>
    """

    index_path = pathlib.Path(st.__file__).parent / "static" / "index.html"
    soup = BeautifulSoup(index_path.read_text(), features="html.parser")
    if not soup.find(id=GA_measurement_id):
        bck_index = index_path.with_suffix('.bck')
        if bck_index.exists():
            shutil.copy(bck_index, index_path)
        else:
            shutil.copy(index_path, bck_index)
        html = str(soup)
        new_html = html.replace('<head>', '<head>\n' + GA_JS)
        index_path.write_text(new_html)













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
