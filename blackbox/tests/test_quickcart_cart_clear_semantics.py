import pytest


def _as_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list):
                return v
    return []


def _extract_items(cart_payload: object) -> list:
    if isinstance(cart_payload, dict):
        items = cart_payload.get("items") or cart_payload.get("cart_items") or cart_payload.get("data")
        if isinstance(items, list):
            return items
    if isinstance(cart_payload, list):
        return cart_payload
    return []


def _get_product_id(product: dict):
    for key in ("product_id", "id"):
        if key in product:
            return product[key]
    raise AssertionError(f"Could not determine product id from keys={list(product)}")


def test_cart_clear_empties_cart(qc, qc_user_id, qc_clean_cart):
    resp = qc.request("GET", "/api/v1/products", user_id=qc_user_id)
    assert resp.status_code == 200
    products = [p for p in _as_list(qc.get_json(resp)) if isinstance(p, dict)]
    if not products:
        pytest.skip("No products")

    pid = _get_product_id(products[0])

    add = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": 1})
    assert add.status_code in (200, 201), add.text

    clear = qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)
    assert clear.status_code in (200, 201)

    cart = qc.request("GET", "/api/v1/cart", user_id=qc_user_id)
    assert cart.status_code == 200
    payload = qc.get_json(cart)
    items = _extract_items(payload)

    assert isinstance(items, list)
    assert len(items) == 0, f"Expected empty cart after clear; got items={items!r}"
