# -*- coding: utf-8 -*-
import pysnooper

import torch
import boto3
import pickle
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
from pandarallel import pandarallel
from sentence_transformers import SentenceTransformer

import io
import os
import time
import click
import logging
import requests
import datetime
from pathlib import Path
from collections import Counter
from dotenv import find_dotenv, load_dotenv

from scoop.src.modules.functions import (
    create_slices,
    json_to_norm_list,
    flatten_lists,
    read_pickle_files,
)

logger = logging.getLogger(__name__)
logger.info("making final data set from raw data")
pandarallel.initialize(progress_bar=False, verbose=0)
os.environ["TOKENIZERS_PARALLELISM"] = "true"
device = torch.device("cpu")


def clean_html(raw_html):
    import re

    cleantext = re.sub(re.compile("<.*?>"), "", raw_html)
    return cleantext


def get_recipes_html(url):
    time.sleep(1)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
    }
    response = requests.get(url, headers)
    html = response.text
    return BeautifulSoup(html, "html.parser")


def get_recipe_instructions(soup: BeautifulSoup):
    """
    Get recipe instructions
    :param soup:
    :return: list of instructions
    """
    instructions = []
    try:
        html = soup.find("ul", {"itemprop": "recipeInstructions"}).findAll("p")
        for indx, instr in enumerate(html):
            instructions.append((indx, clean_html(instr.text).strip()))
    except AttributeError:
        # Handle the case where the expected HTML element is not found
        logger.info("Recipe instructions not found.")
    return instructions


def get_recipe_description(soup: BeautifulSoup):
    description_paragraphs = []
    try:
        html = soup.find("div", {"itemprop": "description"}).findAll("p")
        for par in html:
            description_paragraphs.append(clean_html(par.text).strip())
    except AttributeError:
        # Handle the case where the expected HTML element is not found
        logger.info("Recipe description not found.")
    return " ".join(description_paragraphs)


def get_recipe_reviews(soup: BeautifulSoup):
    reviews_cleaned = []
    try:
        reviews = soup.findAll("div", {"class": "text-comment"})
        for review in reviews:
            review_text = review.text.replace("\n", "").replace(";", ".").strip()
            if review_text != "":
                reviews_cleaned.append(review_text)
    except AttributeError:
        # Handle the case where the expected HTML element is not found
        logger.info("Recipe reviews not found.")
    return "; ".join(reviews_cleaned)


def save_to_s3(data, file_name):
    logger.info("save_to_s3() function called")

    session = boto3.session.Session()
    s3 = session.client(
        service_name="s3", endpoint_url="https://storage.yandexcloud.net"
    )

    # Create a temporary file-like object
    csv_buffer = io.StringIO()

    # Write the DataFrame to the temporary file-like object
    data.to_csv(csv_buffer)

    # Upload the file-like object to S3
    s3.put_object(Body=csv_buffer.getvalue(), Bucket="scoop", Key=file_name)
    logger.info("save_to_s3() function completed: data saved to S3")


def get_html_pages(urls_list):
    logger.info("get_html_pages() function called")

    # Create slices to divide the urls_list into smaller chunks
    slices = create_slices(3_222, len(urls_list) - 1, slice_size=500)

    # Iterate over each slice
    for indx, slice in enumerate(slices):
        slice_from = slice[0]
        slice_to = slice[1]

        # Get the urls to process for the current slice
        url_list_todo = urls_list[slice_from:slice_to]

        # Process each url in the current slice
        html_pages = []
        for url in tqdm(url_list_todo):
            html_pages.append((url, get_recipes_html(url)))

        formatted_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        pd.DataFrame(html_pages).to_pickle(
            "../../data/interim/html_pages/html_pages_slice_from_{}_to_{}".format(
                slice_from, slice_to
            )
        )

        # # Save the processed data to S3
        # save_to_s3(
        #     pd.DataFrame(html_pages),
        #     "html_pages_slice_from_{}_to_{}".format(slice_from, slice_to),
        # )

        logger.info("Slice {}/{} completed".format(indx + 1, len(slices)))


# @pysnooper.snoop()
def process_html_information():
    folder_path = "../../data/interim/html_pages"
    # Get a list of all pickle files in the folder
    pickle_files = [file for file in os.listdir(folder_path) if file.endswith(".pkl")]

    for file in pickle_files:
        file_path = os.path.join(folder_path, file)

        df = pd.read_pickle(file_path).rename(columns=["url", "html"])
        df["instructions"] = df.iloc[:, 1].parallel_apply(
            lambda x: get_recipe_instructions(x)
        )
        df["description"] = df.iloc[:, 1].parallel_apply(
            lambda x: get_recipe_description(x)
        )
        df["reviews"] = df.iloc[:, 1].parallel_apply(lambda x: get_recipe_reviews(x))
        df["combined"] = df[["instructions", "description", "reviews"]].apply(
            lambda row: " ".join(row.dropna().astype(str)), axis=1
        )

        df[["url", "instructions", "description", "combined"]].to_pickle(
            "../../data/processed/html_pages/{}".format(pickle_files)
        )


def create_substitutes_data():
    logger.info("update/creation of substitutes table has begun")
    substitutes = (
        pd.read_excel("../../data/raw/products_substitutes.xlsx")
        .rename(columns={"Продукт": "product", "Альтернатива": "substitute"})
        .assign(
            substites=lambda df_: (df_["product"] + ", " + df_["substitute"])
            .str.lower()
            .str.split(",")
        )
        .drop(columns=["product", "substitute"])
    )

    data = pd.DataFrame()
    for index, row in substitutes.iterrows():
        ingredients = row.substites
        combinations = pd.DataFrame()
        for indx in range(len(ingredients)):
            product = ingredients[indx]
            substitutes = [ingredients[:indx] + ingredients[indx + 1 :]]
            combinations = pd.concat(
                [
                    combinations,
                    pd.DataFrame({"product": product, "substitutes": substitutes}),
                ],
                ignore_index=True,
            )
        data = pd.concat([data, combinations], ignore_index=True)
    data.to_pickle("../../data/processed/dbo_substitutes.pkl")
    logger.info(
        "substites table was successfully created/updated; {} entries were added".format(
            len(data)
        )
    )


def create_products_data():
    logger.info("update/creation of products table has begun")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=device)
    df = (
        pd.read_csv("../../data/raw/povarenok_recipes_2021_06_16.csv").dropna(
            subset=["ingredients"]
        )
    ).ingredients.parallel_apply(lambda x: json_to_norm_list(x))
    data = (
        pd.DataFrame.from_records(
            Counter(flatten_lists(df)).most_common(), columns=["product", "qnt"]
        )
        .assign(occurrence_in_recipes=lambda df_: df_.qnt / len(df))
        .assign(
            name_embedding=lambda df_: df_["product"].apply(
                lambda x: model.encode(
                    x, convert_to_tensor=True, show_progress_bar=False
                ).numpy()
            )
        )
        .query("product != 'огурцы'")
        .reset_index()
        .rename(columns={"index": "id"})
        .merge(
            pd.read_pickle("../../data/processed/dbo_substitutes.pkl"),
            left_on="product",
            right_on="product",
            how="left",
        )
        .merge(
            pd.read_excel(
                "../../data/raw/products_substitutes.xlsx",
                sheet_name="Recycling",
                names=["product", "recycling_method"],
            )
            .dropna()
            .assign(product=lambda df_: df_["product"].apply(lambda x: str(x).lower()))
            .replace({"помидоры": "помидор"})
            .replace({"огурцы": "огурец"}),
            left_on="product",
            right_on="product",
            how="left",
        )
    )
    data.to_pickle("../../data/processed/dbo_products.pkl")
    logger.info(
        "products table was successfully created/updated; {} entries were added".format(
            len(data)
        )
    )


def get_ingredients_ids(j):
    products = pd.read_pickle("../../data/processed/dbo_products.pkl")
    l = json_to_norm_list(j)
    result = []
    for el in l:
        try:
            result.append(int(products[products["product"] == el]["id"]))
        except TypeError:
            pass
    return result


def get_ingredients_substitutes(ingredients_ids):
    products = pd.read_pickle("../../data/processed/dbo_products.pkl")
    ingredients_substitutes = {}
    for ingredient_id in ingredients_ids:
        ingredient_name = products[products["id"] == ingredient_id]["product"].item()
        substitutes = products[products["id"] == ingredient_id]["substitutes"].item()
        if type(substitutes) == list:
            ingredients_substitutes[ingredient_name] = substitutes
        else:
            pass
    return ingredients_substitutes


def get_recycling_recommendations(ingredients_ids):
    products = pd.read_pickle("../../data/processed/dbo_products.pkl")
    ingredients_recommenations = {}
    for ingredient_id in ingredients_ids:
        ingredient_name = products[products["id"] == ingredient_id]["product"].item()
        substitutes = products[products["id"] == ingredient_id]["recycling_method"].item()
        if type(substitutes) == str:
            ingredients_recommenations[ingredient_name] = substitutes
        else:
            pass
    return ingredients_recommenations


# @pysnooper.snoop()
def create_recipes_data():
    logger.info("update/creation of recipes table has begun")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=device)
    data = (
        pd.read_csv("../../data/raw/povarenok_recipes_2021_06_16.csv")
        .dropna(subset=["url", "ingredients"])
        .reset_index(drop=True)
        .reset_index()
        .rename(columns={"index": "id"})
        .assign(
            name_embedding=lambda df_: df_["name"].apply(
                lambda x: model.encode(
                    x, convert_to_tensor=True, show_progress_bar=False
                )
                # .cpu()
                .numpy()
            )
        )
        .assign(
            ingredients_ids=lambda df_: df_["ingredients"].parallel_apply(
                lambda x: get_ingredients_ids(x)
            )
        )
        .assign(
            ingredients_qnt=lambda df_: df_["ingredients_ids"].parallel_apply(
                lambda x: len(x)
            )
        )
        .assign(
            ingredients_substitutes=lambda df_: df_["ingredients_ids"].parallel_apply(
                lambda x: get_ingredients_substitutes(x)
            )
        )
        .assign(
            recycling_recommendations=lambda df_: df_["ingredients_ids"].parallel_apply(
                lambda x: get_recycling_recommendations(x)
            )
        )
        .merge(
            pd.read_pickle("../../data/interim/dbo_parsed_html.pkl"),
            left_on="url",
            right_on="url",
        )
        # .assign(
        #     description_embedding=lambda df_: df_["description"].parallel_apply(
        #         lambda x: model.encode(
        #             x, convert_to_tensor=True, show_progress_bar=False
        #         )
        #     )
        # )
        # .drop(columns=["url"])
    )
    data.to_pickle("../../data/processed/dbo_recipes.pkl")
    logger.info(
        "recipes table was successfully created/updated; {} entries were added".format(
            len(data)
        )
    )


# @click.command()
# @click.argument("input_filepath", type=click.Path(exists=True))
# @click.argument("output_filepath", type=click.Path())
# def main(input_filepath, output_filepath):
def main():
    """Runs data processing scripts to turn raw data from (../raw) into
    cleaned data ready to be analyzed (saved in ../processed).
    """
    create_substitutes_data()
    create_products_data()
    create_recipes_data()


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    load_dotenv(find_dotenv())

    main()
