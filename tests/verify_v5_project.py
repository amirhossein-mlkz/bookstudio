"""Focused regression checks for v5. Run: python -m tests.verify_v5_project"""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bookstudio.book_project import load_workspace,save_workspace,validate_sections,new_section
from bookstudio.renderer import DEFAULTS

def run():
    root=Path(__file__).resolve().parents[1]
    starter=root/'bookstudio/starter_project'
    parts,front=load_workspace(starter)
    assert len(parts)==5 and [p['role'] for p in parts[:2]]==['preface','introduction']
    assert all((starter/'chapters'/f'{p["id"]}.md').exists() for p in parts)
    with TemporaryDirectory() as temp:
        dest=Path(temp)
        reordered=parts[:2]+[parts[4],parts[2],parts[3]]
        save_workspace(dest,reordered,front)
        actual,meta=load_workspace(dest)
        assert [s['id'] for s in actual]==[s['id'] for s in reordered]
        assert meta['toc_include_h2'] is True
        assert actual[2]['odd_tab_text_2']==parts[4]['odd_tab_text_2']
        actual[2]['markdown']='## بخش آزمایشی\n\nاین متن تغییر کرده است.'
        save_workspace(dest,actual,meta)
        check,_=load_workspace(dest)
        assert check[2]['markdown']==actual[2]['markdown']
        old=dest/'book.md';old.write_text('# متن میراثی\n\nمتن آزمایشی',encoding='utf-8')
        (dest/'bookstudio.project.json').unlink()
        legacy,_=load_workspace(dest)
        assert len(legacy)==1 and 'میراثی' in legacy[0]['title']
        try:validate_sections(parts[:2]+[parts[3],parts[2],parts[4]])
        except ValueError:raise AssertionError('Valid reorder rejected')
    print('Project v5 validation / legacy import / reorder: PASS')

if __name__=='__main__':run()
