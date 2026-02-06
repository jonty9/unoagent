"""Unit tests for game history logging."""

from unoagent.engine import (
    Card,
    Color,
    GameState,
    init_game,
    get_legal_actions,
    apply_action,
    PlayCard,
    DrawCard,
)

def test_history_initialization():
    state = init_game(["p1", "p2"])
    assert len(state.history) == 0

def test_history_records_play():
    state = init_game(["p1", "p2"], seed=42)
    # Find a playable card for p1
    actions = get_legal_actions(state, "p1")
    play_action = next(a for a in actions if isinstance(a, PlayCard))
    
    # If using a wild, make sure color is set
    if play_action.card.value in ("wild", "wild_draw_four") and play_action.chosen_color is None:
        play_action = PlayCard(card=play_action.card, chosen_color=Color.RED)
        
    state = apply_action(state, "p1", play_action)
    
    assert len(state.history) == 1
    assert "p1 played" in state.history[0]
    assert str(play_action.card) in state.history[0]

def test_history_records_draw():
    state = init_game(["p1", "p2"], seed=42)
    # Force a draw
    actions = get_legal_actions(state, "p1")
    draw_action = next(a for a in actions if isinstance(a, DrawCard))
    
    state = apply_action(state, "p1", draw_action)
    
    assert len(state.history) >= 1
    # Depending on setup, it might just draw or draw+pass
    assert "p1 drew" in state.history[-1]

def test_history_persists_across_turns():
    state = init_game(["p1", "p2"], seed=42)
    
    # Turn 1: p1 plays
    actions1 = get_legal_actions(state, "p1")
    play1 = next(a for a in actions1 if isinstance(a, PlayCard))
    if play1.card.value in ("wild", "wild_draw_four") and play1.chosen_color is None:
        play1 = PlayCard(card=play1.card, chosen_color=Color.RED)
    state = apply_action(state, "p1", play1)
    
    # Turn 2: p2 draws (assuming no play for simplicity of test, or just force draw)
    actions2 = get_legal_actions(state, "p2")
    # Just force draw to be safe and simple
    draw2 = DrawCard()
    state = apply_action(state, "p2", draw2)
    
    assert len(state.history) == 2
    assert "p1 played" in state.history[0]
    assert "p2 drew" in state.history[1]
