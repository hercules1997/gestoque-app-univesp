from .test_tscheck_auth import login


def test_dashboard_decision_payload(client):
    login(client)
    r = client.get("/dashboard")
    assert r.status_code == 200, r.text
    data = r.json()
    for key in ["total_inventory_value", "critical_stock_count", "forecast_shortage_count", "demand_series", "critical_products", "recent_movements", "stock_distribution"]:
        assert key in data
    assert len(data["demand_series"]) == 7
