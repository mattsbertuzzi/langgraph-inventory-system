from state import StockState
from utils.db_helpers import write_forecast


def record_forecast(state: StockState) -> dict:
    write_forecast(
        product_id=state['product_id'],
        date_range=state['date_range'],
        predicted_quantity=state['predicted_quantity'],
        confidence=state['confidence'],
    )
    return {}
