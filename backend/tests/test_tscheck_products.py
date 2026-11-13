from uuid import uuid4

from .test_tscheck_auth import login


def test_admin_creates_unique_product_and_lists_it(client):
    login(client)
    payload = {"sku":f"tscheck-product-unique-{uuid4().hex[:10]}","name":"Produto TS Check","category":"Teste","unit_cost":12.5,"sale_price":20,"stock":9,"min_stock":2,"reorder_point":3,"supplier":"Fornecedor TS"}
    created = client.post("/products", json=payload)
    assert created.status_code == 200, created.text
    row = created.json()
    assert row["sku"] == payload["sku"].upper()
    listed = client.get("/products")
    assert listed.status_code == 200
    assert any(item["id"] == row["id"] for item in listed.json())


def test_duplicate_sku_rejected(client):
    login(client)
    payload = {"sku":f"tscheck-product-duplicate-{uuid4().hex[:10]}","name":"Produto","category":"Teste","unit_cost":1,"sale_price":2,"stock":1,"min_stock":1,"reorder_point":1}
    assert client.post("/products", json=payload).status_code == 200
    assert client.post("/products", json=payload).status_code == 409
