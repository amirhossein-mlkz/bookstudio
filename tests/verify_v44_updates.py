"""v4.4 regression: default/master geometry and adjustable odd panels; UI inserts.
Does not require distributing or bundling any fonts."""
from pathlib import Path
import copy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bookstudio.renderer import DEFAULTS, validate_settings, mm, render_markdown
from bookstudio import page_art
try:
    import pymupdf as fitz
except ModuleNotFoundError:
    import fitz


def verify_geometry():
    previous = page_art.html_text
    try:
        # Geometry-only regression: avoid dependence on local font assets.
        page_art.html_text = lambda *args, **kwargs: None
        doc = fitz.open()
        a=doc.new_page(width=mm(165), height=mm(235))
        cfg=copy.deepcopy(DEFAULTS)
        page_art.draw_odd(a, '۱', cfg)
        main=[d['rect'] for d in a.get_drawings() if d['type']=='s' and d['rect'].width<12 and d['rect'].height>45]
        assert len(main)==2, main
        left=min(main,key=lambda r:r.x0)
        right=max(main,key=lambda r:r.x0)
        # The newer v5.3 default margins intentionally move both ribbons.
        expected_dy = (666.142 - 608.949) - mm(cfg['odd_tab_margin_bottom'])
        assert abs(left.y0 - (516.189 + expected_dy))<0.09, left
        assert abs(right.y0 - (535.114 + expected_dy))<0.09, right
        assert abs(left.y1 - (586.831 + expected_dy))<0.09, left
        assert abs(right.y1 - (586.831 + expected_dy))<0.09, right
        red_a=[d['rect'] for d in a.get_drawings() if d.get('fill') and d['fill'][0]>.5 and d['rect'].width>20]
        extra=copy.deepcopy(cfg)
        extra['odd_tab_panel_1_height']=60.0
        extra['odd_tab_panel_2_height']=45.0
        b=doc.new_page(width=mm(165), height=mm(235))
        page_art.draw_odd(b, '۳', extra)
        updated=[d['rect'] for d in b.get_drawings() if d['type']=='s' and d['rect'].width<12 and d['rect'].height>45]
        large_left=min(updated,key=lambda r:r.x0)
        large_right=max(updated,key=lambda r:r.x0)
        assert abs(large_left.height-mm(60))<0.08,large_left
        assert abs(large_right.height-mm(45))<0.08,large_right
        assert abs(large_left.y1-left.y1)<0.01
        assert abs(large_right.y1-right.y1)<0.01
        # The red folio's bounding rectangle must remain exactly unchanged.
        red_b=[d['rect'] for d in b.get_drawings() if d.get('fill') and d['fill'][0]>.5 and d['rect'].width>20]
        assert red_a and red_b and red_a[0] == red_b[0]
        doc.close()
    finally:
        page_art.html_text = previous
    # Old saved project -> new default keys, and custom values survive validation.
    clean=validate_settings({'book_title':'قدیمی','odd_tab_text_1':'کتاب','font_size':12})
    assert clean['odd_tab_panel_1_height']==24.92
    assert clean['odd_tab_panel_2_height']==18.25
    custom=validate_settings({'odd_tab_panel_1_height':58, 'odd_tab_panel_2_height':27})
    assert custom['odd_tab_panel_1_height']==58
    assert custom['odd_tab_panel_2_height']==27


def verify_markup():
    text='''این متن کوتیشن دارد.\n\n:::quote position=top-right\nمتن اصلی\n-- توضیح جانبی\n:::\n\nمثال پاورقی[^1]\n\n[^1]: توضیح پاورقی آزمایش\n'''
    out=render_markdown(text,DEFAULTS)
    assert 'book-quote' in out, out[:1000]
    assert 'fn-note' in out, out[:1000]


def verify_ui():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('SKIP browser UI regression (playwright not installed)')
        return
    root = Path(__file__).resolve().parents[1]
    markup=(root/'bookstudio/templates/index.html').read_text(encoding='utf-8')
    css=(root/'bookstudio/static/app.css').read_text(encoding='utf-8')
    script=root/'bookstudio/static/app.js'
    with sync_playwright() as pw:
        try:
            browser=pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        except Exception as exc:
            print('SKIP browser UI regression (Chromium not available):',str(exc)[:100])
            return
        page=browser.new_page(viewport={'width':1440,'height':900})
        errors=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        page.set_content(markup)
        page.add_style_tag(content=css)
        page.add_script_tag(path=str(script))
        assert not errors, errors
        assert page.locator('#insertMenu button').count()==6
        assert page.locator('#breakBtn').count()==1
        assert page.locator('#openImageDialog').count()==1
        assert page.locator('[data-key="odd_tab_panel_1_height"]').count()==1
        assert page.locator('[data-key="odd_tab_panel_2_height"]').count()==1
        # opening top dropdown preserves selection and inserts at caret
        area=page.locator('#markdown')
        area.fill('شروع پایان')
        area.evaluate('(el)=>{el.focus();el.setSelectionRange(5,5)}')
        page.locator('#insertMenu summary').click()
        page.locator('#breakBtn').click()
        result=area.input_value()
        assert '<!-- PAGEBREAK -->' in result and result.startswith('شروع'), result
        assert not page.locator('#insertMenu').evaluate('(el)=>el.open')
        # test quote using selected text and correct metadata position
        area.fill('متن منتخب')
        area.evaluate('(el)=>{el.focus();el.setSelectionRange(0,el.value.length)}')
        page.locator('#insertMenu summary').click()
        page.locator('#quoteBtn').click()
        result=area.input_value()
        assert ':::quote position=top-right' in result,result
        assert 'متن منتخب' in result,result
        assert '-- توضیح کوتاه در حاشیه\n:::' in result,result
        # footnote insertion must allocate next free number (existing 1)
        area.fill('نمونه قدیمی[^1]\n\n[^1]: توضیح قبلی')
        area.evaluate('(el)=>{el.focus();el.setSelectionRange(5,5)}')
        page.locator('#insertMenu summary').click()
        page.locator('#footnoteBtn').click()
        result=area.input_value()
        assert '[^2]' in result,result
        assert '[^2]: متن پاورقی' in result,result
        assert result.count('[^1]:')==1
        # image modal still opens from the top menu
        page.locator('#insertMenu summary').click()
        page.locator('#openImageDialog').click()
        assert page.locator('#imageDialog').evaluate('(el)=>el.open')
        browser.close()
        assert not errors,errors

if __name__=='__main__':
    verify_geometry();print('PASS geometry: independent heights, red number alignment, updated defaults')
    verify_markup();print('PASS markup: quote and footnote parsing')
    verify_ui();print('PASS UI: six menu actions, quote selection, next footnote, image dialog')
