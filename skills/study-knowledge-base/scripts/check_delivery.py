"""只读验收变更清单及 wiki 链接；不上传已经写入的本地文件。"""
import argparse
import json
import re
import time
from urllib.parse import unquote, urlsplit
from pathlib import Path

def check(root, files):
    root = Path(root).resolve()
    index = {}
    for p in root.rglob('*'):
        if p.is_file():
            for key in {p.name, p.stem if p.suffix == '.md' else p.name}:
                index.setdefault(key, []).append(p)
    errors, links = [], 0
    for relative in files:
        p = (root / relative).resolve()
        if not p.is_relative_to(root) or not p.is_file() or p.stat().st_size == 0:
            errors.append({'file':relative,'error':'missing, empty, or outside root'})
            continue
        if p.suffix != '.md':
            continue
        text = p.read_text(encoding='utf-8')
        text = re.sub(r'```.*?```', '', text, flags=re.S)
        # 标准内联Markdown链接按当前文档目录解析，不用同名文件兜底。
        for raw in re.findall(r'!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)\)', text):
            target = raw.strip('<>')
            if urlsplit(target).scheme or target.startswith('//') or target.startswith('#'):
                continue
            links += 1
            target = unquote(target.split('#')[0])
            candidate = (p.parent / target).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file() or candidate.stat().st_size == 0:
                errors.append({'file':relative,'target':target,'error':'missing, empty, or outside root'})
        for raw in re.findall(r'\[\[([^\]]+)\]\]', text):
            target = raw.split('|')[0].split('#')[0]
            if not target:
                continue
            links += 1
            candidates = []
            for base in (root, p.parent):
                for name in (target, target + '.md'):
                    candidate = (base / name).resolve()
                    if candidate.is_relative_to(root) and candidate.is_file():
                        candidates.append(candidate)
            candidates = set(candidates or index.get(target, []))
            if len(candidates) != 1 or not next(iter(candidates)).stat().st_size:
                errors.append({'file':relative,'target':target,'error':'missing, ambiguous, or empty'})
    return {'files':len(files),'links':links,'errors':errors,
            'limitation':'文件与链接检查；不证明裁图完整、数学正确或界面渲染正确；不检查标题锚点'}

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('root')
    parser.add_argument('manifest', help='JSON list of relative changed file paths')
    args=parser.parse_args()
    start=time.perf_counter()
    result=check(args.root,json.loads(Path(args.manifest).read_text(encoding='utf-8')))
    result['seconds']=round(time.perf_counter()-start,3)
    print(json.dumps(result,ensure_ascii=False))
    raise SystemExit(bool(result['errors']))
