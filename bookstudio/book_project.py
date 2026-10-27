"""Book Studio v5: one project, ordered Markdown parts, shared settings.

Manifest v2 intentionally keeps each chapter as a separate UTF-8 file. All
write paths are derived from a generated ID, not from user-submitted paths.
"""
from __future__ import annotations
import copy
import json
import re
import uuid
from pathlib import Path

MAX_PARTS = 160
MAX_BYTES = 3 * 1024 * 1024
ROLES = ('preface', 'introduction', 'chapter')
FRONT_DEFAULTS = {
    'dedication_enabled': True,
    'dedication': 'به مهندسان، مدیران و کارآفرینان صنعت ایران؛\n\nاین کتاب ادای دینی به همت شماست.\n\nباشد که هر صفحه‌اش گامی به سوی حرفه‌ای‌تر شدن باشد.',
    'imprint_enabled': True,
    'toc_enabled': True,
    'toc_include_h1': True,
    'toc_include_h2': True,
    'toc_include_h3': False,
    'toc_title': 'فهرست مطالب',
    'toc_title_color': '#ffffff',
    'toc_title_bg': '#565a8b',
    'toc_text_color': '#202852',
    'toc_rule_color': '#303342',
    'toc_badge_h1_color': '#8587a1',
    'toc_badge_h2_color': '#565a8b',
    'toc_badge_h3_color': '#a0a4b5',
    'toc_badge_preface_color': '#32395f',
    'toc_badge_intro_color': '#59658f',
    'toc_font_size': 10,
    'toc_title_size': 17,
    'toc_row_height_mm': 9,
    'toc_side_margin_mm': 19,
    'toc_top_margin_mm': 40,
    'dedication_border_color': '#202852',
    'dedication_label_bg': '#202852',
    'dedication_font_size': 14,
    'imprint_header_color': '#cf2833',
    'isbn': '978-600-000-000-0',
    'print_run': '۱۰۰۰',
    'edition': 'چاپ اول',
}

def new_section(title='فصل جدید', role='chapter', markdown=None):
    if role not in ROLES: raise ValueError('نوع بخش نامعتبر است')
    section_id = uuid.uuid4().hex[:12]
    return {
        'id': section_id, 'title': title[:160], 'role': role,
        'odd_tab_text_1': '', 'odd_tab_text_2': '',
        'even_tab_text_1': '', 'even_tab_text_2': title[:160], 'include_title_page': True,
        'include_heading_label': True,
        'heading_label_text': '', 'opener_label_text': '', 'opener_title_text': '',
        'markdown': markdown if markdown is not None else f'## {title}\n\nمتن این بخش را بنویسید.\n'
    }

def validate_front(src):
    obj=copy.deepcopy(FRONT_DEFAULTS)
    if not isinstance(src,dict): return obj
    for k,v in src.items():
        if k not in obj:continue
        fallback=obj[k]
        if isinstance(fallback,bool):obj[k]=bool(v)
        elif isinstance(fallback,int):
            try:obj[k]=max(7,min(70,int(v)))
            except(ValueError,TypeError):pass
        elif k.endswith('_color') or k.endswith('_bg'):
            if isinstance(v,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',v):obj[k]=v
        elif isinstance(v,str):obj[k]=v[:15000 if k=='dedication' else 300]
    return obj

def validate_sections(src):
    if not isinstance(src,list) or not (1<=len(src)<=MAX_PARTS):
        raise ValueError('پروژه باید بین ۱ تا ۱۶۰ فایل Markdown داشته باشد.')
    seen=set(); parts=[]; roles=set()
    for item in src:
        if not isinstance(item,dict):raise ValueError('مشخصات یکی از فصل‌ها معتبر نیست.')
        sid=item.get('id')
        if not isinstance(sid,str) or not re.fullmatch(r'[a-f0-9]{12}',sid) or sid in seen:
            raise ValueError('شناسه بخش نامعتبر یا تکراری است.')
        seen.add(sid)
        role=item.get('role','chapter')
        if role not in ROLES:raise ValueError('نوع بخش نامعتبر است.')
        if role in ('preface','introduction'):
            if role in roles:raise ValueError('فقط یک پیشگفتار و یک مقدمه مجاز است.')
            roles.add(role)
        title=item.get('title','')
        text=item.get('markdown','')
        if not isinstance(title,str) or not title.strip():raise ValueError('عنوان بخش نمی‌تواند خالی باشد.')
        if not isinstance(text,str) or len(text.encode('utf-8'))>MAX_BYTES:raise ValueError('فایل Markdown نامعتبر یا خیلی بزرگ است.')
        part={'id':sid,'title':title[:160].strip(),'role':role,'markdown':text,
              'include_title_page':item.get('include_title_page', True) is not False,
              'include_heading_label':item.get('include_heading_label', True) is not False}
        for key in ('odd_tab_text_1','odd_tab_text_2', 'even_tab_text_1','even_tab_text_2',
                    'heading_label_text', 'opener_label_text', 'opener_title_text'):
            value=item.get(key,'')
            part[key] = value[:200].strip() if isinstance(value,str) else ''
        parts.append(part)
    # Preface and intro must be book-openers. Drag order applies to all chapters.
    sequence=[p['role'] for p in parts if p['role'] in ('preface','introduction')]
    if sequence!=[r for r in ('preface','introduction') if r in sequence]:
        raise ValueError('پیشگفتار باید قبل از مقدمه باشد.')
    for index,role in enumerate(('preface','introduction')):
        at=[i for i,p in enumerate(parts) if p['role']==role]
        if at and at[0]>next((j for j,p in enumerate(parts) if p['role']=='chapter'),len(parts)):
            raise ValueError('پیشگفتار و مقدمه باید قبل از فصل‌های شماره‌دار باشند.')
    return parts

def serialize(parts,front):
    return {'application':'bookstudio-lite','version':2,
            'sections':[{k:v for k,v in p.items() if k!='markdown'} for p in parts],
            'frontmatter':validate_front(front)}

def load_workspace(folder:Path):
    manifest=folder/'bookstudio.project.json'
    if manifest.is_file():
        info=json.loads(manifest.read_text(encoding='utf-8'))
        if info.get('version')==2 and info.get('application')=='bookstudio-lite':
            parts=[]
            for item in info.get('sections',[]):
                section_id=item.get('id','')
                if not re.fullmatch(r'[a-f0-9]{12}',str(section_id)):
                    raise ValueError('شناسه فایل Markdown معتبر نیست.')
                file=folder/'chapters'/f'{section_id}.md'
                if not file.is_file():raise ValueError(f'فایل فصل {section_id} وجود ندارد.')
                parts.append({**item,'markdown':file.read_text(encoding='utf-8')})
            return validate_sections(parts),validate_front(info.get('frontmatter'))
    # v1 project import: preserve old book.md in a single chapter.
    old=folder/'book.md'
    if old.is_file():
        content=old.read_text(encoding='utf-8')
        # Existing projects may contain several <!-- CHAPTER --> blocks.
        # Convert each such block into an independent chapter without losing
        # headings, footnotes or pagebreak markers in the source text.
        splits=re.split(r'^\s*<!-- CHAPTER -->\s*$',content,flags=re.M)
        parts=[]
        for idx,chunk in enumerate(splits):
            if not chunk.strip():continue
            if idx==0 and len(splits)>1:
                role='preface' if 'پیشگفتار' in chunk[:250] else ('introduction' if 'مقدمه' in chunk[:250] else 'chapter')
            else:role='chapter'
            match=re.search(r'^#\s+(.+)$',chunk,re.M)
            title=match.group(1).strip() if match else ('متن کتاب' if len(splits)==1 else 'بخش '+str(idx))
            parts.append(new_section(title,role,chunk.strip()))
        return validate_sections(parts or [new_section('کتاب قدیمی','chapter',content)]),validate_front({})
    raise ValueError('پروژه Book Studio معتبر نیست.')

def save_workspace(folder:Path,parts,front):
    parts=validate_sections(parts);front=validate_front(front)
    chapters=folder/'chapters';chapters.mkdir(parents=True,exist_ok=True)
    valid=set()
    for part in parts:
        dest=chapters/f"{part['id']}.md"
        tmp=dest.with_suffix('.tmp')
        tmp.write_text(part['markdown'],encoding='utf-8');tmp.replace(dest)
        valid.add(dest.name)
    for old in chapters.glob('*.md'):
        if old.name not in valid: old.unlink()
    dest=folder/'bookstudio.project.json';temp=dest.with_suffix('.tmp')
    temp.write_text(json.dumps(serialize(parts,front),ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(dest)
    return parts,front
