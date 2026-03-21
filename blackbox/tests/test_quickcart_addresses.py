import pytest


def _maybe_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("addresses", "data", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def test_get_addresses_returns_list(qc, qc_user_id):
    resp = qc.request("GET", "/api/v1/addresses", user_id=qc_user_id)
    assert resp.status_code == 200
    payload = qc.get_json(resp)
    assert isinstance(payload, (list, dict))


def test_add_address_invalid_fields_rejected(qc, qc_user_id):
    # Invalid label
    resp = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "HOUSE", "street": "12345 Main St", "city": "NY", "pincode": "123456", "is_default": False},
    )
    assert resp.status_code == 400

    # Invalid pincode length
    resp = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "HOME", "street": "12345 Main St", "city": "NY", "pincode": "12345", "is_default": False},
    )
    assert resp.status_code == 400

    # Street too short
    resp = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "HOME", "street": "1234", "city": "NY", "pincode": "123456", "is_default": False},
    )
    assert resp.status_code == 400

    # City too short
    resp = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "HOME", "street": "12345 Main St", "city": "N", "pincode": "123456", "is_default": False},
    )
    assert resp.status_code == 400


def test_add_address_success_returns_full_address_object_and_id(qc, qc_user_id):
    resp = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "HOME", "street": "12345 Main Street", "city": "New York", "pincode": "123456", "is_default": True},
    )
    assert resp.status_code in (200, 201)
    payload = qc.get_json(resp)
    assert isinstance(payload, dict)

    # Response should include created address object.
    # Some APIs wrap it, so search nested dicts.
    addr_obj = None
    if all(k in payload for k in ("address_id", "label", "street", "city", "pincode")):
        addr_obj = payload
    else:
        for v in payload.values():
            if isinstance(v, dict) and all(k in v for k in ("address_id", "label", "street", "city", "pincode")):
                addr_obj = v
                break

    assert addr_obj is not None
    assert str(addr_obj["label"]).upper() in ("HOME", "OFFICE", "OTHER")
    assert isinstance(addr_obj.get("address_id"), (int, str))


def test_default_address_uniqueness(qc, qc_user_id):
    # Create two addresses with is_default True; server must ensure only one is default.
    a1 = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "HOME", "street": "11111 Alpha Street", "city": "Alpha", "pincode": "111111", "is_default": True},
    )
    assert a1.status_code in (200, 201)

    a2 = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "OFFICE", "street": "22222 Beta Street", "city": "Beta", "pincode": "222222", "is_default": True},
    )
    assert a2.status_code in (200, 201)

    resp = qc.request("GET", "/api/v1/addresses", user_id=qc_user_id)
    assert resp.status_code == 200
    payload = qc.get_json(resp)
    addresses = _maybe_list(payload)

    defaults = [a for a in addresses if isinstance(a, dict) and a.get("is_default") is True]
    assert len(defaults) <= 1


def test_update_address_allows_only_street_and_is_default(qc, qc_user_id):
    create = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "OTHER", "street": "33333 Gamma Street", "city": "Gamma", "pincode": "333333", "is_default": False},
    )
    assert create.status_code in (200, 201)
    created = qc.get_json(create)

    # Pull address_id from response.
    address_id = None
    for obj in [created] + [v for v in created.values() if isinstance(v, dict)]:
        if isinstance(obj, dict) and "address_id" in obj:
            address_id = obj["address_id"]
            break
    assert address_id is not None

    # Attempt to change city (should be rejected or ignored)
    upd = qc.request(
        "PUT",
        f"/api/v1/addresses/{address_id}",
        user_id=qc_user_id,
        json={"city": "Changed", "street": "33333 Gamma Street UPDATED", "is_default": True},
    )
    assert upd.status_code in (200, 201, 400)

    if upd.status_code in (200, 201):
        payload = qc.get_json(upd)
        updated = payload
        if not (isinstance(updated, dict) and "street" in updated):
            for v in payload.values():
                if isinstance(v, dict) and "street" in v:
                    updated = v
                    break
        assert updated.get("street") == "33333 Gamma Street UPDATED"
        # City should remain the original "Gamma" if returned.
        if "city" in updated:
            assert updated["city"] == "Gamma"


def test_delete_nonexistent_address_returns_404(qc, qc_user_id):
    resp = qc.request("DELETE", "/api/v1/addresses/99999999", user_id=qc_user_id)
    assert resp.status_code in (404, 400)
