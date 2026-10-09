import importlib.util
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest

root = Path(__file__).resolve().parents[1]
path = root/'skills/textbook-library/scripts/check_textbook_library.py'
spec = importlib.util.spec_from_file_location('textbook_check', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

DRAFT = '''# 演示书

<!-- 来源块：dm-p0021-b000 -->
一段正文。

![[学校教材/演示书/演示书-全文/图解/p0021-fig01.jpg|200]]

*图 1-1-1 示例图*

<!-- 来源块：dm-p0021-b003 -->
又一段正文。


| 教材 | 页码 |
|---|---|
| 《演示书》 | PDF物理第 21 页 |
'''

CARD = '''# 示例概念

定义、条件与方法。

## 来源

| 项目 | 节号 | PDF物理页 |
|---|---|---|
| 示例概念 | 1-1 | 21–22 |
'''


class TextbookLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.lib = os.path.join(self.tmp, '学校教材')
        self.book = os.path.join(self.lib, '演示书', '演示书-全文')
        for d in ('正文底稿', '图解', '知识点'):
            os.makedirs(os.path.join(self.book, d), exist_ok=True)
        for name in ('00-阅读入口.md', '00-正文索引.md', '00-知识点索引.md', '索引.md'):
            self.write(os.path.join(self.book, name), '# 演示书\n')
        self.write(os.path.join(self.book, '00-知识点索引.md'), '# 演示书\n\n- [[示例概念]]\n')
        self.write(os.path.join(self.lib, '演示书', '演示书.md'), '# 演示书\n')
        self.write(os.path.join(self.book, '正文底稿', '第1章 演示.md'), DRAFT)
        self.write(os.path.join(self.book, '图解', 'p0021-fig01.jpg'), 'x')
        self.write(os.path.join(self.book, '知识点', '示例概念.md'), CARD)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @staticmethod
    def write(path, text):
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)

    def run_check(self):
        res = module.Result()
        module.check_book(self.book, self.lib, 20, res, self.tmp)
        return res

    def test_valid_library_passes(self):
        res = self.run_check()
        self.assertEqual([], res.fails)
        self.assertEqual(1, res.stat['图题'])
        self.assertEqual(1, res.stat['卡片'])
        self.assertEqual(1, res.stat['页脚'])

    def test_missing_figure_is_reported(self):
        os.remove(os.path.join(self.book, '图解', 'p0021-fig01.jpg'))
        res = self.run_check()
        self.assertTrue(any('不存在的图' in m for m in res.fails))

    def test_unreferenced_figure_is_reported(self):
        self.write(os.path.join(self.book, '图解', 'p0022-fig01.jpg'), 'x')
        res = self.run_check()
        self.assertTrue(any('没人引用的图' in m for m in res.fails))

    def test_footer_page_must_match_its_blocks(self):
        p = os.path.join(self.book, '正文底稿', '第1章 演示.md')
        self.write(p, DRAFT.replace('PDF物理第 21 页', 'PDF物理第 22 页'))
        res = self.run_check()
        self.assertTrue(any('页脚标' in m for m in res.fails))

    def test_caption_without_embed_is_reported(self):
        p = os.path.join(self.book, '正文底稿', '第1章 演示.md')
        self.write(p, DRAFT.replace('![[学校教材/演示书/演示书-全文/图解/p0021-fig01.jpg|200]]', ''))
        res = self.run_check()
        self.assertTrue(any('没有图片嵌入' in m for m in res.fails))

    def test_card_requires_source_section(self):
        self.write(os.path.join(self.book, '知识点', '示例概念.md'), CARD.replace('## 来源', '## 说明'))
        res = self.run_check()
        self.assertTrue(any('## 来源' in m for m in res.fails))

    def test_card_must_be_listed_in_index(self):
        self.write(os.path.join(self.book, '00-知识点索引.md'), '# 演示书\n')
        res = self.run_check()
        self.assertTrue(any('索引里没有卡片' in m for m in res.fails))

    def test_card_links_and_reused_images_are_checked(self):
        card = os.path.join(self.book, '知识点', '示例概念.md')
        valid = CARD + '\n![[学校教材/演示书/演示书-全文/图解/p0021-fig01.jpg|200]]\n'
        valid += '\n[[学校教材/演示书/演示书-全文/正文底稿/第1章 演示#示例|正文]]\n'
        self.write(card, valid)
        res = self.run_check()
        self.assertFalse(any('卡内出现 wikilink' in m for m in res.warns))
        self.assertFalse(any('图片不存在' in m or '链接不存在' in m for m in res.fails))

        self.write(card, CARD + '\n![[学校教材/演示书/演示书-全文/图解/缺图.jpg|200]]\n')
        self.write(card, Path(card).read_text(encoding='utf-8') +
                   '\n[[学校教材/演示书/演示书-全文/知识点/缺卡|缺卡]]\n')
        res = self.run_check()
        self.assertTrue(any('图片不存在' in m for m in res.fails))
        self.assertTrue(any('链接不存在' in m for m in res.fails))

    def test_missing_entry_file_is_reported(self):
        os.remove(os.path.join(self.book, '索引.md'))
        res = self.run_check()
        self.assertTrue(any('缺少入口文件' in m for m in res.fails))

    def test_skill_links_survive_standalone_copy(self):
        copy = Path(self.tmp) / 'textbook-library'
        shutil.copytree(root / 'skills/textbook-library', copy)
        for file in copy.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', file.read_text(encoding='utf-8')):
                if '://' in target:
                    continue
                target_path = (file.parent / target.split('#')[0]).resolve()
                self.assertTrue(target_path.is_relative_to(copy.resolve()), str(file))
                self.assertTrue(target_path.is_file(), target)
