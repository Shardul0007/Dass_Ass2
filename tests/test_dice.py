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


def test_dice_doubles_streak_increments_and_resets(monkeypatch):
    seq = [3, 3, 2, 5]

    def _fake_randint(_a, _b):
        return seq.pop(0)

    monkeypatch.setattr(dice.random, "randint", _fake_randint)

    d = dice.Dice()
    assert d.doubles_streak == 0

    d.roll()  # 3,3 doubles
    assert d.is_doubles() is True
    assert d.doubles_streak == 1

    d.roll()  # 2,5 not doubles
    assert d.is_doubles() is False
    assert d.doubles_streak == 0


def test_dice_reset_and_describe_branches():
    d = dice.Dice()
    d.die1 = 2
    d.die2 = 2
    d.doubles_streak = 7

    assert "(DOUBLES)" in d.describe()
    assert "streak=" in repr(d)

    d.reset()
    assert d.die1 == 0
    assert d.die2 == 0
    assert d.doubles_streak == 0

    d.die1 = 1
    d.die2 = 2
    assert "(DOUBLES)" not in d.describe()
