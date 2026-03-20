import cards


def test_card_deck_draw_on_empty_returns_none():
    d = cards.CardDeck([])
    assert d.draw() is None


def test_card_deck_peek_on_empty_returns_none():
    d = cards.CardDeck([])
    assert d.peek() is None


def test_card_deck_draw_cycles_through_cards():
    c1 = {"description": "1", "action": "collect", "value": 1}
    c2 = {"description": "2", "action": "collect", "value": 2}
    d = cards.CardDeck([c1, c2])

    assert d.draw() is c1
    assert d.draw() is c2
    assert d.draw() is c1


def test_card_deck_peek_does_not_advance_index():
    c1 = {"description": "1", "action": "collect", "value": 1}
    c2 = {"description": "2", "action": "collect", "value": 2}
    d = cards.CardDeck([c1, c2])

    assert d.peek() is c1
    assert d.peek() is c1
    assert d.draw() is c1
    assert d.peek() is c2


def test_card_deck_cards_remaining_counts_down_mod_len():
    c1 = {"description": "1", "action": "collect", "value": 1}
    c2 = {"description": "2", "action": "collect", "value": 2}
    c3 = {"description": "3", "action": "collect", "value": 3}
    d = cards.CardDeck([c1, c2, c3])

    assert d.cards_remaining() == 3
    d.draw()
    assert d.cards_remaining() == 2
    d.draw()
    assert d.cards_remaining() == 1
    d.draw()
    assert d.cards_remaining() == 3


def test_card_deck_reshuffle_resets_index_and_calls_shuffle(monkeypatch):
    c1 = {"description": "1", "action": "collect", "value": 1}
    c2 = {"description": "2", "action": "collect", "value": 2}
    d = cards.CardDeck([c1, c2])

    d.draw()
    assert d.index == 1

    called = {"shuffle": 0}

    def _fake_shuffle(_cards):
        called["shuffle"] += 1

    monkeypatch.setattr(cards.random, "shuffle", _fake_shuffle)

    d.reshuffle()

    assert called["shuffle"] == 1
    assert d.index == 0


def test_card_deck_len_and_repr():
    c1 = {"description": "1", "action": "collect", "value": 1}
    d = cards.CardDeck([c1])

    assert len(d) == 1
    assert "CardDeck(" in repr(d)
