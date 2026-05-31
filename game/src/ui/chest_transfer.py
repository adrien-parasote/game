from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.chest_protocol import ChestUIProtocol


class ChestTransferMixin:
    """Mixin handling item transfers between chest and player inventory."""

    def _transfer_chest_to_inventory(self: "ChestUIProtocol") -> None:
        """Auto-transfer from chest to player inventory."""
        if not self._chest_entity or not self._player:
            return

        contents = self._get_chest_contents()
        for i in range(len(contents)):
            entry = contents[i]
            if entry is None:
                continue

            remaining = self._player.inventory.add_item(entry["item_id"], entry["quantity"])

            if remaining == 0:
                contents[i] = None
            else:
                entry["quantity"] = remaining
                break

    def _transfer_inventory_to_chest(self: "ChestUIProtocol") -> None:
        """Auto-transfer from player inventory to chest."""
        if not self._chest_entity or not self._player:
            return

        contents = self._get_chest_contents()
        inv = self._player.inventory

        for i in range(inv.capacity):
            item = inv.slots[i]
            if item is None:
                continue

            # 1. Try to stack in chest
            stacked = False
            for entry in contents:
                if entry is None:
                    continue
                if entry["item_id"] == item.id and entry["quantity"] < item.stack_max:
                    can_add = min(item.quantity, item.stack_max - entry["quantity"])
                    entry["quantity"] += can_add
                    item.quantity -= can_add
                    if item.quantity <= 0:
                        inv.slots[i] = None
                        stacked = True
                        break

            if stacked:
                continue

            # 2. Add to new slot if chest not full
            for j in range(len(contents)):
                if contents[j] is None:
                    contents[j] = {"item_id": item.id, "quantity": item.quantity}
                    inv.slots[i] = None
                    break
            else:
                # Chest is full
                break

    def _transfer_dragged_to_chest(self: "ChestUIProtocol", target_idx: int) -> None:
        """Move the currently dragged item to the chest at target_idx."""
        if not self._dragging_item or not self._chest_entity or not self._player:
            return

        item_id = self._dragging_item["item_id"]
        qty = self._dragging_item["quantity"]
        source = self._dragging_item["source"]
        src_idx = self._dragging_item["index"]

        contents = self._get_chest_contents()
        target_entry = contents[target_idx]

        if source == "chest":
            if src_idx == target_idx:
                return
            if target_entry is None:
                contents[target_idx] = contents[src_idx]
                contents[src_idx] = None
            elif target_entry["item_id"] == item_id:
                item_data = self._player.inventory.item_data.get(item_id, {})
                stack_max = item_data.get("stack_max", 1)
                can_add = min(qty, stack_max - target_entry["quantity"])
                target_entry["quantity"] += can_add
                contents[src_idx]["quantity"] -= can_add
                if contents[src_idx]["quantity"] <= 0:
                    contents[src_idx] = None
            else:
                contents[target_idx], contents[src_idx] = contents[src_idx], contents[target_idx]
            return

        # Source is inventory
        inv = self._player.inventory

        if target_entry is None:
            contents[target_idx] = {"item_id": item_id, "quantity": qty}
            inv.slots[src_idx] = None
        elif target_entry["item_id"] == item_id:
            item_data = inv.item_data.get(item_id, {})
            stack_max = item_data.get("stack_max", 1)
            can_add = min(qty, stack_max - target_entry["quantity"])
            target_entry["quantity"] += can_add
            inv.slots[src_idx].quantity -= can_add
            if inv.slots[src_idx].quantity <= 0:
                inv.slots[src_idx] = None
        else:
            swapped_id = target_entry["item_id"]
            swapped_qty = target_entry["quantity"]

            contents[target_idx] = {"item_id": item_id, "quantity": qty}
            inv.slots[src_idx] = inv.create_item(swapped_id, swapped_qty)

    def _transfer_dragged_to_inventory(self: "ChestUIProtocol", target_idx: int) -> None:
        """Move the currently dragged item to the player inventory at target_idx."""
        if not self._dragging_item or not self._player:
            return

        item_id = self._dragging_item["item_id"]
        qty = self._dragging_item["quantity"]
        source = self._dragging_item["source"]
        src_idx = self._dragging_item["index"]

        inv = self._player.inventory
        target_slot = inv.slots[target_idx]

        if source == "inv":
            if src_idx == target_idx:
                return
            if target_slot is None:
                inv.slots[target_idx] = inv.slots[src_idx]
                inv.slots[src_idx] = None
            elif target_slot.id == item_id:
                can_add = min(qty, target_slot.stack_max - target_slot.quantity)
                target_slot.quantity += can_add
                inv.slots[src_idx].quantity -= can_add
                if inv.slots[src_idx].quantity <= 0:
                    inv.slots[src_idx] = None
            else:
                inv.slots[target_idx], inv.slots[src_idx] = (
                    inv.slots[src_idx],
                    inv.slots[target_idx],
                )
            return

        # Source is chest
        contents = self._get_chest_contents()

        if target_slot is None:
            inv.slots[target_idx] = inv.create_item(item_id, qty)
            contents[src_idx] = None
        elif target_slot.id == item_id:
            can_add = min(qty, target_slot.stack_max - target_slot.quantity)
            target_slot.quantity += can_add
            contents[src_idx]["quantity"] -= can_add
            if contents[src_idx]["quantity"] <= 0:
                contents[src_idx] = None
        else:
            swapped_id = target_slot.id
            swapped_qty = target_slot.quantity

            inv.slots[target_idx] = inv.create_item(item_id, qty)
            contents[src_idx] = {"item_id": swapped_id, "quantity": swapped_qty}
