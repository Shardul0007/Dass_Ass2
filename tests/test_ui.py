import ui


class _StubProp:
    def __init__(self, name="P", rent=1, mortgaged=False):
        self.name = name
        self._rent = rent
        self.is_mortgaged = mortgaged

    def get_rent(self):
        return self._rent


class _StubPlayer:
    def __init__(self):
        self.name = "A"
        self.balance = 1500
        self.position = 0
        self.properties = []
        self._worth = 1500
        self.in_jail = False
        self.jail_turns = 0
        self.get_out_of_jail_cards = 0

    def net_worth(self):
        return self._worth

    def count_properties(self):
        return len(self.properties)


def test_format_currency_handles_zero_and_negative():
    assert ui.format_currency(0) == "$0"
    assert ui.format_currency(-1) == "$-1"


def test_safe_int_input_valid_number(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _p: "123")
    assert ui.safe_int_input("> ", default=0) == 123


def test_safe_int_input_invalid_returns_default(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _p: "abc")
    assert ui.safe_int_input("> ", default=7) == 7


def test_confirm_yes_variants(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _p: "Y")
    assert ui.confirm("?") is True


def test_confirm_no_variants(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _p: "n")
    assert ui.confirm("?") is False


def test_print_player_card_branches_do_not_crash(monkeypatch):
    # White-box: exercise jail line, jail cards line, properties list, mortgaged tag.
    p = _StubPlayer()
    p.in_jail = True
    p.jail_turns = 2
    p.get_out_of_jail_cards = 1
    p.properties = [_StubProp("P1", rent=10, mortgaged=True), _StubProp("P2", rent=5, mortgaged=False)]

    out = []

    def _print(*args, **kwargs):
        out.append(" ".join(str(a) for a in args))

    monkeypatch.setattr("builtins.print", _print)

    ui.print_player_card(p)

    assert any("IN JAIL" in line for line in out)
    assert any("Jail cards" in line for line in out)
    assert any("[MORTGAGED]" in line for line in out)


def test_print_standings_sorts_by_net_worth_desc(monkeypatch):
    p1 = _StubPlayer()
    p1.name = "low"
    p1._worth = 1

    p2 = _StubPlayer()
    p2.name = "high"
    p2._worth = 999

    lines = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: lines.append(" ".join(str(x) for x in a)))

    ui.print_standings([p1, p2])

    # Expect rank 1 is 'high'
    joined = "\n".join(lines)
    assert "1. high" in joined
