"""RentCast API integration."""
import os
from typing import Dict

import pandas as pd
import requests
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

URL = "https://api.rentcast.io/v1/listings/rental/long-term"


class RentCastError(Exception):
    """Raised when a RentCast request cannot be completed."""


def _build_params(req: Dict) -> Dict:
    params = {"status": "Active", "limit": 50}

    if req.get("city"):
        params["city"] = req["city"]
    if req.get("state"):
        params["state"] = req["state"]
    if req.get("zipCode"):
        params["zipCode"] = req["zipCode"]
    if req.get("bedrooms") is not None:
        params["bedrooms"] = f"{req['bedrooms']}:{req['bedrooms']}"
    if req.get("bathrooms") is not None:
        params["bathrooms"] = f"{req['bathrooms']}:*"
    if req.get("max_price") is not None:
        params["price"] = f"*:{req['max_price']}"
    if req.get("propertyType"):
        params["propertyType"] = req["propertyType"]

    return params


def _normalise_cost_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise fee column names without inventing missing fees."""

    aliases = {
        "securityDeposit": [
            "securityDeposit",
            "security_deposit",
            "security_deposit_amount",
        ],
        "applicationFee": [
            "applicationFee",
            "application_fee",
            "application_fee_amount",
        ],
        "parkingFee": [
            "parkingFee",
            "parking_fee",
            "parking_fee_amount",
        ],
        "petFee": [
            "petFee",
            "pet_fee",
            "pet_fee_amount",
        ],
    }

    for standard_name, possible_names in aliases.items():
        existing_name = next(
            (name for name in possible_names if name in df.columns),
            None,
        )

        if existing_name and existing_name != standard_name:
            df[standard_name] = df[existing_name]
        elif standard_name not in df.columns:
            # Unknown fees remain missing; do not estimate them.
            df[standard_name] = None

    return df


def search_rentals(req: Dict) -> pd.DataFrame:
    """Query RentCast and return rental listings as a DataFrame."""

    api_key = os.getenv("RENTCAST_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets["RENTCAST_API_KEY"]
        except Exception:
            api_key = None

    if not api_key or api_key == "your_rentcast_api_key_here":
        raise RentCastError(
            "RENTCAST_API_KEY is missing. "
            "Add your API key to .env or Streamlit Secrets."
        )

    try:
        response = requests.get(
            URL,
            params=_build_params(req),
            headers={
                "X-Api-Key": api_key,
                "Accept": "application/json",
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RentCastError(
            f"RentCast request failed: {exc}"
        ) from exc

    if response.status_code == 401:
        raise RentCastError("Invalid RentCast API key.")

    if response.status_code == 403:
        raise RentCastError(
            "RentCast rejected the request. Check your API access and key."
        )

    if not response.ok:
        raise RentCastError(
            f"RentCast HTTP {response.status_code}: {response.text[:300]}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RentCastError(
            "RentCast returned an invalid JSON response."
        ) from exc

    if isinstance(payload, list):
        listings = payload
    elif isinstance(payload, dict):
        listings = payload.get("listings", [])
    else:
        listings = []

   
    df = pd.DataFrame(listings)

    if df.empty:
        st.warning("RentCast returned no listings for this search.")
        return df

    # Standardise any fee fields that RentCast actually returns.
    df = _normalise_cost_fields(df)

    # Temporary diagnostic output.
    
    # TEMPORARY DEBUG: Inspect fee fields returned by RentCast.
    '''st.write("DEBUG: RentCast fields returned")
    st.write(df.columns.tolist())

    cost_columns = [
        col for col in df.columns
        if any(word in col.lower() for word in [
            "deposit", "application", "parking", "pet", "fee"
        ])
    ]

    st.write("DEBUG: Actual fee values for returned properties")

    if cost_columns:
        display_columns = [
            col for col in [
                "formattedAddress",
                "price",
                "securityDeposit",
                "applicationFee",
                "parkingFee",
                "petFee",
            ]
            if col in df.columns
        ]

        st.dataframe(df[display_columns].head(10))
    else:
        st.warning(
            "RentCast returned no columns related to additional costs."
        )'''

    return df