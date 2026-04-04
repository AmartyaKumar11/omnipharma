from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_paths_in_openapi() -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json().get("paths", {})
    assert "/dashboard/summary" in paths
    assert "/dashboard/sales-trend" in paths
    assert "/dashboard/store-performance" in paths
    assert "/dashboard/stores" in paths
