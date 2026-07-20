import pytest
from src.framework.stagehand.agent import StagehandAgent

def test_stagehand_login_and_add_backpack(setup_teardown):
    page = setup_teardown
    agent = StagehandAgent(page, max_steps=7)
    
    # Declarative objective
    history = agent.execute_goal("Log in as standard_user and add the backpack to the cart")
    
    # Assert that planning successfully concluded
    assert len(history) > 0
    assert any(h["action"] == "complete" for h in history)
