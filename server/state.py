from typing import TypedDict, List, NotRequired, Annotated
from langgraph.graph.message import add_messages
import operator
from datetime import date

from classes.classes import DatedWeather, Weather, Category

class StockState(TypedDict):
    # Inputs
    product_id: str
    date_range: tuple[date, date]
    # Weather variables
    latitude: float
    longitude: float
    
    # Intermediary data
    sales_history: NotRequired[list[dict]]
    temperature_range: NotRequired[list[DatedWeather]]
    weather_conditions: NotRequired[list[DatedWeather]]
    item: NotRequired[str]
    category: NotRequired[Category]
    
    # Output
    predicted_quantity: NotRequired[int]
    confidence: NotRequired[float]
    messages: Annotated[list, add_messages]
    
    