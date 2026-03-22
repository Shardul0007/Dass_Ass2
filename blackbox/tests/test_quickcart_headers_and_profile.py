import pytest



def test_missing_roll_number_header_returns_401(qc):
    resp = qc.request("GET", "/api/v1/admin/users", headers={"X-Roll-Number": ""})
    # If header is missing entirely, server returns 401.
    # Sending blank should be treated as missing/invalid; accept 401 or 400.
    assert resp.status_code in (400, 401)


def test_missing_roll_number_header_omitted_returns_401(qc):
    # QuickCartClient always injects X-Roll-Number, so we bypass it here and omit headers entirely.
    resp = qc._session.request("GET", qc._url("/api/v1/admin/users"), headers={}, timeout=15)
    assert resp.status_code == 401


def test_non_integer_roll_number_returns_400(qc):
    resp = qc.request("GET", "/api/v1/admin/users", headers={"X-Roll-Number": "abc"})
    assert resp.status_code == 400


def test_admin_endpoints_do_not_require_or_validate_x_user_id(qc):
    resp = qc.request("GET", "/api/v1/admin/users", headers={"X-User-ID": "-1"})
    assert resp.status_code == 200

    resp = qc.request("GET", "/api/v1/admin/users", headers={"X-User-ID": "abc"})
    assert resp.status_code == 200


def test_user_endpoint_missing_user_id_returns_400(qc):
    resp = qc.request("GET", "/api/v1/profile", user_id=None)
    # Profile is user-scoped; missing X-User-ID should be rejected.
    assert resp.status_code == 400


def test_user_endpoint_invalid_user_id_returns_400(qc):
    resp = qc.request("GET", "/api/v1/profile", user_id=-1)
    assert resp.status_code == 400


def test_user_endpoint_nonexistent_user_id_returns_400(qc):
    resp = qc.request("GET", "/api/v1/profile", user_id=99999999)
    assert resp.status_code == 400


def test_get_profile_returns_json_object(qc, qc_user_id):
    resp = qc.request("GET", "/api/v1/profile", user_id=qc_user_id)
    assert resp.status_code == 200
    payload = qc.get_json(resp)
    assert isinstance(payload, dict)


def test_update_profile_valid_and_invalid_boundaries(qc, qc_user_id):
    # Invalid: name too short
    resp = qc.request("PUT", "/api/v1/profile", user_id=qc_user_id, json={"name": "A", "phone": "0123456789"})
    assert resp.status_code == 400

    # Invalid: name too long (51)
    resp = qc.request(
        "PUT",
        "/api/v1/profile",
        user_id=qc_user_id,
        json={"name": "A" * 51, "phone": "0123456789"},
    )
    assert resp.status_code == 400

    # Invalid: phone not exactly 10 digits
    resp = qc.request("PUT", "/api/v1/profile", user_id=qc_user_id, json={"name": "Valid Name", "phone": "123"})
    assert resp.status_code == 400

    # Valid boundary: name length 2, phone 10 digits
    resp = qc.request("PUT", "/api/v1/profile", user_id=qc_user_id, json={"name": "AB", "phone": "0123456789"})
    assert resp.status_code in (200, 201)
    payload = qc.get_json(resp)
    assert isinstance(payload, dict)
