#!/usr/bin/env python3
"""只读审计 Markdown 知识库的链接、附件与重复；不自动修改或删除笔记。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import parse_qs, unquote, urlparse

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif', '.bmp'}


def is_link_like(path: Path) -> bool:
    """Windows 联接点也是重解析目录，不能只检查符号链接。"""
    if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
        return True
    attrs = getattr(path.lstat(), 'st_file_attributes', 0)
    return bool(attrs & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))


def path_key(value: str) -> str:
    """按 Obsidian 在 Windows 上常见的大小写不敏感路径进行比较。"""
    return value.replace('\\', '/').strip('/').casefold()


def blank(match: re.Match) -> str:
    """遮住非导航内容，同时保留字符数及原行号。"""
    return ''.join('\n' if c == '\n' else ' ' for c in match[0])


def without_code(text: str) -> str:
    result, fence = [], None
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if marker:
            if fence is None:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = None
            result.append(''.join('\n' if c == '\n' else ' ' for c in line))
        elif fence:
            result.append(''.join('\n' if c == '\n' else ' ' for c in line))
        else:
            result.append(re.sub(r'(`+)(.*?)\1', blank, line))
    return re.sub(r'<!--[\s\S]*?-->', blank, ''.join(result))


def navigation_text(text: str) -> str:
    """公式和 HTML 表内的字面方括号不是 Markdown 导航。"""
    text = re.sub(r'(?<!\\)\$\$[\s\S]*?(?<!\\)\$\$', blank, text)
    # 行内公式不跨空行，避免一个未闭合的美元符号遮掉后续段落。
    text = re.sub(r'(?<![\\$])\$(?!\$)(?:\\.|[^$\n])*?(?<!\\)\$(?!\$)', blank, text)
    return re.sub(r'<table\b[\s\S]*?</table\s*>', blank, text, flags=re.I)


def markdown_links(text: str):
    """解析平衡括号，支持路径中的英文括号、转义和尖括号空格路径。"""
    i = 0
    while i < len(text):
        if text[i] != '[' or (i and text[i - 1] == '\\') or text[i:i + 2] == '[[':
            i += 1
            continue
        end, depth = i + 1, 1
        while end < len(text) and depth:
            if text[end] == '\\':
                end += 2
                continue
            depth += (text[end] == '[') - (text[end] == ']')
            end += 1
        if depth or end >= len(text) or text[end] != '(':
            i = end
            continue
        pos, depth = end + 1, 1
        while pos < len(text) and depth:
            if text[pos] == '\\':
                pos += 2
                continue
            depth += (text[pos] == '(') - (text[pos] == ')')
            pos += 1
        if depth:
            i = end
            continue
        raw_target = text[end + 1:pos - 1].strip()
        if raw_target.startswith('<') and '>' in raw_target:
            target = raw_target[1:raw_target.index('>')]
        else:
            target = re.sub(r'\s+[\"\'].*$', '', raw_target).strip()
        yield i, target, bool(i and text[i - 1] == '!'), text[i:pos]
        i = pos


def heading_key(value: str) -> str:
    value = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', value)
    value = re.sub(r'<[^>]*>', '', value)
    value = re.sub(r'[`*_~]', '', value)
    return re.sub(r'\s+', ' ', html.unescape(value)).strip().casefold()


def heading_slug(value: str) -> str:
    return re.sub(r'[^\w\- ]', '', heading_key(value)).replace(' ', '-')


class VaultIndex:
    def __init__(self, root: Path):
        self.root = root.resolve()
        if not self.root.is_dir():
            raise ValueError('知识库根目录不存在或不是目录：' + str(root))
        self.files, self.texts = {}, {}
        self.lookup, self.names, self.stems = {}, defaultdict(list), defaultdict(list)
        self.headings, self.blocks, self.skipped = {}, {}, []
        for dirpath, directories, filenames in os.walk(self.root, followlinks=False):
            kept = []
            for directory in directories:
                path = Path(dirpath, directory)
                if directory.startswith('.') or is_link_like(path):
                    self.skipped.append(path.relative_to(self.root).as_posix())
                else:
                    kept.append(directory)
            directories[:] = kept
            for filename in filenames:
                path = Path(dirpath, filename)
                if filename.startswith('.') or is_link_like(path):
                    continue
                relative = path.relative_to(self.root).as_posix()
                self.files[relative] = path
                self.lookup[path_key(relative)] = relative
                self.names[path.name.casefold()].append(relative)
                self.stems[path.stem.casefold()].append(relative)
                if path.suffix.casefold() == '.md':
                    text = path.read_text(encoding='utf-8-sig', errors='replace')
                    self.texts[relative] = text
                    plain = without_code(text)
                    titles = re.findall(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$', plain, re.M)
                    anchors = {heading_key(title) for title in titles}
                    counts = Counter()
                    for title in titles:
                        base = heading_slug(title)
                        anchors.add(base if not counts[base] else f'{base}-{counts[base]}')
                        counts[base] += 1
                    anchors.update(re.findall(r'<(?:a|span)\b[^>]*?id=[\"\']([^\"\']+)', plain, re.I))
                    self.headings[relative] = anchors
                    self.blocks[relative] = set(re.findall(r'(?:^|\s)\^([\w-]+)(?:\s|$)', plain))

    def resolve(self, source: str, target: str, wiki: bool):
        decoded = re.sub(r'\\([\[\]() ])', r'\1', unquote(html.unescape(target))).replace('\\', '/')
        k = path_key(decoded)
        if wiki and '/' not in decoded:
            candidates = self.names.get(k, []) or self.names.get(k + '.md', []) or self.stems.get(k, [])
            # 短名可被不同目录复用；不替 Obsidian 猜测选中了哪个。
            return list(dict.fromkeys(candidates)), 'short_name'
        if wiki:
            keys = [k, k + '.md']
            parent = Path(source).parent.as_posix()
            keys += [path_key(parent + '/' + decoded), path_key(parent + '/' + decoded) + '.md']
        else:
            absolute = Path(os.path.normpath(os.path.join(str(self.root), str(Path(source).parent), decoded)))
            try:
                relative = absolute.relative_to(self.root).as_posix()
            except ValueError:
                return [], 'outside_root'
            keys = [path_key(relative), path_key(relative) + '.md']
        found = [self.lookup[k] for k in keys if k in self.lookup]
        # 明确目录的双链优先以根目录解释，其次才是来源目录相对路径。
        return list(dict.fromkeys(found))[:1], 'explicit_path'


def audit(root: Path) -> dict:
    index = VaultIndex(root)
    links, incoming, embedded = [], Counter(), Counter()
    for relative, original in index.texts.items():
        code_free = without_code(original)
        visible = navigation_text(code_free)
        found = [(m.start(), m[2].replace('\\|', '|').split('|', 1)[0], bool(m[1]), m[0], 'wiki')
                 for m in re.finditer(r'(!?)\[\[([^\]\n]+)\]\]', visible)]
        found += [(p, t, e, raw, 'markdown') for p, t, e, raw in markdown_links(visible)]
        found += [(m.start(), m[2], m[1].lower() == 'img', m[0], 'html')
                  for m in re.finditer(r'<(img|a)\b[^>]*?(?:src|href)=[\"\']([^\"\']+)[\"\'][^>]*>', code_free, re.I)]
        for position, target, embed, raw, syntax in sorted(found):
            line = visible.count('\n', 0, position) + 1
            record = dict(file=relative, line=line, target=target, syntax=syntax, embed=embed)
            if target.casefold().startswith('obsidian:'):
                query = parse_qs(urlparse(target).query)
                record.update(status='vault_uri', vault=query.get('vault', [None])[0],
                              uri_file=query.get('file', [None])[0], certainty='uri_not_opened')
            elif re.match(r'^(?:https?|mailto|data|codex|ftp|tel):', target, re.I):
                record.update(status='external_url', certainty='network_not_checked')
            elif re.match(r'^(?:file:|[a-zA-Z]:[\\/])', target):
                record.update(status='absolute_local_path', certainty='portability_issue_target_not_read')
            else:
                path, _, anchor = target.partition('#')
                path = path.split('?', 1)[0]
                matches, mode = index.resolve(relative, path, syntax == 'wiki') if path else ([relative], 'self')
                if not matches:
                    # 计划标记只解释链接意图，不自动补建内容。
                    context = original.splitlines()[line - 1]
                    planned = bool(re.search(r'待创建|待建|预留|计划卡|尚未创建|audit:planned', context))
                    record.update(status=('outside_root' if mode == 'outside_root' else 'planned_target' if planned else 'missing_target'),
                                  certainty='not_read_outside_root' if mode == 'outside_root' else 'target_absent_in_scanned_root')
                elif len(matches) > 1:
                    record.update(status='ambiguous_short_name', certainty='multiple_existing_targets', candidates=matches)
                else:
                    destination = matches[0]
                    record.update(status='resolved', resolved_to=destination, certainty='file_exists')
                    incoming[destination] += 1
                    if embed:
                        embedded[destination] += 1
                    if anchor and destination.casefold().endswith('.md'):
                        anchor = unquote(anchor)
                        is_block = anchor.startswith('^')
                        exists = anchor[1:] in index.blocks[destination] if is_block else heading_key(anchor) in index.headings[destination] or heading_slug(anchor) in index.headings[destination]
                        if not exists:
                            record.update(status='missing_block_anchor' if is_block else 'missing_heading_anchor', certainty='anchor_absent_in_scanned_text')
            links.append(record)
    duplicates = defaultdict(list)
    for relative, text in index.texts.items():
        duplicates[hashlib.sha256(text.encode('utf-8')).hexdigest()].append(relative)
    extensions = Counter(path.suffix.casefold() or '(无扩展名)' for path in index.files.values())
    findings = [record for record in links if record['status'] not in {'resolved', 'external_url'}]
    return dict(
        schema_version=1,
        generated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
        root=str(index.root),
        counts=dict(files=len(index.files), markdown=len(index.texts), images=sum(extensions[e] for e in IMAGE_EXTENSIONS),
                    extensions=dict(extensions), link_status=dict(Counter(record['status'] for record in links))),
        links=links,
        findings=findings,
        exact_markdown_duplicates=[paths for paths in duplicates.values() if len(paths) > 1],
        notes_without_incoming=[path for path in index.texts if not incoming[path]],
        images_without_markdown_embeds=[path for path, item in index.files.items() if item.suffix.casefold() in IMAGE_EXTENSIONS and not embedded[path]],
        skipped_directories=index.skipped,
        limitations=[
            '机械检查全量扫描 Markdown，不能证明数学正确、原图完整或来源可靠。',
            '只读取指定根目录；隐藏配置、插件目录和符号链接不跟随。',
            '外部网页、其他 vault URI 和本机绝对路径只登记，不请求网络或读取外部文件。',
            '无入链、无嵌入、内容完全相同均为整理候选，不构成删除建议。',
            '计划目标只按同一行的明确待建文字分类，其余缺失目标仍须人工核对意图。',
            '支持 wiki、内联 Markdown 和 HTML src/href；不解析 Markdown 引用式链接或插件私有语法。',
            '大小写不敏感路径用于 Windows 库；区分大小写的环境需人工复核同名冲突。',
            '标题匹配支持可读标题、常见 GitHub slug 与块 ID；客户端具体渲染仍需另验。',
        ],
    )


def render_report(result: dict) -> str:
    counts = result['counts']
    lines = ['# 知识库结构审计', '', f'根目录：`{result["root"]}`', '',
             f'Markdown {counts["markdown"]} 个；图片 {counts["images"]} 个；可见文件 {counts["files"]} 个。', '',
             '| 状态 | 数量 |', '|---|---:|']
    lines.extend(f'| {state} | {count} |' for state, count in sorted(counts['link_status'].items()))
    lines += ['', '## 逐行待处理项', '']
    lines.extend(f'- `{r["file"]}:{r["line"]}` · {r["status"]} · `{r["target"]}`' for r in result['findings'])
    lines += ['', '## 检查边界', '']
    lines.extend('- ' + limitation for limitation in result['limitations'])
    return '\n'.join(lines) + '\n'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, help='实际 Obsidian vault 根目录，通常含 .obsidian；不要误用它的子目录')
    parser.add_argument('--output', type=Path, required=True, help='JSON 和中文报告输出目录，必须在被审计库之外')
    args = parser.parse_args(argv)
    root, output = args.root.resolve(), args.output.resolve()
    if output == root or root in output.parents:
        parser.error('输出目录必须在被审计库之外，以免下一次把报告自身当成笔记。')
    result = audit(root)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'report.md').write_text(render_report(result), encoding='utf-8')
    print(json.dumps(result['counts'], ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
