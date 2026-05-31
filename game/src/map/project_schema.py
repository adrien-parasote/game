import json
import logging
import os


class TiledProject:
    """
    Registry for Tiled Project metadata.
    Handles recursive resolution of class-based custom properties.
    """

    def __init__(self, project_path: str):
        self.registry: dict[str, dict] = {}
        self._load(project_path)

    def _load(self, path: str):
        """Loads and parses the .tiled-project file into a class registry."""
        if not os.path.exists(path):
            logging.warning(f"Tiled project file not found: {path}")
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            property_types = data.get("propertyTypes", [])
            for pt in property_types:
                if pt.get("type") == "class":
                    self.registry[pt["name"]] = pt
        except Exception as e:
            logging.error(f"Failed to load tiled project {path}: {e}")

    def resolve(self, class_name: str, overrides: dict | None = None) -> dict:
        """
        Recursively merges class defaults with provided overrides.

        Args:
            class_name: The name of the Tiled class to resolve.
            overrides: A dictionary of values provided by the map instance.

        Returns:
            A complete dictionary of properties with defaults filled in.
        """
        if overrides is None:
            overrides = {}

        template = self.registry.get(class_name)
        if not template:
            # If class is unknown, we can't resolve defaults, just return overrides
            return overrides

        resolved = {}
        members = template.get("members", [])

        for member in members:
            name = member["name"]
            m_type = member.get("type", "string")
            default_val = member.get("value")

            # 1. Start with the class-level default for this member
            current_val = default_val

            # 2. Apply instance-level override for this member if present
            instance_override = overrides.get(name)

            if m_type == "class":
                prop_type = member.get("propertyType")
                # For classes, 'current_val' is a dict of defaults for the nested class
                # We merge template defaults with ANY overrides provided at the instance level
                nested_overrides = instance_override if instance_override is not None else {}

                # Special case: Tiled allows providing a dict of overrides as the "value" of a class member
                # We base our resolution on the template's nested defaults
                base_nested_defaults = default_val if isinstance(default_val, dict) else {}

                # Resolve the nested class
                # We combine template's nested overrides with instance's nested overrides
                combined_overrides = {**base_nested_defaults, **nested_overrides}
                resolved[name] = self.resolve(prop_type, combined_overrides)
            else:
                # For primitives, instance override takes absolute priority
                resolved[name] = instance_override if instance_override is not None else current_val

        # 3. Preserve any properties from overrides that weren't in the template members
        # This ensures ad-hoc properties added in the map but not in the Tiled Project Class are kept.
        for key, value in overrides.items():
            if key not in resolved:
                resolved[key] = value

        return resolved
