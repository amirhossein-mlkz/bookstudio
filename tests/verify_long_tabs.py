"""Regression test for long Persian labels on odd folio tabs.

Requires the user-supplied Vazirmatn regular and bold fonts in bookstudio/fonts.
Run from the project root: python tests/verify_long_tabs.py
"""
from pathlib import Path
import copy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import pymupdf as fitz
except ModuleNotFoundError:
    import fitz
from bookstudio.page_art import draw_odd
from bookstudio.renderer import DEFAULTS, mm


def verify():
    cfg = copy.deepcopy(DEFAULTS)
    cfg['odd_tab_text_1'] = 'بازاریابی صنعتی مقدماتی'
    cfg['odd_tab_text_2'] = 'طبقه‌بندی محصولات صنعتی'
    cfg['odd_tab_text_padding'] = 0.8
    with fitz.open() as pdf:
        p = pdf.new_page(width=mm(165), height=mm(235))
        draw_odd(p, '۲۳', cfg)
        assert p.get_text().strip(), 'No text was drawn on the first tab'

        cfg['odd_tab_text_1'] = 'بازاریابی صنعتی مقدماتی' * 12
        cfg['odd_tab_text_padding'] = 5
        p2 = pdf.new_page(width=mm(165), height=mm(235))
        draw_odd(p2, '۲۵', cfg)
        assert p2.get_text().strip(), 'No text was drawn on the second tab'
    print('PASS: ordinary and extreme Persian folio label render without exception')


if __name__ == '__main__':
    verify()
