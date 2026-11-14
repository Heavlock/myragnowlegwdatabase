import math
import unittest
from retrieval import metric_values


class MetricTests(unittest.TestCase):
    def test_perfect_and_missing(self):
        self.assertEqual(metric_values(['a','b'],{'a':1,'b':1})['ndcg_at_10'],1.)
        self.assertEqual(metric_values(['z'],{'a':1})['mrr_at_10'],0.)
        self.assertEqual(metric_values([],{'a':1})['hit_at_1'],0.)

    def test_rank_and_duplicate_gain(self):
        result=metric_values(['z','a','a','b'],{'a':1,'b':1})
        self.assertEqual(result['hit_at_1'],0.)
        self.assertEqual(result['mrr_at_10'],.5)
        self.assertEqual(result['recall_at_5'],1.)
        expected=(1/math.log2(3)+1/math.log2(5))/(1+1/math.log2(3))
        self.assertAlmostEqual(result['ndcg_at_10'],expected)

    def test_partial_recall(self):
        self.assertEqual(metric_values(['a'],{'a':1,'b':1})['recall_at_10'],.5)


if __name__=='__main__':
    unittest.main()
