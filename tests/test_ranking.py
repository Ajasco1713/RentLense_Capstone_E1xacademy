from services.demo_data import demo_properties
from services.parser import parse_requirements
from services.ranking import rank_properties


def test_austin_apartment_search_returns_exact_matches():
    req = parse_requirements(
        "I need a 2-bedroom apartment in Austin, Texas below $3000 per month with parking and security."
    )
    result = rank_properties(demo_properties(), req)
    assert not result.empty
    assert all(result["city"].str.lower() == "austin")
    assert all(result["propertyType"].str.lower() == "apartment")
    assert all(result["bedrooms"] >= 2)
    assert all(result["price"] <= 3000)


def test_dallas_search_does_not_return_austin():
    req = parse_requirements("I need a 2-bedroom apartment in Dallas, Texas below $3000")
    result = rank_properties(demo_properties(), req)
    assert not result.empty
    assert all(result["city"].str.lower() == "dallas")
