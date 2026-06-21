from dotenv import load_dotenv
load_dotenv()
import os
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from classes.classes import Weather, Category
from utils.date_helpers import get_month, get_week_of_year, get_day_of_month, get_day_of_week

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
SALES_HISTORY_SHEET = 'sales_history'

_sheet_key = os.getenv('GOOGLE_SHEET_KEY')
if not _sheet_key:
    raise RuntimeError('GOOGLE_SHEET_KEY environment variable is not set.')

_credentials_path = Path(__file__).parent.parent / 'google_sheet_credentials.json'
creds = Credentials.from_service_account_file(str(_credentials_path), scopes=SCOPES)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(_sheet_key)


def _get_records() -> list[dict]:
    return spreadsheet.worksheet(SALES_HISTORY_SHEET).get_all_records()


# --- Date-related getters ---

def get_by_month_day(day: int) -> list[dict]:
    return [s for s in _get_records() if get_day_of_month(s['date']) == day]

def get_by_weekday(weekday: int) -> list[dict]:
    return [s for s in _get_records() if get_day_of_week(s['date']) == weekday]

def get_by_week(week: int) -> list[dict]:
    return [s for s in _get_records() if get_week_of_year(s['date']) == week]

def get_by_month(month: int) -> list[dict]:
    return [s for s in _get_records() if get_month(s['date']) == month]


# --- Weather-related getters ---

def get_by_temperature_range(min_c: float, max_c: float) -> list[dict]:
    return [s for s in _get_records() if min_c <= float(s['temperature_c']) <= max_c]

def get_by_weather(weather: Weather) -> list[dict]:
    return [s for s in _get_records() if s['weather'] == weather.value]



# --- Product-related getters ---

def get_sales_by_category(cat: Category) -> list[dict]:
    return [s for s in _get_records() if s['category'] == cat.value]