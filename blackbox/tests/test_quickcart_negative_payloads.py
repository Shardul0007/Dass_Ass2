import pytest


@pytest.mark.parametrize(
    "path,method,payload",
    [
        ("/api/v1/profile", "PUT", {}),
        ("/api/v1/profile", "PUT", {"name": "Valid Name"}),
        ("/api/v1/profile", "PUT", {"phone": "0123456789"}),
    ],
)
def test_profile_update_missing_fields_rejected(qc, qc_user_id, path, method, payload):
    resp = qc.request(method, path, user_id=qc_user_id, json=payload)
    assert resp.status_code == 400


def test_profile_update_wrong_types_rejected(qc, qc_user_id):
    resp = qc.request(
        "PUT",
        "/api/v1/profile",
        user_id=qc_user_id,
        json={"name": 12345, "phone": 12345},
    )
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"label": "HOME"},
        {"label": "HOME", "street": "12345 Main Street"},
        {"label": "HOME", "street": "12345 Main Street", "city": "City"},
    ],
)
def test_address_add_missing_fields_rejected(qc, qc_user_id, payload):
    resp = qc.request("POST", "/api/v1/addresses", user_id=qc_user_id, json=payload)
    assert resp.status_code == 400


def test_address_add_is_default_optional(qc, qc_user_id):
    resp = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "HOME", "street": "12345 Main Street", "city": "City", "pincode": "123456"},
    )
    assert resp.status_code in (200, 201)


def test_address_add_wrong_types_rejected(qc, qc_user_id):
    resp = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "HOME", "street": 12345, "city": 999, "pincode": 123456, "is_default": "yes"},
    )
    assert resp.status_code == 400


def test_address_add_boundary_lengths(qc, qc_user_id):
    # street: 5..100, city: 2..50, pincode: exactly 6 digits
    street_5 = "A" * 5
    street_100 = "B" * 100
    city_2 = "CC"
    city_50 = "D" * 50

    r1 = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "OTHER", "street": street_5, "city": city_2, "pincode": "123456", "is_default": False},
    )
    assert r1.status_code in (200, 201)

    r2 = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "OTHER", "street": street_100, "city": city_50, "pincode": "654321", "is_default": False},
    )
    assert r2.status_code in (200, 201)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"product_id": 1},
        {"quantity": 1},
        {"product_id": "1", "quantity": "2"},
    ],
)
def test_cart_add_missing_or_wrong_types_rejected(qc, qc_user_id, qc_clean_cart, payload):
    resp = qc.request("POST", "/api/v1/cart/add", user_id=qc_user_id, json=payload)
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/wallet/add",
        "/api/v1/wallet/pay",
    ],
)
def test_wallet_endpoints_missing_amount_rejected(qc, qc_user_id, endpoint):
    resp = qc.request("POST", endpoint, user_id=qc_user_id, json={})
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/wallet/add",
        "/api/v1/wallet/pay",
    ],
)
def test_wallet_endpoints_wrong_amount_type_rejected(qc, qc_user_id, endpoint):
    resp = qc.request("POST", endpoint, user_id=qc_user_id, json={"amount": "10"})
    assert resp.status_code == 400


def test_loyalty_redeem_missing_or_wrong_type_rejected(qc, qc_user_id):
    resp = qc.request("POST", "/api/v1/loyalty/redeem", user_id=qc_user_id, json={})
    assert resp.status_code == 400

    resp = qc.request("POST", "/api/v1/loyalty/redeem", user_id=qc_user_id, json={"amount": "1"})
    assert resp.status_code == 400


def test_checkout_missing_or_wrong_payment_method_rejected(qc, qc_user_id):
    resp = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={})
    assert resp.status_code == 400

    resp = qc.request("POST", "/api/v1/checkout", user_id=qc_user_id, json={"payment_method": 123})
    assert resp.status_code == 400


def test_coupon_apply_wrong_type_rejected(qc, qc_user_id):
    resp = qc.request("POST", "/api/v1/coupon/apply", user_id=qc_user_id, json={"code": 123})
    assert resp.status_code == 400


def test_support_ticket_missing_fields_rejected(qc, qc_user_id):
    resp = qc.request("POST", "/api/v1/support/ticket", user_id=qc_user_id, json={})
    assert resp.status_code == 400

    resp = qc.request("POST", "/api/v1/support/ticket", user_id=qc_user_id, json={"subject": "valid subject"})
    assert resp.status_code == 400

    resp = qc.request("POST", "/api/v1/support/ticket", user_id=qc_user_id, json={"message": "hi"})
    assert resp.status_code == 400


def test_support_ticket_wrong_types_rejected(qc, qc_user_id):
    resp = qc.request("POST", "/api/v1/support/ticket", user_id=qc_user_id, json={"subject": 123, "message": 456})
    assert resp.status_code == 400
