# RentLense Capstone Project Documentation

## Chapter One — Problem Understanding

The project brief identifies rental searching as a fragmented process involving multiple sources, intermediaries, viewings, verification, negotiation and additional costs. RentLense addresses this by allowing a house seeker to describe requirements in natural language and receive ranked rental options.

### Objectives

1. Accept rental requirements in natural language.
2. Extract location, budget, property type, bedrooms, bathrooms and requested amenities.
3. Retrieve property data from RentCast when live mode is enabled.
4. Provide a controlled demo dataset for reliable presentation and testing.
5. Filter properties against explicit requirements.
6. Rank suitable properties using a transparent weighted matching algorithm.
7. Explain why a property matches.
8. Export ranked results as CSV.

## Chapter Two — Proposed Solution and System Design

```text
User
  ↓
Natural-language query
  ↓
Requirement parser
  ↓
Structured requirements
  ↓
RentCast API / Demo dataset
  ↓
Hard filters
  ↓
Weighted ranking
  ↓
Match explanation
  ↓
Streamlit results
```

### Structured requirement schema

- `city`
- `state`
- `zipCode`
- `max_price`
- `bedrooms`
- `bathrooms`
- `propertyType`
- `parking`
- `security`

### Ranking approach

The matcher considers six requirement groups:

| Requirement | Maximum weight |
|---|---:|
| Budget | 30 |
| Bedrooms | 25 |
| Property type | 15 |
| Location | 10 |
| Parking | 5 |
| Security | 5 |

The final score is normalized to a 0–100 percentage over the criteria that the user actually requested.

## Chapter Three — Implementation

### `app.py`

Provides the Streamlit interface, search controls, structured-requirement display, result cards, score breakdown and CSV export.

### `services/parser.py`

Performs lightweight natural-language information extraction using regular expressions and normalization rules. It supports common property types, US state names/codes, prices, bedrooms, bathrooms and ZIP codes.

### `services/rentcast.py`

Builds a RentCast query from structured requirements, performs the API request and converts the response to a pandas DataFrame. API failures are exposed as readable application errors.

### `services/ranking.py`

Applies explicit hard filters and calculates a transparent weighted match score. It also creates human-readable match reasons and a score breakdown.

### `services/demo_data.py`

Provides controlled Austin and Dallas listings so the end-to-end application can be demonstrated without a live API dependency.

## Chapter Four — Testing and Evaluation

### Test scenarios

1. Two-bedroom apartment in Austin under $3,000 with parking and security.
2. Two-bedroom apartment in Dallas under $3,000.
3. Bathroom requirement.
4. ZIP-code extraction.
5. No-result scenario after strict filtering.
6. Missing or invalid RentCast API key.
7. Demo mode with no API key.

### Suggested evaluation metrics

- Requirement extraction accuracy.
- Precision@K for returned relevant properties.
- End-to-end task success rate.
- API failure handling success.
- User-perceived usefulness of match explanations.

The automated tests in `tests/` cover core parser and ranking behavior. For the final presentation, the team should also record results from several realistic queries and discuss limitations.

## Chapter Five — Limitations and Future Work

### Current limitations

- The parser is deterministic and handles a defined set of language patterns rather than every possible natural-language expression.
- Demo data is intentionally small and fictional.
- Live property coverage depends on the external RentCast service and API access.
- Amenity detection is based on available listing text/fields.
- The current MVP does not implement maps, conversational refinement or vector search.

### Future improvements

The project brief identifies optional extensions including semantic/vector search, map visualization, conversational refinement, property comparison and similar-property search. These can be added without changing the core workflow.

## Deployment

The application is packaged as a normal Python/Streamlit project. It can be run locally in VS Code and can later be deployed to a Streamlit-compatible hosting environment after configuring the RentCast API key securely.
