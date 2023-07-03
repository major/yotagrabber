"""Get a list of Toyota models from the Toyota website."""
import json

import pandas as pd
import requests

from yotagrabber import config

# Set to True to use local data and skip requests to the Toyota website.
USE_LOCAL_DATA_ONLY = False


def get_models_query():
    """Read models query from a file."""
    with open(f"{config.BASE_DIRECTORY}/graphql/models.graphql", "r") as fileh:
        query = fileh.read()

    # Replace the zip code with a random zip code.
    # query = query.replace("ZIPCODE", config.random_zip_code())
    query = query.replace("ZIPCODE", "90210")

    return query


def read_local_data():
    """Read local raw data from the disk instead of querying Toyota."""
    with open("output/models_raw.json", "r") as fileh:
        result = json.load(fileh)

    return result


def query_toyota():
    """Query Toyota for a list of models."""
    query = get_models_query()

    # Make request.
    json_post = {"query": query}
    url = "https://api.search-inventory.toyota.com/graphql"
    resp = requests.post(
        url,
        json=json_post,
        headers=config.get_headers(),
        timeout=15,
    )

    return resp.json()["data"]["models"]


def update_models():
    """Generate a JSON file containing Toyota models."""
    result = read_local_data() if USE_LOCAL_DATA_ONLY else query_toyota()

    # Get the models from the result.
    df = pd.json_normalize(result)

    df.sort_values("modelCode").to_json(
        "output/models_raw.json", orient="records", indent=2
    )

    # Build a view and write it out as JSON.
    models = (
        df[
            [
                "modelCode",
                "title",
            ]
        ]
        .sort_values("title", ascending=True)
        .reset_index(drop=True)
    )

    # Toyota uses different names for some models when you query the graphQL API.
    # https://github.com/major/yotagrabber/issues/32
    models.loc[models["modelCode"] == "gr86", "modelCode"] = "86"
    models.loc[models["modelCode"] == "grsupra", "modelCode"] = "supra"

    print(models.to_string())
    models.to_json("output/models.json", orient="records", indent=2)
