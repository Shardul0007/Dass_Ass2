import math

import pytest


def _get_product_id(product: dict):
    for key in ("product_id", "id"):
        if key in product:
            return product[key]
    raise AssertionError(f"Could not determine product id from keys={list(product)}")


def _get_price(product: dict) -> float:
    for key in ("price", "unit_price"):
        if key in product and isinstance(product[key], (int, float)):
            return float(product[key])
    raise AssertionError(f"Could not determine product price from keys={list(product)}")


def test_products_list_returns_only_active_products(qc):
    admin = qc.request("GET", "/api/v1/admin/products")
    assert admin.status_code == 200
    admin_payload = qc.get_json(admin)

    # Build a set of inactive ids from admin listing.
    inactive_ids = set()
    for row in (admin_payload if isinstance(admin_payload, list) else []):
        if isinstance(row, dict):
            active = row.get("active") if "active" in row else row.get("is_active")
            if active is False:
                inactive_ids.add(row.get("product_id") or row.get("id"))

    resp = qc.request("GET", "/api/v1/products", headers={})
    assert resp.status_code == 200
    payload = qc.get_json(resp)

    products = payload if isinstance(payload, list) else payload.get("products") or payload.get("data") or []
    assert isinstance(products, list)

    returned_ids = {(p.get("product_id") or p.get("id")) for p in products if isinstance(p, dict)}
    assert not (returned_ids & inactive_ids)


def test_get_product_by_id_404_for_unknown(qc):
    resp = qc.request("GET", "/api/v1/products/99999999")
    assert resp.status_code in (404, 400)


def test_cart_add_update_remove_and_totals(qc, qc_user_id, qc_product, qc_clean_cart):
    product_id = _get_product_id(qc_product)
    unit_price = _get_price(qc_product)

    # Add invalid qty
    resp = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": product_id, "quantity": 0})
    assert resp.status_code == 400

    # Add invalid product
    resp = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": 99999999, "quantity": 1})
    assert resp.status_code in (404, 400)

    # Add valid qty=1
    resp = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": product_id, "quantity": 1})
    assert resp.status_code in (200, 201)

    # Add same product again; quantity should add up (not replace)
    resp = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": product_id, "quantity": 2})
    assert resp.status_code in (200, 201)

    cart = qc.request("GET", "/api/v1/cart", user_id=qc_user_id)
    assert cart.status_code == 200
    cart_payload = qc.get_json(cart)
    assert isinstance(cart_payload, dict)

    items = cart_payload.get("items") or cart_payload.get("cart_items") or []
    assert isinstance(items, list)

    # Find our product line
    line = None
    for it in items:
        if isinstance(it, dict) and (it.get("product_id") == product_id or it.get("id") == product_id):
            line = it
            break
    assert line is not None

    qty = line.get("quantity")
    assert qty == 3

    # Subtotal should be quantity * unit_price (allow small float differences)
    subtotal = line.get("subtotal") or line.get("line_total")
    assert isinstance(subtotal, (int, float))
    assert math.isclose(float(subtotal), float(qty) * unit_price, rel_tol=1e-6, abs_tol=0.01)

    total = cart_payload.get("total") or cart_payload.get("cart_total")
    assert isinstance(total, (int, float))

    # Total should equal sum of subtotals
    computed_total = 0.0
    for it in items:
        if isinstance(it, dict):
            st = it.get("subtotal") or it.get("line_total")
            if isinstance(st, (int, float)):
                computed_total += float(st)
    assert math.isclose(float(total), computed_total, rel_tol=1e-6, abs_tol=0.01)

    # Update invalid qty
    resp = qc.request("POST", "/api/v1/cart/update", user_id=qc_user_id, json={"product_id": product_id, "quantity": 0})
    assert resp.status_code == 400

    # Update to qty=1
    resp = qc.request("POST", "/api/v1/cart/update", user_id=qc_user_id, json={"product_id": product_id, "quantity": 1})
    assert resp.status_code in (200, 201)

    # Remove item
    resp = qc.request("POST", "/api/v1/cart/remove", user_id=qc_user_id, json={"product_id": product_id})
    assert resp.status_code in (200, 201)

    # Removing again should 404
    resp = qc.request("POST", "/api/v1/cart/remove", user_id=qc_user_id, json={"product_id": product_id})
    assert resp.status_code in (404, 400)


def test_cart_rejects_quantity_more_than_stock(qc, qc_user_id, qc_product, qc_clean_cart):
    product_id = _get_product_id(qc_product)
    stock = qc_product.get("stock")

    if not isinstance(stock, int) or stock <= 0:
        pytest.skip("Selected product has no usable stock info")

    resp = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": product_id, "quantity": stock + 1})
    assert resp.status_code == 400
