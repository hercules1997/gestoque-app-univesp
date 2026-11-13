from uuid import uuid4

from .test_tscheck_auth import login


def test_admin_imports_unique_csv_equivalent_payload(client):
    login(client)
    payload = {"sku":f"tscheck-import-product-{uuid4().hex[:10]}","name":"Importado TS","category":"Teste","unit_cost":3,"sale_price":6,"stock":7,"min_stock":2,"reorder_point":3,"supplier":"CSV"}
    r = client.post("/import/products", json={"products":[payload]})
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 1
    assert any(p["sku"] == payload["sku"].upper() for p in client.get("/products").json())
