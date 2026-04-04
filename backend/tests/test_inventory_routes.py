from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_inventory_routes_registered() -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    assert "/inventory/product" in paths
    assert "/inventory/batch" in paths
    assert "/inventory/stock" in paths
    assert "/inventory/reduce" in paths
    assert "/inventory" in paths
    assert "/inventory/alerts" in paths
