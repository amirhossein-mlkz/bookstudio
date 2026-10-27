"""Book Studio layout smoke test (needs valid bundled fonts + dependencies).

Run: python tests/verify_layout.py
Runs the renderer on a temporary isolated project; never rewrites your book.
"""
from pathlib import Path
import copy
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fitz
from bookstudio import renderer

MD = '''<!-- CHAPTER -->
# فصل اول: نمونه

این یک متن آزمایشی برای پاورقی است.[^1]

[^1]: این متن پاورقی در پایین همین صفحه قرار می‌گیرد.

:::quote position=top-right
این یک کوتیشن کوتاه است.
-- توضیح کوتاه
:::

<!-- BLANKPAGE -->

<!-- PAGEBREAK -->

## محتوای ادامه

این پاراگراف بعد از یک صفحه ویژه قرار دارد.

<!-- PAGEBREAK -->

### صفحه زوج

این صفحه برای بررسی زبانه بالای سمت چپ است.
'''


def near(v, target, tolerance=1.3):
    return abs(v - target) <= tolerance


def verify():
    saved = (renderer.PROJECT, renderer.MARKDOWN, renderer.SETTINGS,
             renderer.OUTPUT, renderer.PDF)
    with tempfile.TemporaryDirectory(prefix='bookstudio-layout-') as tmp:
        root=Path(tmp)
        try:
            renderer.PROJECT=root
            renderer.MARKDOWN=root/'book.md'
            renderer.SETTINGS=root/'settings.json'
            renderer.OUTPUT=root/'output'
            renderer.PDF=renderer.OUTPUT/'book.pdf'
            renderer.MARKDOWN.write_text(MD,encoding='utf-8')
            cfg=copy.deepcopy(renderer.DEFAULTS)
            cfg['odd_tab_text_1']='آزمون کتاب'
            cfg['odd_tab_text_2']='فصل نمونه'
            cfg['quote_margin_top']=3
            cfg['quote_margin_bottom']=3
            cfg['quote_margin_left']=1
            cfg['quote_margin_right']=1
            renderer.SETTINGS.write_text(json.dumps(cfg,ensure_ascii=False),encoding='utf-8')
            n=renderer.render_pdf()
            with fitz.open(renderer.PDF) as doc:
                assert n==len(doc)==5, f'expected exactly 5 pages, found {len(doc)}'
                assert 'فصل' in doc[0].get_text()
                assert 'پاورقی' in doc[1].get_text(), 'footnote missing from anchor page'
                assert not doc[2].get_text().strip(), 'special blank page has unexpected text'
                assert len(doc[2].get_drawings())==3, 'special blank should have precisely three vector lines'
                assert 'محتوای ادامه' in doc[3].get_text()
                # First numbered page is 1 (odd) and appears bottom-right.
                odd = doc[1]
                odd_red = [v['rect'] for v in odd.get_drawings()
                           if v.get('fill') and v['rect'].x0>odd.rect.width-75
                           and v['rect'].y0>odd.rect.height-100]
                assert odd_red, 'odd red number box missing from bottom right'
                assert any(near(r.x1, odd.rect.width-renderer.mm(cfg['odd_tab_margin_right'])) and
                               near(r.y1, odd.rect.height-renderer.mm(cfg['odd_tab_margin_bottom'])) for r in odd_red), odd_red
                # Special blank counts in folios, so fourth physical page is number 3.
                assert '۳' in doc[3].get_text(), 'Persian folio after special sheet missing'
                even = doc[4]
                even_red = [v['rect'] for v in even.get_drawings()
                            if v.get('fill') and v['rect'].x1<75 and v['rect'].y0<100]
                assert any(near(r.x0, renderer.mm(cfg['even_tab_margin_left'])) and
                               near(r.y0, renderer.mm(cfg['even_tab_margin_top'])) for r in even_red), even_red
                # Some Arabic fonts have a broken ToUnicode map and return a
                # substituted character for Persian ۴ even when its glyph is visible.
                # Verify a nonempty text span is physically inside the red folio.
                red_area = max(even_red, key=lambda r: r.width * r.height)
                number_spans = [sp for block in even.get_text('dict')['blocks'] if 'lines' in block
                                for line in block['lines'] for sp in line['spans']
                                if fitz.Rect(sp['bbox']).intersects(red_area) and sp['text'].strip()]
                assert number_spans, 'Even folio text absent from red box'
            # A direct page-break in the middle of two flow chunks is one split.
            assert [k for k,_ in renderer.split_book_into_pages(renderer.render_markdown(MD,cfg))] == [
                'chapter','flow','blank','flow','flow']
        finally:
            renderer.PROJECT, renderer.MARKDOWN, renderer.SETTINGS, renderer.OUTPUT, renderer.PDF=saved
    print('PASS: 5 exact sheets, chapter, footnote, 3-line special page, vector odd/even tabs, Persian numerals.')


if __name__=='__main__':
    verify()
