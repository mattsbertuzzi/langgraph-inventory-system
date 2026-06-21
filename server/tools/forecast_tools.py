from langchain_core.tools import tool
from classes.classes import Weather, Category
from utils.db_helpers import get_by_month, get_by_week, get_by_month_day, get_by_weekday, get_by_weather, get_by_temperature_range
from typing import NotRequired, Literal

@tool
def get_sales_by_month(
    month: int,
    product_id: str | None = None,
    category: Category | None = None
    ) -> list[dict]:
    ''' Get all sales by month of year, with optional product_id and product category.
    - If product_id not None, sales are filtered by product_id.
    - If category not None, sales are filtered by category.
    - if product_id == None and category == None, all monthly sales are returned.
    Args:
    month: Month of year (numeric value) to get sales for (required)
    product_id: Product ID for which to filter sales (optional)
    category: Category for which to filter sales (optional)
    '''
    monthly_sales = get_by_month(month)
    if product_id:
        monthly_sales = [s for s in monthly_sales if product_id == s['product_id']]
    if category:
        monthly_sales = [s for s in monthly_sales if category.value == s['category']]
    return monthly_sales

@tool
def get_sales_by_week(
    week: int,
    product_id: str | None = None,
    category: Category | None = None
    ) -> list[dict]:
    ''' Get all sales by week of year, with optional product_id and product category.
    - If product_id not None, sales are filtered by product_id.
    - If category not None, sales are filtered by category.
    - if product_id == None and category == None, all weekly sales are returned.
    Args:
    week: Week of year (numeric value) to get sales for (required)
    product_id: Product ID for which to filter sales (optional)
    category: Category for which to filter sales (optional)
    '''
    weekly_sales = get_by_week(week)
    if product_id:
        weekly_sales = [s for s in weekly_sales if product_id == s['product_id']]
    if category:
        weekly_sales = [s for s in weekly_sales if category.value == s['category']]
    return weekly_sales

@tool
def get_sales_by_day(
    day: int,
    day_type: Literal['month_day', 'weekday'],
    product_id: str | None = None,
    category: Category | None = None
    ) -> list[dict]:
    ''' Get all sales by day of month or weekday, with optional product_id and product category.
    - If product_id not None, sales are filtered by product_id.
    - If category not None, sales are filtered by category.
    - if product_id == None and category == None, all monthly sales are returned.
    Args:
    day: Day (numeric value) to get sales for. If weekday, 1 = Monday and 7 = Sunday (required)
    day_type: month_day if filtering by day of month. weekday if filtering by weekday (required)
    product_id: Product ID for which to filter sales (optional)
    category: Category for which to filter sales (optional)
    '''
    daily_sales = get_by_month_day(day) if day_type == 'month_day' else get_by_weekday(day)
    if product_id:
        daily_sales = [s for s in daily_sales if product_id == s['product_id']]
    if category:
        daily_sales = [s for s in daily_sales if category.value == s['category']]
    return daily_sales

@tool
def get_sales_by_weather(
    weather: Weather,
    product_id: str | None = None,
    category: Category | None = None
    ) -> list[dict]:
    ''' Get all sales by weather conditions, with optional product_id and product category.
    - If product_id not None, sales are filtered by product_id.
    - If category not None, sales are filtered by category.
    - if product_id == None and category == None, all monthly sales are returned.
    Args:
    weather: Weather condition to get sales for
    product_id: Product ID for which to filter sales (optional)
    category: Category for which to filter sales (optional)
    '''
    sales = get_by_weather(weather)
    if product_id:
        sales = [s for s in sales if product_id == s['product_id']]
    if category:
        sales = [s for s in sales if category.value == s['category']]
    return sales

@tool
def get_sales_by_temperature_range(
    min_temp: float,
    max_temp: float,
    product_id: str | None = None,
    category: Category | None = None
    ) -> list[dict]:
    ''' Get all sales within temperature range, with optional product_id and product category.
    - If product_id not None, sales are filtered by product_id.
    - If category not None, sales are filtered by category.
    - if product_id == None and category == None, all monthly sales are returned.
    Args:
    min_temp: Minimum temperature of filter range
    max_temp: Maximum temperature of filter range
    product_id: Product ID for which to filter sales (optional)
    category: Category for which to filter sales (optional)
    '''
    sales = get_by_temperature_range(min_temp, max_temp)
    if product_id:
        sales = [s for s in sales if product_id == s['product_id']]
    if category:
        sales = [s for s in sales if category.value == s['category']]
    return sales