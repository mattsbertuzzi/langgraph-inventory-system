# langgraph-inventory-system

A LangGraph agent that generates weather-adjusted, evidence-based 7-day demand forecasts for retail SKUs.

## Business problem

Grocery retailers set replenishment quantities against forecasts that typically ignore short-term weather signals, even though precipitation, temperature, and sky conditions measurably shift demand across categories — from beverages and produce to frozen goods and personal care. Static averages and manual buyer judgment leave money on the table through overstock write-offs and lost sales from stockouts.

This agent combines real-time weather forecasts with historical sales patterns to produce a per-SKU quantity estimate and a confidence score that downstream replenishment or ordering logic can act on programmatically.

## Architecture

The system is a four-node LangGraph `StateGraph`:

```
START → get_weather → call_tools ⇄ tools → set_stocks → END
```

| Node | Role |
|---|---|
| `get_weather` | Fetches a 7-day daily forecast (weather code, min/max temperature) from the Open-Meteo API. No authentication required. |
| `call_tools` | A data-collection agent (GPT-4o-mini) that iteratively queries historical sales across five dimensions: month of year, week of year, day pattern, weather condition, and temperature range. Loops until sufficient evidence is gathered. |
| `tools` | Executes LangChain tool calls against a Google Sheets sales history via `gspread`. Each tool filters by `product_id` before returning records. |
| `set_stocks` | A synthesis agent (GPT-4o-mini, structured output) that applies the collected evidence to the forecasted weather and returns a `predicted_quantity` (int) and `confidence` (0.0–1.0). |

The `call_tools ⇄ tools` loop is managed by a conditional edge: if the last LLM message contains tool calls, control passes to `tools` and back; otherwise it proceeds to `set_stocks`.

## Tech stack

- **LangGraph / LangChain** — agent orchestration and tool-calling loop
- **OpenAI GPT-4o-mini** — data collection and demand synthesis
- **Google Sheets + gspread** — historical sales store
- **Open-Meteo API** — free daily weather forecast (no API key required)
- **FastAPI + Uvicorn** — REST API layer
- **Python 3.11+**

## Setup

### Prerequisites

- Python 3.11+
- An OpenAI API key
- A Google Cloud service account with Sheets and Drive access enabled
- A Google Sheet containing the sales history (schema below)

### Install dependencies

```bash
cd server
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure environment

```bash
cp server/.env.example server/.env
```

Edit `server/.env` with your values. Place your Google service account JSON file at `server/google_sheet_credentials.json` (excluded from version control).

### Sales history schema

The Google Sheet worksheet named `sales_history` must contain these columns:

| Column | Type | Example |
|---|---|---|
| `date` | `YYYY-MM-DD` | `2024-06-06` |
| `product_id` | string | `P049` |
| `item` | string | `Sparkling Water 1L` |
| `quantity` | int | `4` |
| `category` | string | `Drinks` |
| `weather` | string | `Sunny`, `Cloudy`, `Rainy`, or `Snowy` |
| `temperature_c` | float | `21.5` |

Valid category values: `Bakery`, `Dairy`, `Drinks`, `Frozen`, `Fruit & Veg`, `Household`, `Meat & Fish`, `Pantry`, `Personal Care`, `Snacks`.

A 5,000-record sample dataset is provided in `data/grocery_sales.csv`.

### Run the API

```bash
cd server
uvicorn main:app --reload
```

### Request example

```bash
curl -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "P049",
    "start_date": "2026-06-21",
    "end_date": "2026-06-27",
    "latitude": 51.5074,
    "longitude": -0.1278
  }'
```

Response:

```json
{
  "predicted_quantity": 42,
  "confidence": 0.78
}
```

## Project structure

```
server/
├── graph.py              # LangGraph StateGraph definition
├── state.py              # TypedDict state schema
├── main.py               # FastAPI entry point
├── nodes/
│   ├── weather_getter.py # Open-Meteo API call
│   ├── tool_caller.py    # Data-collection LLM agent
│   └── stock_setter.py   # Demand synthesis LLM agent
├── tools/
│   └── forecast_tools.py # LangChain @tool definitions
├── utils/
│   ├── db_helpers.py     # Google Sheets data access layer
│   └── date_helpers.py   # Date parsing helpers
├── classes/
│   └── classes.py        # Enums: Weather, Category; model: DatedWeather
└── requirements.txt
data/
└── grocery_sales.csv     # 5,000-record sample dataset
```

---

Built by Matteo Bertuzzi — AI engineer working at the intersection of consumer behavior, AI, and retail intelligence.

[matteobertuzzi.com](#) · [LinkedIn](#)
