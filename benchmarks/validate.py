"""Independently verify saved document-level metrics using trec_eval."""
import argparse
import json
import statistics
from pathlib import Path

import pytrec_eval


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('results',type=Path)
    args=parser.parse_args()
    report=json.loads(args.results.read_text())
    details=[]
    mapping={'hit_at_1':'P_1','recall_at_5':'recall_5','recall_at_10':'recall_10','recall_at_20':'recall_20','mrr_at_10':'recip_rank','ndcg_at_10':'ndcg_cut_10'}
    for run in report['runs']:
        assert len(run['per_query'])==report['dataset']['queries']
        qrels={q['query_id']:q['relevant_documents'] for q in run['per_query']}
        evaluator=pytrec_eval.RelevanceEvaluator(qrels,{'P.1','recall.5','recall.10','recall.20','recip_rank','ndcg_cut.10'})
        predictions={q['query_id']:{row['document_id']:float(20-i) for i,row in enumerate(q['top20'])} for q in run['per_query']}
        evaluated=evaluator.evaluate(predictions)
        for key,trec_name in mapping.items():
            # MRR is evaluated over ten results rather than the saved top twenty.
            if key=='mrr_at_10':
                short={qid:{doc:score for doc,score in docs.items() if score>=11} for qid,docs in predictions.items()}
                values=evaluator.evaluate(short)
            else:
                values=evaluated
            actual=statistics.fmean(value[trec_name] for value in values.values())
            assert abs(actual-run['document_metrics'][key])<1e-12, (run['model_id'],run['mode'],key,actual)
        details.append({'model':run['model_id'],'mode':run['mode'],'queries':report['dataset']['queries'],'metrics_verified':list(mapping)})
    assert len(details)==len(report['models'])*2
    result={'tool':'pytrec-eval-terrier 0.5.10','passed':True,'runs':details}
    (args.results.parent/'metric-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'Independent trec_eval verification passed for all {len(details)} runs and {report["dataset"]["queries"]} queries each')


if __name__=='__main__':
    main()
