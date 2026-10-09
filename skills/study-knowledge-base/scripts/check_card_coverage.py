"""只读核对实际 Markdown 卡片是否同时登记于台账和交付清单。"""
import argparse
import json
from pathlib import Path, PureWindowsPath


def check(root, cards=('questions', 'topics'), ledger='ledger.json', manifest='manifest.json'):
    root = Path(root).resolve()
    errors = []
    card_files, ledger_files, manifest_files = set(), set(), set()
    items, entries = [], []

    def error(source, message, file=None):
        record = {'source': source, 'error': message}
        if file is not None:
            record['file'] = file
        errors.append(record)

    def relative_path(value, source, directory=False):
        if not isinstance(value, str) or not value.strip():
            error(source, '路径必须为非空字符串')
            return None
        # 两种斜线统一处理；盘符相对路径在非 Windows 系统上也不能漏过。
        name = value.replace('\\', '/')
        if name.startswith('/') or PureWindowsPath(name).drive:
            error(source, '必须使用 ROOT 内的相对路径，不能使用绝对路径或盘符', value)
            return None
        try:
            path = (root / name).resolve()
            if not path.is_relative_to(root):
                error(source, '路径越界：解析后位于 ROOT 外', value)
                return None
            exists = path.is_dir() if directory else path.is_file()
            if not exists:
                error(source, '目录不存在或不是目录' if directory else '文件不存在或不是文件', value)
                return None
            return path
        except (OSError, RuntimeError, ValueError) as exc:
            error(source, '路径无法解析：' + str(exc), value)
            return None

    unavailable = object()

    def read_json(value, source):
        path = relative_path(value, source)
        if path is None:
            return unavailable
        try:
            return json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as exc:
            error(source, '无法读取 JSON：' + str(exc), value)
            return unavailable

    if not root.is_dir():
        error('root', 'ROOT 不存在或不是目录', str(root))
    else:
        if not cards:
            error('cards', '至少指定一个卡片目录')
        for name in cards:
            folder = relative_path(name, 'cards', directory=True)
            if folder is None:
                continue
            try:
                for path in folder.rglob('*'):
                    if path.suffix.lower() == '.md' and not path.is_dir():
                        resolved = relative_path(path.relative_to(root).as_posix(), 'cards')
                        if resolved is not None:
                            card_files.add(resolved)
            except OSError as exc:
                error('cards', '无法枚举目录：' + str(exc), name)

        data = read_json(ledger, 'ledger')
        if data is not unavailable:
            if not isinstance(data, dict) or not isinstance(data.get('items'), list):
                error('ledger', '台账必须为对象，且 items 必须为列表')
            else:
                items = data['items']
                for index, item in enumerate(items):
                    source = 'ledger.items[' + str(index) + ']'
                    if not isinstance(item, dict):
                        error(source, '条目必须为对象，且包含 output_file')
                        continue
                    value = item.get('output_file')
                    if not isinstance(value, str) or not value.strip():
                        error(source, '缺少有效 output_file：必须为非空字符串')
                        continue
                    path = relative_path(value, source + '.output_file')
                    if path is not None:
                        ledger_files.add(path)

        data = read_json(manifest, 'manifest')
        if data is not unavailable:
            if not isinstance(data, list):
                error('manifest', '清单必须为相对文件路径列表')
            else:
                entries = data
                for index, value in enumerate(entries):
                    path = relative_path(value, 'manifest[' + str(index) + ']')
                    if path is not None:
                        manifest_files.add(path)

        # 从实际文件反查两份记录；不以 expected_ids 充当实际卡片范围。
        for path in sorted(card_files):
            relative = path.relative_to(root).as_posix()
            if path not in ledger_files:
                error('coverage', '卡片缺少对应的 ledger.items.output_file', relative)
            if path not in manifest_files:
                error('coverage', '卡片未列入 manifest', relative)

    return {
        'cards': len(card_files),
        'ledger_items': len(items),
        'ledger_covered': len(card_files & ledger_files),
        'manifest_entries': len(entries),
        'manifest_covered': len(card_files & manifest_files),
        'errors': errors,
        'limitation': '仅检查文件登记与路径，不验证题干、数学语义或审查真实性',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root')
    parser.add_argument('--cards', nargs='+', default=['questions', 'topics'],
                        help='相对于 ROOT 的卡片目录，递归检查其中的 Markdown')
    parser.add_argument('--ledger', default='ledger.json', help='相对于 ROOT 的台账 JSON')
    parser.add_argument('--manifest', default='manifest.json', help='相对于 ROOT 的清单 JSON')
    args = parser.parse_args()
    result = check(args.root, args.cards, args.ledger, args.manifest)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(bool(result['errors']))
