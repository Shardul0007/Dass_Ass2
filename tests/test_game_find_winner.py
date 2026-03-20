import game


def test_find_winner_returns_highest_net_worth_player():
    # White-box: winner should be the player with the highest net worth.

    class _P:
        def __init__(self, name, worth):
            self.name = name
            self._worth = worth

        def net_worth(self):
            return self._worth

    p_low = _P("low", 1)
    p_high = _P("high", 999)

    g = game.Game.__new__(game.Game)
    g.players = [p_low, p_high]

    winner = g.find_winner()

    assert winner is p_high
