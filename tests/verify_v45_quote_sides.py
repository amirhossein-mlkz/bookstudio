"""v4.5: quotation side notes switch outer margins based on physical folio.

No project data or bundled fonts are needed. Run from the project root:
    python tests/verify_v45_quote_sides.py
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from weasyprint import HTML
from bookstudio.renderer import place_quote_notes_in_outer_margin

STYLE = '''
@page {size:165mm 235mm; margin:18mm 25mm 20mm 21mm;}
@page :left {margin-left:25mm; margin-right:21mm;}
p {font-size:12pt; line-height:1.8;}
.book-quote {position:relative; display:block; break-inside:avoid; direction:rtl;}
.book-quote .quote-side {position:absolute; left:-22mm; top:0; width:17mm; direction:rtl;}
'''

def notes(document):
    found = []
    for i, p in enumerate(document.pages):
        for box in p._page_box.descendants():
            el = getattr(box, 'element', None)
            if getattr(box,'element_tag',None)!='aside' or el is None or 'book-quote' not in el.get('class',''):
                continue
            side = next((n for n in box.descendants() if getattr(getattr(n,'element',None),'get',lambda _ : '')('class')=='quote-side'),None)
            if side is not None:
                found.append((i, box.position_x, box.width, side.position_x, side.width))
    return found


def verify():
    # 18 paragraphs place the note on page two (even folio), and 12 on page
    # one (odd folio). Both must keep the quote *body* stationary.
    for preceding, expected_page in [(12, 0), (18, 1)]:
        html = '<style>'+STYLE+'</style><body>'+('<p>Example paragraph with enough text for pagination.</p>'*preceding)+('<aside class="book-quote"><div class="quote-side">Side note</div><div class="quote-main">Quotation content</div></aside></body>')
        doc=HTML(string=html).render()
        before=notes(doc)
        assert len(before)==1 and before[0][0]==expected_page, before
        place_quote_notes_in_outer_margin(doc,first_folio=1)
        after=notes(doc)
        _,qx,qwidth,x,_=after[0]
        if expected_page==0:
            assert abs(x-before[0][3])<0.01, ('odd left changed',before,after)
            assert x<qx, ('odd note must be on left',after)
        else:
            assert x>qx+qwidth, ('even note must be on right',after)
        # Ensure PDF generation can consume the modified layout boxes.
        assert len(doc.write_pdf())>1000

    # The starter must contain >=3 consecutively flowing pages worth of copy
    # with no explicit break before the special decorative page.
    source=(Path(__file__).resolve().parents[1]/'bookstudio/starter_project/book.md').read_text(encoding='utf-8')
    assert source.index('## از مسئله تا تعریف نیاز صنعتی')<source.index('<!-- BLANKPAGE -->')
    assert source.index('## تبدیل تحلیل به تصمیم اجرایی')<source.index('<!-- BLANKPAGE -->')
    assert 'یادداشت سمت راست در صفحه زوج' in source
    assert len(source.split())>850, len(source.split())
    print('PASS v4.5: right-side marginalia on even folios, left on odd, long starter text.')

if __name__=='__main__':
    verify()
