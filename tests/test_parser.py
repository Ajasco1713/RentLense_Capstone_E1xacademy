from services.parser import parse_requirements


def test_parser_extracts_austin_query():
    req = parse_requirements(
        "I need a 2-bedroom apartment in Austin, Texas below $3000 per month with parking and security."
    )
    assert req["city"] == "Austin"
    assert req["state"] == "TX"
    assert req["max_price"] == 3000
    assert req["bedrooms"] == 2
    assert req["propertyType"] == "Apartment"
    assert req["parking"] is True
    assert req["security"] is True


def test_parser_extracts_bathrooms_and_zip():
    req = parse_requirements("3 bedroom, 2 bathroom house near Dallas, TX 75201 under $4,000")
    assert req["bedrooms"] == 3
    assert req["bathrooms"] == 2
    assert req["city"] == "Dallas"
    assert req["state"] == "TX"
    assert req["zipCode"] == "75201"
    assert req["max_price"] == 4000
