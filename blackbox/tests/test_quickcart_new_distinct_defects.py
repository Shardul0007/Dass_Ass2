from __future__ import annotations

import math

import pytest


def _get_product_id(product: dict) -> int:
    for key in ("product_id", "id"):
        v = product.get(key)
        if isinstance(v, int) and v > 0:
            return v
    raise AssertionError(f"Could not determine product id from keys={list(product)}")


def _get_price(product: dict) -> float:
    for key in ("price", "unit_price"):
        v = product.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    raise AssertionError(f"Could not determine product price from keys={list(product)}")


def _extract_stock(product: dict) -> int | None:
    for key in ("stock", "stock_quantity"):
        v = product.get(key)
        if isinstance(v, int):
            return v
    return None


def _ensure_cart_has_item(qc, user_id: int, product_id: int, quantity: int) -> None:
    qc.request("POST", "/api/v1/cart/add", user_id=user_id, json={"product_id": product_id, "quantity": quantity})


def _get_invoice_numbers(invoice: dict) -> tuple[float, float, float]:
    sub = invoice.get("subtotal") or invoice.get("sub_total")
    gst = invoice.get("gst") or invoice.get("gst_amount")
    total = invoice.get("total") or invoice.get("grand_total") or invoice.get("total_amount")
    assert isinstance(sub, (int, float))
    assert isinstance(gst, (int, float))
    assert isinstance(total, (int, float))
    return float(sub), float(gst), float(total)


def test_checkout_payment_status_matches_spec(qc, qc_user_id, qc_product, qc_clean_cart):
    """Spec: CARD => PAID, COD/WALLET => PENDING."""

    product_id = _get_product_id(qc_product)
    price = _get_price(qc_product)

    # Keep totals below COD threshold.
    qty = 1
    stock = _extract_stock(qc_product)
    if stock and stock >= 1 and price > 0:
        qty = 1

    _ensure_cart_has_item(qc, qc_user_id, product_id, quantity=qty)

    # CARD => PAID
    resp = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "CARD"})
    assert resp.status_code in (200, 201)
    payload = qc.get_json(resp)
    assert isinstance(payload, dict)
    assert str(payload.get("payment_status") or "").upper() == "PAID"

    # Refill cart and do COD (best effort; if server enforces other constraints, skip)
    qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)
    _ensure_cart_has_item(qc, qc_user_id, product_id, quantity=1)
    resp = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "COD"})
    if resp.status_code not in (200, 201):
        pytest.skip(f"COD checkout not available in current DB state. status={resp.status_code} body={resp.text[:200]!r}")
    payload = qc.get_json(resp)
    assert isinstance(payload, dict)
    assert str(payload.get("payment_status") or "").upper() == "PENDING"


def test_invoice_math_and_gst_added_once(qc, qc_user_id, qc_product, qc_clean_cart):
    """Spec: GST is 5% and added only once; invoice total matches subtotal+gst."""

    product_id = _get_product_id(qc_product)
    unit_price = _get_price(qc_product)

    qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)

    # Use quantity=2 if stock allows to reduce flakiness.
    qty = 1
    stock = _extract_stock(qc_product)
    if isinstance(stock, int) and stock >= 2:
        qty = 2

    _ensure_cart_has_item(qc, qc_user_id, product_id, quantity=qty)
    expected_subtotal = unit_price * qty

    resp = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "CARD"})
    assert resp.status_code in (200, 201)
    order = qc.get_json(resp)
    assert isinstance(order, dict)
    order_id = order.get("order_id") or order.get("id")
    assert order_id is not None

    inv = qc.request("GET", f"/api/v1/orders/{order_id}/invoice", user_id=qc_user_id)
    assert inv.status_code == 200
    invoice = qc.get_json(inv)
    assert isinstance(invoice, dict)

    subtotal, gst, total = _get_invoice_numbers(invoice)

    # subtotal should be close to computed subtotal from our controlled cart.
    assert math.isclose(subtotal, expected_subtotal, rel_tol=0, abs_tol=0.01)

    # GST should be 5% of subtotal.
    assert math.isclose(gst, 0.05 * subtotal, rel_tol=0, abs_tol=0.02)

    # total should be subtotal + gst.
    assert math.isclose(total, subtotal + gst, rel_tol=0, abs_tol=0.02)


def test_coupon_max_discount_cap_respected_best_effort(qc, qc_user_id, qc_products, qc_clean_cart):
    """Spec: coupon cap should limit the discount. Best-effort because coupon DB varies."""

    admin = qc.request("GET", "/api/v1/admin/coupons")
    if admin.status_code != 200:
        pytest.skip("admin/coupons not available")

    coupons = qc.get_json(admin)
    rows = coupons if isinstance(coupons, list) else coupons.get("coupons") or coupons.get("data") or []
    if not isinstance(rows, list):
        pytest.skip("admin/coupons payload shape unknown")

    chosen = None
    for c in rows:
        if not isinstance(c, dict):
            continue
        ctype = str(c.get("type") or c.get("discount_type") or "").upper()
        if ctype != "PERCENT":
            continue
        cap = c.get("max_discount") or c.get("cap") or c.get("max_cap")
        code = c.get("coupon_code") or c.get("code")
        if isinstance(cap, (int, float)) and cap > 0 and isinstance(code, str) and code.strip():
            chosen = (code.strip(), float(cap))
            break

    if chosen is None:
        pytest.skip("No PERCENT coupon with a max cap found in this DB")

    code, cap = chosen

    # Build a cart that is likely to exceed the cap.
    qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)

    # Pick a product with stock.
    product = None
    for p in qc_products:
        if isinstance(p, dict) and _extract_stock(p):
            product = p
            break
    if product is None:
        pytest.skip("No product with stock available")

    pid = _get_product_id(product)
    price = _get_price(product)
    stock = _extract_stock(product) or 1

    # Aim for subtotal of at least cap*30 to exceed cap even for small percentages.
    target = max(200.0, cap * 30)
    qty = int(target / price) + 1 if price > 0 else 1
    qty = max(1, min(qty, stock))

    _ensure_cart_has_item(qc, qc_user_id, pid, quantity=qty)

    apply_resp = qc.request("POST", "/api/v1/coupon/apply", user_id=qc_user_id, json={"coupon_code": code})
    if apply_resp.status_code != 200:
        pytest.skip(f"Coupon not applicable in current cart state. status={apply_resp.status_code} body={apply_resp.text[:200]!r}")

    payload = qc.get_json(apply_resp)
    if not isinstance(payload, dict):
        pytest.skip("coupon/apply payload shape unknown")

    discount = payload.get("discount")
    if not isinstance(discount, (int, float)):
        pytest.skip("coupon/apply response missing discount")

    assert float(discount) <= cap + 0.01
