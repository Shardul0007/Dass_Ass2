from __future__ import annotations

import pytest


def _iter_dicts(payload):
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
    elif isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        yield item


def _find_address(payload, address_id: int) -> dict | None:
    for row in _iter_dicts(payload):
        aid = row.get("address_id") or row.get("id")
        if aid == address_id:
            return row
        if isinstance(aid, str) and aid.isdigit() and int(aid) == address_id:
            return row
    return None


def test_address_update_does_not_allow_restricted_field_changes(qc, qc_user_id):
    create = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={
            "label": "HOME",
            "street": "11111 Alpha Street",
            "city": "Alpha",
            "pincode": "111111",
            "is_default": False,
        },
    )
    assert create.status_code in (200, 201), create.text
    created_payload = qc.get_json(create)
    created_addr = created_payload.get("address") if isinstance(created_payload, dict) else None
    assert isinstance(created_addr, dict) and created_addr.get("address_id"), f"Unexpected create payload: {created_payload!r}"

    address_id = int(created_addr["address_id"])
    original = {
        "label": str(created_addr.get("label")),
        "city": str(created_addr.get("city")),
        "pincode": str(created_addr.get("pincode")),
        "street": str(created_addr.get("street")),
    }

    new_street = "22222 Beta Street"
    update = qc.request(
        "PUT",
        f"/api/v1/addresses/{address_id}",
        user_id=qc_user_id,
        json={
            "label": "OFFICE",
            "street": new_street,
            "city": "ChangedCity",
            "pincode": "999999",
            "is_default": True,
        },
    )

    # Spec allows either rejecting the request (400) or accepting but ignoring restricted fields.
    if update.status_code == 400:
        return
    assert update.status_code in (200, 201), update.text

    # Verify actual stored data via admin endpoint.
    admin = qc.request("GET", "/api/v1/admin/addresses")
    assert admin.status_code == 200, admin.text
    row = _find_address(qc.get_json(admin), address_id)
    assert isinstance(row, dict), f"Could not find address_id={address_id} in admin/addresses"

    assert str(row.get("label")) == original["label"], f"label changed: was {original['label']!r} now {row.get('label')!r}"
    assert str(row.get("city")) == original["city"], f"city changed: was {original['city']!r} now {row.get('city')!r}"
    assert str(row.get("pincode")) == original["pincode"], f"pincode changed: was {original['pincode']!r} now {row.get('pincode')!r}"

    # Street is allowed to change; if update claimed success, expect it to actually persist.
    assert str(row.get("street")) == new_street, f"street did not update: expected {new_street!r} got {row.get('street')!r}"
