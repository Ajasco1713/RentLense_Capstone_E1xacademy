
from services.llm_service import extract_rental_requirements

request = (
    "Find a two-bedroom apartment in Austin, Texas, "
    "under $2,000 per month, with parking and security."
)

try:
    result = extract_rental_requirements(request)
    print("Groq integration successful!")
    print(result)

except Exception as exc:
    print(f"Groq test failed: {exc}")