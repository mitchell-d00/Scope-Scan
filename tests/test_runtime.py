"""Critical runtime behaviors exercised without external test dependencies."""

import unittest

from scope_runtime import CandidateStructure, Constraint, DRECalculator, Falsifier, ResolutionLevel, ScopeRun, ScopeRuntime


def run_with(check=None, violated=False):
    return ScopeRun(
        host_domain="test", resolution_level=ResolutionLevel.OPERATIONAL,
        candidate_claim_set=[CandidateStructure(name, name, [], [], []) for name in ("bad", "good")],
        explicit_constraints=[Constraint("limit", "bounded", True, True, violated=violated)],
        dependency_structure={},
        domain_indexed_falsifiers=[Falsifier("check", "rule", "predicate", "test", 0.9, check=check)],
        operational_discrimination_metric="survivor count", governance_recursion_cost=0.1,
        scoring_procedure="predicate", termination_trigger="no elimination", decommissioning_condition="stop",
    )


class RuntimeTests(unittest.TestCase):
    def test_executable_elimination_sticky_trigger_and_termination(self):
        run = run_with(lambda candidate: candidate.name == "bad")
        result = ScopeRuntime(run).execute()
        self.assertTrue(result.admissible)
        self.assertEqual(result.final_viable_candidates, 1)
        self.assertEqual(result.iteration_count, 2)
        self.assertEqual([t.candidate_name for t in result.elimination_traces], ["bad"])
        self.assertTrue(run.domain_indexed_falsifiers[0].result)

    def test_descriptive_check_preserves_candidates(self):
        result = ScopeRuntime(run_with()).execute()
        self.assertEqual(result.final_viable_candidates, 2)
        self.assertFalse(result.scope_run.domain_indexed_falsifiers[0].applied)

    def test_violated_constraint_blocks_pruning(self):
        result = ScopeRuntime(run_with(lambda candidate: True, violated=True)).execute()
        self.assertFalse(result.admissible)
        self.assertEqual(result.elimination_traces, [])

    def test_non_boolean_falsifier_is_error(self):
        result = ScopeRuntime(run_with(lambda candidate: "true")).execute()
        self.assertFalse(result.admissible)
        self.assertEqual(result.final_viable_candidates, 2)

    def test_drift_window_includes_current_observation(self):
        for window in (1, 2, 5):
            calc = DRECalculator(window_size=window)
            for index in range(window):
                result = calc.calculate(2, 2, 0, 0)
                self.assertEqual(result.drift_detected, index == window - 1)

    def test_current_progress_blocks_drift(self):
        for current in ((1, 2, 0, 0), (2, 2, 1, 0), (2, 2, 0, 1)):
            calc = DRECalculator(window_size=3)
            for _ in range(2):
                calc.calculate(2, 2, 0, 0)
            self.assertFalse(calc.calculate(*current).drift_detected)


if __name__ == "__main__":
    unittest.main()
