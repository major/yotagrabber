"""Get a list of Toyota models from the Toyota website."""
import json

import pandas as pd
from python_graphql_client import GraphqlClient

from yotagrabber import config

# Set to True to use local data and skip requests to the Toyota website.
USE_LOCAL_DATA_ONLY = True


def get_models_query():
    """Read models query from a file."""
    with open(f"{config.BASE_DIRECTORY}/graphql/models.graphql", "r") as fileh:
        query = fileh.read()

    # Replace the zip code with a random zip code.
    query = query.replace("ZIPCODE", config.random_zip_code())

    return query


def read_local_data():
    """Read local raw data from the disk instead of querying Toyota."""
    with open("output/models_raw.json", "r") as fileh:
        result = json.load(fileh)

    return result


def query_toyota():
    """Query Toyota for a list of models."""
    client = GraphqlClient(
        endpoint="https://api.search-inventory.toyota.com/graphql",
        headers=config.get_headers(),
    )

    result = client.execute(query=get_models_query())

    with open("output/models_raw.json", "w") as fileh:
        fileh.write(json.dumps(result, indent=2))

    return result


def update_models():
    """Generate a JSON file containing Toyota models."""
    result = read_local_data() if USE_LOCAL_DATA_ONLY else query_toyota()

    # Get the models from the result.
    models = result["data"]["models"]
    df = pd.json_normalize(models)

    # Build a view and write it out as JSON.
    models = (
        df[
            [
                "modelCode",
                "title",
                "image",
            ]
        ]
        .sort_values("modelCode", ascending=True)
        .reset_index(drop=True)
    )
    models.to_json("output/models.json", orient="records", indent=2)
