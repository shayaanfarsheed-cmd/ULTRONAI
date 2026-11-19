import unittest

from ultron_agent import (
    MATH_KNOWLEDGE,
    AgentInputError,
    run_agent_benchmark,
    solve_question,
)
from ultron_data import SUPPORTED_TOPICS, generate_example
import random


class MathAgentTests(unittest.TestCase):
    def test_agent_has_a_summary_for_every_supported_topic(self):
        self.assertEqual(set(MATH_KNOWLEDGE), set(SUPPORTED_TOPICS))
        for summary in MATH_KNOWLEDGE.values():
            self.assertTrue(summary["concept"])
            self.assertTrue(summary["rule"])
            self.assertTrue(summary["method"])

    def test_agent_solves_questions_without_answer_or_steps_input(self):
        for index, topic in enumerate(SUPPORTED_TOPICS):
            with self.subTest(topic=topic):
                example = generate_example(topic, random.Random(1200 + index), difficulty=2, sample_index=index)
                result = solve_question(topic, example["question"])
                self.assertEqual(result["answer"], example["answer"])
                self.assertEqual(result["steps"], example["steps"])
                self.assertIn("rule", result["knowledge"])

    def test_fraction_and_decimal_arithmetic_are_exact(self):
        self.assertEqual(solve_question("fractions", "Calculate: (1/3) + (1/6)")["answer"], "1/2")
        self.assertEqual(solve_question("decimals", "Calculate: 0.1 + 0.2")["answer"], "0.3")

    def test_agent_rejects_unsupported_or_malformed_questions(self):
        with self.assertRaises(AgentInputError):
            solve_question("unknown", "Calculate: 1 + 1")
        with self.assertRaises(AgentInputError):
            solve_question("whole_number_arithmetic", "Calculate: __import__('os').system('id')")
        with self.assertRaises(AgentInputError):
            solve_question([], "Calculate: 1 + 1")
        with self.assertRaises(AgentInputError):
            solve_question("whole_number_arithmetic", "1" * 1001)

    def test_benchmark_is_deterministic_and_independently_verified(self):
        first = run_agent_benchmark(70, seed=987)
        second = run_agent_benchmark(70, seed=987)
        self.assertEqual(first["generated_questions"], 70)
        self.assertEqual(first["independently_verified_correct"], 70)
        self.assertEqual(first["by_topic"], second["by_topic"])
        self.assertEqual(first["sample_solutions"], second["sample_solutions"])
        self.assertFalse(first["training_started"])
        self.assertFalse(first["model_weights_changed"])

    def test_benchmark_reports_throughput_and_topic_metrics(self):
        report = run_agent_benchmark(28, seed=7)
        self.assertGreater(report["questions_per_second"], 0)
        self.assertGreater(report["verified_solutions_per_second"], 0)
        self.assertEqual(sum(row["generated"] for row in report["by_topic"].values()), 28)
        self.assertEqual(len(report["sample_solutions"]), 20)

    def test_benchmark_limits_and_validates_inputs(self):
        for call in (
            lambda: run_agent_benchmark(0),
            lambda: run_agent_benchmark(50001),
            lambda: run_agent_benchmark(1, seed=True),
            lambda: run_agent_benchmark(1, topics=("not-a-topic",)),
            lambda: run_agent_benchmark(1, maximum_seconds=0),
        ):
            with self.subTest(call=call):
                with self.assertRaises(AgentInputError):
                    call()


if __name__ == "__main__":
    unittest.main()
