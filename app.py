import json
import os
import urllib.error
import urllib.request

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "orders.json")
HANDLERS = ["王芳", "李强", "赵敏", "陈浩"]
NOTIFICATION_SERVICE_URL = os.environ.get(
    "NOTIFICATION_SERVICE_URL", "http://localhost:8081"
).rstrip("/")


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


@app.route("/orders")
def orders_page():
    return render_template("orders.html")


@app.route("/api/order/<order_id>")
def api_get_order(order_id):
    order = find_order(order_id)
    if order is None:
        return jsonify({"success": False, "message": "未找到该订单"}), 404
    return jsonify({"success": True, "data": order})


@app.route("/api/orders")
def api_list_orders():
    orders = load_orders()
    status_filter = (request.args.get("status") or "").strip()
    keyword = (request.args.get("q") or "").strip().lower()
    if status_filter:
        orders = [o for o in orders if o.get("status") == status_filter]
    if keyword:
        orders = [
            o for o in orders
            if keyword in o.get("order_id", "").lower()
            or keyword in o.get("customer", {}).get("name", "").lower()
        ]
    page = max(int(request.args.get("page", 1)), 1)
    page_size = max(min(int(request.args.get("page_size", 20)), 100), 1)
    total = len(orders)
    start = (page - 1) * page_size
    page_data = orders[start: start + page_size]
    result = [
        {
            "order_id": o["order_id"],
            "status": o["status"],
            "total": o["total"],
            "customer_name": o.get("customer", {}).get("name", ""),
            "created_at": o.get("created_at", ""),
        }
        for o in page_data
    ]
    return jsonify({"success": True, "data": result, "total": total, "page": page, "page_size": page_size})


@app.route("/api/orders/suggest")
def api_suggest_orders():
    orders = load_orders()
    return jsonify({"success": True, "data": [{"order_id": o["order_id"], "status": o["status"]} for o in orders]})


@app.route("/api/handlers")
def api_handlers():
    return jsonify({"success": True, "data": HANDLERS})


def send_reminder(order_id, handler):
    service_url = NOTIFICATION_SERVICE_URL
    if service_url and not service_url.startswith(("http://", "https://")):
        service_url = "http://" + service_url
    payload = json.dumps({"order_id": order_id, "handler": handler}).encode("utf-8")
    request_obj = urllib.request.Request(
        service_url + "/api/reminders",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=5) as response:
            return json.loads(response.read().decode("utf-8")), response.status
    except urllib.error.HTTPError as error:
        return {"success": False, "message": "催办服务返回错误"}, error.code
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return {"success": False, "message": "无法连接催办服务"}, 502


@app.route("/api/reminders", methods=["POST"])
def api_send_reminder():
    data = request.get_json(silent=True) or {}
    order_id = (data.get("order_id") or "").strip()
    handler = (data.get("handler") or "").strip()

    if not order_id or not handler:
        return jsonify({"success": False, "message": "订单编号和处理者不能为空"}), 400
    if find_order(order_id) is None:
        return jsonify({"success": False, "message": "未找到该订单"}), 404
    if handler not in HANDLERS:
        return jsonify({"success": False, "message": "处理者不在可选列表中"}), 400

    result, status_code = send_reminder(order_id, handler)
    if not result.get("success"):
        return jsonify(result), status_code
    return jsonify({"success": True, "data": result})


if __name__ == "__main__":
    app.run(debug=True, port=8080)
