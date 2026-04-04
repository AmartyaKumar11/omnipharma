from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_orders_routes_registered() -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    assert "/orders" in paths
    assert "/orders/{order_id}" in paths
