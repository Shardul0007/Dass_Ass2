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


def _extract_cart_items(payload: object) -> list[dict]:
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("cart_items") or payload.get("data")
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


def test_cart_add_same_product_accumulates_quantity(qc, qc_user_id, qc_clean_cart):
    resp = qc.request("GET", "/api/v1/products", user_id=qc_user_id)
    assert resp.status_code == 200
    products = [p for p in _as_list(qc.get_json(resp)) if isinstance(p, dict)]
    if not products:
        pytest.skip("No products")

    pid = _get_product_id(products[0])
    assert isinstance(pid, int)

    a1 = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": 1})
    assert a1.status_code in (200, 201), a1.text

    a2 = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": pid, "quantity": 2})
    assert a2.status_code in (200, 201), a2.text

    cart = qc.request("GET", "/api/v1/cart", user_id=qc_user_id)
    assert cart.status_code == 200
    payload = qc.get_json(cart)

    items = _extract_cart_items(payload)
    line = next((it for it in items if it.get("product_id") == pid or it.get("id") == pid), None)
    assert line is not None, f"Could not find cart line for pid={pid}. items={items!r}"

    qty = line.get("quantity")
    assert qty == 3, f"Expected accumulated qty=3; got qty={qty!r} line={line!r}"
