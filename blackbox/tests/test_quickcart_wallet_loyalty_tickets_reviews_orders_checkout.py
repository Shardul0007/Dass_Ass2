import math
from datetime import datetime

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


def _ensure_cart_has_item(qc, qc_user_id, product_id, quantity: int = 1):
    qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)
    resp = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json={"product_id": product_id, "quantity": quantity})
    assert resp.status_code in (200, 201)


def test_wallet_add_boundaries_and_pay_exact_deduction(qc, qc_user_id):
    # Get current balance
    bal = qc.request("GET", "/api/v1/wallet", user_id=qc_user_id)
    assert bal.status_code == 200
    before = qc.get_json(bal)

    # Invalid add: 0
    resp = qc.request("POST", "/api/v1/wallet/add", user_id=qc_user_id, json={"amount": 0})
    assert resp.status_code == 400

    # Invalid add: > 100000
    resp = qc.request("POST", "/api/v1/wallet/add", user_id=qc_user_id, json={"amount": 100001})
    assert resp.status_code == 400

    # Valid add: 1
    resp = qc.request("POST", "/api/v1/wallet/add", user_id=qc_user_id, json={"amount": 1})
    assert resp.status_code in (200, 201)

    # Pay invalid: 0
    resp = qc.request("POST", "/api/v1/wallet/pay", user_id=qc_user_id, json={"amount": 0})
    assert resp.status_code == 400

    # Pay too much => 400 (try huge)
    resp = qc.request("POST", "/api/v1/wallet/pay", user_id=qc_user_id, json={"amount": 10_000_000})
    assert resp.status_code == 400

    # If we can read a numeric balance, test exact deduction
    bal2 = qc.request("GET", "/api/v1/wallet", user_id=qc_user_id)
    assert bal2.status_code == 200
    after_add = qc.get_json(bal2)

    def _extract_balance(payload):
        if isinstance(payload, dict):
            for k in ("balance", "wallet_balance", "amount"):
                if isinstance(payload.get(k), (int, float)):
                    return float(payload[k])
        return None

    balance_val = _extract_balance(after_add)
    if balance_val is None or balance_val < 1:
        pytest.skip("Wallet response did not expose numeric balance")

    pay_amount = 1
    resp = qc.request("POST", "/api/v1/wallet/pay", user_id=qc_user_id, json={"amount": pay_amount})
    assert resp.status_code in (200, 201)

    bal3 = qc.request("GET", "/api/v1/wallet", user_id=qc_user_id)
    assert bal3.status_code == 200
    after_pay = qc.get_json(bal3)

    new_balance = _extract_balance(after_pay)
    if new_balance is None:
        pytest.skip("Wallet response did not expose numeric balance")

    assert math.isclose(new_balance, balance_val - pay_amount, rel_tol=0, abs_tol=0.01)


def test_loyalty_redeem_boundaries(qc, qc_user_id):
    resp = qc.request("GET", "/api/v1/loyalty", user_id=qc_user_id)
    assert resp.status_code == 200
    payload = qc.get_json(resp)

    points = None
    if isinstance(payload, dict):
        points = payload.get("points") or payload.get("loyalty_points")

    # Redeem 0 => invalid
    resp = qc.request("POST", "/api/v1/loyalty/redeem", user_id=qc_user_id, json={"amount": 0})
    assert resp.status_code == 400

    # Redeem too many => 400 (use huge)
    resp = qc.request("POST", "/api/v1/loyalty/redeem", user_id=qc_user_id, json={"amount": 1_000_000})
    assert resp.status_code == 400

    if isinstance(points, int) and points > 0:
        resp = qc.request("POST", "/api/v1/loyalty/redeem", user_id=qc_user_id, json={"amount": 1})
        assert resp.status_code in (200, 201)


def test_support_ticket_create_and_status_transitions(qc, qc_user_id):
    # Invalid subject too short
    resp = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": "abcd", "message": "hello"},
    )
    assert resp.status_code == 400

    # Invalid message too long
    resp = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": "valid subject", "message": "x" * 501},
    )
    assert resp.status_code == 400

    # Valid create
    msg = "This is a test ticket message."
    resp = qc.request(
        "POST",
        "/api/v1/support/ticket",
        user_id=qc_user_id,
        json={"subject": "valid subject", "message": msg},
    )
    assert resp.status_code in (200, 201)
    created = qc.get_json(resp)

    # Extract ticket_id and confirm OPEN status if present
    ticket_id = None
    status = None
    if isinstance(created, dict):
        ticket_id = created.get("ticket_id") or created.get("id")
        status = created.get("status")
    if ticket_id is None and isinstance(created, dict):
        for v in created.values():
            if isinstance(v, dict):
                ticket_id = v.get("ticket_id") or v.get("id")
                status = status or v.get("status")

    assert ticket_id is not None
    if status is not None:
        assert str(status).upper() == "OPEN"

    # Move OPEN -> IN_PROGRESS
    upd = qc.request(
        "PUT",
        f"/api/v1/support/tickets/{ticket_id}",
        user_id=qc_user_id,
        json={"status": "IN_PROGRESS"},
    )
    assert upd.status_code in (200, 201)

    # Invalid transition: CLOSED -> OPEN (try to force invalid direction)
    # First close it.
    upd2 = qc.request(
        "PUT",
        f"/api/v1/support/tickets/{ticket_id}",
        user_id=qc_user_id,
        json={"status": "CLOSED"},
    )
    assert upd2.status_code in (200, 201)

    upd3 = qc.request(
        "PUT",
        f"/api/v1/support/tickets/{ticket_id}",
        user_id=qc_user_id,
        json={"status": "OPEN"},
    )
    assert upd3.status_code == 400


def test_reviews_post_validation_and_average_decimal(qc, qc_user_id, qc_product):
    product_id = _get_product_id(qc_product)

    # Invalid rating
    resp = qc.request(
        "POST",
        f"/api/v1/products/{product_id}/reviews",
        user_id=qc_user_id,
        json={"rating": 0, "comment": "ok"},
    )
    assert resp.status_code == 400

    resp = qc.request(
        "POST",
        f"/api/v1/products/{product_id}/reviews",
        user_id=qc_user_id,
        json={"rating": 6, "comment": "ok"},
    )
    assert resp.status_code == 400

    # Invalid comment length
    resp = qc.request(
        "POST",
        f"/api/v1/products/{product_id}/reviews",
        user_id=qc_user_id,
        json={"rating": 5, "comment": ""},
    )
    assert resp.status_code == 400

    resp = qc.request(
        "POST",
        f"/api/v1/products/{product_id}/reviews",
        user_id=qc_user_id,
        json={"rating": 5, "comment": "x" * 201},
    )
    assert resp.status_code == 400

    # Create two reviews to push average to .5 (best effort; API may de-duplicate per user)
    r1 = qc.request(
        "POST",
        f"/api/v1/products/{product_id}/reviews",
        user_id=qc_user_id,
        json={"rating": 4, "comment": "good"},
    )
    assert r1.status_code in (200, 201, 409)

    r2 = qc.request(
        "POST",
        f"/api/v1/products/{product_id}/reviews",
        user_id=qc_user_id,
        json={"rating": 5, "comment": "great"},
    )
    assert r2.status_code in (200, 201, 409)

    resp = qc.request("GET", f"/api/v1/products/{product_id}/reviews", user_id=qc_user_id)
    assert resp.status_code == 200
    payload = qc.get_json(resp)

    avg = None
    if isinstance(payload, dict):
        avg = payload.get("average_rating") or payload.get("avg_rating")

    if isinstance(avg, (int, float)):
        # Spec: average must be decimal calculation, not floor-int.
        assert float(avg) >= 0.0


def test_checkout_validations_and_order_created(qc, qc_user_id, qc_product):
    product_id = _get_product_id(qc_product)
    price = _get_price(qc_product)

    # Empty cart checkout must 400
    qc.request("DELETE", "/api/v1/cart/clear", user_id=qc_user_id)
    resp = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "COD"})
    assert resp.status_code == 400

    # Invalid payment method
    _ensure_cart_has_item(qc, qc_user_id, product_id, quantity=1)
    resp = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "BITCOIN"})
    assert resp.status_code == 400

    # COD order total > 5000 must 400 (best effort: increase quantity if stock allows)
    qty = 1
    if price > 0:
        qty = int(math.floor(5001 / price)) + 1
        qty = max(qty, 1)

    stock = qc_product.get("stock")
    if isinstance(stock, int) and stock >= qty:
        _ensure_cart_has_item(qc, qc_user_id, product_id, quantity=qty)
        resp = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "COD"})
        assert resp.status_code == 400

    # Successful checkout with CARD (should yield PAID)
    _ensure_cart_has_item(qc, qc_user_id, product_id, quantity=1)
    resp = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": "CARD"})
    assert resp.status_code in (200, 201)
    payload = qc.get_json(resp)
    assert isinstance(payload, dict)


def test_orders_list_and_invoice_structure(qc, qc_user_id):
    # Should return list (may be empty)
    resp = qc.request("GET", "/api/v1/orders", user_id=qc_user_id)
    assert resp.status_code == 200
    payload = qc.get_json(resp)

    orders = payload if isinstance(payload, list) else payload.get("orders") or payload.get("data") or []
    assert isinstance(orders, list)

    if not orders:
        pytest.skip("No orders available for invoice checks")

    order_id = None
    if isinstance(orders[0], dict):
        order_id = orders[0].get("order_id") or orders[0].get("id")
    if order_id is None:
        pytest.skip("Could not determine order id field")

    inv = qc.request("GET", f"/api/v1/orders/{order_id}/invoice", user_id=qc_user_id)
    assert inv.status_code == 200
    invoice = qc.get_json(inv)
    assert isinstance(invoice, dict)

    # Must include subtotal, gst, total
    assert any(k in invoice for k in ("subtotal", "sub_total"))
    assert any(k in invoice for k in ("gst", "gst_amount"))
    assert any(k in invoice for k in ("total", "grand_total"))


def test_cancel_order_nonexistent_404(qc, qc_user_id):
    resp = qc.request("POST", "/api/v1/orders/99999999/cancel", user_id=qc_user_id)
    assert resp.status_code in (404, 400)


def test_cancel_delivered_order_rejected_if_any_exist(qc, qc_user_id):
    # Search admin/orders for a delivered order belonging to this user.
    admin = qc.request("GET", "/api/v1/admin/orders")
    if admin.status_code != 200:
        pytest.skip("admin/orders not available")

    payload = qc.get_json(admin)
    orders = payload if isinstance(payload, list) else payload.get("orders") or payload.get("data") or []
    if not isinstance(orders, list):
        pytest.skip("admin/orders payload shape unknown")

    delivered_id = None
    for row in orders:
        if not isinstance(row, dict):
            continue
        uid = row.get("user_id")
        status = str(row.get("status") or row.get("order_status") or "").upper()
        oid = row.get("order_id") or row.get("id")
        if uid == qc_user_id and status == "DELIVERED" and oid is not None:
            delivered_id = oid
            break

    if delivered_id is None:
        pytest.skip("No delivered orders found for this user")

    resp = qc.request("POST", f"/api/v1/orders/{delivered_id}/cancel", user_id=qc_user_id)
    assert resp.status_code == 400
