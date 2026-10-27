"""Regression: quote background must follow the marginal note on even sheets.

Runs without bundled fonts. It compares the actual PDF rectangles rather
than relying only on WeasyPrint's box positions.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz
from weasyprint import HTML
from bookstudio.renderer import place_quote_notes_in_outer_margin

STYLE = '''
@page {size:165mm 235mm; margin:18mm 25mm 20mm 21mm;}
body {direction:rtl;}
.book-quote {position:relative; display:block; break-inside:avoid; direction:rtl;}
.book-quote .quote-side {position:absolute; left:-22mm; top:0; width:17mm; direction:rtl; text-align:right;}
.book-quote .quote-mark {display:block; margin:0 0 1.5mm auto; width:6.5mm; height:6.5mm;
  background:#b9b9b9; color:#fff; font-size:13pt; text-align:center; line-height:6.5mm;}
.book-quote .quote-source {font-size:9pt; line-height:1.75; text-align:right;}
.book-quote .quote-main {direction:rtl; font-size:16pt; line-height:1.7;}
.page-two {break-before:page;}
'''
QUOTE = '<aside class="book-quote"><div class="quote-side"><div class="quote-mark">”</div><div class="quote-source">یادداشت حاشیه‌ای</div></div><div class="quote-main">متن نقل قول</div></aside>'


def test():
    html = '<style>'+STYLE+'</style><body>'+QUOTE+'<div class="page-two">'+QUOTE+'</div></body>'
    laid_out = HTML(string=html).render()
    assert len(laid_out.pages) == 2, len(laid_out.pages)
    place_quote_notes_in_outer_margin(laid_out, first_folio=1)
    pdf_bytes = laid_out.write_pdf()
    with fitz.open(stream=pdf_bytes, filetype='pdf') as pdf:
        squares=[]
        for page in pdf:
            rectangles = [draw['rect'] for draw in page.get_drawings()
                          if draw.get('fill') and
                          all(abs(c-185/255)<0.01 for c in draw['fill'])]
            assert len(rectangles)==1, rectangles
            square=rectangles[0]
            assert 15 < square.width < 22 and 15 < square.height < 22, square
            # The square must sit above and in the same margin as its note.
            note_blocks = [fitz.Rect(b[:4]) for b in page.get_text('blocks') if 'یادداشت' in b[4]]
            assert len(note_blocks)==1, note_blocks
            note = note_blocks[0]
            assert note.y0 > square.y1, ('symbol must be above its note', square, note)
            assert square.x0 < note.x1 and note.x0 < square.x1, ('symbol and note must share a margin', square, note)
            squares.append(square)
        assert squares[0].x1 < 65, f'odd marker is not in the left margin: {squares[0]}'
        assert squares[1].x0 > 390, f'even marker is not in the right margin: {squares[1]}'
    print('PASS: quote glyph background left on odd folios, right on even folios; both above the note.')

if __name__ == '__main__':
    test()
