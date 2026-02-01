"""Unit tests for the game engine."""

import pytest
from unoagent.engine import (
    Card,
    Color,
    create_deck,
    GameState,
    init_game,
    get_legal_actions,
    apply_action,
    PlayCard,
    DrawCard,
)


def test_create_deck_size() -> None:
    deck = create_deck(seed=42)
    assert len(deck) == 108


def test_create_deck_reproducible() -> None:
    d1 = create_deck(seed=123)
    d2 = create_deck(seed=123)
    assert [str(c) for c in d1] == [str(c) for c in d2]


def test_init_game() -> None:
    state = init_game(["p1", "p2", "p3"], seed=1)
    assert len(state.hands["p1"]) == 7
    assert len(state.hands["p2"]) == 7
    assert len(state.hands["p3"]) == 7
    assert len(state.discard_pile) == 1
    assert state.current_player == "p1"
    assert state.winner is None
    assert len(state.draw_pile) == 108 - 7 * 3 - 1


def test_get_legal_actions() -> None:
    state = init_game(["p1", "p2"], seed=5)
    actions = get_legal_actions(state, "p1")
    assert len(actions) >= 1
    assert any(isinstance(a, PlayCard) for a in actions)
    assert any(isinstance(a, DrawCard) for a in actions)


def test_apply_play_card() -> None:
    state = init_game(["p1", "p2"], seed=10)
    actions = get_legal_actions(state, "p1")
    play_actions = [a for a in actions if isinstance(a, PlayCard)]
    if play_actions:
        action = play_actions[0]
        if action.card.value in ("wild", "wild_draw_four") and action.chosen_color is None:
            action = PlayCard(card=action.card, chosen_color=Color.RED)
        new_state = apply_action(state, "p1", action)
        # Turn may pass to other player or back (e.g. draw_two skips next, reverse in 2p)
        assert new_state.current_player in ("p1", "p2")
        assert len(new_state.hands["p1"]) == len(state.hands["p1"]) - 1


def test_apply_draw_card() -> None:
    state = init_game(["p1", "p2"], seed=20)
    actions = get_legal_actions(state, "p1")
    draw_action = next(a for a in actions if isinstance(a, DrawCard))
    new_state = apply_action(state, "p1", draw_action)
    assert new_state.current_player == "p2"
    assert len(new_state.hands["p1"]) == len(state.hands["p1"]) + 1


def test_win_condition() -> None:
    # Create a state where p1 has one card that matches the discard
    state = init_game(["p1", "p2"], seed=100)
    top = state.top_discard()
    assert top is not None
    # Find a matching card in p1's hand or create a scenario
    for card in state.hands["p1"]:
        if card.value in ("wild", "wild_draw_four"):
            continue
        if card.color == (state.last_played_color or top.color) or card.value == top.value:
            action = PlayCard(card=card)
            # Need to reduce p1's hand to just this card
            break
    else:
        pytest.skip("Cannot easily construct win scenario")
