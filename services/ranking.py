
"""Filtering and weighted rental-property ranking."""

from typing import Dict, List

import pandas as pd


def _location_match(row, req) -> bool:
    """Require the listing's city and state to match the request."""
    city = str(req.get("city") or "").strip().casefold()
    state = str(req.get("state") or "").strip().casefold()

    row_city = str(row.get("city") or "").strip().casefold()
    row_state = str(row.get("state") or "").strip().casefold()

    if city and row_city != city:
        return False

    if state and row_state != state:
        return False

    return True


def _property_type_match(value, required) -> bool:
    """Compare property types while supporting common aliases."""
    if not required:
        return True

    value = str(value or "").strip().lower()
    required = str(required).strip().lower()

    aliases = {
        "single family": {"single family", "house", "single-family"},
        "condo": {"condo", "condominium"},
        "townhouse": {"townhouse", "townhome"},
        "apartment": {"apartment"},
    }

    return value in aliases.get(required, {required})


def _amenity_status(row, amenity: str):
    """Return True, False, or None if amenity status is unknown."""
    value = row.get(amenity)

    if isinstance(value, bool):
        return value

    if value is not None and not pd.isna(value):
        text = str(value).strip().lower()

        if text in {"true", "yes", "1", "available", "included"}:
            return True

        if text in {"false", "no", "0", "unavailable", "not available"}:
            return False

    description = " ".join(
        str(row.get(field) or "")
        for field in ["features", "description"]
    ).lower()

    if amenity == "parking":
        negative = [
            "no parking",
            "parking unavailable",
            "parking not available",
            "without parking",
        ]
        positive = ["parking", "garage", "carport"]

    elif amenity == "security":
        negative = [
            "no security",
            "security unavailable",
            "security not available",
            "without security",
        ]
        positive = [
            "security",
            "secure",
            "gated community",
            "controlled access",
        ]

    else:
        return None

    if any(term in description for term in negative):
        return False

    if any(term in description for term in positive):
        return True

    return None



def rank_properties(df: pd.DataFrame, req: Dict) -> pd.DataFrame:
    """Filter explicit requirements and rank qualifying properties."""

    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    # Normalize numeric fields.
    for column in [
        "price",
        "bedrooms",
        "bathrooms",
        "squareFootage",
        "yearBuilt",
    ]:
        if column in out.columns:
            out[column] = pd.to_numeric(
                out[column], errors="coerce"
            )

    # Hard filter: monthly budget.
    if req.get("max_price") is not None:
        if "price" not in out.columns:
            return pd.DataFrame()

        budget = float(req["max_price"])
        out = out[
            out["price"].notna()
            & (out["price"] <= budget)
        ]

    # Hard filter: minimum bedrooms.
    if req.get("bedrooms") is not None:
        if "bedrooms" not in out.columns:
            return pd.DataFrame()

        out = out[
            out["bedrooms"].notna()
            & (out["bedrooms"] >= float(req["bedrooms"]))
        ]

    # Hard filter: minimum bathrooms.
    if req.get("bathrooms") is not None:
        if "bathrooms" not in out.columns:
            return pd.DataFrame()

        out = out[
            out["bathrooms"].notna()
            & (out["bathrooms"] >= float(req["bathrooms"]))
        ]

    # Hard filter: property type.
    if req.get("propertyType"):
        if "propertyType" not in out.columns:
            return pd.DataFrame()

        out = out[
            out["propertyType"].apply(
                lambda value: _property_type_match(
                    value, req["propertyType"]
                )
            )
        ]

    # Hard filter: location.
    if req.get("city") or req.get("state"):
        out = out[
            out.apply(
                lambda row: _location_match(row, req),
                axis=1,
            )
        ]

    # Filter out properties only when an amenity is
    # explicitly unavailable. Keep unknown statuses.
    for amenity in ["parking", "security"]:
        if req.get(amenity) is True:
            out = out[
                out.apply(
                    lambda row: (
                        _amenity_status(row, amenity) is not False
                    ),
                    axis=1,
                )
            ]

    out = out.copy().reset_index(drop=True)

    if out.empty:
        return out

    # Calculate the weights for the requirements being evaluated.
    active_weights = sum([
        30 if req.get("max_price") is not None else 0,
        25 if req.get("bedrooms") is not None else 0,
        15 if req.get("propertyType") else 0,
        10 if req.get("city") or req.get("state") else 0,
        5 if req.get("parking") is True else 0,
        5 if req.get("security") is True else 0,
    ])

    scores = []
    reasons = []
    breakdowns = []

    # Score each property separately.
    for _, row in out.iterrows():
        points = {}
        why = []

        # Budget.
        if req.get("max_price") is not None:
            budget = float(req["max_price"])
            price = float(row["price"])

            points["Budget"] = max(
                0.0,
                min(30.0, 30.0 * (1 - (price / budget) * 0.5)),
            )
            why.append("within budget")

        # Bedrooms.
        if req.get("bedrooms") is not None:
            difference = abs(
                float(row["bedrooms"])
                - float(req["bedrooms"])
            )

            points["Bedrooms"] = max(
                0.0, 25.0 - 10.0 * difference
            )

            if difference == 0:
                why.append("exact bedroom match")
            else:
                why.append("meets minimum bedroom requirement")

        # Property type.
        if req.get("propertyType"):
            matched = _property_type_match(
                row.get("propertyType"),
                req["propertyType"],
            )
            points["Property type"] = 15.0 if matched else 0.0

            if matched:
                why.append("property type matches")

        # Location.
        if req.get("city") or req.get("state"):
            matched = _location_match(row, req)
            points["Location"] = 10.0 if matched else 0.0

            if matched:
                why.append("location matches")

        # Requested amenities have already passed the hard filters.
        
        # Score amenities using available evidence.
        for amenity, label in [
            ("parking", "Parking"),
            ("security", "Security"),
        ]:
            if req.get(amenity) is True:
                status = _amenity_status(row, amenity)

                if status is True:
                    points[label] = 5.0
                    why.append(f"{amenity} evidence found")
                else:
                    points[label] = 0.0
                    why.append(
                        f"{amenity} not confirmed; verify with provider"
                    )

        score = (
            sum(points.values()) / active_weights * 100
            if active_weights > 0
            else 0.0
        )

        scores.append(round(min(100.0, score), 2))
        reasons.append(why)
        breakdowns.append(points)

    # Defensive check: each property must have one entry per result column.
    if not (
        len(out) == len(scores)
        == len(reasons) == len(breakdowns)
    ):
        raise ValueError(
            "Ranking error: property and scoring result counts differ."
        )

    out["match_score"] = scores
    out["match_reasons"] = reasons
    out["score_breakdown"] = breakdowns

    return out.sort_values(
        "match_score", ascending=False
    ).reset_index(drop=True)

