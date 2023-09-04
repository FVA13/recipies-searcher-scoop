import streamlit as st
from matcher import get_matching_recipies


st.set_page_config(
    page_title="Scoop - AI Recipies for everyone",
    # page_icon=icon,
    layout="centered",
    initial_sidebar_state="auto",
)


def main():
    products_input = st.text_input("Enter some ingredients")
    description_input = st.text_input(
        "Describe what dish you would want to cook | your mood | anything you want to \N{grinning face}"
    )
    do_search = st.button("Get Recipies! \U0001F929")

    if do_search:
        st.spinner()
        with st.spinner(text="In progress"):
            search_result = get_matching_recipies(products_input, description_input)[['name', 'ingredients']]
            st.table(search_result)
            st.success("Done \N{hugging face}")


if __name__ == "__main__":
    main()
