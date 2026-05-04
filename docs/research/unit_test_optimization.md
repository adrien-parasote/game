# Research Results: Unit Test Optimization

### Topic Decomposition
| # | Sub-Question | Why Necessary | Source Types |
|---|-------------|---------------|-------------|
| 1 | Which tests are the slowest and can they be optimized? | To reduce CI/CD and local development feedback loops. | Pytest `--durations` logs |
| 2 | What are the lowest coverage files? | To maintain and exceed the >=90% global coverage target. | Pytest `--cov-report=term-missing` |
| 3 | How can we increase coverage for UI components? | UI components like dialogue and speech bubble often lack interaction tests. | Pytest mocks and existing UI tests |

### Source Evaluation
| Source | Type | Date | Credibility | Key Findings | Conflicts? |
|--------|------|------|-------------|-------------|------------|
| Pytest Profiling | CLI Output | 2026-05-04 | High | Slowest tests are ~0.07s. Suite total time is ~3.9s. No performance bottlenecks found. | No |
| Coverage Report | CLI Output | 2026-05-04 | High | Global coverage is 91%. Lowest files: tmj_parser.py (79%), project_schema.py (80%), game_state_manager.py (82%), game.py (83%), dialogue.py (83%), pickup.py (83%), speech_bubble.py (84%). | No |
| src/ui/speech_bubble.py | Source Code | 2026-05-04 | High | Lines 215-245 (name_plate rendering) are entirely uncovered because `speaker_name` is never tested. | No |
| src/ui/dialogue.py | Source Code | 2026-05-04 | High | Contains only 1 test. Missing event handling and draw method tests. | No |

### Gaps Identified
| Gap | Why It Matters | What Research Would Fill It |
|-----|---------------|---------------------------|
| SpeechBubble Name Plate | Visual feature untested. Regression risk when changing fonts or scaling. | Write a test passing `speaker_name` to `draw()`. |
| DialogueManager Interaction | Dialogue advance, choices, and typing effects are untested. | Write `update()` and `handle_event()` tests. |
| TMJ Parser Error Handling | Map loading errors could crash the game if not properly handled. | Write tests simulating invalid TMJ JSON structures. |

### Recommendation
- **Chosen approach:** Adapt existing tests and Build new coverage tests.
- **Justification:** The test suite is already highly optimized for speed (3.9s for 532 tests). The "optimization" therefore must focus on **coverage robustness** and **test completeness**, specifically targeting the UI components and Map Parsers that sit below the 85% threshold.
- **Impact on spec:** The specification for tests will be updated to require mocking of `pygame.Surface` and `pygame.font` specifically for testing UI state changes without needing a valid display driver.

### Discovered Patterns
- **Mocking Pygame Surfaces:** `tests/ui/test_speech_bubble.py` correctly uses `MagicMock` for `blit_func` to avoid C-level Pygame dependencies. This pattern should be adopted for `DialogueManager`.
- **Test-Driven UI Interaction:** `tests/engine/test_game.py` simulates Pygame events using mocked Event objects. We will reuse this to test `DialogueManager.handle_event()`.
