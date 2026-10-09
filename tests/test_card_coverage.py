import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / 'skills/study-knowledge-base/scripts/check_card_coverage.py'
spec = importlib.util.spec_from_file_location('card_coverage', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CardCoverageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / 'vault'
        self.root.mkdir()
        for name in ('questions', 'topics'):
            (self.root / name).mkdir()

    def card(self, relative):
        file = self.root / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('# 测试卡片\n', encoding='utf-8')
        return relative

    def records(self, outputs, manifest=None):
        data = {'items': [{'id': str(i), 'output_file': value} for i, value in enumerate(outputs)]}
        (self.root / 'ledger.json').write_text(json.dumps(data), encoding='utf-8')
        (self.root / 'manifest.json').write_text(json.dumps(outputs if manifest is None else manifest), encoding='utf-8')

    def cli(self, *options):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(path), str(self.root), *options],
                                capture_output=True, text=True, encoding='utf-8')
        return result.returncode, json.loads(result.stdout)

    def test_three_questions_do_not_cover_three_topics_then_complete_passes(self):
        questions = [self.card('questions/q' + str(i) + '.md') for i in range(3)]
        topics = [self.card('topics/t' + str(i) + '.md') for i in range(3)]
        self.records(questions, questions + topics)
        code, report = self.cli()
        self.assertEqual(code, 1)
        self.assertEqual(report['cards'], 6)
        self.assertEqual(report['ledger_covered'], 3)
        self.assertEqual({e['file'] for e in report['errors']}, set(topics))
        self.records(questions + topics)
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        code, report = self.cli()
        self.assertEqual(code, 0)
        self.assertFalse(report['errors'])
        self.assertEqual(report['ledger_covered'], 6)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_manifest_missing_card_fails_independently_of_ledger(self):
        question = self.card('questions/q.md')
        topic = self.card('topics/t.md')
        self.records([question, topic], [question])
        report = module.check(self.root)
        self.assertEqual(report['ledger_covered'], 2)
        self.assertEqual(report['manifest_covered'], 1)
        self.assertEqual(report['errors'], [{'source': 'coverage', 'error': '卡片未列入 manifest', 'file': topic}])

    def test_custom_chinese_directories_and_normalized_relative_paths(self):
        self.card('题库/嵌套/第一题.md')
        self.card('知识卡/特征值.md')
        self.records(['.\\题库\\嵌套\\第一题.md', '知识卡/../知识卡/特征值.md'],
                     ['题库/嵌套/第一题.md', './知识卡/特征值.md'])
        (self.root / 'ledger.json').rename(self.root / '台账.json')
        (self.root / 'manifest.json').rename(self.root / '清单.json')
        code, report = self.cli('--cards', '题库', '知识卡', '--ledger', '台账.json', '--manifest', '清单.json')
        self.assertEqual(code, 0)
        self.assertEqual(report['cards'], 2)
        self.assertFalse(report['errors'])

    def test_invalid_extra_output_is_rejected_even_when_cards_are_covered(self):
        question = self.card('questions/q.md')
        for extra in ({}, {'output_file': ''}, {'output_file': 'missing.md'}, {'output_file': 'topics'}):
            with self.subTest(extra=extra):
                self.records([question])
                data = json.loads((self.root / 'ledger.json').read_text(encoding='utf-8'))
                data['items'].append(extra)
                (self.root / 'ledger.json').write_text(json.dumps(data), encoding='utf-8')
                report = module.check(self.root)
                self.assertEqual(report['ledger_covered'], 1)
                self.assertEqual(len(report['errors']), 1)
                self.assertIn('ledger.items[1]', report['errors'][0]['source'])

    def test_outside_and_absolute_paths_are_rejected_in_both_records(self):
        (self.root.parent / 'outside.md').write_text('外部文件', encoding='utf-8')
        for value in ('../outside.md', '../vault-other/card.md', '/absolute.md',
                      'C:\\outside.md', 'C:outside.md', '\\\\server\\share\\card.md'):
            with self.subTest(value=value):
                self.records([value], [value])
                report = module.check(self.root)
                self.assertEqual(len(report['errors']), 2)
                self.assertTrue(all('ROOT' in e['error'] for e in report['errors']))

    def test_resolved_symlink_cannot_escape_root(self):
        outside = self.root.parent / 'outside.md'
        outside.write_text('外部文件', encoding='utf-8')
        try:
            (self.root / 'questions/linked.md').symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('当前系统不允许创建符号链接')
        self.records(['questions/linked.md'])
        report = module.check(self.root)
        self.assertEqual(len(report['errors']), 3)
        self.assertTrue(all('路径越界' in e['error'] for e in report['errors']))

    def test_missing_card_directory_and_missing_record_files_report_errors(self):
        code, report = self.cli('--cards', '不存在')
        self.assertEqual(code, 1)
        self.assertEqual({e['source'] for e in report['errors']}, {'cards', 'ledger', 'manifest'})
        self.records([])
        self.assertFalse(module.check(self.root)['errors'])
        report = module.check(self.root, cards=['../'])
        self.assertEqual(report['errors'][0]['source'], 'cards')
        self.assertIn('越界', report['errors'][0]['error'])

    def test_missing_manifest_target_and_malformed_inputs_return_json_failure(self):
        self.records([], ['missing.png'])
        code, report = self.cli()
        self.assertEqual(code, 1)
        self.assertIn('文件不存在', report['errors'][0]['error'])
        for ledger, manifest in (('{', '[]'), ('[]', '{}'), ('{"items":[null]}', '[null]')):
            with self.subTest(ledger=ledger, manifest=manifest):
                (self.root / 'ledger.json').write_text(ledger, encoding='utf-8')
                (self.root / 'manifest.json').write_text(manifest, encoding='utf-8')
                code, report = self.cli()
                self.assertEqual(code, 1)
                self.assertTrue(report['errors'])


if __name__ == '__main__':
    unittest.main()
