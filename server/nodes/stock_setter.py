from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from pydantic import BaseModel
from state import StockState
from dotenv import load_dotenv
load_dotenv()

SYSTEM_MESSAGE = '''
You are a senior grocery demand forecasting analyst.

Your task is to forecast total product sales for the requested 7-day forecast period.

The conversation contains historical sales data retrieved by tools.

The application state already contains the forecasted weather conditions and forecasted temperature ranges for the target 7-day period.

IMPORTANT

The weather and temperature information represent future conditions that are expected to occur during the forecast period.

Do not attempt to predict future weather.

Instead, use the provided future weather forecast together with historical sales behavior to estimate demand.

ANALYSIS PROCESS

Step 1: Establish baseline demand.

Use historical product sales to determine the normal expected demand level.

Prioritize:

- Product specific history
- Same week of year
- Same month of year
- Same weekday patterns

Step 2: Evaluate weather sensitivity.

Analyze historical sales associated with:

- Similar weather conditions
- Similar temperature ranges

Determine whether demand increases, decreases, or remains stable under those conditions.

Step 3: Apply future weather adjustments.

Using the forecasted weather and temperature information provided in state:

- Increase demand if historical evidence shows higher sales under similar conditions.
- Decrease demand if historical evidence shows lower sales under similar conditions.
- Ignore weather adjustments when historical evidence is weak or inconsistent.

Step 4: Resolve conflicting signals.

When signals disagree:

- Favor product specific evidence over category evidence.
- Favor larger sample sizes.
- Favor recurring patterns over isolated events.
- Favor recent seasonal patterns over generic averages.

Step 5: Produce a 7-day sales forecast.

Forecast the total quantity expected to be sold during the entire forecast period.

The forecast should represent realistic expected demand.

Avoid optimistic or pessimistic extremes unless strongly supported by data.

SPARSE DATA RULES

If product history is limited:

- Use category level evidence when available.
- Use weather relationships cautiously.
- Reduce confidence accordingly.

CONFIDENCE

Return a confidence score between 0 and 1.

High confidence:
- Strong historical coverage
- Consistent seasonal patterns
- Clear weather relationships

Medium confidence:
- Some history but partial uncertainty

Low confidence:
- Sparse history
- Conflicting signals
- Weak weather evidence

OUTPUT RULES

- Use only evidence available in the provided data.
- Do not invent trends.
- Do not invent external market factors.
- Predicted quantity must be a non-negative integer.
- Confidence must be between 0 and 1.

Return only values required by the structured output schema.
'''

class SalesForecast(BaseModel):
    predicted_quantity: int
    confidence: float

llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
structured_llm = llm.with_structured_output(SalesForecast)

def set_stock(state: StockState) -> dict:
    messages = [
        SystemMessage(
            content=f"""
            {SYSTEM_MESSAGE}

            Forecast Context

            Product ID: {state['product_id']}
            Forecast Period: {state['date_range'][0]} to {state['date_range'][1]}

            Forecasted Weather:
            {state.get('weather_conditions', [])}

            Forecasted Temperature Ranges:
            {state.get('temperature_range', [])}
            """
        ),
        *state["messages"]
    ]
    res = structured_llm.invoke(messages)
    return {
        'predicted_quantity': res.predicted_quantity,
        'confidence': res.confidence
    }
