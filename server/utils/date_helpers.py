from datetime import datetime

DATE_FORMAT = '%Y-%m-%d'

def get_day_of_month(date: str) -> int:
    return int(datetime.strptime(date, DATE_FORMAT).day)

def get_day_of_week(date: str) -> int:
    # datetime.date.weekday() ranges 0 - 6; add +1 for uniformity
    return int(datetime.strptime(date, DATE_FORMAT).weekday()) + 1

def get_week_of_year(date: str) -> int:
    return int(datetime.strptime(date, DATE_FORMAT).isocalendar().week)

def get_month(date: str) -> int:
    return int(datetime.strptime(date, DATE_FORMAT).month)