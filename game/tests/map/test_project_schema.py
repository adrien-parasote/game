import json
import logging


class TestTiledProjectCoverage:
    def test_missing_file_warns(self, caplog, tmp_path):
        from src.map.project_schema import TiledProject

        with caplog.at_level(logging.WARNING):
            TiledProject(str(tmp_path / "missing.tiled-project"))
        assert "not found" in caplog.text.lower()

    def test_bad_json_logs_error(self, caplog, tmp_path):
        from src.map.project_schema import TiledProject

        bad = tmp_path / "bad.tiled-project"
        bad.write_text("{bad json")
        with caplog.at_level(logging.ERROR):
            TiledProject(str(bad))
        assert caplog.text  # error was logged

    def test_resolve_nested_class(self, tmp_path):
        from src.map.project_schema import TiledProject

        data = {
            "propertyTypes": [
                {
                    "type": "class",
                    "name": "Inner",
                    "members": [{"name": "color", "type": "string", "value": "red"}],
                },
                {
                    "type": "class",
                    "name": "Outer",
                    "members": [
                        {"name": "inner", "type": "class", "propertyType": "Inner", "value": {}}
                    ],
                },
            ]
        }
        f = tmp_path / "p.tiled-project"
        f.write_text(json.dumps(data))
        tp = TiledProject(str(f))
        result = tp.resolve("Outer", {})
        assert "inner" in result


# assert True (legacy bypass)

# assert True (legacy bypass)
