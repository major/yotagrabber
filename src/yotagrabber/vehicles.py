"""Get a list of Toyota vehicles from the Toyota website."""
import datetime
from functools import cache
import os
import json
import random
import sys
import uuid

import pandas as pd
import requests

from yotagrabber import config

# Set to True to use local data and skip requests to the Toyota website.
USE_LOCAL_DATA_ONLY = False

# Get the model that we should be searching for.
MODEL = os.environ.get("MODEL")


@cache
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
    return pd.read_parquet(f"output/{MODEL}_raw.parquet")


def query_toyota(page_number):
    """Query Toyota for a list of vehicles."""

    # Load query and replace the page number.
    query = get_vehicles_query()
    query = query.replace("PAGENUMBER", str(page_number))

    # Make request.
    json_post = {"query": query}
    url = "https://api.search-inventory.toyota.com/graphql"
    resp = requests.post(
        url,
        json=json_post,
        headers=config.get_headers(),
        timeout=15,
    )

    result = resp.json()["data"]["locateVehiclesByZip"]

    if not result or "vehicleSummary" not in result:
        print(resp.text)
        return None
    else:
        return result


def get_all_pages():
    """Get all pages of results for a query to Toyota."""
    df = pd.DataFrame()
    page_number = 1

    while True:
        # Get a page of vehicles.
        print(f"Getting page {page_number} of {MODEL} vehicles")
        result = query_toyota(page_number)

        # Stop if we received no more results.
        if not result:
            print("No more results.")
            break

        # Add the current page to the big dataframe.
        df = pd.concat([df, pd.json_normalize(result["vehicleSummary"])])

        page_number += 1
        continue

    return df


def update_vehicles():
    """Generate a curated database of vehicles."""
    if not MODEL:
        sys.exit("Set the MODEL environment variable first")

    df = read_local_data() if USE_LOCAL_DATA_ONLY else get_all_pages()

    # Stop here if there are no vehicles to list.
    if df.empty:
        print(f"No vehicles found for model: {MODEL}")
        return

    # Write the raw data to a file.
    if not USE_LOCAL_DATA_ONLY:
        df.sort_values("vin", inplace=True)
        df.to_parquet(f"output/{MODEL}_raw.parquet", index=False)

    # Add dealer data.
    dealers = pd.read_csv(f"{config.BASE_DIRECTORY}/data/dealers.csv")[
        ["dealerId", "state"]
    ]
    dealers.rename(columns={"state": "Dealer State"}, inplace=True)
    df["dealerCd"] = df["dealerCd"].apply(pd.to_numeric)
    df = df.merge(dealers, left_on="dealerCd", right_on="dealerId")

    renames = {
        "vin": "VIN",
        "price.baseMsrp": "Base MSRP",
        "model.marketingName": "Model",
        "extColor.marketingName": "Color",
        "dealerCategory": "Shipping Status",
        "dealerMarketingName": "Dealer",
        "dealerWebsite": "Dealer Website",
        "isPreSold": "Pre-Sold",
        "holdStatus": "Hold Status",
        "year": "Year",
        "drivetrain.code": "Drivetrain",
    }

    with open(f"output/models.json", "r") as fileh:
        title = [x["title"] for x in json.load(fileh) if x["modelCode"] == MODEL][0]

    df = (
        df[
            [
                "vin",
                "dealerCategory",
                "price.baseMsrp",
                "price.dioTotalDealerSellingPrice",
                "isPreSold",
                "holdStatus",
                "year",
                "drivetrain.code",
                "media",
                "model.marketingName",
                "extColor.marketingName",
                "dealerMarketingName",
                "dealerWebsite",
                "Dealer State",
            ]
        ]
        .copy(deep=True)
        .rename(columns=renames)
    )

    # Remove the model name (like 4Runner) from the model column (like TRD Pro).
    df["Model"] = df["Model"].str.replace(f"{title} ", "")

    # Clean up missing colors and colors with extra tags.
    df = df[df["Color"].notna()]
    df["Color"] = df["Color"].str.replace(" [extra_cost_color]", "", regex=False)

    # Calculate the dealer price + markup.
    df["Dealer Price"] = df["Base MSRP"] + df["price.dioTotalDealerSellingPrice"]
    df["Dealer Price"] = df["Dealer Price"].fillna(df["Base MSRP"])
    df["Markup"] = df["Dealer Price"] - df["Base MSRP"]
    df.drop(columns=["price.dioTotalDealerSellingPrice"], inplace=True)

    # Remove any old models that might still be there.
    last_year = datetime.date.today().year - 1
    df.drop(df[df["Year"] < last_year].index, inplace=True)

    statuses = {None: False, 1: True, 0: False}
    df.replace({"Pre-Sold": statuses}, inplace=True)

    statuses = {
        "A": "Factory to port",
        "F": "Port to dealer",
        "G": "At dealer",
    }
    df.replace({"Shipping Status": statuses}, inplace=True)

    df["Image"] = df["media"].apply(
        lambda x: [x["href"] for x in x if x["type"] == "carjellyimage"][0]
    )
    df.drop(columns=["media"], inplace=True)

    df = df[
        [
            "Year",
            "Model",
            "Color",
            "Drivetrain",
            "Base MSRP",
            "Markup",
            "Dealer Price",
            "Shipping Status",
            "Pre-Sold",
            "Hold Status",
            "VIN",
            "Dealer",
            "Dealer Website",
            "Dealer State",
            "Image",
        ]
    ]

    # Write the data to a file.
    df.sort_values(by=["VIN"], inplace=True)
    df.to_csv(f"output/{MODEL}.csv", index=False)
