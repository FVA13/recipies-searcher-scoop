import requests
import logging
from PIL import Image
from io import BytesIO
import streamlit as st
from googletrans import Translator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def rescale_photo(image, scale_factor):
    width, height = image.size
    new_width = int(width / scale_factor)
    new_height = int(height / scale_factor)
    resized_image = image.resize((new_width, new_height))
    return resized_image


def resize_image_by_height(image, desired_height):
    width, height = image.size
    aspect_ratio = width / height
    desired_width = int(desired_height * aspect_ratio)
    resized_image = image.resize((desired_width, desired_height))
    return resized_image


def get_image_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        return image
    else:
        print("Failed to retrieve the image.")
        return None


def translate_russian_to_english(text):
    translator = Translator(service_urls=["translate.google.com"])
    translation = translator.translate(text, src="ru", dest="en")
    translated_text = translation.text
    return translated_text


def get_photo(description):
    logger.info("function get_photo() call")
    description_en = translate_russian_to_english(description)
    logger.info("translated name of the dish: {}".format(description_en))
    response = requests.get(
        "https://api.unsplash.com/search/photos",
        params={
            "query": description_en,
            "content_safety": "high",
            "client_id": st.streamlit["unsplash_token"],
            "page": 1,
            "per_page": 2,
            "order_by": "relevant",
        },
    )
    resp_res = response.json()["results"]
    urls = []
    for el in resp_res:
        urls.append(el.get("urls")["full"])
    image = get_image_from_url(urls[1])
    return image
