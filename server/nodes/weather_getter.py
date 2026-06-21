import requests
from datetime import datetime
from classes.classes import DatedWeather, Weather
from state import StockState

def parse_weathercode(code: int) -> Weather:
    if code == 0 or code in (1, 2, 3):
        return Weather.SUNNY.value
    elif code in (45, 48):
        return Weather.CLOUDY.value
    elif code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99):
        return Weather.RAINY.value
    elif code in (71, 73, 75, 77, 85, 86):
        return Weather.SNOWY.value
    else:
        raise ValueError(f"Unknown weathercode: {code}")

def get_7day_forecast(state: StockState) -> dict:
    url = 'https://api.open-meteo.com/v1/forecast'
    params = {
        'latitude': state.get('latitude'),
        'longitude': state.get('longitude'),
        'daily': ['weathercode', 'temperature_2m_max', 'temperature_2m_min'],
        'forecast_days': 7,
        'timezone': 'auto'
    }

    res = requests.get(url, params=params)
    res.raise_for_status()

    data = res.json()['daily']
    daily_forecasts = []

    for date, weather_condition, min_temp, max_temp in zip(
        data['time'],
        data['weathercode'],
        data['temperature_2m_min'],
        data['temperature_2m_max']
    ):
        daily_forecasts.append({
            'date': datetime.strptime(date, '%Y-%m-%d').date().isoformat(),
            'weather_condition': weather_condition,
            'min_temp': min_temp,
            'max_temp': max_temp,
        })

    return {
        'date_range': (daily_forecasts[0]['date'], daily_forecasts[-1]['date']),
        'temperature_range': [{'date': el['date'], 'data': (el['min_temp'], el['max_temp'])} for el in daily_forecasts],
        'weather_conditions': [{'date': el['date'], 'data': parse_weathercode(el['weather_condition'])} for el in daily_forecasts],
    }

    