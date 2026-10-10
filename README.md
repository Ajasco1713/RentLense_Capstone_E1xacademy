# RentLense — AI & Machine Learning Capstone

**RentLense** is an intelligent rental-property search assistant. It accepts a user's rental requirements in natural language, converts them into structured requirements, retrieves rental listings from RentCast or a controlled demo dataset, filters candidates, ranks them using a weighted matching algorithm, and explains why each property matches.

## Capstone workflow

```text
Natural-language request
        ↓
Requirement parser
        ↓
Structured requirements
        ↓
RentCast API / Demo data
        ↓
Hard requirement filtering
        ↓
Weighted matching + ranking
        ↓
Match explanations
        ↓
Results + CSV export
```

This directly follows the project brief's required workflow: natural-language requirements → structured requirements → property API → ranking → best matches and comparison-ready results.

## 1. Requirements

- Python 3.10 or newer
- VS Code
- Internet connection when installing packages or using RentCast
- A RentCast API key for live API mode

## 2. Open in VS Code

Extract the ZIP and open the **RentLense_Capstone** folder in VS Code.

Open the VS Code terminal and run:

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Then open `.env` and add your RentCast key:

```text
RENTCAST_API_KEY=your_real_api_key_here
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## 3. Run the application

```bash
streamlit run app.py
```

Streamlit will display a local address, normally:

```text
http://localhost:8501
```

## 4. Demo without an API key

Keep **Use demo data** switched on. The built-in dataset contains Austin and Dallas examples, so the complete workflow can be demonstrated without a live API key.

Try:

```text
I need a 2-bedroom apartment in Austin, Texas below $3000 per month with parking and security.
```

or:

```text
I need a 2-bedroom apartment in Dallas, Texas below $3000 with parking and security.
```

## 5. Live RentCast mode

Turn off **Use demo data** after adding a valid `RENTCAST_API_KEY` to `.env`.

The application sends the structured location, bedroom, bathroom, budget and property-type requirements to RentCast and then applies the same ranking/explanation stage.

## 6. Run tests

```bash
pytest -q
```

The tests cover requirement extraction and ranking/filtering scenarios.

## 7. Project structure

```text
RentLense_Capstone/
│
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── PROJECT_DOCUMENTATION.md
│
├── services/
│   ├── __init__.py
│   ├── parser.py
│   ├── rentcast.py
│   ├── ranking.py
│   └── demo_data.py
│
└── tests/
    ├── test_parser.py
    └── test_ranking.py
```

## 8. AI component

The MVP's AI-style intelligence is the natural-language requirement extraction and requirement-aware matching workflow. The parser identifies entities and constraints such as location, budget, bedrooms, bathrooms, property type, parking and security. The ranking layer then uses those structured requirements to make a transparent recommendation instead of generating a generic answer.

The architecture can later be extended with an LLM structured-output parser, semantic/vector search, conversational refinement, maps, property comparison and similar-property recommendations.

## 9. Important security rule

Never commit `.env` or expose your RentCast API key in source code, screenshots or GitHub.
