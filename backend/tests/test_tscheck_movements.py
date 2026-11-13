from uuid import uuid4

from .test_tscheck_auth import login


def test_movement_updates_created_product_stock_and_history(client):
    login(client)
    payload = {"sku":f"tscheck-movement-product-{uuid4().hex[:10]}","name":"Mov Produto","category":"Teste","unit_cost":5,"sale_price":8,"stock":10,"min_stock":2,"reorder_point":3}
    product = client.post("/products", json=payload).json()
    movement = client.post("/movements", json={"product_id":product["id"],"type":"entrada","quantity":4,"reason":"tscheck entrada"})
    assert movement.status_code == 200, movement.text
    assert movement.json()["id"]
    updated = client.get("/products").json()
    assert next(p for p in updated if p["id"] == product["id"])["stock"] == 14
    assert any(m["id"] == movement.json()["id"] for m in client.get("/movements").json())


def test_negative_stock_is_rejected(client):
    login(client)
    product = client.post("/products", json={"sku":f"tscheck-movement-reject-{uuid4().hex[:10]}","name":"Reject","category":"Teste","unit_cost":1,"sale_price":2,"stock":1,"min_stock":1,"reorder_point":1}).json()
    r = client.post("/movements", json={"product_id":product["id"],"type":"saida","quantity":2,"reason":"tscheck"})
    assert r.status_code == 422
