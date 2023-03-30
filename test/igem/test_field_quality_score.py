import unittest

from sbol_utilities.igem.qc_field_quality_score import QCFieldQualityScore


class TestFieldQualityScore(unittest.TestCase):

    def test_add(self):
        score_1 = QCFieldQualityScore()
        score_1["a"] = 1
        score_1["b"] = 2
        score_1["c"] = 3
        score_2 = QCFieldQualityScore()
        score_2["a"] = 1
        score_2["b"] = 2
        score_2["d"] = 3
        score_3 = score_1 + score_2
        self.assertEqual(score_3["a"], 2)
        self.assertEqual(score_3["b"], 4)
        self.assertEqual(score_3["c"], 3)
        self.assertEqual(score_3["d"], 3)

    def test_copy(self):
        score_1 = QCFieldQualityScore()
        score_1["a"] = 1
        score_1["b"] = 2
        score_1["c"] = 3
        score_2 = score_1.__copy__()
        self.assertEqual(score_2["a"], 1)
        self.assertEqual(score_2["b"], 2)
        self.assertEqual(score_2["c"], 3)
        score_1["a"] = 2
        self.assertEqual(score_2["a"], 1)   
