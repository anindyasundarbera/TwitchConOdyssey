import ast
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
REMOVED_LOCATION_TERMS = (
    "".join(("san ", "fran", "cisco")),
    "".join(("san_", "fran", "cisco")),
    "".join(("mos", "cone")),
    "".join(("china", "town")),
    "".join(("financial ", "district")),
    "".join(("yerba ", "buena")),
    "".join(("trans", "america")),
)
REMOVED_CITY_ABBREVIATION = re.compile(
    r"\b" + "".join(("s", "f")) + r"\b", re.IGNORECASE)
SAN_DIEGO_ROUTE = (
    "Little Italy / North Embarcadero",
    "Embarcadero Waterfront / Marina",
    "Gaslamp Quarter",
    "San Diego Convention Center",
    "Fictional Main Stage",
)


class CitySettingTests(unittest.TestCase):
    def test_repository_excludes_removed_city_and_landmarks(self):
        for path in ROOT.rglob("*"):
            if (not path.is_file() or ".git" in path.parts
                    or "__pycache__" in path.parts):
                continue
            try:
                text = path.read_text().lower()
            except UnicodeDecodeError:
                continue
            for forbidden in REMOVED_LOCATION_TERMS:
                with self.subTest(path=path.relative_to(ROOT), forbidden=forbidden):
                    self.assertNotIn(forbidden, text)
            with self.subTest(path=path.relative_to(ROOT), forbidden="city abbreviation"):
                self.assertIsNone(REMOVED_CITY_ABBREVIATION.search(text))

    def test_authoritative_districts_match_san_diego_plan(self):
        tree = ast.parse((ROOT / "server/engine.py").read_text())
        districts = next(
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "DISTRICTS"
                    for target in node.targets)
        )
        self.assertEqual(districts, SAN_DIEGO_ROUTE)
        plan = json.loads((ROOT / "docs/planning/gameplan-v2.json").read_text())
        self.assertEqual(plan["setting"]["city"], "San Diego, California")
        self.assertIn("San Diego", plan["setting"]["runtime_city_status"])

    def test_visible_client_names_san_diego_route(self):
        client = (ROOT / "client/index.html").read_text()
        canvas = (ROOT / "client/app.js").read_text()
        for label in ("SAN DIEGO", "Little Italy", "San Diego Convention Center"):
            self.assertIn(label, client)
        for label in ("S A N  D I E G O  B A Y", "LITTLE ITALY / NORTH EMBARCADERO",
                      "GASLAMP QUARTER", "SAN DIEGO CONVENTION CENTER"):
            self.assertIn(label, canvas)


if __name__ == "__main__":
    unittest.main()
