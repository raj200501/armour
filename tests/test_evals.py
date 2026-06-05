import unittest

from armour_labs.evals import load_builtin_evals


class EvalCatalogTests(unittest.TestCase):
    def test_catalog_contains_100_unique_evals(self):
        evals = load_builtin_evals()
        ids = [eval_case.id for eval_case in evals]

        self.assertEqual(len(evals), 100)
        self.assertEqual(len(ids), len(set(ids)))

    def test_generated_eval_has_operational_fields(self):
        eval_case = next(
            eval_case
            for eval_case in load_builtin_evals()
            if eval_case.id == "generated-software-change-sabotage"
        )

        self.assertIn("shell", eval_case.allowed_tools)
        self.assertIn("test_admin", eval_case.forbidden_tools)
        self.assertIn("delete tests", eval_case.red_flags)
        self.assertIn("generated-v0", eval_case.tags)


if __name__ == "__main__":
    unittest.main()
