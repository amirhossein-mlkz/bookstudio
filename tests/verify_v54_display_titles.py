"""v5.4: section presentation labels, preservation, and live rendering."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys, shutil
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bookstudio.book_project import new_section, validate_sections, save_workspace, load_workspace
from bookstudio import renderer as R, book_compose as C


def verify():
    p = new_section('عنوان رسمی فصل')
    assert p['heading_label_text']==p['opener_label_text']==p['opener_title_text']==''
    p.update(heading_label_text='عنوان مستقل داخل مستطیل',
             opener_label_text='بخش یک',
             opener_title_text='عنوان اختصاصی صفحه بازکننده')
    p['markdown'] = '# عنوان رسمی فصل\n\n## بخش آموزشی\n\nاین متن بخشی از فصل است.\n'
    with TemporaryDirectory() as td:
        folder=Path(td)
        save_workspace(folder, [p], {})
        loaded,_=load_workspace(folder)
        assert {x:loaded[0][x] for x in ('heading_label_text','opener_label_text','opener_title_text')}=={
            x:p[x] for x in ('heading_label_text','opener_label_text','opener_title_text')}
        assert loaded[0]['title']=='عنوان رسمی فصل'
        q=new_section('تست پیش‌فرض', markdown='متن بدون تیتر')
        assert validate_sections([q])[0]['heading_label_text']==''

    cfg=R.validate_settings({})
    custom=R.render_markdown('<!-- CHAPTER -->\n\n# عنوان رسمی فصل\n\n# زیرعنوان مستقل', cfg,
                             heading_label_override=p['heading_label_text'],
                             opener_label_override=p['opener_label_text'],
                             opener_title_override=p['opener_title_text'])
    assert '<div class="chapter-label"' in custom
    assert '>بخش یک</div>' in custom
    assert 'عنوان اختصاصی صفحه بازکننده</div>' in custom
    assert 'عنوان مستقل داخل مستطیل' in custom
    assert 'زیرعنوان مستقل' in custom
    assert custom.count('h1-label')==2
    default=R.render_markdown('<!-- CHAPTER -->\n\n# عنوان رسمی فصل',cfg)
    assert '>فصل</div>' in default
    assert 'عنوان رسمی فصل</div>' in default

    ui=(Path(__file__).resolve().parents[1]/'bookstudio/templates/index.html').read_text('utf8')
    js=(Path(__file__).resolve().parents[1]/'bookstudio/static/app.js').read_text('utf8')
    for field in ('sectionHeadingLabel','sectionOpenerLabel','sectionOpenerTitle'):
        assert f'id="{field}"' in ui
        assert f"$('{field}')" in js

    # PDF integration using local Noto substitution fonts that are removed
    # immediately. No test fonts are shipped with the project.
    fontdir=Path(__file__).resolve().parents[1]/'bookstudio/fonts'
    reg=fontdir/'Vazirmatn-Regular.ttf'; bold=fontdir/'Vazirmatn-Bold.ttf'
    assert not reg.exists() and not bold.exists(), 'Do not overwrite user fonts'
    sysreg=Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf')
    sysbold=Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf')
    if sysreg.is_file() and sysbold.is_file():
        original = {name:getattr(R,name) for name in ('PROJECT','SETTINGS','OUTPUT','PDF')}
        compose_original = {name:getattr(C,name) for name in ('OUTPUT','SECTION_OUTPUT')}
        try:
            shutil.copyfile(sysreg,reg);shutil.copyfile(sysbold,bold)
            with TemporaryDirectory() as td:
                temp=Path(td); project=temp/'project'; project.mkdir()
                output=temp/'output';output.mkdir()
                R.PROJECT=project;R.SETTINGS=project/'settings.json';R.OUTPUT=output;R.PDF=output/'book.pdf'
                C.OUTPUT=output;C.SECTION_OUTPUT=output/'sections'
                first=new_section('عنوان رسمی فصل', markdown='# عنوان رسمی فصل\n\n## متن\n\nاین یک متن آزمایشی است.\n')
                first.update(heading_label_text='کادر متن سفارشی',opener_label_text='برچسب بالا',
                             opener_title_text='عنوان پایین')
                second=new_section('فصل دوم',markdown='# فصل دوم\n\nمتن نمونه دوم.\n')
                save_workspace(project,[first,second],{})
                R.save_settings(R.validate_settings({}))
                out=C.compose_book()
                import pymupdf as fitz
                with fitz.open(R.PDF) as doc:
                    joined='\n'.join(page.get_text() for page in doc)
                    assert 'کادر متن سفارشی' in joined, 'Custom in-content H1 missing'
                    assert 'برچسب' in joined and 'عنوان پایین' in joined
                    assert len(doc)==out['pages']
                assert out['sections'][0]['pages'] >= 2
                # No opener must still retain the custom H1.
                first['include_title_page']=False
                save_workspace(project,[first,second],{})
                off=C.compose_book()
                with fitz.open(R.PDF) as doc:
                    joined='\n'.join(page.get_text() for page in doc)
                    assert 'کادر متن سفارشی' in joined
                    assert 'برچسب بالا' not in joined
                    assert len(doc)==off['pages']
                assert off['pages']==out['pages']-1, (out['pages'],off['pages'])
        finally:
            for name,val in original.items():setattr(R,name,val)
            for name,val in compose_original.items():setattr(C,name,val)
            reg.unlink(missing_ok=True);bold.unlink(missing_ok=True)
    print('PASS v5.4: independent default/custom H1, opener labels, persistence, full PDF, no-opener PDF')

if __name__=='__main__':verify()
