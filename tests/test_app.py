import os
import sys
import unittest
from unittest import mock


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import app as app_module
from app import HANDLERS, app, find_order, load_orders


class LoadOrdersTestCase(unittest.TestCase):
    def test_load_orders_returns_real_data(self):
        orders = load_orders()
        self.assertIsInstance(orders, list)
        self.assertTrue(orders)
        self.assertIn("order_id", orders[0])
        self.assertIn("status", orders[0])

    def test_load_orders_returns_empty_when_file_missing(self):
        missing_path = os.path.join(PROJECT_ROOT, "data", "orders-missing.json")
        with mock.patch.object(app_module, "DATA_FILE", missing_path):
            self.assertEqual(load_orders(), [])


class FindOrderTestCase(unittest.TestCase):
    def test_find_order_matches_exact_id(self):
        order = find_order("ORD-20260801-001")
        self.assertIsNotNone(order)
        self.assertEqual(order["order_id"], "ORD-20260801-001")

    def test_find_order_is_case_insensitive_and_trims_whitespace(self):
        order = find_order("  ord-20260801-001  ")
        self.assertIsNotNone(order)
        self.assertEqual(order["order_id"], "ORD-20260801-001")

    def test_find_order_blank_returns_none(self):
        self.assertIsNone(find_order(""))
        self.assertIsNone(find_order("   "))
        self.assertIsNone(find_order(None))

    def test_find_order_unknown_returns_none(self):
        self.assertIsNone(find_order("ORD-NOT-EXISTS"))


class FlaskApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_index_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("订单查询系统".encode("utf-8"), response.data)

    def test_api_get_order_found(self):
        response = self.client.get("/api/order/ORD-20260801-001")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["order_id"], "ORD-20260801-001")

    def test_api_get_order_not_found(self):
        response = self.client.get("/api/order/ORD-NOT-EXISTS")
        self.assertEqual(response.status_code, 404)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertIn("未找到该订单", payload["message"])

    def test_orders_page_renders(self):
        response = self.client.get("/orders")
        self.assertEqual(response.status_code, 200)
        self.assertIn("订单总览".encode("utf-8"), response.data)

    def test_api_list_orders_returns_all(self):
        response = self.client.get("/api/orders")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertIn("data", payload)
        self.assertIn("total", payload)
        self.assertGreater(payload["total"], 0)
        first = payload["data"][0]
        for key in ("order_id", "status", "total", "customer_name", "created_at"):
            self.assertIn(key, first)

    def test_api_list_orders_filter_by_status(self):
        response = self.client.get("/api/orders?status=已发货")
        payload = response.get_json()
        self.assertTrue(payload["success"])
        for item in payload["data"]:
            self.assertEqual(item["status"], "已发货")

    def test_api_list_orders_filter_by_keyword(self):
        response = self.client.get("/api/orders?q=ORD-20260801-001")
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["data"]), 1)
        self.assertEqual(payload["data"][0]["order_id"], "ORD-20260801-001")

    def test_api_list_orders_pagination(self):
        response = self.client.get("/api/orders?page=1&page_size=5")
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertLessEqual(len(payload["data"]), 5)
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 5)

    def test_api_suggest_orders(self):
        response = self.client.get("/api/orders/suggest")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertGreater(len(payload["data"]), 0)
        for item in payload["data"]:
            self.assertIn("order_id", item)
            self.assertIn("status", item)


class ReminderApiTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_api_handlers(self):
        response = self.client.get("/api/handlers")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"], HANDLERS)

    def test_api_send_reminder_success(self):
        with mock.patch.object(
            app_module,
            "send_reminder",
            return_value=({"success": True, "result": "ok"}, 200),
        ):
            response = self.client.post(
                "/api/reminders",
                json={"order_id": "ORD-20260801-001", "handler": "王芳"},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["result"], "ok")

    def test_api_send_reminder_requires_fields(self):
        response = self.client.post("/api/reminders", json={"order_id": "ORD-1"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_api_send_reminder_unknown_order(self):
        response = self.client.post(
            "/api/reminders",
            json={"order_id": "ORD-NOT-EXISTS", "handler": "王芳"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_api_send_reminder_invalid_handler(self):
        response = self.client.post(
            "/api/reminders",
            json={"order_id": "ORD-20260801-001", "handler": "不存在的人"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_api_send_reminder_service_unavailable(self):
        with mock.patch.object(
            app_module,
            "send_reminder",
            return_value=({"success": False, "message": "无法连接催办服务"}, 502),
        ):
            response = self.client.post(
                "/api/reminders",
                json={"order_id": "ORD-20260801-001", "handler": "王芳"},
            )
        self.assertEqual(response.status_code, 502)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["message"], "无法连接催办服务")


class SendReminderUrlTestCase(unittest.TestCase):
    def test_send_reminder_normalizes_missing_scheme(self):
        with mock.patch.object(app_module, "NOTIFICATION_SERVICE_URL", "localhost:9999"), \
             mock.patch("urllib.request.Request") as request_cls, \
             mock.patch("urllib.request.urlopen", side_effect=ValueError("offline")):
            result, status_code = app_module.send_reminder("ORD-1", "王芳")

        request_cls.assert_called_once()
        self.assertEqual(request_cls.call_args.args[0], "http://localhost:9999/api/reminders")
        self.assertEqual(status_code, 502)
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
