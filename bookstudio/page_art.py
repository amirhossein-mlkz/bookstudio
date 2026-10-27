"""Page-master artwork, authored in PDF vector geometry (points).

Coordinates were measured from the 165 x 235 mm color reference PDF's
actual PDF paths, NOT rescaled from a screenshot.
"""
from __future__ import annotations

import html
import logging
try:
    import pymupdf as fitz
except ModuleNotFoundError:
    import fitz
from pathlib import Path
from functools import lru_cache
from .paths import FONT_FAMILIES, resource_path

# Master reference size and actual traced paths, in PDF points.
REF_W, REF_H = 467.717, 666.142

def rgb(hex_code):
    return tuple(int(hex_code[i:i+2], 16) / 255 for i in (1,3,5))

def font_css(family):
    names = FONT_FAMILIES[family]
    regular = names[400]
    bold = names[700]
    return (f'@font-face {{font-family:BookArabic;src:url("{regular}");font-weight:400;}}'
            f'@font-face {{font-family:BookArabic;src:url("{bold}");font-weight:700;}}'
            'html,body,p{margin:0;padding:0;} p{font-family:BookArabic;'
            'font-size:7pt;line-height:1.25;text-align:center;direction:rtl;color:#202852;}')

@lru_cache(maxsize=8)
def _rotated_alignment_css(family):
    """Calibrate PyMuPDF's rotated RTL alignment to physical page edges.

    PyMuPDF releases differ in how left/right CSS alignment maps after a
    90-degree HTML-box rotation. Measure the actual glyph position once per
    font family instead of assuming which direction points up.
    """
    archive=fitz.Archive(str(resource_path('fonts')))
    css_base=font_css(family)
    positions={}
    with fitz.open() as probe:
        for css_align in ('left', 'right'):
            page=probe.new_page(width=140,height=270)
            css=css_base + f'p{{font-size:9pt;text-align:{css_align};white-space:nowrap;}}'
            remaining,_=page.insert_htmlbox(
                fitz.Rect(50,30,66,230), '<p>آزمایش</p>',css=css,
                archive=archive,rotate=90,scale_low=0.3)
            if remaining < 0:
                continue
            y_values=[s['bbox'][1] for b in page.get_text('dict')['blocks']
                      for ln in b.get('lines',[]) for s in ln['spans']
                      if s['text'].strip()]
            if y_values:positions[css_align]=min(y_values)
    if len(positions)==2 and positions['left']!=positions['right']:
        upper=min(positions,key=positions.get)
        lower='right' if upper=='left' else 'left'
        return {'start':upper,'middle':'center','end':lower}
    logging.warning('Book Studio: could not calibrate rotated text alignment')
    return {'start':'right','middle':'center','end':'left'}


@lru_cache(maxsize=1024)
def _text_layout_probe(label, family, width, height, rotate, size, color, weight, text_align):
    """Measure visible ink, not the HTML box, for accurate centring.

    ``insert_htmlbox`` aligns the *line box* to the top; the visible glyphs
    usually sit several points above centre, especially for Persian digits.
    Return the relative ink centre and the accepted text/scale for this exact
    box. All probes stay in memory and do not touch the actual PDF page.
    """
    css = (font_css(family)
           + f'p{{font-size:{size}pt;color:{color};font-weight:{weight};'
             f'line-height:1.08;white-space:nowrap;text-align:{text_align};}}')
    archive = fitz.Archive(str(resource_path('fonts')))
    candidates = [label]
    for n in (90,72,56,44,32,26,20,16,12,8,5,2):
        if len(label)>n:
            variant=label[:n].rstrip()+'…'
            if variant not in candidates:
                candidates.append(variant)
    for candidate in candidates:
        with fitz.open() as probe:
            test=probe.new_page(width=max(260,width+120), height=max(530,height+120))
            box=fitz.Rect(50,50,50+width,50+height)
            remaining,_=test.insert_htmlbox(box, '<p>'+html.escape(candidate)+'</p>',
                                            css=css,archive=archive,rotate=rotate,scale_low=0.10)
            if remaining<0:continue
            ink=[]
            for block in test.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line.get('spans',[]):
                        if span.get('text','').strip():ink.append(fitz.Rect(span['bbox']))
            if not ink:continue
            ink_rect=fitz.Rect(min(a.x0 for a in ink),min(a.y0 for a in ink),
                               max(a.x1 for a in ink),max(a.y1 for a in ink))
            return candidate, ink_rect.x0+ink_rect.width/2-box.x0, ink_rect.y0+ink_rect.height/2-box.y0
    return None


def html_text(page, rect, text, family, *, rotate=0, size=7, color='#202852',
              weight=400, align='middle', center_target=None, center_axis=None):
    """Write Persian text with optional *glyph-centred* PDF placement.

    Rotated side labels keep their start/middle/end position on the long axis,
    but centre the glyphs in the full panel's physical width. Folio numbers
    centre on both axes of the coloured number box. This also works for
    differently sized text, non-symmetric padding and variable ribbon widths.
    """
    if not text:return
    rect=fitz.Rect(rect)
    if rect.width<=1 or rect.height<=1:
        logging.warning('Book Studio: folio label panel too small')
        return
    original=str(text).strip()
    css_align=(_rotated_alignment_css(family).get(align,'center')
               if rotate==90 else 'center')
    probe=_text_layout_probe(original,family,round(rect.width,4),round(rect.height,4),
                             rotate,float(size),color,int(weight),css_align)
    if probe is None:
        logging.warning('Book Studio: could not draw folio label: %s', original)
        return
    candidate,ink_x,ink_y=probe
    if candidate!=original:
        logging.warning('Book Studio: long folio text abbreviated to fit: %s',original)
    target=fitz.Rect(center_target) if center_target is not None else rect
    dx=target.x0+target.width/2-(rect.x0+ink_x) if center_axis in ('cross','both') else 0.
    dy=target.y0+target.height/2-(rect.y0+ink_y) if center_axis=='both' else 0.
    moved=fitz.Rect(rect.x0+dx,rect.y0+dy,rect.x1+dx,rect.y1+dy)
    css=(font_css(family)
         + f'p{{font-size:{size}pt;color:{color};font-weight:{weight};'
           f'line-height:1.08;white-space:nowrap;text-align:{css_align};}}')
    archive=fitz.Archive(str(resource_path('fonts')))
    remaining,_=page.insert_htmlbox(moved,'<p>'+html.escape(candidate)+'</p>',
                                     css=css,archive=archive,rotate=rotate,scale_low=0.10)
    if remaining<0:
        logging.warning('Book Studio: centred folio text could not be rendered: %s',original)


def outline(page, box, dark, *, fill=None):
    page.draw_rect(fitz.Rect(*box), color=dark, fill=fill, width=1.0, overlay=True)

def _inset_physical(rect, cfg, prefix):
    """Apply four independent physical paddings, without invalid HTML boxes.

    Extremely large paddings on narrow panels are reduced proportionally
    only when necessary to keep a minimally usable rendering rectangle.
    """
    box = fitz.Rect(rect)
    top, bottom, left, right = (
        max(0., float(cfg.get(prefix + '_pad_' + side, default))) * 72 / 25.4
        for side, default in (('top', 1.05), ('bottom', 1.1), ('left', 0.5), ('right', 0.5))
    )
    min_inner = 3.6
    avail_x = max(0., box.width - min_inner)
    avail_y = max(0., box.height - min_inner)
    if left + right > avail_x:
        f = avail_x / (left + right) if left + right else 0
        left *= f; right *= f
    if top + bottom > avail_y:
        f = avail_y / (top + bottom) if top + bottom else 0
        top *= f; bottom *= f
    return fitz.Rect(box.x0+left, box.y0+top, box.x1-right, box.y1-bottom)


def _width_pt(cfg, parity, index):
    default = 3.67 if index == 1 else 4.03
    return max(2.5, min(18., float(cfg.get(f'{parity}_tab_panel_{index}_width', default)))) * 72 / 25.4


def _font_pt(cfg, parity, index):
    default = 7.7 if index == 1 else 7.0
    return float(cfg.get(f'{parity}_tab_panel_{index}_font_size',default))


def _number_box(page, rect, number, cfg, parity):
    navy=rgb(cfg['navy'])
    outline(page,rect,navy,fill=rgb(cfg.get('tab_number_bg_color',cfg['crimson'])))
    # Center the number within the full sum of the two ribbons' widths.
    inner = fitz.Rect(rect)
    inset = min(2., inner.width*0.08, inner.height*0.12)
    inner.x0 += inset;inner.x1 -= inset
    inner.y0 += inset;inner.y1 -= inset
    html_text(page,inner,number,cfg['font_family'],size=float(cfg.get(f'{parity}_tab_number_font_size',8.3)),
              weight=400,color=cfg.get('tab_number_text_color','#ffffff'),
              center_target=rect,center_axis='both')


def draw_odd(page, number, cfg):
    """Right-bottom folio: adjacent variable-width panels above one number box."""
    W,H = page.rect.width,page.rect.height
    scale=min(W/REF_W,H/REF_H)
    ref_right_margin=(REF_W-433.917)*scale
    ref_bottom_margin=(REF_H-608.949)*scale
    dx=ref_right_margin-float(cfg.get('odd_tab_margin_right',8.0))*72/25.4+float(cfg.get('odd_tab_offset_x',0))*72/25.4
    dy=ref_bottom_margin-float(cfg.get('odd_tab_margin_bottom',14.0))*72/25.4+float(cfg.get('odd_tab_offset_y',0))*72/25.4
    def pt(x,y):return fitz.Point(W-(REF_W-x)*scale+dx,H-(REF_H-y)*scale+dy)
    w1=_width_pt(cfg,'odd',1);w2=_width_pt(cfg,'odd',2)
    right=pt(433.917,586.831).x
    boundary=right-w2;left=boundary-w1
    bottom=pt(0,586.831).y
    h1=float(cfg.get('odd_tab_panel_1_height',24.92))*72/25.4
    h2=float(cfg.get('odd_tab_panel_2_height',18.25))*72/25.4
    panel1=fitz.Rect(left,bottom-h1,boundary,bottom)
    panel2=fitz.Rect(boundary,bottom-h2,right,bottom)
    navy=rgb(cfg['navy']);muted=rgb(cfg['muted'])
    outline(page,panel1,navy)
    outline(page,panel2,navy)
    # Folded corner follows panel 2's upper edge even as its width changes.
    fold=min(10.109*scale,max(1.5,w2-1.0))
    x=boundary+min(0.5*scale,w2*0.10)
    y=panel2.y0-0.5*scale
    shape=page.new_shape()
    triangle=[fitz.Point(x,y),fitz.Point(x+fold,y),fitz.Point(x,y-fold)]
    shape.draw_polyline(triangle+[triangle[0]])
    shape.finish(color=None,fill=muted);shape.commit(overlay=True)
    red_top=pt(0,587.122).y;red_bottom=pt(0,608.949).y
    family=cfg['font_family']
    html_text(page,_inset_physical(panel1,cfg,'odd_tab_panel_1'),cfg.get('odd_tab_text_1',''),family,
              rotate=90,size=_font_pt(cfg,'odd',1),color=cfg['navy'],weight=700,
              align=cfg.get('odd_tab_panel_1_align','start'),center_target=panel1,center_axis='cross')
    html_text(page,_inset_physical(panel2,cfg,'odd_tab_panel_2'),cfg.get('odd_tab_text_2',''),family,
              rotate=90,size=_font_pt(cfg,'odd',2),color=cfg['navy'],weight=400,
              align=cfg.get('odd_tab_panel_2_align','start'),center_target=panel2,center_axis='cross')
    _number_box(page,fitz.Rect(left,red_top,right,red_bottom),number,cfg,'odd')


def draw_even(page, number, cfg):
    """Left-top folio: adjacent variable-width panels below one number box."""
    W,H=page.rect.width,page.rect.height
    scale=min(W/REF_W,H/REF_H)
    dx=float(cfg.get('even_tab_margin_left',8.0))*72/25.4-34.366*scale+float(cfg.get('even_tab_offset_x',0))*72/25.4
    dy=float(cfg.get('even_tab_margin_top',14.0))*72/25.4-57.193*scale+float(cfg.get('even_tab_offset_y',0))*72/25.4
    def pt(x,y):return fitz.Point(x*scale+dx,y*scale+dy)
    left=pt(34.366,0).x
    w1=_width_pt(cfg,'even',1);w2=_width_pt(cfg,'even',2)
    boundary=left+w1;right=boundary+w2
    top=pt(0,79.312).y
    h1=float(cfg.get('even_tab_panel_1_height',39.0))*72/25.4
    h2=float(cfg.get('even_tab_panel_2_height',92.35))*72/25.4
    panel1=fitz.Rect(left,top,boundary,top+h1)
    panel2=fitz.Rect(boundary,top,right,top+h2)
    navy=rgb(cfg['navy']);muted=rgb(cfg['muted'])
    outline(page,panel1,navy)
    outline(page,panel2,navy)
    # Grey folded tip stays attached to panel 1's lower-right corner.
    # The folded triangular flap shares *exactly* panel 1's width.
    # Its horizontal span follows all panel-1 width edits, not a capped fixed tip.
    fold=w1
    y=panel1.y1;x=boundary
    shape=page.new_shape()
    triangle=[fitz.Point(x,y),fitz.Point(x,y+fold),fitz.Point(x-fold,y)]
    shape.draw_polyline(triangle+[triangle[0]])
    shape.finish(color=None,fill=muted);shape.commit(overlay=True)
    family=cfg['font_family']
    html_text(page,_inset_physical(panel1,cfg,'even_tab_panel_1'),cfg.get('even_tab_text_1',''),family,
              rotate=90,size=_font_pt(cfg,'even',1),color=cfg['navy'],weight=700,
              align=cfg.get('even_tab_panel_1_align','start'),center_target=panel1,center_axis='cross')
    html_text(page,_inset_physical(panel2,cfg,'even_tab_panel_2'),cfg.get('even_tab_text_2',''),family,
              rotate=90,size=_font_pt(cfg,'even',2),color=cfg['navy'],weight=400,
              align=cfg.get('even_tab_panel_2_align','start'),center_target=panel2,center_axis='cross')
    _number_box(page,fitz.Rect(left,pt(0,57.193).y,right,pt(0,79.020).y),number,cfg,'even')

def draw_blank_special(page,cfg):
    """The three-diagonal-line page: exact one-page standalone art."""
    W,H=page.rect.width,page.rect.height
    dark=rgb(cfg['navy']);mute=rgb(cfg['muted'])
    x=W/2;y=H/2
    page.draw_line((x-31,y+30),(x+34,y-35),color=dark,width=1.75)
    page.draw_line((x+12,y-41),(x+24,y-53),color=mute,width=1.55)
    page.draw_line((x-43,y+54),(x-27,y+38),color=mute,width=1.55)

def decorate(doc,cfg,kinds):
    if len(doc) != len(kinds):
        raise ValueError('تعداد صفحات با نوع صفحه‌ها منطبق نیست.')
    start=int(cfg.get('page_number_start',1))
    first_visible = next((i for i, kind in enumerate(kinds) if kind == 'flow'), 0)
    for idx,(page,kind) in enumerate(zip(doc,kinds)):
        if kind == 'blank':
            draw_blank_special(page,cfg)
            continue
        if kind == 'chapter':
            continue
        # The first *numbered* page gets the configured starting number.
        # Later chapter and blank pages still count in physical pagination.
        printed=start+idx-first_visible
        if printed%2:
            draw_odd(page,str(printed).translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹')),cfg)
        else:
            draw_even(page,str(printed).translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹')),cfg)
