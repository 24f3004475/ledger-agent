
from fastapi import FastAPI
from pydantic import BaseModel
import json
from datetime import datetime
from zoneinfo import ZoneInfo

app = FastAPI()

# Load order data once when the server starts
with open("orders.json", "r", encoding="utf-8-sig") as file:
    orders = json.load(file)

# Exchange rates supplied by the assignment
USD_RATES = {
    "USD": 1.0,
    "EUR": 1.09,
    "INR": 0.01198
}

class QuestionRequest(BaseModel):
    question: str


def prepare_orders():
    # Keep the latest version of each order ID
    latest = {}

    for order in orders:
        order_id = order["id"]

        if order_id not in latest:
            latest[order_id] = order
        else:
            old_date = datetime.fromisoformat(
                latest[order_id]["updated_at"].replace("Z", "+00:00")
            )
            new_date = datetime.fromisoformat(
                order["updated_at"].replace("Z", "+00:00")
            )

            if new_date > old_date:
                latest[order_id] = order

    return list(latest.values())


current_orders = prepare_orders()


@app.get("/")
def home():
    return {"message": "Ledger Agent is running"}


@app.get("/health")
def health():
    return {"status": "ok", "orders_loaded": len(current_orders)}


@app.post("/")
def answer_question(request: QuestionRequest):
    question = request.question.lower()

    # Revenue includes only paid orders
    paid_orders = [
        order for order in current_orders
        if order["status"].lower() == "paid"
    ]

    # Convert every paid order amount into USD
    revenue_usd = sum(
        float(order["amount"]) *
        USD_RATES.get(order["currency"].upper(), 0)
        for order in paid_orders
    )

    if "revenue" in question or "sales" in question:
        answer = round(revenue_usd, 2)

    elif "refund" in question:
    refunded = [
        order for order in current_orders
        if order["status"].lower() == "refunded"
    ]

    # Filter by region if the question specifies one
    if "south" in question:
        refunded = [
            order for order in refunded
            if order["region"].strip().lower() == "south"
        ]

    # Filter by the business date in March 2026
    if "march" in question and "2026" in question:
        march_orders = []

        for order in refunded:
            created = datetime.fromisoformat(
                order["created_at"].replace("Z", "+00:00")
            )

            created = created.astimezone(ZoneInfo("Asia/Kolkata"))

            if created.year == 2026 and created.month == 3:
                march_orders.append(order)

        refunded = march_orders

    answer = len(refunded)

    elif "customer" in question:
        answer = len(set(
            order["customer"] for order in current_orders
        ))

    elif "order" in question:
        answer = len(current_orders)

    else:
        answer = (
            "I could not identify the requested calculation. "
            "Try asking about revenue, refunds, customers, or orders."
        )

    return {"answer": answer}
