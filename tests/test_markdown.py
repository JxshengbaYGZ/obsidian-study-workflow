import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1]/'skills/study-knowledge-base/scripts/check_markdown.py'
spec = importlib.util.spec_from_file_location('markdown_check', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MarkdownTests(unittest.TestCase):
    def test_reviewer_extra_delimiter_rejected(self):
        self.assertTrue(module.inspect('> $$\n> x=1\n> $$\n> $$\n> 结论')[0])

    def test_uneven_matrix_rejected(self):
        text = r'$$\begin{vmatrix}s(1,1,1)\\a&b&c\end{vmatrix}$$'
        self.assertTrue(module.inspect(text)[0])

    def test_valid_callout(self):
        self.assertFalse(module.inspect('> $$\n> x=1\n> $$\n> 结论')[0])

    def test_code_and_escaped_dollar(self):
        self.assertFalse(module.inspect('```\n$$\n```\n`$` \\$5')[0])
