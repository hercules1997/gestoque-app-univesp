from .test_tscheck_auth import login


def product_payload(sku):
    return {"sku":sku,"name":"Perm Produto","category":"Teste","unit_cost":1,"sale_price":2,"stock":3,"min_stock":1,"reorder_point":1}


def test_operator_can_consult_and_cannot_admin_actions(client):
    login(client, "operador@gestoque.com", "Operador123!")
    assert client.get("/products").status_code == 200
    assert client.get("/dashboard").status_code == 200
    assert client.post("/products", json=product_payload("tscheck-permission-product")).status_code == 403
    assert client.post("/import/products", json={"products":[product_payload("tscheck-permission-import")]}).status_code == 403
