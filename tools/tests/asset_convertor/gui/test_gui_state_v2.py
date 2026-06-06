"""
Unit tests for AppState v2 and RecolorState.

Spec: tools/docs/specs/asset_convertor_mv_gui.md

TDD: Tests written RED — state.py refactor not yet done.
IDs: TC-001 … TC-010 (unit), IT-001 … IT-005 (integration)
"""

from __future__ import annotations

import dataclasses

import pytest
from PIL import Image

# ===========================================================================
# AppState — UNIT TESTS
# ===========================================================================

class TestAppStateV2:

    def setup_method(self) -> None:
        from asset_convertor.gui.state import AppState, RecolorState
        self.AppState = AppState
        self.RecolorState = RecolorState

    # TC-001: Default resource_type is "A2"
    def test_default_resource_type(self) -> None:
        state = self.AppState()
        assert state.resource_type == "A2"

    # TC-002: Default format is "MV"
    def test_default_format(self) -> None:
        state = self.AppState()
        assert state.format == "MV"

    # TC-003: resource_type and format are independent
    def test_resource_type_and_format_independent(self) -> None:
        state = self.AppState()
        s2 = dataclasses.replace(state, resource_type="A3", format="XP")
        assert s2.resource_type == "A3"
        assert s2.format == "XP"

    # TC-004: AppState is frozen (FrozenInstanceError on mutation)
    def test_frozen(self) -> None:
        state = self.AppState()
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.format = "XP"  # type: ignore[misc]

    # TC-005: export_tsx defaults to True
    def test_export_tsx_default_true(self) -> None:
        state = self.AppState()
        assert state.export_tsx is True

    # TC-006: export_png defaults to True
    def test_export_png_default_true(self) -> None:
        state = self.AppState()
        assert state.export_png is True

    # TC-007: recolor defaults to None
    def test_recolor_default_none(self) -> None:
        state = self.AppState()
        assert state.recolor is None

    # TC-008: RecolorState remap_table defaults to empty dict
    def test_recolor_state_default_remap_empty(self) -> None:
        rs = self.RecolorState()
        assert rs.remap_table == {}

    # TC-009: RecolorState source_palette defaults to empty list
    def test_recolor_state_default_palette_empty(self) -> None:
        rs = self.RecolorState()
        assert rs.source_palette == []

    # TC-010: replace() preserves nested RecolorState
    def test_replace_preserves_recolor_state(self) -> None:
        state = self.AppState()
        rs = self.RecolorState(active_preset="Autumn")
        s2 = dataclasses.replace(state, recolor=rs)
        assert s2.recolor.active_preset == "Autumn"


# ===========================================================================
# AppState — INTEGRATION TESTS
# ===========================================================================

class TestAppStateIntegration:

    def setup_method(self) -> None:
        from asset_convertor.gui.state import AppState, RecolorState
        self.AppState = AppState
        self.RecolorState = RecolorState

    # IT-001: resource_type "Recolor" → export_tsx should be False (business rule tested via helper)
    def test_recolor_type_tsx_false_logic(self) -> None:
        state = self.AppState(resource_type="Recolor", export_tsx=False)
        assert state.resource_type == "Recolor"
        assert state.export_tsx is False

    # IT-002: Switching from Recolor back to A2 restores export_tsx=True via replace()
    def test_non_recolor_type_tsx_true(self) -> None:
        state = self.AppState(resource_type="Recolor", export_tsx=False)
        s2 = dataclasses.replace(state, resource_type="A2", export_tsx=True)
        assert s2.export_tsx is True

    # IT-003: RecolorState can hold a full palette
    def test_recolor_state_holds_palette(self) -> None:
        palette = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]
        rs = self.RecolorState(source_palette=palette)
        assert len(rs.source_palette) == 3

    # IT-004: Full replace chain doesn't mutate intermediate states
    def test_replace_chain_immutable(self) -> None:
        s0 = self.AppState()
        s1 = dataclasses.replace(s0, resource_type="A3")
        s2 = dataclasses.replace(s1, format="XP")
        # s0 and s1 unchanged
        assert s0.resource_type == "A2"
        assert s1.format == "MV"
        assert s2.format == "XP"
        assert s2.resource_type == "A3"

    # IT-005: AppState has no 'mode' attribute (it was renamed to 'format')
    def test_no_mode_attribute(self) -> None:
        state = self.AppState()
        assert not hasattr(state, "mode"), (
            "'mode' attribute still present — rename to 'format' not complete"
        )


# ===========================================================================
# Resize ResourceType — UNIT TESTS
# Spec: tools/docs/specs/asset_convertor_toolbar_split_resize.md
# IDs: TC-RSZ-U-001 … TC-RSZ-U-005
# ===========================================================================

class TestResizeResourceType:

    def setup_method(self) -> None:
        from asset_convertor.gui.state import AppState
        self.AppState = AppState

    # TC-RSZ-U-001: ResourceType accepte "Resize"
    def test_resize_resource_type_accepted(self) -> None:
        state = self.AppState(resource_type="Resize")  # type: ignore[arg-type]
        assert state.resource_type == "Resize"

    # TC-RSZ-U-002: AppState Resize force export_tsx=False (règle métier testée via state)
    def test_resize_export_tsx_can_be_false(self) -> None:
        state = self.AppState(resource_type="Resize", export_tsx=False)  # type: ignore[arg-type]
        assert state.export_tsx is False

    # TC-RSZ-U-003: dataclasses.replace() préserve resource_type="Resize"
    def test_replace_preserves_resize_type(self) -> None:
        import dataclasses
        state = self.AppState()
        s2 = dataclasses.replace(state, resource_type="Resize")  # type: ignore[arg-type]
        assert s2.resource_type == "Resize"

    # TC-RSZ-U-004: AppState frozen avec resource_type="Resize"
    def test_frozen_with_resize_type(self) -> None:
        import dataclasses
        state = self.AppState(resource_type="Resize")  # type: ignore[arg-type]
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.resource_type = "A2"  # type: ignore[misc]

    # TC-RSZ-U-005: result_img est None par défaut pour Resize
    def test_resize_result_img_none_by_default(self) -> None:
        state = self.AppState(resource_type="Resize")  # type: ignore[arg-type]
        assert state.result_img is None
