import dice


def test_dice_roll_uses_six_sided_die(monkeypatch):
    # White-box: verify Dice.roll uses randint(1, 6) not randint(1, 5).
    calls = []

    def _fake_randint(a, b):
        calls.append((a, b))
        return 1

    monkeypatch.setattr(dice.random, "randint", _fake_randint)

    d = dice.Dice()
    d.roll()

    assert calls, "Expected randint to be called"
    assert all(a == 1 and b == 6 for a, b in calls)
