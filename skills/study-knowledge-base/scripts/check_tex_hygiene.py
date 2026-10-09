"""检查美元公式内疑似漏写的命令；只报告，不自动改写数学。"""
import argparse,json,re
from pathlib import Path

def inspect(text):
    text=re.sub(r'^\s*(?:>\s*)+', '', text, flags=re.M)
    text=re.sub(r'```[\s\S]*?```|`[^`\n]*`','',text)
    findings=[]
    for m in re.finditer(r'\\\(|\\\[',text):
        findings.append({'line':text[:m.start()].count('\n')+1,'token':m.group(),'severity':'warning','reason':'替代数学定界符：本交付模板要求美元定界符，须核对最终显示和检查器覆盖范围'})
    for m in re.finditer(r'(?<!\\)\$\$([\s\S]*?)(?<!\\)\$\$|(?<!\\)\$(?!\$)([^\n$]*?)(?<!\\)\$',text):
        tex=m.group(1) if m.group(1) is not None else m.group(2)
        # 自然文字内容不作为疑似命令；复杂嵌套仍须人工判断。
        scanned=re.sub(r'\\(?:text|operatorname)\{[^{}]*\}','',tex)
        for hit in re.finditer(r'(?<![\\A-Za-z])(?:qquad|quad|frac|dfrac|tfrac|begin|end|det)(?![A-Za-z])',scanned):
            findings.append({'line':text[:m.start()].count('\n')+1,'token':hit.group(),'severity':'warning','tex':tex,'reason':'疑似缺少命令反斜杠；须人工核对，可能为刻意使用的记号'})
    return findings

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    files=sorted(a.root.rglob('*.md')) if a.root.is_dir() else [a.root]
    issues=[dict(x,file=str(f)) for f in files for x in inspect(f.read_text(encoding='utf-8-sig'))]
    result={'files':len(files),'findings':issues,'scope':'启发式排版疑点，不证明数学正确；未自动改写'}
    if a.output:a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
