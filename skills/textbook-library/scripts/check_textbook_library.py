#!/usr/bin/env python3
"""教材库结构检查：锚点、页脚、图嵌、图题、知识点卡与索引。

用法:
    python check_textbook_library.py <库目录> [--link-root <链接根目录>] [--caption-window 20]

`--link-root` 是 wiki 链接的解析根（Obsidian 里即 vault 根），默认取库目录的上一级。
只读，无第三方依赖，Python 3.9+。检查页码归属、结构与链接一致性；不检查内容正确性，
也不会判断插图页码是否为真实页（那需要模板匹配，见 references/truth-and-gates.md）。
发现 FAIL 时返回非零。
"""
import os
import re
import sys
from pathlib import Path

ANCHOR = re.compile(r'^<!--\s*来源块：\S*?-p(\d{4})-b(\d{3})\s*-->$')
FOOTER = re.compile(r'^\|\s*《[^|]+》\s*\|\s*PDF物理第\s*(\d+)\s*页\s*\|\s*$')
EMBED = re.compile(r'!\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]')
CAPTION = re.compile(r'^\*图\s*(\d{1,2})-(\d{1,2})-(\d{1,2})\s*([^*]*)\*$')
DOC_ENTRIES = ('00-阅读入口.md', '00-正文索引.md', '00-知识点索引.md', '索引.md')
WIKILINK = re.compile(r'(?<!!)\[\[([^\]|]+)(?:\|[^\]]*)?\]\]')


def unescape(target):
    return target.replace('\\|', '|').replace('\\', '/')


def check_draft(path, lib, win, res, root):
    """正文底稿：锚点顺序、页脚对应、图嵌、图题。"""
    name = os.path.basename(path)
    lines = Path(path).read_text(encoding='utf-8').split('\n')
    cur, pages, footers, last_footer = None, [], [], 0
    embeds, captions = [], []
    for i, ln in enumerate(lines, 1):
        m = ANCHOR.match(ln)
        if m:
            cur = int(m.group(1))
            pages.append(cur)
            continue
        f = FOOTER.match(ln)
        if f:
            n = int(f.group(1))
            footers.append(n)
            if cur != n:
                res.fail('%s:%d 页脚标 %s 页，但该页段最后一块属于 %s 页' %
                         (name, i, n, cur if cur is not None else '未知'))
            if n < last_footer:
                res.fail('%s:%d 页脚页码回退：%s → %s' % (name, i, last_footer, n))
            last_footer = n
            continue
        e = EMBED.search(ln)
        if e:
            target = unescape(e.group(1))
            found = os.path.exists(os.path.join(root, target)) or \
                os.path.exists(os.path.join(lib, target))
            if '/' not in target:
                res.fail('%s:%d 图片嵌入不是库内相对路径：%s' % (name, i, target))
            elif not found:
                res.fail('%s:%d 图片嵌入指向不存在的文件：%s' % (name, i, target))
            embeds.append((i, os.path.basename(target)))
            continue
        c = CAPTION.match(ln)
        if c:
            captions.append((i, '图%s-%s-%s' % c.groups()[:3]))
    for prev, nxt in zip(pages, pages[1:]):
        if nxt < prev:
            res.fail('%s 锚点页号回退：%s → %s' % (name, prev, nxt))
    for i, cap in captions:
        if not any(j > i - win and j <= i for j, _ in embeds):
            res.fail('%s:%d 图题 %s 前 %d 行内没有图片嵌入' % (name, i, cap, win))
    res.stat['图题'] = res.stat.get('图题', 0) + len(captions)
    res.stat['图嵌'] = res.stat.get('图嵌', 0) + len(embeds)
    return set(f for _, f in embeds), len(footers)


def check_cards(book, res, root):
    cards = sorted(f for f in os.listdir(os.path.join(book, '知识点'))
                   if f.endswith('.md'))
    if not cards:
        res.fail('%s 没有知识点卡' % book)
        return 0
    idx = os.path.join(book, '00-知识点索引.md')
    text = Path(idx).read_text(encoding='utf-8') if os.path.exists(idx) else ''
    if not text:
        res.fail('%s 缺少 00-知识点索引.md' % book)
    for f in cards:
        body = Path(book, '知识点', f).read_text(encoding='utf-8')
        h1 = [l for l in body.split('\n') if l.startswith('# ')]
        if len(h1) != 1 or h1[0][2:].strip() != f[:-3]:
            res.fail('%s/知识点/%s 的 H1 必须是文件名本身（单个一级标题）' % (book, f))
        # 简洁卡片不要求展示来源栏目；来源位置由后台记录保存。
        if f[:-3] not in text:
            res.fail('%s 的索引里没有卡片：%s' % (book, f[:-3]))
        for image in EMBED.finditer(body):
            target = unescape(image.group(1))
            if not (os.path.isfile(os.path.join(root, target)) or
                    os.path.isfile(os.path.join(book, target))):
                res.fail('%s/知识点/%s 图片不存在：%s' % (book, f, target))
        for link in WIKILINK.finditer(body):
            target = unescape(link.group(1).split('#', 1)[0])
            if '/' not in target:
                continue  # 未限定路径的别名由 Obsidian 自行解析，不猜目标
            candidate = target if target.endswith('.md') else target + '.md'
            if not (os.path.isfile(os.path.join(root, candidate)) or
                    os.path.isfile(os.path.join(book, candidate))):
                res.fail('%s/知识点/%s 链接不存在：%s' % (book, f, target))
    return len(cards)


def check_book(book, lib, win, res, root=None):
    name = os.path.relpath(book, lib)
    root = root or os.path.dirname(os.path.abspath(lib))
    missing = [f for f in DOC_ENTRIES if not os.path.exists(os.path.join(book, f))]
    if missing:
        res.fail('%s 缺少入口文件：%s' % (name, '、'.join(missing)))
    stub = os.path.join(os.path.dirname(book), os.path.basename(book)[:-3] + '.md')
    if not os.path.exists(stub):
        res.fail('%s 缺少书籍入口文件：%s' % (name, os.path.basename(stub)))

    figs = set()
    figdir = os.path.join(book, '图解')
    if not os.path.isdir(figdir):
        res.fail('%s 缺少 图解 目录' % name)
    else:
        figs = set(os.listdir(figdir))

    used, nfoot = set(), 0
    for f in sorted(os.listdir(os.path.join(book, '正文底稿'))):
        if f.endswith('.md'):
            u, n = check_draft(os.path.join(book, '正文底稿', f), lib, win, res, root)
            used |= u
            nfoot += n
    dangling = used - figs
    orphan = figs - used
    for f in sorted(dangling):
        res.fail('%s 引用了 图解 里不存在的图：%s' % (name, f))
    for f in sorted(orphan):
        res.fail('%s 图解 里没人引用的图：%s' % (name, f))
    cards = check_cards(book, res, root)
    res.stat['页脚'] = res.stat.get('页脚', 0) + nfoot
    res.stat['卡片'] = res.stat.get('卡片', 0) + cards
    res.stat['图解文件'] = res.stat.get('图解文件', 0) + len(figs)
    if not res.fail_count_delta():
        res.ok(name, nfoot, len(figs), cards)


class Result:
    def __init__(self):
        self.fails, self.warns, self.oks, self.stat = [], [], [], {}
        self._seen = 0

    def fail(self, msg):
        self.fails.append(msg)

    def warn(self, msg):
        self.warns.append(msg)

    def ok(self, name, nfoot, nfig, ncard):
        self.oks.append(name)
        self.stat.setdefault('书', []).append(
            '%s：页脚 %d、图 %d、卡 %d' % (name, nfoot, nfig, ncard))

    def fail_count_delta(self):
        n = len(self.fails)
        d = n > self._seen
        self._seen = n
        return d


def parse_args(argv):
    lib, win, root = None, 20, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--caption-window':
            win = int(argv[i + 1]);  i += 2;  continue
        if a == '--link-root':
            root = argv[i + 1];  i += 2;  continue
        if lib is None:
            lib = a
        i += 1
    return lib, win, root


def main():
    lib, win, root = parse_args(sys.argv[1:])
    if not lib:
        print(__doc__.strip())
        return 2
    if not os.path.isdir(lib):
        print('目录不存在：%s' % lib)
        return 2

    res = Result()
    books = []
    for course in sorted(os.listdir(lib)):
        cdir = os.path.join(lib, course)
        if not os.path.isdir(cdir):
            continue
        for d in sorted(os.listdir(cdir)):
            if d.endswith('-全文') and os.path.isdir(os.path.join(cdir, d)):
                books.append(os.path.join(cdir, d))
    if not books:
        print('没有找到 <课程>/<书名>-全文 目录：%s' % lib)
        return 2

    for b in books:
        check_book(b, lib, win, res, root)

    for line in res.stat.get('书', []):
        print('  %s' % line)
    print('合计：书 %d 本｜页脚 %d｜图解文件 %d｜图题 %d｜卡 %d' %
          (len(books), res.stat.get('页脚', 0), res.stat.get('图解文件', 0),
           res.stat.get('图题', 0), res.stat.get('卡片', 0)))
    for w in res.warns:
        print('[warn] %s' % w)
    for f in res.fails:
        print('[FAIL] %s' % f)
    print('FAIL %d，warn %d' % (len(res.fails), len(res.warns)))
    return 1 if res.fails else 0


if __name__ == '__main__':
    sys.exit(main())
