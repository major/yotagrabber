"""Get a list of Toyota vehicles from the Toyota website."""
import os
import json
import random
import sys
import uuid

import pandas as pd
from python_graphql_client import GraphqlClient

from yotagrabber import config

# Set to True to use local data and skip requests to the Toyota website.
USE_LOCAL_DATA_ONLY = False

# Get the model that we should be searching for.
MODEL = os.environ.get("MODEL")


def get_vehicles_query():
    """Read vehicles query from a file."""
    with open(f"{config.BASE_DIRECTORY}/graphql/vehicles.graphql", "r") as fileh:
        query = fileh.read()

    # Replace certain place holders in the query with values.
    query = query.replace("ZIPCODE", config.random_zip_code())
    query = query.replace("MODELCODE", MODEL)
    query = query.replace("DISTANCEMILES", str(random.randrange(10000, 20000)))
    query = query.replace("LEADIDUUID", str(uuid.uuid4()))

    return query


def read_local_data():
    """Read local raw data from the disk instead of querying Toyota."""
    with open(f"output/{MODEL}_raw.json", "r") as fileh:
        result = json.load(fileh)

    return result


def query_toyota(page_number):
    """Query Toyota for a list of vehicles."""
    print(f"Getting page {page_number}")

    client = GraphqlClient(
        endpoint="https://api.search-inventory.toyota.com/graphql",
        headers=config.get_headers(),
    )

    # Run the query.
    query = get_vehicles_query()
    query = query.replace("PAGENUMBER", str(page_number))
    result = client.execute(query=query)

    return result["data"]["locateVehiclesByZip"]["vehicleSummary"]


def get_all_pages():
    """Get all pages of results for a query to Toyota."""
    df = pd.DataFrame()
    page_number = 1
    while True:
        try:
            vehicles = query_toyota(page_number)
        except Exception as exc:
            print(f"Error: {exc}")
            break

        if vehicles:
            df = pd.concat([df, pd.json_normalize(vehicles)])
            page_number += 1
            continue

        break

    return df


def update_vehicles():
    """Generate a JSON file containing Toyota vehicles."""
    if not MODEL:
        sys.exit("Set the MODEL environment variable first")

    result = read_local_data() if USE_LOCAL_DATA_ONLY else get_all_pages()

    # Write the raw data to a file.
    result.to_json(f"output/{MODEL}_raw.json", orient="records", indent=2)

    # Get the models from the result.
    # models = result["data"]["models"]
    # df = pd.json_normalize(models)

    # # Build a view and write it out as JSON.
    # models = (
    #     df[
    #         [
    #             "modelCode",
    #             "title",
    #             "image",
    #         ]
    #     ]
    #     .sort_values("modelCode", ascending=True)
    #     .reset_index(drop=True)
    # )
    # models.to_json("output/models.json", orient="records", indent=2)
