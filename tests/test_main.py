import sys
import pytest
from src.main import main

def test_main_executes(monkeypatch):
    # Mock Game and Game.run
    class MockGame:
        def __init__(self):
            pass
        def run(self):
            # Simulate a successful run
            pass
            
    monkeypatch.setattr("src.main.Game", MockGame)
    # Mock sys.exit to avoid test process termination if it's called
    monkeypatch.setattr(sys, "exit", lambda x: None)
    
    # Run main
    main()
    # If no crash, it passes

def test_main_error_handling(monkeypatch):
    # Mock Game to raise error
    class MockGameError:
        def __init__(self):
            raise Exception("Test Error")
            
    monkeypatch.setattr("src.main.Game", MockGameError)
    monkeypatch.setattr(sys, "exit", lambda x: None)
    
    # Should print error and exit(1)
    main()
