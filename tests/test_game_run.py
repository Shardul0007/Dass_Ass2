import game


def _make_game_with_players(players):
    g = game.Game.__new__(game.Game)
    g.board = None
    g.bank = None
    g.dice = None
    g.players = players
    g.current_index = 0
    g.turn_number = 0
    g.running = True
    g.chance_deck = None
    g.community_deck = None
    return g


def test_run_with_no_players_prints_no_winner_message(stub_ui, monkeypatch):
    # CFG: run -> winner is None (else branch)
    g = _make_game_with_players([])
    monkeypatch.setattr(game, "ui", stub_ui)
    monkeypatch.setattr(g, "find_winner", lambda: None, raising=False)

    printed = []

    def _print(*args, **_kwargs):
        printed.append(" ".join(str(a) for a in args))

    monkeypatch.setattr("builtins.print", _print)

    # Act
    g.run()

    # Assert
    assert any("no players remaining" in line for line in printed)


def test_run_with_one_player_prints_game_over_banner(stub_ui, monkeypatch):
    # CFG: run -> len(players) <= 1 causes break; winner exists branch
    from conftest import StubPlayer

    g = _make_game_with_players([StubPlayer("A", balance=10)])
    monkeypatch.setattr(game, "ui", stub_ui)

    # Act
    g.run()

    # Assert
    assert "Welcome to MoneyPoly!" in stub_ui.banners
    assert "GAME OVER" in stub_ui.banners


def test_run_stops_at_max_turns_and_calls_standings_each_turn(stub_ui, monkeypatch):
    # CFG: run -> while self.running and self.turn_number < MAX_TURNS
    from conftest import StubPlayer

    g = _make_game_with_players([StubPlayer("A"), StubPlayer("B")])
    monkeypatch.setattr(game, "ui", stub_ui)

    def _play_turn():
        g.turn_number += 1

    monkeypatch.setattr(g, "play_turn", _play_turn, raising=False)

    # Act
    g.run()

    # Assert
    assert g.turn_number == game.MAX_TURNS
    assert stub_ui.standings_calls == game.MAX_TURNS


def test_run_exits_when_players_reduce_to_one(stub_ui, monkeypatch):
    # CFG: run -> breaks when len(self.players) <= 1 inside loop
    from conftest import StubPlayer

    p1 = StubPlayer("A")
    p2 = StubPlayer("B")
    g = _make_game_with_players([p1, p2])
    monkeypatch.setattr(game, "ui", stub_ui)

    called = {"turns": 0}

    def _play_turn():
        called["turns"] += 1
        g.players = [p1]
        g.turn_number += 1

    monkeypatch.setattr(g, "play_turn", _play_turn, raising=False)

    # Act
    g.run()

    # Assert
    assert called["turns"] == 1
    assert len(g.players) == 1
    assert stub_ui.standings_calls == 1


def test_run_propagates_exception_from_play_turn(stub_ui, monkeypatch):
    # CFG: run -> exception path (no try/except)
    from conftest import StubPlayer

    g = _make_game_with_players([StubPlayer("A"), StubPlayer("B")])
    monkeypatch.setattr(game, "ui", stub_ui)

    def _play_turn():
        raise RuntimeError("boom")

    monkeypatch.setattr(g, "play_turn", _play_turn, raising=False)

    # Act / Assert
    try:
        g.run()
    except RuntimeError as exc:
        assert "boom" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError to propagate")


def test_run_when_not_running_skips_loop_and_does_not_call_play_turn(stub_ui, monkeypatch):
    # CFG: run -> while self.running and ... (False due to self.running)
    from conftest import StubPlayer

    g = _make_game_with_players([StubPlayer("A"), StubPlayer("B")])
    g.running = False
    monkeypatch.setattr(game, "ui", stub_ui)

    def _boom():
        raise AssertionError("play_turn should not be called when running=False")

    monkeypatch.setattr(g, "play_turn", _boom, raising=False)

    # Act
    g.run()

    # Assert
    assert stub_ui.standings_calls == 0
    assert "Welcome to MoneyPoly!" in stub_ui.banners
