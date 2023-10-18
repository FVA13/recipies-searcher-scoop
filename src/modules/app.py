import os
import ast
import pandas as pd
from PIL import Image
import streamlit as st
from matcher import get_matching_recipes
from models import get_photo, resize_image_by_height


def product_card(
    name,
    description,
    ingredients,
    instructions,
    recycling_recommendations=None,
    substitutes=None,
    photo_url=None,
):
    # Display the product name
    st.header(name)

    # Display the product description
    st.subheader("Описание")
    st.write(description)

    # Display the product description
    if ingredients:
        st.subheader("Ингредиенты")
        ingredients_dict = ast.literal_eval(ingredients)
        ingredients = ", ".join(
            [
                f"{key}: {value}" if value is not None else f"{key}"
                for key, value in ingredients_dict.items()
            ]
        )
        st.write(ingredients)

    # Display the instructions to cook the product
    st.subheader("Инструкции")
    if instructions:
        for instruction in instructions:
            st.write(instruction[0], instruction[1])

    # Display products substitutes if there are any
    if substitutes:
        for substitute in substitutes:
            st.subheader("Продукты заменители")
            st.write("Продукты, которыми можно заменить некоторые продукты из рецепта")
            st.write(substitute + ": " + ", ".join(substitutes[substitute]))

    # Display utilization recommendations if there are any
    if recycling_recommendations:
        for recycling_recommendation in recycling_recommendations:
            st.subheader("Рекомендции по переработке")
            st.write(
                recycling_recommendation
                + ": "
                + recycling_recommendations[recycling_recommendation]
            )

    # Display the product photo
    if photo_url:
        st.image(
            # "https://images.unsplash.com/photo-1571091718767-18b5b1457add?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8OXx8YnVyZ2VyfGVufDB8fDB8fHww&w=1000&q=80",
            photo_url,
            # zcaption=name,
            use_column_width=True,
        )
    else:
        try:
            ingredients_names = ", ".join(ingredients_dict.keys())
            st.image(
                get_photo(ingredients_names),
                use_column_width=True,
            )
        except:
            pass


def increment_counter():
    st.session_state.count += 1


st.set_page_config(
    page_title="Scoop - AI Recipes for everyone",
    page_icon="🥘",
    layout="centered",
    initial_sidebar_state="auto",
)

# Add Link to GitHub repo
# """
#     [![Repo](https://badgen.net/badge/icon/GitHub?icon=github&label)](https://github.com/FVA13/recipes-searcher-scoop)
# """
# st.markdown("<br>", unsafe_allow_html=True)

# logo_path = os.path.abspath("logo.svg")
path = os.path.dirname(__file__)
logo_path = path + "/logo.svg"
with open(logo_path, "r") as f:
    svg_text = f.read()

modified_svg_text = svg_text.replace("<svg", "<svg width='100' height='100'")

# sentence = f"<div style='display: flex; align-items: flex-end;'> \
#                 <h1 style='margin-right: 0; padding-right: 0;'>{modified_svg_text}</strong></h1> \
#                 <strong><h2 style='margin-bottom: 55px;;'>- AI рецепты для каждого!</h2> \
#             </div>"

# Display the sentence using markdown
st.markdown(modified_svg_text, unsafe_allow_html=True)
# # Add the title
st.markdown("# AI рецепты для каждого!")


# indx = 0  # Initialize indx outside the main() function
def main():
    # global indx
    products_include = st.text_input(
        "Введите пожалуйста ингредиенты"
    )  # Enter some ingredients
    products_exclude = st.text_input(
        "Введите пожалуйста ингредиенты, которые вы хотите исключить"
    )
    description_input = st.text_input(
        # "Describe what dish you would want to cook | your mood | anything you want to \N{grinning face}"
        "Опишите что вы хотите приготовить | ваше настроение | что-угодно \N{grinning face}"
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        do_search = st.button("Получить рецепты! \U0001F929")  # Get Recipes!
    with col2:
        next_recipe = st.button("Следующий рецепт!", on_click=increment_counter)

    if do_search:
        st.session_state.count = 0
        st.spinner()
        with st.spinner(text="In progress"):
            search_result = get_matching_recipes(
                products_include=products_include,
                products_exclude=products_exclude,
                text_description=description_input,
            )
            if type(search_result) is pd.DataFrame:
                # st.table(search_result)  # Display the table
                st.success("Готово \N{hugging face}")
                product_card(
                    name=search_result["name"][0],
                    description=search_result["description"][0],
                    ingredients=search_result["ingredients"][0],
                    instructions=search_result["instructions"][0],
                    recycling_recommendations=search_result[
                        "recycling_recommendations"
                    ][0],
                    substitutes=search_result["ingredients_substitutes"][0],
                    photo_url=None,
                )
            else:
                st.success(
                    """Ничего не найдено \U0001F641
                    \n Попробуйте указать другие ингредиенты \U0001F47E"""
                )

    if next_recipe:
        search_result = get_matching_recipes(
            products_include=products_include,
            products_exclude=products_exclude,
            text_description=description_input,
        )
        if search_result is not None and st.session_state.count < len(search_result):
            product_card(
                name=search_result["name"][st.session_state.count],
                description=search_result["description"][st.session_state.count],
                ingredients=search_result["ingredients"][st.session_state.count],
                instructions=search_result["instructions"][st.session_state.count],
                recycling_recommendations=search_result["recycling_recommendations"][
                    st.session_state.count
                ],
                substitutes=search_result["ingredients_substitutes"][
                    st.session_state.count
                ],
                photo_url=None,
            )
        else:
            st.text("Recipes with those ingredients finished :(")


if __name__ == "__main__":
    main()
