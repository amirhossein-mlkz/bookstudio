"""Multipiece book compositor. Existing v4.5 page renderer remains the content engine.

Front matter is built as separate vector-PDF pages. All Markdown parts are
paginated first, then an automatic TOC is built from their laid-out headings.
"""
from __future__ import annotations
import html
import re
from pathlib import Path

try: import pymupdf as fitz
except ImportError: import fitz
from weasyprint import HTML

from . import renderer as R
from .book_project import load_workspace
from .page_art import draw_even,draw_odd,draw_blank_special,html_text,rgb
from .paths import resource_path, FONT_FAMILIES

OUTPUT=R.OUTPUT
SECTION_OUTPUT=OUTPUT/'sections'

def safe_html(page,rect,inner,cfg,*,size=10,align='right',color='#202852',weight=400):
    family=cfg.get('font_family','Vazirmatn')
    font=FONT_FAMILIES[family]
    fonts=f'''@font-face{{font-family:BSF;src:url("{font[400]}");font-weight:400;}}
@font-face{{font-family:BSF;src:url("{font[700]}");font-weight:700;}}'''
    # MuPDF's HTMLBox in RTL treats CSS left/right alignment as logical
    # start/end rather than physical edges. Invert for the printed right edge.
    physical_align = {'right': 'left', 'left': 'right'}.get(align, align)
    css=fonts+f'''*{{box-sizing:border-box}}html,body{{margin:0;padding:0;width:100%;direction:rtl}}.block{{display:block;width:100%;font-family:BSF,sans-serif;font-weight:{weight};font-size:{size}pt;line-height:1.85;color:{color};direction:rtl;text-align:{physical_align}!important;white-space:pre-wrap}}'''
    ar=fitz.Archive(str(resource_path('fonts')))
    return page.insert_htmlbox(rect,f'<div class="block" dir="rtl">{inner}</div>',css=css,archive=ar,scale_low=.65)

def put_text(page,rect,text,cfg,**kwargs):
    return safe_html(page,rect,html.escape(str(text)),cfg,**kwargs)

def colored_label(page,rect,text,cfg,fill,size=12,color="#ffffff"):
    page.draw_rect(rect,color=None,fill=rgb(fill))
    put_text(page,rect,text,cfg,size=size,color=color,weight=700,align='center')

def create_imprint(cfg,front):
    doc=fitz.open();p=doc.new_page(width=R.mm(cfg['page_width']),height=R.mm(cfg['page_height']))
    W,H=p.rect.width,p.rect.height;nav=rgb(cfg['navy']);muted=rgb(cfg['muted'])
    x=W*.19;right=W*.85;top=H*.255;bw=right-x
    # Reference: diagonals, grey tab, red book-title stripe and registry panel.
    for a,b,c,d in [(.15,.13,.21,.07),(.68,.10,.75,.03),(.85,.18,.9,.13),(.15,.79,.21,.73),(.77,.85,.87,.75)]:
        p.draw_line((W*a,H*b),(W*c,H*d),color=muted,width=1.25)
    p.draw_rect(fitz.Rect(x,top+R.mm(9),right,top+R.mm(112)),color=nav,fill=(.95,.95,.965),width=.9)
    colored_label(p,fitz.Rect(right-R.mm(52),top-R.mm(3),right,top+R.mm(8)),'شناسنامه کتاب',cfg,cfg['navy'],size=11)
    colored_label(p,fitz.Rect(x,top+R.mm(9),right,top+R.mm(21)),cfg['book_title'],cfg,front['imprint_header_color'],size=12)
    rows=[f'پدیدآورنده: {cfg.get("author","")}     |     ناشر: {cfg.get("publisher","")}',
          f'سال انتشار: {cfg.get("publication_year","")}      |      نوبت چاپ: {front["edition"]}',
          f'شمارگان: {front["print_run"]}      |      شابک: {front["isbn"]}',
          f'عنوان کتاب: {cfg.get("book_title","")}  /  {cfg.get("book_subtitle","")}',
          'مشخصات نشر، موضوع و شناسه کتابشناختی بر اساس اطلاعات ناشر',
          'کلیه حقوق مادی و معنوی اثر برای صاحب اثر محفوظ است.']
    for i,line in enumerate(rows):
        y=top+R.mm(22+i*14)
        if i<3:p.draw_line((x,y+R.mm(13)),(right,y+R.mm(13)),color=nav,width=.6)
        put_text(p,fitz.Rect(x+R.mm(3),y+R.mm(1),right-R.mm(3),y+R.mm(12)),line,cfg,size=8.2 if i!=3 else 8.7)
    p.draw_rect(fitz.Rect(x,top+R.mm(112),x+R.mm(23),top+R.mm(130)),color=nav,fill=rgb(front['imprint_header_color']))
    put_text(p,fitz.Rect(x+R.mm(26),top+R.mm(116),right,top+R.mm(130)),cfg.get('publisher',''),cfg,size=9,color=cfg['navy'])
    return doc

def create_dedication(cfg,front):
    doc=fitz.open();p=doc.new_page(width=R.mm(cfg['page_width']),height=R.mm(cfg['page_height']))
    W,H=p.rect.width,p.rect.height;nav=rgb(front['dedication_border_color']);muted=rgb(cfg['muted'])
    x=W*.19;right=W*.84;top=H*.29;bottom=H*.80
    path=p.new_shape()
    path.draw_polyline([(x,top),(right,top),(right,bottom-R.mm(4)),(right-R.mm(4),bottom),(x,bottom),(x,top)])
    path.finish(color=nav,width=1.2);path.commit()
    page_label=fitz.Rect(x,top-R.mm(14),x+R.mm(31),top)
    colored_label(p,page_label,'تقدیم به',cfg,front['dedication_label_bg'],size=13)
    s=p.new_shape();s.draw_polyline([(x+R.mm(31),top-R.mm(14)),(x+R.mm(42),top),(x+R.mm(31),top)]);s.finish(fill=muted,color=None);s.commit()
    p.draw_line((x-R.mm(27),top+R.mm(28)),(x-R.mm(5),top+R.mm(6)),color=nav,width=1.75)
    p.draw_line((x-R.mm(11),top+R.mm(33)),(x-R.mm(5),top+R.mm(27)),color=muted,width=1)
    p.draw_line((x+R.mm(3),top-R.mm(25)),(x+R.mm(18),top-R.mm(40)),color=muted,width=1.4)
    txt=front.get('dedication','').strip()
    put_text(p,fitz.Rect(x+R.mm(6),top+R.mm(9),right-R.mm(5),bottom-R.mm(29)),txt,cfg,size=front['dedication_font_size'],align='right')
    name=f"{cfg.get('author','')}\n{cfg.get('publication_year','')}"
    put_text(p,fitz.Rect(x+R.mm(4),bottom-R.mm(26),right-R.mm(6),bottom-R.mm(5)),name,cfg,size=10,align='right')
    return doc

def toc_pages(cfg,front,entries):
    doc=fitz.open();w=R.mm(cfg['page_width']);h=R.mm(cfg['page_height'])
    navy=rgb(front['toc_rule_color'])
    fs=front['toc_font_size'];max_y=h-R.mm(25)
    start_y=R.mm(front.get('toc_top_margin_mm',40))
    left_x=front.get('toc_side_margin_mm',19)
    def make_page():
        p=doc.new_page(width=w,height=h)
        colored_label(p,fitz.Rect(w*.51,R.mm(16),w*.85,R.mm(27)),front['toc_title'],cfg,front['toc_title_bg'],size=front['toc_title_size'],color=front['toc_title_color'])
        return p
    p=make_page();y=start_y
    for item in entries:
        depth=item['level'];role=item.get('role','chapter')
        extra=min(2,int(len(item['label'])/42));rh=R.mm(front.get('toc_row_height_mm',9)+3*extra)
        if y+rh>max_y:p=make_page();y=start_y
        side_x=w-R.mm(22);row_right=side_x-R.mm(1.5)
        label=item['label'];printed=R.persian_number(item['page'])
        box=fitz.Rect(side_x,y,side_x+R.mm(7),y+R.mm(6.5))
        badge_key = ('toc_badge_preface_color' if role == 'preface'
                     else 'toc_badge_intro_color' if role == 'introduction'
                     else 'toc_badge_h3_color' if depth == 3
                     else 'toc_badge_h2_color' if depth == 2
                     else 'toc_badge_h1_color')
        p.draw_rect(box,color=None,fill=rgb(front[badge_key]))
        put_text(p,box,printed,cfg,size=7.5,color='#ffffff',align='center',weight=700)
        shift=(depth-1)*R.mm(6)
        left=R.mm(left_x)+shift
        right=row_right
        put_text(p,fitz.Rect(left,y-R.mm(.5),right,y+rh-R.mm(2)),label,cfg,align='right',
                 size=fs-(2 if depth==3 else (1 if role in ('preface','introduction') else 0)),
                 color=front['toc_text_color'],weight=700 if role=='chapter' and depth==1 else 400)
        p.draw_line((R.mm(left_x),y+rh-R.mm(.8)),(w-R.mm(18),y+rh-R.mm(.8)),color=navy,width=.5)
        y+=rh
    return doc

def _heading_items(laid_out):
    items=[];seen=set()
    for i,page in enumerate(laid_out.pages):
        for box in page._page_box.descendants():
            if getattr(box,'element_tag',None) not in ('h2','h3'):continue
            element=getattr(box,'element',None)
            if element is None:continue
            key=id(element)
            if key in seen:continue
            seen.add(key)
            label=''.join(element.itertext()).strip()
            if label:items.append((label,2 if box.element_tag=='h2' else 3,i))
    return items

def _section_folio_config(cfg, part):
    """Four section labels; legacy blank even labels inherit useful defaults.

    The fallback is deliberately display-only: older project manifests and
    user-entered per-section values are never overwritten on disk.
    """
    return {
        'odd_tab_text_1': part.get('odd_tab_text_1') or '',
        'odd_tab_text_2': part.get('odd_tab_text_2') or '',
        'even_tab_text_1': (part.get('even_tab_text_1') or
                            part.get('odd_tab_text_1') or cfg['book_title']),
        'even_tab_text_2': (part.get('even_tab_text_2') or
                            part.get('odd_tab_text_2') or part['title']),
    }


def compose_book():
    R.OUTPUT.mkdir(parents=True,exist_ok=True);SECTION_OUTPUT.mkdir(parents=True,exist_ok=True)
    parts,front=load_workspace(R.PROJECT);cfg=R.load_settings()
    R.font_path(400,family=cfg['font_family']);R.font_path(700,family=cfg['font_family'])
    shell=R.build_html('',cfg)
    assert '<body></body>' in shell
    md_book=fitz.open();kinds=[];owners=[];part_ranges={};headings=[];first_flow=None
    chapter_number=0
    try:
        for part in parts:
            cfg_section={**cfg, **_section_folio_config(cfg, part)}
            # One shared chapter-opening style for all Markdown files.
            uniform_style=(cfg.get('chapter_styles') or {}).get('1',{})
            cfg_section['chapter_styles']={str(n):uniform_style for n in range(1,len(parts)+5)}
            if part['role']=='chapter':chapter_number+=1
            source=part['markdown']
            source=re.sub(r'^\s*<!-- CHAPTER -->\s*$', '',source,flags=re.M)
            # A legacy top-level Markdown # line used to double as section
            # metadata. Keep the v5.7 behavior when the automatic label is ON.
            # With it OFF, never discard an author-written # heading.
            include_heading=part.get('include_heading_label', True)
            if include_heading:
                source=re.sub(r'^#\s+[^\n]+\n?', '',source,count=1)
            include_opener=part.get('include_title_page', True)
            # All presentation overrides leave the canonical section title
            # (TOC/export/navigation) unchanged.
            heading_label = part.get('heading_label_text') or part['title']
            prolog=(f'<!-- CHAPTER -->\n\n# {part["title"]}\n\n' if include_opener
                    else (f'# {heading_label}\n\n' if include_heading else ''))
            chapter_start=(chapter_number - (1 if include_opener else 0)
                           if part['role']=='chapter' else 0)
            body=R.render_markdown(prolog+source,cfg_section,
                                    chapter_start_index=chapter_start,
                                    chapter_mode=part['role'],
                                    heading_label_override=heading_label if include_opener and include_heading else None,
                                    include_chapter_heading=include_heading,
                                    opener_label_override=part.get('opener_label_text') or None,
                                    opener_title_override=part.get('opener_title_text') or None)
            if not include_opener and include_heading:
                # Only the automatically generated H1 uses the compact heading
                # margin. Manually entered # headings retain their normal style.
                body=body.replace('<h1>', '<h1 class="content-chapter-label">', 1)
            chunks=R.split_book_into_pages(body)
            begin=len(md_book);section_heading=[]
            for kind,piece in chunks:
                if kind=='blank':
                    md_book.new_page(width=R.mm(cfg['page_width']),height=R.mm(cfg['page_height']))
                    kinds.append('blank');owners.append(part['id']);continue
                fragment_shell=shell
                if kind=='flow' and first_flow is None:first_flow=len(md_book)
                if kind=='flow':
                    folio=int(cfg['page_number_start'])+len(md_book)-first_flow
                    if folio%2==0:
                        fragment_shell=(shell.replace('@page :left','@page :TEMP')
                                       .replace('@page :right','@page :left')
                                       .replace('@page :TEMP','@page :right'))
                render_html=fragment_shell.replace('<body></body>','<body>'+piece+'</body>')
                laid_out=HTML(string=render_html,base_url=R.PROJECT.as_uri()+'/').render()
                if kind=='flow':
                    R.place_quote_notes_in_outer_margin(laid_out,folio)
                    section_heading.extend([(title,depth,len(md_book)+offset)
                      for title,depth,offset in _heading_items(laid_out)])
                blob=laid_out.write_pdf()
                with fitz.open(stream=blob,filetype='pdf') as frag:
                    if kind=='chapter' and len(frag)!=1:raise ValueError('صفحه عنوان فصل نباید بیش از یک صفحه شود.')
                    md_book.insert_pdf(frag)
                    kinds.extend([kind]*len(frag));owners.extend([part['id']]*len(frag))
            end=len(md_book)
            part_ranges[part['id']]=(begin,end)
            headings.extend([(part['id'],title,depth,page) for title,depth,page in section_heading])
        if first_flow is None:first_flow=0
        start=int(cfg['page_number_start'])
        # Numbering is global. Shared geometry; four folio strings vary per section.
        byid={p['id']:p for p in parts}
        for ix,(page,kind,pid) in enumerate(zip(md_book,kinds,owners)):
            if kind=='blank':draw_blank_special(page,cfg);continue
            if kind=='chapter':continue
            folio=start+ix-first_flow
            cfg_part={**cfg, **_section_folio_config(cfg, byid[pid])}
            number=R.persian_number(folio)
            if folio%2:draw_odd(page,number,cfg_part)
            else:draw_even(page,number,cfg_part)
        entries=[];count=0
        for part in parts:
            if part['role']=='chapter':count+=1
            first,last=part_ranges[part['id']]
            page=start+max(0,first-first_flow)
            if first<first_flow:page=start
            if front['toc_include_h1']:
                role=part['role']
                title=(f'فصل {R.persian_number(count)}: ' if role=='chapter' else '')+part['title']
                entries.append({'label':title,'level':1,'page':page,'role':role})
            for pid,title,depth,global_page in headings:
                if pid!=part['id']:continue
                if front.get(f'toc_include_h{depth}',False):
                    entries.append({'label':title,'level':depth,'page':start+global_page-first_flow,'role':part['role']})
        front_pdf=fitz.open()
        if front.get('imprint_enabled'):front_pdf.insert_pdf(create_imprint(cfg,front))
        if front.get('dedication_enabled'):front_pdf.insert_pdf(create_dedication(cfg,front))
        if front.get('toc_enabled'):front_pdf.insert_pdf(toc_pages(cfg,front,entries))
        front_pages=len(front_pdf)
        front_pdf.insert_pdf(md_book)
        tmp=R.PDF.with_suffix('.tmp.pdf');front_pdf.save(tmp,garbage=3,deflate=True);tmp.replace(R.PDF)
        for part in parts:
            first,last=part_ranges[part['id']]
            # Separate PDFs preserve printed numbers and original page art.
            single=fitz.open()
            single.insert_pdf(md_book,from_page=first,to_page=last-1)
            dst=SECTION_OUTPUT/(part['id']+'.pdf');out=dst.with_suffix('.tmp.pdf')
            single.save(out,garbage=3,deflate=True);out.replace(dst);single.close()
        return {'pages':len(front_pdf),'front_pages':front_pages,
                'sections':[{'id':p['id'],'title':p['title'],'role':p['role'],
                             'pages':part_ranges[p['id']][1]-part_ranges[p['id']][0],
                             'first_pdf_page':front_pages+part_ranges[p['id']][0]+1} for p in parts],
                'toc_entries':len(entries)}
    finally:
        md_book.close()
