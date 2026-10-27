"""Verify inline SVG quote marker follows the marginal note after even-page positioning."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz
from weasyprint import HTML
from bookstudio.renderer import build_html, DEFAULTS, place_quote_notes_in_outer_margin

source = ''':::quote
نقل قول آزمایشی صفحه فرد.
-- یادداشت فرد
:::

<!-- PAGEBREAK -->

:::quote
نقل قول آزمایشی صفحه زوج.
-- یادداشت زوج
:::'''
html = build_html(source, DEFAULTS)
assert html.count('<svg class="quote-mark-svg"') == 2
pdfdoc = HTML(string=html).render()
assert len(pdfdoc.pages) == 2, len(pdfdoc.pages)
place_quote_notes_in_outer_margin(pdfdoc, 1)
with fitz.open(stream=pdfdoc.write_pdf(), filetype='pdf') as pdf:
    for index, page in enumerate(pdf):
        sq = [d['rect'] for d in page.get_drawings()
              if d.get('fill') and max(abs(d['fill'][j] - 185/255) for j in range(3)) < 0.01]
        assert len(sq) == 1, (index, sq)
        if index == 0:
            assert sq[0].x1 < page.rect.width/4, sq
        else:
            assert sq[0].x0 > 3*page.rect.width/4, sq
print('PASS: quote SVG appears in left margin on odd and right margin on even PDF pages')
