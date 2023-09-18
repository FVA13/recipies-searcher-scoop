import os
import pandas as pd
from PIL import Image
import streamlit as st
from matcher import get_matching_recipies


st.set_page_config(
    page_title="Scoop - AI Recipes for everyone",
    page_icon="🥘",
    layout="centered",
    initial_sidebar_state="auto",
)

# Add Link to GitHub repo
"""
    [![Repo](https://badgen.net/badge/icon/GitHub?icon=github&label)](https://github.com/FVA13/recipies-searcher-scoop)
"""
st.markdown("<br>", unsafe_allow_html=True)

# logo_path = os.path.abspath("logo.svg")
path = os.path.dirname(__file__)
logo_path = path+'/logo.svg'
with open(logo_path, "r") as f:
    svg_text = f.read()

modified_svg_text = svg_text.replace("<svg", "<svg width='200' height='200'")

# sentence = f"<div style='display: flex; align-items: flex-end;'> \
#                 <h1 style='margin-right: 0; padding-right: 0;'>{modified_svg_text}</strong></h1> \
#                 <strong><h2 style='margin-bottom: 55px;;'>- AI рецепты для каждого!</h2> \
#             </div>"

# Display the sentence using markdown
st.markdown(modified_svg_text, unsafe_allow_html=True)
# # Add the title
st.markdown("# AI рецепты для каждого!")


def main():
    products_include = st.text_input(
        "Введите пожалуйста ингредиенты"
    )  # Enter some ingredients
    description_input = st.text_input(
        # "Describe what dish you would want to cook | your mood | anything you want to \N{grinning face}"
        "Опишите что вы хотите приготовить | ваше настроение | что-угодно \N{grinning face}"
    )
    products_exclude = st.text_input(
        "Введите пожалуйста ингредиенты, которые вы хотите исключить"
    )
    do_search = st.button("Получить рецепты! \U0001F929")  # Get Recipies!

    if do_search:
        st.spinner()
        with st.spinner(text="In progress"):
            search_result = get_matching_recipies(
                products_include=products_include,
                products_exclude=products_exclude,
                text_description=description_input,
            )
            if type(search_result) is pd.DataFrame:
                st.table(search_result)  # Display the table
                st.success("Готово \N{hugging face}")
            else:
                st.success(
                    """Ничего не найдено \U0001F641
                    \n Попробуйте указать другие ингредиенты \U0001F47E"""
                )


if __name__ == "__main__":
    main()
