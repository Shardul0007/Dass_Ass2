import pytest


def _as_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list):
                return v
    return []


def _get_product_id(product: dict):
    for key in ("product_id", "id"):
        if key in product:
            return product[key]
    raise AssertionError(f"Could not determine product id from keys={list(product)}")


def test_checkout_rejects_invalid_payment_method_with_non_empty_cart(qc, qc_user_id, qc_clean_cart):
    resp = qc.request("GET", "/api/v1/products", user_id=qc_user_id)
    assert resp.status_code == 200
    products = [p for p in _as_list(qc.get_json(resp)) if isinstance(p, dict)]
    if not products:
        pytest.skip("No products")

    pid = _get_product_id(products[0])

    add = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": 1})
    assert add.status_code in (200, 201), add.text

    chk = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "BITCOIN"})
    assert chk.status_code == 400, f"status={chk.status_code} body={chk.text[:200]!r}"
