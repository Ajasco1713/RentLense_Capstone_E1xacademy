
import json
import os

from groq import Groq


def extract_rental_requirements(query: str) -> dict:
    """Extract structured rental requirements using Groq AI."""

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is missing. Add it to your environment or .env file."
        )

    client = Groq(api_key=api_key)

    prompt = f"""
Extract rental search requirements from the user's request.

Return only a valid JSON object with these keys:
city, state, zipCode, max_monthly_rent,
bedrooms, bathrooms, propertyType, parking, security.

Use null for unknown text or numeric values.
Use true or false for parking and security.

Rules:
- max_monthly_rent must be the monthly rental budget.
- If the user gives an annual budget, divide it by 12.
- Do not confuse a monthly budget with an annual budget.
- Return numeric values for rent, bedrooms, and bathrooms.
- Use a two-letter US state abbreviation when identifiable.
- Do not invent missing requirements.

User request: {query}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract rental requirements and return "
                    "a valid JSON object only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    if not isinstance(result, dict):
        raise ValueError("Groq returned an invalid response.")

    return result