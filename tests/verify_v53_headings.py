"""Regression checks for v5.3 H1 title banner and default page-tab margins.

No font bundle is required: the PDF renderer can use system fallbacks.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from weasyprint import HTML
from bookstudio.renderer import DEFAULTS, validate_settings, build_html, render_markdown


def verify():
    cfg=validate_settings({})
    assert [cfg[k] for k in ('odd_tab_margin_right', 'odd_tab_margin_bottom',
                              'even_tab_margin_left','even_tab_margin_top')]==[8,14,8,14]
    assert cfg['heading_styles']['h1']['triangle_color'].lower()=='#7d81a4'
    assert validate_settings({'odd_tab_margin_right':5.5})['odd_tab_margin_right']==5.5
    cfg=validate_settings({'heading_styles':{'h1':{'triangle_color':'#C86346',
                                                 'background':'#112244', 'color':'#ffffff'}}})
    html=build_html('# فصل اول\n\n# مدیریت بازارهای صنعتی و برنامه‌ریزی بلندمدت برای مراکز تولیدی و شرکت‌های خدماتی تخصصی',cfg)
    assert 'linear-gradient(to top right, #C86346 50%, transparent 50%)' in html
    assert html.count('h1-wedge')>=3
    doc=HTML(string=html).render()
    boxes=[]
    for page in doc.pages:
        parts=[]
        for box in page._page_box.descendants():
            el=getattr(box,'element',None)
            cl=el.get('class','') if el is not None else ''
            if type(box).__name__=='BlockBox' and cl in {'h1-wedge','h1-label'}:
                parts.append((cl,box))
        wedges=[b for c,b in parts if c=='h1-wedge']
        labels=[b for c,b in parts if c=='h1-label']
        assert len(wedges)==len(labels)
        for w,label in zip(wedges, labels):
            assert abs(w.border_height()-label.border_height())<0.1, (w.border_height(),label.border_height())
            assert w.position_x > label.position_x
            boxes.append(w.border_height())
    assert len(boxes)==2,boxes
    assert max(boxes)>=min(boxes)*1.5, boxes
    ui=(Path(__file__).resolve().parents[1]/'bookstudio/templates/index.html').read_text('utf-8')
    js=(Path(__file__).resolve().parents[1]/'bookstudio/static/app.js').read_text('utf-8')
    assert 'headingTriangleColor' in ui and 'headingTriangleColor' in js
    assert "level!=='h1'" in js
    print('PASS v5.3: full-height wedge, right-aligned H1, independent triangle color, updated defaults')

if __name__=='__main__':verify()
