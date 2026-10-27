from pathlib import Path
import sys
import unicodedata
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fitz
from bookstudio.book_compose import compose_book,toc_pages
from bookstudio.book_project import load_workspace
from bookstudio.renderer import PROJECT,load_settings,PDF,OUTPUT

def run():
    result=compose_book()
    parts,front=load_workspace(PROJECT)
    cfg=load_settings()
    assert result['sections'] and result['front_pages']>=3
    with fitz.open(PDF) as full:
        assert len(full)==result['pages']
        texts=[full[i].get_text() for i in range(3)]
        for term,text in zip(('شناسنامه کتاب','تقدیم به','فهرست مطالب'),texts):
            norm=lambda x: ''.join(unicodedata.normalize('NFKC',x).split())
            assert norm(term) in norm(text), (term,text[:150])
        for item in result['sections']:
            file=OUTPUT/'sections'/(item['id']+'.pdf')
            with fitz.open(file) as sep:
                assert len(sep)==item['pages']
                assert sep[0].rect==full[item['first_pdf_page']-1].rect
    examples=[{'label':f'عنوان طولانی بخش نمونه {i}: راهبرد بازاریابی صنعتی و مدیریت زنجیره ارزش','level':2,'page':i,'role':'chapter'} for i in range(120)]
    extra=toc_pages(cfg,front,examples)
    assert len(extra)>1
    extra.close()
    print('PDF assembly, front pages, per-section export, multi-page TOC: PASS',result['pages'])

if __name__=='__main__':run()
