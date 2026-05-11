import unittest

from cod.core.models import TrustTier
from cod.services.classifier import SourceClassifier


class TestSourceClassifier(unittest.TestCase):
    def setUp(self):
        self.clf = SourceClassifier()

    def test_fda_is_tier1(self):
        tier, score = self.clf.suggest_tier("https://www.fda.gov/drugs")
        self.assertEqual(tier, TrustTier.CANONICAL)
        self.assertEqual(score, 1.0)

    def test_nejm_is_tier2(self):
        tier, score = self.clf.suggest_tier("https://www.nejm.org/article/123")
        self.assertEqual(tier, TrustTier.EVIDENCE)
        self.assertEqual(score, 0.7)

    def test_blog_is_tier3(self):
        tier, score = self.clf.suggest_tier("https://someblog.medium.com/article")
        self.assertEqual(tier, TrustTier.EXPLORATORY)
        self.assertEqual(score, 0.3)

    def test_unknown_defaults_to_tier3(self):
        tier, _ = self.clf.suggest_tier("https://unknownsource123.com")
        self.assertEqual(tier, TrustTier.EXPLORATORY)

    def test_subdomain_not_spoofed(self):
        tier, _ = self.clf.suggest_tier("https://fda.gov.evil.com/drugs")
        self.assertEqual(tier, TrustTier.EXPLORATORY)

    def test_to_dict_snapshot(self):
        result = self.clf.classify("https://www.fda.gov")
        data = result.to_dict()
        self.assertEqual(data["tier"], "CANONICAL")
        self.assertIn("authority_score", data)
        self.assertIn("timestamp", data)


if __name__ == "__main__":
    unittest.main()
