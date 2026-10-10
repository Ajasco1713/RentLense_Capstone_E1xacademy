"""Natural-language rental requirement extraction.

The parser is deliberately dependency-light so the MVP works without an LLM.
It extracts the structured fields required by the capstone workflow.
"""
import re
from typing import Any, Dict, Optional

STATE_ALIASES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "florida": "FL",
    "georgia": "GA", "illinois": "IL", "indiana": "IN", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "missouri": "MO",
    "nevada": "NV", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "virginia": "VA", "washington": "WA", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC", "dc": "DC",
}
STATE_CODES = set(STATE_ALIASES.values())

PROPERTY_TYPES = {
    "apartment": "Apartment",
    "condo": "Condo",
    "condominium": "Condo",
    "townhouse": "Townhouse",
    "townhome": "Townhouse",
    "house": "Single Family",
    "single family": "Single Family",
}


def _number(text: str) -> float:
    return float(text.replace(",", ""))


def _extract_price(text: str) -> Optional[float]:
    patterns = [
        r"(?:below|under|less than|up to|max(?:imum)?(?:\s+of)?)\s*\$?\s*([\d,]+(?:\.\d+)?)",
        r"(?:budget\s*(?:of|is|:)?|maximum\s*budget\s*(?:of|is|:)?)\s*\$?\s*([\d,]+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return _number(match.group(1))
    return None


def _extract_city_state(text: str):
    # Handles "Austin, Texas" without consuming the next phrase such as "below $3000".
    match = re.search(
        r"(?:in|around|near|at)\s+([A-Za-z][A-Za-z .'-]{1,40}?),\s*([A-Za-z .'-]+?)(?=\s+(?:below|under|less|with|and|for|near|around|$))",
        text,
        re.I,
    )
    if match:
        city = re.sub(r"\s+", " ", match.group(1)).strip().title()
        state_raw = re.sub(r"\s+", " ", match.group(2)).strip().lower()
        return city, STATE_ALIASES.get(state_raw, state_raw.upper())

    # Fallback for a known two-letter state code.
    match = re.search(
        r"(?:in|around|near|at)\s+([A-Za-z][A-Za-z .'-]{1,40}?),\s*([A-Za-z]{2})(?=\s|$)",
        text,
        re.I,
    )
    if match and match.group(2).upper() in STATE_CODES:
        return match.group(1).strip().title(), match.group(2).upper()

    return None, None


def parse_requirements(query: str) -> Dict[str, Any]:
    """Convert a natural-language rental request into structured requirements."""
    text = query.strip()
    lower = text.lower()

    result: Dict[str, Any] = {
        "raw_query": text,
        "city": None,
        "state": None,
        "zipCode": None,
        "max_price": _extract_price(text),
        "bedrooms": None,
        "bathrooms": None,
        "propertyType": None,
        "parking": "parking" in lower,
        "security": "security" in lower or "secure" in lower,
    }

    bedroom = re.search(r"\b(\d+)\s*[- ]?bed(?:room)?s?\b", lower)
    if bedroom:
        result["bedrooms"] = int(bedroom.group(1))

    bathroom = re.search(r"\b(\d+(?:\.\d+)?)\s*[- ]?bath(?:room)?s?\b", lower)
    if bathroom:
        value = float(bathroom.group(1))
        result["bathrooms"] = int(value) if value.is_integer() else value

    city, state = _extract_city_state(text)
    result["city"] = city
    result["state"] = state

    zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", text)
    if zip_match:
        result["zipCode"] = zip_match.group(1)

    for phrase, normalized in sorted(PROPERTY_TYPES.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(phrase)}\b", lower):
            result["propertyType"] = normalized
            break

    return result
