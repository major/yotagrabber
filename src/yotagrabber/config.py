"""Common configuration items used by the application."""
import json
import pathlib
import random

BASE_DIRECTORY = pathlib.Path(__file__).parent.resolve()


def random_user_agent():
    """Choose a user agent from a list of commonly used agents."""
    with open(f"{BASE_DIRECTORY}/data/common_user_agents.json", "r") as fileh:
        user_agents = json.load(fileh)

    random.shuffle(user_agents)
    return [x["ua"] for x in user_agents][0]


def random_zip_code():
    """Choose a random zip code from a list of zip codes."""
    with open(f"{BASE_DIRECTORY}/data/zipcodes.txt", "r") as fileh:
        zip_codes = fileh.readlines()

    random.shuffle(zip_codes)
    return [x for x in zip_codes][0].strip()


def get_headers():
    """Get the headers used when making requests to the Toyota website."""
    headers = {
        "origin": "https://www.toyota.com",
        "referrer": "https://www.toyota.com/",
        "user-agent": random_user_agent(),
        "accept": "*/*",
    }
    return headers
