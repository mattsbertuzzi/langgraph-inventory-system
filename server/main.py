from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()

from graph import build_graph
from classes.classes import Category

app = FastAPI(title="Retail Demand Forecasting Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(","),
    allow_methods=["POST"],
    allow_headers=["*"],
)


class ForecastRequest(BaseModel):
    product_id: str
    start_date: date
    end_date: date
    latitude: float
    longitude: float
    category: Optional[Category] = None


@app.post("/forecast")
def forecast(req: ForecastRequest):
    graph = build_graph()
    state_input = {
        "product_id": req.product_id,
        "date_range": (req.start_date.isoformat(), req.end_date.isoformat()),
        "latitude": req.latitude,
        "longitude": req.longitude,
    }
    if req.category is not None:
        state_input["category"] = req.category
    result = graph.invoke(state_input)
    return {
        "predicted_quantity": result["predicted_quantity"],
        "confidence": result["confidence"],
    }
