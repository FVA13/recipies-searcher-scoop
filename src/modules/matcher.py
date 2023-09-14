from Levenshtein import distance as lev_distance
import pandas as pd
import logging
import gdown
import re
import os

from db_create import read_from_db

# from scoop.modules.db_create import read_from_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def get_products_matches(products_input: str):
    logger.info("def call: get_products_matches")
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
    logger.info("def call: get_matching_recipies")
    path = "../../data/processed"
    path_to = "../../data"
    try:
        if not os.listdir(path):
            url = "https://drive.google.com/drive/folders/10cmVnMrmZAzaH_8vpWfCTbqd3eI_zaaU?usp=sharing"
            gdown.download_folder(url, output=path_to)
    except FileNotFoundError:
        os.mkdir(path_to)
        url = "https://drive.google.com/drive/folders/10cmVnMrmZAzaH_8vpWfCTbqd3eI_zaaU?usp=sharing"
        gdown.download_folder(url, output=path_to)
    # if not os.listdir('../../data/processed'):
    #     url = "https://drive.google.com/drive/folders/10cmVnMrmZAzaH_8vpWfCTbqd3eI_zaaU?usp=sharing"
    #     gdown.download_folder(url, output='../../data')
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
