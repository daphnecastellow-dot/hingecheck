import tempfile
import unittest
from pathlib import Path

from hingecheck import (
    HingecheckError,
    add_assumption,
    add_authority,
    add_dependent,
    audit,
    change_status,
    impact,
    load,
    new_project,
    render_markdown,
    render_mermaid,
    save,
)


class HingecheckTests(unittest.TestCase):
    def test_challenged_hinge_surfaces_dependents_without_mutating_them(self):
        data = new_project("North Reach")
        add_authority(data, "A001", "Sourceweave check", "sourceweave:S004", "tool-record")
        hid = add_assumption(data, "S004 is independent of S002.", "uncertain", ["A001"], "Relationship established.")
        add_dependent(data, hid, "E007", "evidence", "relies-on", "Independence affects corroboration.")
        change_status(data, hid, "challenged", "S004 cites material derived from S002.", ["A001"])
        deps = impact(data, hid)
        self.assertEqual(deps[0]["id"], "E007")
        self.assertEqual(data["assumptions"][0]["status"], "challenged")

    def test_dependency_is_explicit_not_inferred(self):
        data = new_project("Explicit")
        hid = add_assumption(data, "An assumption.")
        self.assertEqual(impact(data, hid), [])

    def test_duplicate_dependent_is_rejected(self):
        data = new_project("Duplicates")
        hid = add_assumption(data, "A hinge.")
        add_dependent(data, hid, "C001", "claim", "requires", "Needed.")
        with self.assertRaises(HingecheckError):
            add_dependent(data, hid, "C001", "claim", "requires", "Again.")

    def test_audit_flags_thin_assumption(self):
        data = new_project("Audit")
        add_assumption(data, "Thin assumption.")
        findings = audit(data)
        self.assertTrue(any("no authority pointer" in x for x in findings))
        self.assertTrue(any("no recheck condition" in x for x in findings))

    def test_round_trip_and_renderers(self):
        data = new_project("Render")
        add_authority(data, "A001", "Ledger", "evidence:E001", "tool-record")
        hid = add_assumption(data, "Sources are independent.", "supported", ["A001"], "Source relation changes.")
        add_dependent(data, hid, "U004", "writing-unit", "weakens-if-false", "Wording strength depends on independence.")

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "hinges.json"
            save(p, data)
            loaded = load(p)

        self.assertIn("U004", render_markdown(loaded))
        self.assertIn("weakens-if-false", render_mermaid(loaded))


if __name__ == "__main__":
    unittest.main()
