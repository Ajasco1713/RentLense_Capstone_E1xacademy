"""Filtering and weighted rental-property ranking."""
from typing import Dict, List

import pandas as pd


def _contains(text: str, term: str) -> bool:
    return term.lower() in str(text).lower()


def _location_match(row, req) -> bool:
    city = req.get("city")
    state = req.get("state")
    address = str(row.get("formattedAddress", ""))
    row_city = str(row.get("city", ""))
    row_state = str(row.get("state", ""))

    city_ok = not city or city.lower() in address.lower() or city.lower() == row_city.lower()
    state_ok = not state or state.lower() in address.lower() or state.lower() == row_state.lower()
    return city_ok and state_ok


def _property_type_match(value, required) -> bool:
    if not required:
        return True
    value = str(value or "").lower()
    required = required.lower()
    aliases = {
        "single family": {"single family", "house", "single-family"},
        "condo": {"condo", "condominium"},
        "townhouse": {"townhouse", "townhome"},
        "apartment": {"apartment"},
    }
    return value in aliases.get(required, {required})


def rank_properties(df: pd.DataFrame, req: Dict) -> pd.DataFrame:
    """Apply hard requirements then calculate a 0-100 weighted match score."""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    # Normalize common numeric fields when present.
    for column in ["price", "bedrooms", "bathrooms", "squareFootage", "yearBuilt"]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")

    # Hard filters for explicit user constraints.
    if req.get("max_price") is not None and "price" in out.columns:
        out = out[out["price"].isna() | (out["price"] <= float(req["max_price"]))]

    if req.get("bedrooms") is not None and "bedrooms" in out.columns:
        out = out[out["bedrooms"].isna() | (out["bedrooms"] >= float(req["bedrooms"]))]

    if req.get("bathrooms") is not None and "bathrooms" in out.columns:
        out = out[out["bathrooms"].isna() | (out["bathrooms"] >= float(req["bathrooms"]))]

    if req.get("propertyType") and "propertyType" in out.columns:
        out = out[out["propertyType"].apply(lambda x: _property_type_match(x, req["propertyType"]))]

    if req.get("city") or req.get("state"):
        out = out[out.apply(lambda row: _location_match(row, req), axis=1)]

    if out.empty:
        return out

    scores: List[float] = []
    reasons: List[List[str]] = []
    breakdowns: List[Dict[str, float]] = []

    for _, row in out.iterrows():
        points = {}
        why = []

        # 30 points: affordability. Being exactly at the budget receives full credit.
        if req.get("max_price") is not None and pd.notna(row.get("price")):
            budget = float(req["max_price"])
            price = float(row["price"])
            points["Budget"] = max(0.0, min(30.0, 30.0 * (1 - (price / budget) * 0.5)))
            if price <= budget:
                why.append("within budget")
        else:
            points["Budget"] = 0.0

        # 25 points: bedrooms.
        if req.get("bedrooms") is not None and pd.notna(row.get("bedrooms")):
            diff = abs(float(row["bedrooms"]) - float(req["bedrooms"]))
            points["Bedrooms"] = 25.0 if diff == 0 else max(0.0, 25.0 - 10.0 * diff)
            if diff == 0:
                why.append("exact bedroom match")
        else:
            points["Bedrooms"] = 0.0

        # 15 points: property type.
        if req.get("propertyType"):
            matched = _property_type_match(row.get("propertyType"), req["propertyType"])
            points["Property type"] = 15.0 if matched else 0.0
            if matched:
                why.append("property type matches")
        else:
            points["Property type"] = 0.0

        # 10 points: location.
        if req.get("city") or req.get("state"):
            matched = _location_match(row, req)
            points["Location"] = 10.0 if matched else 0.0
            if matched:
                why.append("location matches")
        else:
            points["Location"] = 0.0

        searchable = " ".join(
            str(row.get(k, "")) for k in ["features", "description", "parking", "security"]
        )

        # 5 points each: requested amenities.
        if req.get("parking"):
            matched = _contains(searchable, "parking")
            points["Parking"] = 5.0 if matched else 0.0
            if matched:
                why.append("parking available")
        else:
            points["Parking"] = 0.0

        if req.get("security"):
            matched = _contains(searchable, "security") or _contains(searchable, "secure")
            points["Security"] = 5.0 if matched else 0.0
            if matched:
                why.append("security available")
        else:
            points["Security"] = 0.0

        # When the user omits a criterion, normalize only over requested criteria.
        active_weights = sum(
            weight for name, weight in {
                "Budget": 30, "Bedrooms": 25, "Property type": 15,
                "Location": 10, "Parking": 5, "Security": 5,
            }.items() if (
                (name == "Budget" and req.get("max_price") is not None)
                or (name == "Bedrooms" and req.get("bedrooms") is not None)
                or (name == "Property type" and req.get("propertyType"))
                or (name == "Location" and (req.get("city") or req.get("state")))
                or (name == "Parking" and req.get("parking"))
                or (name == "Security" and req.get("security"))
            )
        )
        raw_score = sum(points.values())
        score = (raw_score / active_weights * 100) if active_weights else 0.0

        scores.append(min(100.0, score))
        reasons.append(why)
        breakdowns.append(points)

    out["match_score"] = scores
    out["match_reasons"] = reasons
    out["score_breakdown"] = breakdowns
    return out.sort_values(["match_score"], ascending=False).reset_index(drop=True)
