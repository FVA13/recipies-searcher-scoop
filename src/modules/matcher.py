from sentence_transformers import SentenceTransformer
from Levenshtein import distance as lev_distance
from numpy.linalg import norm
import pandas as pd
import logging
import urllib
import re
import os

from db_create import read_from_db

# from scoop.modules.db_create import read_from_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def get_products_matches(products_input: str):
    logger.info("def call: get_products_matches")
    # regEx to read user's input correctly
    products = re.split("; |, |\;|\n|\\s", products_input)
    # get products embeddings to calculate later cosine similarity with known products
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    products_embeddings = [
        model.encode(product, convert_to_tensor=True, show_progress_bar=False).numpy()
        for product in products
    ]

    # get our products data from S3
    data_dir = "../../data"
    processed_dir = f"{data_dir}/processed"
    dbo_products_path = f"{processed_dir}/dbo_products.pkl"

    if os.path.exists(dbo_products_path):
        db_products = pd.read_pickle(dbo_products_path)
    else:
        logger.info("downloading data from S3")
        opener = urllib.request.URLopener()
        db_products = pd.read_pickle(
            opener.open("https://storage.yandexcloud.net/scoop/dbo_products.pkl")
        )
        logger.info("[DONE] downloading data from S3")

    # identify matches between users input and our database
    matches = []
    for product, name_embedding in zip(products, products_embeddings):
        closest_match_id = (
            db_products.assign(
                lev_distance=lambda df_: df_["product"].apply(
                    lambda x: lev_distance(x, product)
                )
            )
            .assign(
                cos_sim=lambda df_: df_["name_embedding"].apply(
                    lambda x: x @ name_embedding / (norm(x) * norm(name_embedding))
                )
            )
            .sort_values(by="cos_sim", ascending=False)
            .query("(cos_sim > 0.9) | (lev_distance < 2)")
        )

        # if there are any matches found
        if len(closest_match_id):
            closest_match_id = closest_match_id.index[0]  # taking the best match
            closest_match_name = db_products.iloc[closest_match_id]["product"]
            matches.append(closest_match_id)
            logger.info(
                "Found match to {orig} is {match}".format(
                    orig=product, match=closest_match_name
                )
            )
        else:
            logger.info("Found no match to {orig}".format(orig=product))
    return matches


def lists_match(l, matches, match_type: str = "full", return_type: str = "bool"):
    """
    Identifies whether one list contains the other when match_type 'full' is selected
    or whether one list contain the part of the other when match_type is set to 'include'
    :param l:
    :param matches:
    :param match_type: can be either full or include
    :param return_type: can be either bool or cntr
    :return:
    """
    cntr = 0
    for el in l:
        if el in matches:
            cntr += 1
    if return_type == "cntr":
        return cntr
    elif match_type == "full":
        return cntr == len(matches)
    else:
        return cntr >= 1


def get_matching_recipes(
    products_include: str, products_exclude: str = None, text_description: str = None
):
    logger.info("def call: get_matching_recipes")

    # get recipes data
    data_dir = "../../data"
    processed_dir = f"{data_dir}/processed"
    dbo_products_path = f"{processed_dir}/dbo_recipes.pkl"

    if os.path.exists(dbo_products_path):
        recipes = pd.read_pickle(dbo_products_path)
        print(recipes.columns)
    else:
        logger.info("downloading data from S3")
        opener = urllib.request.URLopener()
        recipes = pd.read_pickle(
            opener.open("https://storage.yandexcloud.net/scoop/dbo_recipes.pkl")
        )
        logger.info("[DONE] downloading data from S3")

    # think of sorting strategy; for now based on the amount of ingredients
    matches_include = get_products_matches(products_include)
    print(matches_include)
    matches_exclude = ['']
    if not matches_include:
        return "Ничего не найдено :("
    if products_exclude:
        matches_exclude = get_products_matches(products_exclude)
    df = (
        recipes.assign(
            is_match=lambda df_: df_.ingredients_ids.apply(
                lambda x: lists_match(x, matches_include, match_type="include")
            )
        )
        .query("is_match")
        .dropna()
        .assign(
            matches_qnt=lambda df_: df_.ingredients_ids.apply(
                lambda x: lists_match(
                    x, matches_include, match_type="include", return_type="cntr"
                )
            )
        )
        .assign(
            is_full_match=lambda df_: df_.ingredients_ids.apply(
                lambda x: lists_match(x, matches_include)
            )
        )
        .assign(
            matches_exclude=lambda df_: df_.ingredients_ids.apply(
                lambda x: lists_match(x, matches_exclude)
            )
        )
        # .query("~matches_exclude")
        # .query("is_full_match")
        .dropna()
        .sort_values(
            by=["is_full_match", "matches_qnt", "ingredients_qnt"],
            ascending=[False, False, True],
        )
        .pipe(lambda df: df[df['instructions'].apply(lambda x: x != [])])
        .reset_index(drop=True)
        # .drop(columns=["is_match", "is_full_match"])
        .head(100)
        [['name', 'ingredients', 'instructions', 'description', 'ingredients_substitutes', 'recycling_recommendations']]
        # .pipe(lambda df_: df_[df_['instructions'].notna()])
        # .query("instructions != '[]'")
        # .astype(str)
    )
    # print(df)
    return df


# get_matching_recipes("Молоко, Клубнка Сахар")
# помидор окурец чеснок
