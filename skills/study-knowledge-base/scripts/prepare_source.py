"""可选PDF裁图：记录真实页码、裁图边界与原文件摘要；不做OCR。需要PyMuPDF。"""
import argparse,json,hashlib
from pathlib import Path
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pdf',type=Path);p.add_argument('--page',type=int,required=True);p.add_argument('--rect',type=float,nargs=4,default=[0,0,1,1]);p.add_argument('--dpi',type=int,default=288);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    import pymupdf
    x0,y0,x1,y1=a.rect
    if not (0<=x0<x1<=1 and 0<=y0<y1<=1 and 72<=a.dpi<=600):p.error('rect应为0到1的归一化矩形，dpi为72到600')
    if a.output.exists() or a.output.with_suffix('.source.json').exists():p.error('目标已存在，不覆盖原裁图')
    with pymupdf.open(a.pdf) as doc:
        if not 1<=a.page<=len(doc):p.error('物理页码超出PDF')
        page=doc[a.page-1];r=page.rect;clip=pymupdf.Rect(x0*r.width,y0*r.height,x1*r.width,y1*r.height)
        a.output.parent.mkdir(parents=True,exist_ok=True);page.get_pixmap(matrix=pymupdf.Matrix(a.dpi/72,a.dpi/72),clip=clip,alpha=False).save(a.output)
        record={'pdf_name':a.pdf.name,'pdf_sha256':hashlib.sha256(a.pdf.read_bytes()).hexdigest(),'physical_page':a.page,'total_pages':len(doc),'normalized_rect':a.rect,'dpi':a.dpi,'includes_page_right_boundary':x1==1,'includes_page_bottom_boundary':y1==1,'note':'边界为PDF页面边界，不证明纸质原件没有裁损；生成后须实际看图确认题干和图形完整'}
    a.output.with_suffix('.source.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(record,ensure_ascii=False))
if __name__=='__main__':main()
