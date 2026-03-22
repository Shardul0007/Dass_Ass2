import pytest


def _extract_address_id(payload: object) -> int | None:
    if isinstance(payload, dict):
        if isinstance(payload.get("address"), dict):
            payload = payload["address"]
        aid = payload.get("address_id")
        if isinstance(aid, int) and aid > 0:
            return aid
    return None


def _as_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list):
                return v
    return []


def test_address_update_persists_street_change(qc, qc_user_id):
    create = qc.request(
        "POST",
        "/api/v1/addresses",
        user_id=qc_user_id,
        json={"label": "OTHER", "street": "44444 Persist Street", "city": "Persist", "pincode": "444444", "is_default": False},
    )
    assert create.status_code in (200, 201), create.text
    address_id = _extract_address_id(qc.get_json(create))
    if address_id is None:
        pytest.skip("Could not determine address_id from create response")

    new_street = "44444 Persist Street UPDATED"
    upd = qc.request(
        "PUT",
        f"/api/v1/addresses/{address_id}",
        user_id=qc_user_id,
        json={"street": new_street, "is_default": False},
    )
    assert upd.status_code in (200, 201), upd.text

    lst = qc.request("GET", "/api/v1/addresses", user_id=qc_user_id)
    assert lst.status_code == 200
    payload = qc.get_json(lst)
    addrs = [a for a in _as_list(payload) if isinstance(a, dict)]
    if not addrs and isinstance(payload, dict):
        v = payload.get("addresses") or payload.get("data")
        if isinstance(v, list):
            addrs = [a for a in v if isinstance(a, dict)]

    target = next((a for a in addrs if a.get("address_id") == address_id), None)
    assert target is not None, f"Could not find address_id={address_id} in list"

    assert target.get("street") == new_street, f"Street did not persist. target={target!r}"
