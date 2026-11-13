from .test_tscheck_auth import login


def test_forecast_supported_horizons_and_model(client):
    login(client)
    for days in (7, 15, 30, 60):
        r = client.get(f"/forecast?days={days}")
        assert r.status_code == 200, r.text
        assert r.json()["days"] == days
        assert "Média móvel ponderada" in r.json()["model_name"]
        assert isinstance(r.json()["items"], list)


def test_forecast_invalid_horizon_rejected(client):
    login(client)
    assert client.get("/forecast?days=8").status_code == 422
