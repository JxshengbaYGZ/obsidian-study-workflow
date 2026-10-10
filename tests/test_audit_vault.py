"""用自编的小库验证机械审计边界，不读取任何私人知识库。"""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_vault.py'
SPEC = importlib.util.spec_from_file_location('audit_vault', MODULE_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class VaultAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / '中文小库'
        self.root.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def note(self, relative, body):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8')

    def records(self):
        return AUDIT.audit(self.root)['links']

    def test_reparse_directory_is_not_traversed(self):
        self.note('另一个库/不应读取.md', '# 私有内容占位\n')
        self.note('正常.md', '# 正常\n')
        with patch.object(AUDIT, 'is_link_like', side_effect=lambda p: p.name == '另一个库'):
            result = AUDIT.audit(self.root)
        self.assertEqual(result['counts']['markdown'], 1)
        self.assertIn('另一个库', result['skipped_directories'])

    def test_wiki_heading_block_and_pdf_anchor(self):
        self.note('笔记/概念.md', '# 概念\n## 适用条件\n一段解释。 ^证据-1\n')
        self.note('入口.md', '[[笔记/概念#适用条件]]\n[[笔记/概念#^证据-1]]\n[[笔记/概念#不存在]]\n[[笔记/概念#^空块]]\n[[原稿.pdf#page=2]]\n')
        (self.root / '原稿.pdf').write_bytes(b'%PDF-fixture')
        self.assertEqual([r['status'] for r in self.records()], ['resolved', 'resolved', 'missing_heading_anchor', 'missing_block_anchor', 'resolved'])

    def test_table_escaped_wiki_alias_and_short_name_ambiguity(self):
        self.note('甲/同名.md', '# 同名\n')
        self.note('乙/同名.md', '# 同名\n')
        self.note('入口.md', '| 入口 |\n|---|\n| [[甲/同名\\|唯一标题]] |\n[[同名]]\n')
        records = self.records()
        self.assertEqual(records[0]['resolved_to'], '甲/同名.md')
        self.assertEqual(records[1]['status'], 'ambiguous_short_name')
        self.assertEqual(set(records[1]['candidates']), {'甲/同名.md', '乙/同名.md'})

    def test_root_short_name_is_still_ambiguous(self):
        self.note('同名.md', '# 根文件\n')
        self.note('乙/同名.md', '# 子文件\n')
        self.note('入口.md', '[[同名]]\n')
        self.assertEqual(self.records()[0]['status'], 'ambiguous_short_name')

    def test_html_units_and_math_are_not_links(self):
        self.note('入口.md', '<table><tr><td>安[培](A)</td><td>伏[特](V)</td></tr></table>\n$h(z)=[1/(2z^2)](1-z/2)^{-1}$\n$$\n[a](b)\n$$\n`[[代码示例]]`\n```md\n[[未创建的模板]]\n```\n<!-- [[注释]] -->\n')
        self.assertEqual(self.records(), [])

    def test_html_images_and_urls_are_recorded(self):
        self.note('入口.md', '<table><td><img src="图.png"/></td></table>\n<img src="https://example.invalid/图.png"/>\n')
        (self.root / '图.png').write_bytes(b'image-fixture')
        records = self.records()
        self.assertEqual([r['status'] for r in records], ['resolved', 'external_url'])
        self.assertEqual(AUDIT.audit(self.root)['images_without_markdown_embeds'], [])

    def test_markdown_parentheses_percent_and_relative_path(self):
        self.note('笔记/概念 (版本).md', '# 概念\n')
        self.note('记录/记录.md', '[一](../笔记/概念%20(版本).md)\n[二](<../笔记/概念 (版本).md>)\n')
        self.assertEqual([r['status'] for r in self.records()], ['resolved', 'resolved'])

    def test_same_vault_and_other_vault_are_not_confused(self):
        self.note('Good Notes/笔记/概念.md', '# 概念\n')
        self.note('学校教材/教材.md', '# 教材\n')
        self.note('Good Notes/入口.md', '[[学校教材/教材]]\n[[Good Notes/笔记/概念]]\n[外库](../../另一库/概念.md)\n[跨库](obsidian://open?vault=另一库&file=概念)\n')
        records = self.records()
        self.assertEqual([r['status'] for r in records], ['resolved', 'resolved', 'outside_root', 'vault_uri'])
        self.assertEqual(records[-1]['vault'], '另一库')

    def test_planned_target_and_hidden_configuration(self):
        self.note('入口.md', '待建：[[新概念]]\n[[真的缺失]]\n')
        self.note('.obsidian/plugins/demo/data.md', '[[配置中不是笔记的路径]]\n')
        result = AUDIT.audit(self.root)
        self.assertEqual([r['status'] for r in result['links']], ['planned_target', 'missing_target'])
        self.assertEqual(result['counts']['markdown'], 1)

    def test_duplicate_and_orphan_are_candidates_only(self):
        self.note('甲.md', '# 自编概念\n')
        self.note('乙.md', '# 自编概念\n')
        result = AUDIT.audit(self.root)
        self.assertEqual([set(paths) for paths in result['exact_markdown_duplicates']], [{'甲.md', '乙.md'}])
        self.assertEqual(result['findings'], [])

    def test_cli_refuses_output_inside_vault(self):
        self.note('入口.md', '# 入口\n')
        with self.assertRaises(SystemExit) as caught:
            AUDIT.main([str(self.root), '--output', str(self.root / '报告')])
        self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
