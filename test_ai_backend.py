import unittest

from ai_mission import generate_mission
from compiler_service import compile_source
from ml_battery import model


class AiAndMlTests(unittest.TestCase):
    def test_ai_generation_produces_a_valid_mission(self):
        suggestion = generate_mission("Visit waypoint A at 100,100 and fly at altitude 40")
        result = compile_source(suggestion.source)
        self.assertEqual(result["status"], "COMPLETED", result)
        self.assertIn("FLY TO A", suggestion.source)

    def test_ai_generation_warns_when_coordinates_are_assumed(self):
        suggestion = generate_mission("Visit waypoint A and return home")
        self.assertTrue(suggestion.warnings)

    def test_ml_prediction_is_non_negative_and_exposes_remaining_battery(self):
        prediction = model.predict(distance=100, altitude=50, hover_seconds=10, battery=100)
        self.assertGreater(prediction.predicted_use, 0)
        self.assertLess(prediction.remaining_battery, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
