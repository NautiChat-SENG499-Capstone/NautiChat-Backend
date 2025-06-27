import os
from pathlib import Path

from dotenv import load_dotenv
from onc import ONC

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
ONC_TOKEN = os.getenv("ONC_TOKEN")
CAMBRIDGE_LOCATION_CODE = os.getenv(
    "CAMBRIDGE_LOCATION_CODE"
)  # Change for a different location
onc = ONC(ONC_TOKEN)


params = {
    "locationCode": "CBY",
    # "locationCode": CAMBRIDGE_LOCATION_CODE,
}
if CAMBRIDGE_LOCATION_CODE:
    locations = onc.getLocationsTree(params)
else:
    locations = onc.getLocations()

for loc in locations:
    print(loc)
