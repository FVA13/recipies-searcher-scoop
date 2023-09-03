import pandas as pd
from pandarallel import pandarallel
import torch
from sentence_transformers import SentenceTransformer
import sqlite3

import logging
import os
from collections import Counter

from scoop.functions import json_to_norm_list, flatten_lists

# logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
pandarallel.initialize(progress_bar=False, verbose=0)
os.environ["TOKENIZERS_PARALLELISM"] = "true"

device = torch.device("cpu")
# if torch.backends.mps.is_available():
#     device = torch.device("mps")
# elif torch.cuda.is_available():
#     device = torch.device("cuda")
# else:
#     print("Neither MPS nor CUDA devices were found.")


def insert_into_db(df, table_name):
    db_file = "../data/processed/scoop.db"
    try:
        conn = sqlite3.connect(db_file)
        df.to_sql(table_name, conn, if_exists="replace", index=False, index_label="id")
        conn.close()
    except sqlite3.Error as error:
        print("Failed to connect with sqlite3 database", error)


def read_from_db(query):
    conn = sqlite3.connect("../data/processed/scoop.db")
    df = pd.read_sql(query, conn)
    return df


def create_products_data():
    logger.info("update/creation of products table has begun")
    df = (
        pd.read_csv("../data/raw/povarenok_recipes_2021_06_16.csv").dropna(
            subset=["ingredients"]
        )
    ).ingredients.parallel_apply(lambda x: json_to_norm_list(x))

    data = (
        pd.DataFrame.from_records(
            Counter(flatten_lists(df)).most_common(), columns=["product", "qnt"]
        )
        .assign(occurrence_in_recipies=lambda df_: df_.qnt / len(df))
        .reset_index()
        .rename(columns={"index": "id"})
    )
    insert_into_db(data, "products")
    logger.info(
        "products table was successfully created/updated; {} entries were added".format(
            len(data)
        )
    )


def get_ingredients_ids(j):
    products = read_from_db(
        """
        select  *
        from    products
        """
    )
    l = json_to_norm_list(j)
    result = []
    for el in l:
        result.append(int(products[products["product"] == el].id))
    return result


def create_recipies_data():
    logger.info("update/creation of recipies table has begun")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=device)
    data = (
        pd.read_csv("../data/raw/povarenok_recipes_2021_06_16.csv")
        .drop(columns=["url"])
        .dropna(subset=["ingredients"])
        .reset_index(drop=True)
        .reset_index()
        .rename(columns={"index": "id"})
        .assign(
            embedding=lambda df_: df_["name"].apply(
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
    )
    data.to_pickle("desperate_backup.pkl")
    insert_into_db(data, "recipies")
    logger.info(
        "recipies table was successfully created/updated; {} entries were added".format(
            len(data)
        )
    )


if __name__ == "__main__":
    create_products_data()
    create_recipies_data()

# %%
