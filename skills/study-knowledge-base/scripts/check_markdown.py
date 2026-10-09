"""检查美元符号数学定界符与简单矩阵列数；不验证数学内容或最终显示。"""
import argparse
import json
from pathlib import Path
import re


def inspect(text):
    # 去除代码和callout前缀，避免把代码示例当公式。
    text = re.sub(r'^\s*(?:>\s*)+', '', text, flags=re.M)
    text = re.sub(r'```[\s\S]*?```|~~~[\s\S]*?~~~', '', text)
    text = re.sub(r'`[^`\n]*`', '', text)
    opened = None
    formulas, errors = [], []
    for token in re.finditer(r'(?<!\\)(\$\$|\$)', text):
        if opened is None:
            opened = token
        elif token.group() != opened.group():
            errors.append('混用单美元与双美元定界符')
        else:
            tex = text[opened.end():token.start()]
            formulas.append({'tex': tex, 'display': token.group() == '$$'})
            opened = None
    if opened:
        errors.append('未闭合数学定界符')
    for formula in formulas:
        for matrix in re.finditer(r'\\begin\{(vmatrix|bmatrix|pmatrix)\}([\s\S]*?)\\end\{\1\}', formula['tex']):
            body = matrix[2]
            if '\\begin{' in body:
                continue
            rows = [row.strip() for row in re.split(r'\\\\', body) if row.strip()]
            widths = [len(re.split(r'(?<!\\)&', row)) for row in rows]
            if len(set(widths)) > 1:
                errors.append('简单矩阵各行列数不一致')
    return errors, formulas


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+')
    parser.add_argument('--output', help='可选JSON检查记录')
    args = parser.parse_args()
    files = set()
    for name in args.paths:
        path = Path(name)
        if not path.exists():
            parser.error('路径不存在：' + name)
        files.update(path.rglob('*.md') if path.is_dir() else [path])
    report = {'files': len(files), 'errors': [], 'formulas': []}
    for file in sorted(files):
        errors, formulas = inspect(file.read_text(encoding='utf-8-sig'))
        report['errors'].extend({'file': str(file), 'error': error} for error in errors)
        report['formulas'].extend(dict(formula, file=str(file)) for formula in formulas)
    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'files': len(files), 'formulas': len(report['formulas']), 'errors': report['errors']}, ensure_ascii=False))
    raise SystemExit(bool(report['errors']))
