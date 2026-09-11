import unittest

def calculate_ensemble_scores(
    s_iaa_spec: float, s_iaa_comp: float,
    s_iqa_spec: float, s_iqa_comp: float,
    s_ista_spec: float, s_ista_comp: float,
    s_comp_direct: float
) -> dict:
    """
    4-Prompt Ensemble & Aesthetic-Weighted Fusion (IAA: 0.4, IQA: 0.3, ISTA: 0.3)
    """
    final_iaa = round((s_iaa_spec + s_iaa_comp) / 2.0, 1)
    final_iqa = round((s_iqa_spec + s_iqa_comp) / 2.0, 1)
    final_ista = round((s_ista_spec + s_ista_comp) / 2.0, 1)

    s_analysis = round((0.4 * final_iaa) + (0.3 * final_iqa) + (0.3 * final_ista), 1)

    s_raw = (s_comp_direct + s_analysis) / 2.0
    final_overall = min(100, max(0, round(s_raw)))

    return {
        "overall": final_overall,
        "iaa": final_iaa,
        "iqa": final_iqa,
        "ista": final_ista,
        "weighted_analysis": s_analysis
    }

class TestEnsembleMath(unittest.TestCase):
    def test_perfect_scores(self):
        res = calculate_ensemble_scores(100, 100, 100, 100, 100, 100, 100)
        self.assertEqual(res["overall"], 100)
        self.assertEqual(res["iaa"], 100.0)
        self.assertEqual(res["iqa"], 100.0)
        self.assertEqual(res["ista"], 100.0)

    def test_zero_scores(self):
        res = calculate_ensemble_scores(0, 0, 0, 0, 0, 0, 0)
        self.assertEqual(res["overall"], 0)
        self.assertEqual(res["iaa"], 0.0)
        self.assertEqual(res["iqa"], 0.0)
        self.assertEqual(res["ista"], 0.0)

    def test_aesthetic_weighted_fusion(self):
        # High aesthetics (90), medium quality (70), medium texture (70)
        # IAA_bar = 90, IQA_bar = 70, ISTA_bar = 70
        # s_analysis = 0.4*90 + 0.3*70 + 0.3*70 = 36 + 21 + 21 = 78.0
        # s_comp_direct = 80
        # s_raw = (80 + 78.0) / 2 = 79.0
        res = calculate_ensemble_scores(90, 90, 70, 70, 70, 70, 80)
        self.assertEqual(res["iaa"], 90.0)
        self.assertEqual(res["iqa"], 70.0)
        self.assertEqual(res["ista"], 70.0)
        self.assertEqual(res["weighted_analysis"], 78.0)
        self.assertEqual(res["overall"], 79)

    def test_clamping_upper(self):
        # Extreme input beyond 100 if any
        res = calculate_ensemble_scores(105, 105, 100, 100, 100, 100, 100)
        self.assertEqual(res["overall"], 100)

if __name__ == "__main__":
    unittest.main()
