from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date
from dotenv import load_dotenv
import os

load_dotenv()

from graph import build_graph

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


@app.post("/forecast")
def forecast(req: ForecastRequest):
    graph = build_graph()
    result = graph.invoke({
        "product_id": req.product_id,
        "date_range": (req.start_date.isoformat(), req.end_date.isoformat()),
        "latitude": req.latitude,
        "longitude": req.longitude,
    })
    return {
        "predicted_quantity": result["predicted_quantity"],
        "confidence": result["confidence"],
    }
