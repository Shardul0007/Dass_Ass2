import game


def _make_game_with_stubs(*, dice, players):
    g = game.Game.__new__(game.Game)
    g.board = None
    g.bank = None
    g.dice = dice
    g.players = players
    g.current_index = 0
    g.turn_number = 0
    g.running = True
    g.chance_deck = None
    g.community_deck = None
    return g


class _FakeDice:
    def __init__(self, *, roll_total=7, doubles_streak=0, doubles=False):
        self._roll_total = roll_total
        self.doubles_streak = doubles_streak
        self._doubles = doubles

    def roll(self):
        return self._roll_total

    def is_doubles(self):
        return self._doubles

    def describe(self):
        return "fake"


def test_play_turn_in_jail_branch_handles_jail_and_advances(stub_ui, monkeypatch):
    # CFG: play_turn -> if player.in_jail (True branch)
    from conftest import StubPlayer

    player = StubPlayer("A")
    player.in_jail = True
    g = _make_game_with_stubs(dice=_FakeDice(), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"jail": 0, "advance": 0}

    monkeypatch.setattr(g, "_handle_jail_turn", lambda _p: called.__setitem__("jail", called["jail"] + 1))
    monkeypatch.setattr(g, "advance_turn", lambda: called.__setitem__("advance", called["advance"] + 1))
    monkeypatch.setattr(g, "_move_and_resolve", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Should not move while jailed")))

    # Act
    g.play_turn()

    # Assert
    assert called["jail"] == 1
    assert called["advance"] == 1


def test_play_turn_three_doubles_sends_player_to_jail_and_advances(stub_ui, monkeypatch):
    # CFG: play_turn -> if self.dice.doubles_streak >= 3 (True branch)
    from conftest import StubPlayer

    player = StubPlayer("A", position=0)
    g = _make_game_with_stubs(dice=_FakeDice(doubles_streak=3, doubles=True, roll_total=4), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"advance": 0}
    monkeypatch.setattr(g, "advance_turn", lambda: called.__setitem__("advance", called["advance"] + 1))
    monkeypatch.setattr(g, "_move_and_resolve", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Should not move after third doubles")))

    # Act
    g.play_turn()

    # Assert
    assert player.in_jail is True
    assert player.position == 10
    assert called["advance"] == 1


def test_play_turn_doubles_grants_extra_turn_does_not_advance(stub_ui, monkeypatch):
    # CFG: play_turn -> if self.dice.is_doubles() (True branch)
    from conftest import StubPlayer

    player = StubPlayer("A")
    g = _make_game_with_stubs(dice=_FakeDice(doubles_streak=1, doubles=True, roll_total=6), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"move": 0, "advance": 0}
    monkeypatch.setattr(g, "_move_and_resolve", lambda _p, steps: called.__setitem__("move", steps))
    monkeypatch.setattr(g, "advance_turn", lambda: called.__setitem__("advance", called["advance"] + 1))

    # Act
    g.play_turn()

    # Assert
    assert called["move"] == 6
    assert called["advance"] == 0


def test_play_turn_non_doubles_advances_turn(stub_ui, monkeypatch):
    # CFG: play_turn -> if self.dice.is_doubles() (False branch)
    from conftest import StubPlayer

    player = StubPlayer("A")
    g = _make_game_with_stubs(dice=_FakeDice(doubles_streak=0, doubles=False, roll_total=5), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"move": 0, "advance": 0}
    monkeypatch.setattr(g, "_move_and_resolve", lambda _p, steps: called.__setitem__("move", steps))
    monkeypatch.setattr(g, "advance_turn", lambda: called.__setitem__("advance", called["advance"] + 1))

    # Act
    g.play_turn()

    # Assert
    assert called["move"] == 5
    assert called["advance"] == 1

def test_play_turn_banner_turn_number_is_one_indexed(stub_ui, monkeypatch):
    from conftest import StubPlayer

    player = StubPlayer("A")
    g = _make_game_with_stubs(dice=_FakeDice(doubles_streak=0, doubles=False, roll_total=5), players=[player])
    monkeypatch.setattr(game, "ui", stub_ui)

    monkeypatch.setattr(g, "_move_and_resolve", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(g, "advance_turn", lambda: None)

    g.turn_number = 0
    g.play_turn()

    assert stub_ui.banners, "Expected play_turn() to render a banner"
    assert stub_ui.banners[0].startswith("Turn 1"), stub_ui.banners[0]
