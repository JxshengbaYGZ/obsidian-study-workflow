"""验证模型正文与程序管理的标题/路径没有重复职责；不检查专业结论。"""
from pathlib import Path
import argparse,re,json

def inspect(text):
    errors=[]
    if re.search(r'^#\s',text,re.M):errors.append('正文片段不得自带一级标题，题名由元数据生成')
    if '[[' in text:errors.append('正文片段不得生成 wiki 文件链接')
    for link in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',text):
        if not re.match(r'https?://',link[1]):errors.append('正文片段不得生成本地路径链接，关系由元数据生成')
    if re.search(r'\\\(|\\\[',text):errors.append('请使用美元公式定界符')
    return errors

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('solver',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    files=[f for kind in ['answers','methods','topics'] for f in (a.solver/kind).glob('*.md')]
    errors=[{'file':str(f),'error':e} for f in files for e in inspect(f.read_text(encoding='utf-8-sig'))]
    result={'files':len(files),'errors':errors,'scope':'只检查片段职责、定界符，不证明内容正确'}
    if a.output:a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(bool(errors))
