"""Repository-level checks which do not require a Home Assistant test install."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "opple"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RepositoryTests(unittest.TestCase):
    """Validate the installable repository layout."""

    def test_manifest_is_a_modern_config_flow_integration(self) -> None:
        """The manifest must override the legacy core integration cleanly."""
        manifest = _load_json(COMPONENT / "manifest.json")
        self.assertEqual(manifest["domain"], "opple")
        self.assertIs(manifest["config_flow"], True)
        self.assertEqual(manifest["integration_type"], "device")
        self.assertEqual(manifest["iot_class"], "local_polling")
        self.assertTrue(manifest["version"])

    def test_translations_match_source_strings(self) -> None:
        """English translations should stay synchronized with strings.json."""
        self.assertEqual(
            _load_json(COMPONENT / "strings.json"),
            _load_json(COMPONENT / "translations" / "en.json"),
        )

    def test_required_component_files_exist(self) -> None:
        """All runtime modules required by the integration are present."""
        for name in {
            "__init__.py",
            "config_flow.py",
            "const.py",
            "coordinator.py",
            "diagnostics.py",
            "light.py",
            "manifest.json",
            "strings.json",
        }:
            with self.subTest(name=name):
                self.assertTrue((COMPONENT / name).is_file())


if __name__ == "__main__":
    unittest.main()
