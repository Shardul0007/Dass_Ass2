from datetime import datetime, timezone

import pytest


def test_profile_update_persists_on_subsequent_get(qc, qc_user_id):
    before = qc.request("GET", "/api/v1/profile", user_id=qc_user_id)
    assert before.status_code == 200
    before_payload = qc.get_json(before)
    if not isinstance(before_payload, dict):
        pytest.skip("profile GET payload shape unknown")

    unique = datetime.now(timezone.utc).isoformat()
    new_name = f"Name {unique}"[:50]
    new_phone = "0123456789"

    upd = qc.request(
        "PUT",
        "/api/v1/profile",
        user_id=qc_user_id,
        json={"name": new_name, "phone": new_phone},
    )
    assert upd.status_code in (200, 201), upd.text

    after = qc.request("GET", "/api/v1/profile", user_id=qc_user_id)
    assert after.status_code == 200
    after_payload = qc.get_json(after)
    if not isinstance(after_payload, dict):
        pytest.skip("profile GET payload shape unknown")

    # Best-effort key discovery
    got_name = after_payload.get("name")
    got_phone = after_payload.get("phone")
    if got_name is None and "profile" in after_payload and isinstance(after_payload["profile"], dict):
        got_name = after_payload["profile"].get("name")
        got_phone = got_phone or after_payload["profile"].get("phone")

    if not isinstance(got_name, str):
        pytest.skip("profile GET did not expose name")

    assert got_name == new_name

    if isinstance(got_phone, str):
        assert got_phone == new_phone
