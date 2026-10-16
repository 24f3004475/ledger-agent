
from fastapi import FastAPI
from pydantic import BaseModel
import json
from datetime import datetime
from zoneinfo import ZoneInfo

app = FastAPI()

with open("orders.json", "r", encoding="utf-8-sig") as file:
    orders = json.load(file)

USD_RATES = {
    "USD": 1.0,
    "EUR": 1.09,
    "INR": 0.01198
}


class QuestionRequest(BaseModel):
    question: str


def parse_date(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(ZoneInfo("Asia/Kolkata"))


def prepare_orders():
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
    return {
        "status": "ok",
        "orders_loaded": len(current_orders)
    }


@app.post("/")
def answer_question(request: QuestionRequest):
    question = request.question.lower()
    filtered = current_orders

    # Filter by region when specified
    regions = ["south", "north", "east", "west", "central"]
    for region in regions:
        if region in question:
            filtered = [
                order for order in filtered
                if order.get("region", "").strip().lower() == region
            ]
            break

    # Filter by month and year when specified
    months = {
        "january": 1, "february": 2, "march": 3,
        "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9,
        "october": 10, "november": 11, "december": 12
    }

    target_month = None
    for month_name, month_number in months.items():
        if month_name in question:
            target_month = month_number
            break

    target_year = None
    for year in range(2020, 2036):
        if str(year) in question:
            target_year = year
            break

    if target_month and target_year:
        dated_orders = []

        for order in filtered:
            date_value = order.get("created_at")
            if date_value:
                order_date = parse_date(date_value)

                if (
                    order_date.month == target_month
                    and order_date.year == target_year
                ):
                    dated_orders.append(order)

        filtered = dated_orders

    # Count refunded orders after applying filters
    if "refund" in question:
        answer = sum(
            1 for order in filtered
            if order.get("status", "").lower() == "refunded"
        )

    # Count unique customers
    elif "customer" in question:
        answer = len({
            order.get("customer")
            for order in filtered
            if order.get("customer") is not None
        })

    # Revenue and sales: paid orders only, converted to USD
    elif "revenue" in question or "sales" in question:
        answer = round(sum(
            float(order.get("amount", 0))
            * USD_RATES.get(order.get("currency", "USD").upper(), 0)
            for order in filtered
            if order.get("status", "").lower() == "paid"
        ), 2)

    # Count orders
    elif "order" in question:
        answer = len(filtered)

    # Product questions
    elif "product" in question:
        product_counts = {}
        for order in filtered:
            product = order.get("product", "Unknown")
            product_counts[product] = product_counts.get(product, 0) + 1

        answer = product_counts

    else:
        answer = (
            "I could not identify the requested calculation. "
            "Try asking about revenue, refunds, customers, orders, or products."
        )

    return {"answer": answer}
