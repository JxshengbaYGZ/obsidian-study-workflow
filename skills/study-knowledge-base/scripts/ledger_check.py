"""检查审查台账结构；不代替来源阅读或数学审查。"""
import argparse
import collections
import json
import sys


def validate(data, complete=False):
    errors = []
    expected = data.get('expected_ids', [])
    items = data.get('items', [])
    ids = [x.get('id') for x in items]
    if not expected or len(set(expected)) != len(expected):
        errors.append('expected_ids 为空或重复')
    if len(set(ids)) != len(ids) or set(ids) != set(expected):
        errors.append('记录缺失、重复或超出范围')
    statuses = {'unread', 'pending', 'verified', 'corrected', 'duplicate', 'no_independent_tip'}
    for x in items:
        prefix = str(x.get('id')) + ': '
        if x.get('final_review') == 'passed':
            review = x.get('final_review_record', {})
            if not isinstance(review, dict) or not all(review.get(k) for k in ('reviewer', 'evidence', 'scope')) or review.get('mode') != 'independent':
                errors.append(prefix + '终审通过缺独立复核记录：reviewer/mode/evidence/scope')
        for key, allowed in [('kind', {'topic', 'question', 'tip'}), ('source_kind', {'scan', 'transcript', 'authored'}), ('status', statuses), ('source_check', {'unread', 'matched', 'unclear', 'not_applicable'}), ('semantic_check', {'unread', 'passed', 'failed', 'blocked'})]:
            if x.get(key) not in allowed:
                errors.append(prefix + key + ' 无效')
        if not isinstance(x.get('evidence'), list) or not isinstance(x.get('reason'), str):
            errors.append(prefix + '缺证据列表或理由')
        if x.get('status') in {'verified', 'corrected'}:
            source_ok = x.get('source_check') == 'matched' or (x.get('source_kind') == 'authored' and x.get('source_check') == 'not_applicable')
            evidence = x.get('evidence')
            concrete = isinstance(evidence, list) and bool(evidence) and all(isinstance(e, str) and e.strip() for e in evidence)
            if not source_ok or x.get('semantic_check') != 'passed' or not concrete:
                errors.append(prefix + '不能认定已验证：缺来源核对、独立审查或证据')
        if x.get('status') == 'duplicate':
            target = x.get('duplicate_of')
            known = set(ids) | set(data.get('existing_ids', []))
            if not target or target == x.get('id') or target not in known or not x.get('reason'):
                errors.append(prefix + '重复项缺真实目标或原因')
            if x.get('source_check') != 'matched':
                errors.append(prefix + '未读来源不能判断重复')
        if x.get('status') == 'no_independent_tip' and (x.get('kind') != 'tip' or not x.get('reason')):
            errors.append(prefix + '无独立技巧处置无效')
        if x.get('status') == 'no_independent_tip' and x.get('source_check') != 'matched':
            errors.append(prefix + '未读来源不能判断无独立技巧')
        if complete and x.get('status') in {'unread', 'pending'}:
            errors.append(prefix + '尚未完成')
    redirects = {x['id']: x.get('duplicate_of') for x in items if x.get('status') == 'duplicate'}
    for start in redirects:
        seen = set()
        current = start
        while current in redirects:
            if current in seen:
                errors.append(str(start) + ': 重复引用形成循环')
                break
            seen.add(current)
            current = redirects[current]
    return errors, dict(collections.Counter(x.get('status') for x in items))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger')
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    with open(args.ledger, encoding='utf-8-sig') as f:
        errors, counts = validate(json.load(f), args.require_complete)
    print(json.dumps({'counts': counts, 'errors': errors, 'limitation': '仅结构检查，非数学正确性证明'}, ensure_ascii=False, indent=2))
    sys.exit(bool(errors))
