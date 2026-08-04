import json
import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "orders.json")


def load_orders():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def find_order(order_id):
    order_id = (order_id or "").strip()
    if not order_id:
        return None
    for order in load_orders():
        if order.get("order_id", "").lower() == order_id.lower():
            return order
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/order/<order_id>")
def api_get_order(order_id):
    order = find_order(order_id)
    if order is None:
        return jsonify({"success": False, "message": "未找到该订单"}), 404
    return jsonify({"success": True, "data": order})


@app.route("/api/orders/suggest")
def api_suggest_orders():
    orders = load_orders()
    return jsonify({"success": True, "data": [{"order_id": o["order_id"], "status": o["status"]} for o in orders]})


if __name__ == "__main__":
    app.run(debug=True, port=5555)
