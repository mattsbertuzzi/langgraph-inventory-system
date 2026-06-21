from enum import Enum
from pydantic import BaseModel
from datetime import date

class Weather(str, Enum):
    CLOUDY = 'Cloudy'
    SUNNY = 'Sunny'
    RAINY = 'Rainy'
    SNOWY = 'Snowy'
    
class DatedWeather(BaseModel):
    date: date
    data: tuple[float, float] | Weather

class Category(str, Enum):
    BAKERY = "Bakery"
    DAIRY = "Dairy"
    DRINKS = "Drinks"
    FROZEN = "Frozen"
    FRUIT_AND_VEG = "Fruit & Veg"
    HOUSEHOLD = "Household"
    MEAT_AND_FISH = "Meat & Fish"
    PANTRY = "Pantry"
    PERSONAL_CARE = "Personal Care"
    SNACKS = "Snacks"