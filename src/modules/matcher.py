import pandas as pd
from Levenshtein import distance as lev_distance
import re
import logging

from db_create import read_from_db
# from scoop.modules.db_create import read_from_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def get_products_matches(products_input: str):
    products = re.split("; |, |\;|\n|\\s", products_input)
    db_products = read_from_db(
        """
        select  *
        from    products
        """
    )
    matches = []
    for product in products:
        closest_match_id = (
            db_products["product"]
            .apply(lambda x: lev_distance(x, product))
            .sort_values()
            .index[0]
        )
        closest_match_name = db_products.iloc[closest_match_id]["product"]
        matches.append(closest_match_id)
        logger.info(
            "Found match to {orig} is {match}".format(
                orig=product, match=closest_match_name
            )
        )
    return matches


def is_length_match(l, matches):
    cntr = 0
    for el in l:
        if el in matches:
            cntr += 1
    return cntr == len(matches)


def get_matching_recipies(products_input: str, text_description: str = None):
    # think of sorting strategy; for now based on the amount of ingredients
    matches = get_products_matches(products_input)
    # recipies = pd.read_pickle("../data/processed/dbo_recipies.pkl")
    recipies = pd.read_pickle("../../data/processed/dbo_recipies.pkl")
    # recipies = read_from_db(
    #     """
    #     select  *
    #     from    recipies
    #     """
    # )
    df = (
        recipies.assign(
            is_match=lambda df_: df_.ingredients_ids.apply(
                lambda x: is_length_match(x, matches)
            )
        )
        .query("is_match")
        .dropna()
        .assign(
            is_full_match=lambda df_: df_.ingredients_ids.apply(
                lambda x: is_length_match(x, matches)
            )
        )
        .query("is_full_match")
        .dropna()
        .sort_values(by="ingredients_qnt")
        .reset_index(drop=True)
        .drop(columns=["is_match", "is_full_match"])
        .head(10)
    )
    # print(df)
    return df


# get_matching_recipies("Молоко, Клубнка Сахар")
