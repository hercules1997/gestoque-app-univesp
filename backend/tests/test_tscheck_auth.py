import httpx


def login(client, email="admin@stokos.demo", password="Admin123!"):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def test_demo_auth_and_role(client):
    admin = login(client)
    assert admin["role"] == "admin"
    client.post("/auth/logout")
    operator = login(client, "operador@stokos.demo", "Operador123!")
    assert operator["role"] == "operator"
    assert client.get("/auth/me").status_code == 200


def test_invalid_login_rejected(client):
    r = client.post("/auth/login", json={"email": "admin@stokos.demo", "password": "wrong"})
    assert r.status_code == 401
