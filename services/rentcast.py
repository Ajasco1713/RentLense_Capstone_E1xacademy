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


def search_rentals(req: Dict) -> pd.DataFrame:
    """Query RentCast and return listings as a DataFrame."""
    api_key = os.getenv("RENTCAST_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets["RENTCAST_API_KEY"]
        except Exception:
            api_key = None

    if not api_key or api_key == "your_rentcast_api_key_here":
        raise RentCastError(
            "RENTCAST_API_KEY is missing. Add your API key to .env or Streamlit Secrets."
        )

    try:
        response = requests.get(
            URL,
            params=_build_params(req),
            headers={"X-Api-Key": api_key, "Accept": "application/json"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RentCastError(f"RentCast request failed: {exc}") from exc

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

    listings = payload if isinstance(payload, list) else payload.get("listings", [])

    return pd.DataFrame(listings)