"""Single-template, offline-first Markdown -> paginated PDF renderer."""
from __future__ import annotations
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote

GTK_BIN = r"C:\msys64\ucrt64\bin"
if os.name == "nt" and os.path.isdir(GTK_BIN):
    os.add_dll_directory(GTK_BIN)

try:
    import pymupdf as fitz
except ModuleNotFoundError:
    import fitz
from markdown_it import MarkdownIt
from weasyprint import HTML

from .paths import font_path, resource_path, FONT_FAMILIES, WEIGHT_LABELS, normalize_weight

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / 'project'
OUTPUT = ROOT / 'output'
SETTINGS = PROJECT / 'settings.json'
MARKDOWN = PROJECT / 'book.md'
PDF = OUTPUT / 'book.pdf'

DEFAULTS = {
    'book_title': 'کتاب نمونه صنعتی',
    'author': 'نویسنده',
    'publication_year': '۱۴۰۵',
    'publisher': 'نام ناشر',
    'book_subtitle': 'علمی و کاربردی',
    'navy': '#1f2656',
    'crimson': '#cf2833',
    'muted': '#7d81a4',
    'font_family': 'Vazirmatn',
    'font_size': 12.0,
    'font_weight': 400,
    'line_height': 1.8,
    'margin_top': 18,
    'margin_bottom': 20,
    'margin_inner': 21,
    'margin_outer': 25,
    'page_width': 165,
    'page_height': 235,
    'page_number_start': 1,
    'odd_tab_margin_right': 8.0, 'odd_tab_margin_bottom': 14.0,
    'even_tab_margin_left': 8.0, 'even_tab_margin_top': 14.0,
    'odd_tab_offset_x': 0, 'odd_tab_offset_y': 0,
    'even_tab_offset_x': 0, 'even_tab_offset_y': 0,
    # Per-panel box geometry; widths stay adjacent and span the folio box.
    'odd_tab_panel_1_width': 3.67, 'odd_tab_panel_2_width': 4.03,
    'even_tab_panel_1_width': 3.67, 'even_tab_panel_2_width': 4.03,
    # 16 physical, independent paddings (millimetres).
    'odd_tab_panel_1_pad_top': 1.05,
    'odd_tab_panel_1_pad_bottom': 1.1,
    'odd_tab_panel_1_pad_left': 0.5,
    'odd_tab_panel_1_pad_right': 0.5,
    'odd_tab_panel_2_pad_top': 1.05,
    'odd_tab_panel_2_pad_bottom': 1.1,
    'odd_tab_panel_2_pad_left': 0.5,
    'odd_tab_panel_2_pad_right': 0.5,
    'even_tab_panel_1_pad_top': 1.05,
    'even_tab_panel_1_pad_bottom': 1.1,
    'even_tab_panel_1_pad_left': 0.5,
    'even_tab_panel_1_pad_right': 0.5,
    'even_tab_panel_2_pad_top': 1.05,
    'even_tab_panel_2_pad_bottom': 1.1,
    'even_tab_panel_2_pad_left': 0.5,
    'even_tab_panel_2_pad_right': 0.5,
    'odd_tab_panel_1_font_size': 7.7, 'odd_tab_panel_2_font_size': 7.0,
    'even_tab_panel_1_font_size': 7.7, 'even_tab_panel_2_font_size': 7.0,
    'odd_tab_number_font_size': 8.3, 'even_tab_number_font_size': 8.3,
    'tab_number_bg_color': '#cf2833', 'tab_number_text_color': '#ffffff',
    'odd_tab_panel_1_height': 24.92,  # mm, long book-name ribbon
    'odd_tab_panel_2_height': 18.25,  # mm, shorter chapter-name ribbon
    'even_tab_panel_1_height': 39.0,  # mm, restored reference even-page height
    'even_tab_panel_2_height': 92.35, # mm, restored reference even-page height
    'odd_tab_panel_1_align': 'start', 'odd_tab_panel_2_align': 'start',
    'even_tab_panel_1_align': 'start', 'even_tab_panel_2_align': 'start',
    'odd_tab_text_1': 'نام کتاب',
    'odd_tab_text_2': 'عنوان فصل',
    'even_tab_text_1': 'نام کتاب',
    'even_tab_text_2': 'عنوان فصل',
    'chapter_styles': {},
    'heading_styles': {
        'h1': {'font_size': 13, 'font_weight': 700, 'background': '#1f2656', 'color': '#ffffff', 'triangle_color': '#7d81a4'},
        'h2': {'font_size': 13, 'font_weight': 700, 'background': '#575A84', 'color': '#ffffff'},
        'h3': {'font_size': 12, 'font_weight': 700, 'background': '#D1D1E0', 'color': '#575A84'},
    },
    'footnote_line_color': '#9a9a9a',
    'footnote_font_size': 9.0,
    'footnote_color': '#808080',
    'quote_symbol_bg': '#b9b9b9',
    'quote_font_size': 16.0,
    'quote_color': '#222222',
    'quote_meta_font_size': 9.0,
    'quote_meta_color': '#969696',
    'quote_position': 'top-right',
    'quote_margin_top': 3.0,
    'quote_margin_right': 1.0,
    'quote_margin_bottom': 3.0,
    'quote_margin_left': 1.0,
}

BOUNDS = {
    'font_size': (8, 22), 'line_height': (1.1, 2.6), 'margin_top': (8, 35),
    'margin_bottom': (8, 35), 'margin_inner': (10, 40), 'margin_outer': (25, 40),
    'page_width': (130, 220), 'page_height': (180, 310), 'page_number_start': (1, 9999),
    'odd_tab_margin_right': (0, 40), 'odd_tab_margin_bottom': (0, 40),
    'even_tab_margin_left': (0, 40), 'even_tab_margin_top': (0, 40),
    'odd_tab_offset_x': (-12,12), 'odd_tab_offset_y': (-12,12),
    'even_tab_offset_x': (-12,12), 'even_tab_offset_y': (-12,12),
    # Old 'odd_tab_text_padding' projects are migrated below.
    'odd_tab_panel_1_pad_top': (0,8),
    'odd_tab_panel_1_pad_bottom': (0,8),
    'odd_tab_panel_1_pad_left': (0,8),
    'odd_tab_panel_1_pad_right': (0,8),
    'odd_tab_panel_2_pad_top': (0,8),
    'odd_tab_panel_2_pad_bottom': (0,8),
    'odd_tab_panel_2_pad_left': (0,8),
    'odd_tab_panel_2_pad_right': (0,8),
    'even_tab_panel_1_pad_top': (0,8),
    'even_tab_panel_1_pad_bottom': (0,8),
    'even_tab_panel_1_pad_left': (0,8),
    'even_tab_panel_1_pad_right': (0,8),
    'even_tab_panel_2_pad_top': (0,8),
    'even_tab_panel_2_pad_bottom': (0,8),
    'even_tab_panel_2_pad_left': (0,8),
    'even_tab_panel_2_pad_right': (0,8),
    'odd_tab_panel_1_width': (2.5, 18), 'odd_tab_panel_2_width': (2.5, 18),
    'even_tab_panel_1_width': (2.5, 18), 'even_tab_panel_2_width': (2.5, 18),
    'odd_tab_panel_1_font_size': (4, 18), 'odd_tab_panel_2_font_size': (4, 18),
    'even_tab_panel_1_font_size': (4, 18), 'even_tab_panel_2_font_size': (4, 18),
    'odd_tab_number_font_size': (5, 22), 'even_tab_number_font_size': (5, 22),
    'odd_tab_panel_1_height': (10, 100), 'odd_tab_panel_2_height': (10, 100),
    'even_tab_panel_1_height': (10, 125), 'even_tab_panel_2_height': (10, 125),
    'footnote_font_size': (7, 14), 'quote_font_size': (10, 40), 'quote_meta_font_size': (8, 18),
    'quote_margin_top': (0, 60), 'quote_margin_right': (0, 60), 'quote_margin_bottom': (0, 60), 'quote_margin_left': (0, 60),
}
COLOR_KEYS = {'tab_number_bg_color', 'tab_number_text_color', 'navy', 'crimson', 'muted', 'footnote_line_color', 'footnote_color', 'quote_symbol_bg', 'quote_color', 'quote_meta_color'}
TEXT_KEYS = {'book_title', 'author', 'publication_year', 'publisher', 'book_subtitle', 'odd_tab_text_1', 'odd_tab_text_2', 'even_tab_text_1', 'even_tab_text_2'}
FOLIO_ALIGN_KEYS = {'odd_tab_panel_1_align', 'odd_tab_panel_2_align',
                    'even_tab_panel_1_align', 'even_tab_panel_2_align'}
FOLIO_ALIGN_VALUES = {'start', 'middle', 'end'}

md = MarkdownIt('commonmark', {'html': False, 'breaks': False}).enable('table')


def persian_number(value):
    return str(value).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))


def mm(v):
    return v * 72 / 25.4


def load_settings():
    if not SETTINGS.exists():
        return DEFAULTS.copy()
    try:
        obj = json.loads(SETTINGS.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return DEFAULTS.copy()
    return validate_settings(obj)


def validate_settings(obj):
    clean = json.loads(json.dumps(DEFAULTS, ensure_ascii=False))
    if not isinstance(obj, dict):
        return clean
    for key, value in obj.items():
        if key not in clean:
            continue
        if key in BOUNDS:
            try:
                v = float(value)
            except (ValueError, TypeError):
                continue
            low, high = BOUNDS[key]
            if key == 'page_number_start':
                clean[key] = int(max(low, min(high, v)))
            else:
                clean[key] = max(low, min(high, v))
        elif key in FOLIO_ALIGN_KEYS:
            if isinstance(value, str) and value in FOLIO_ALIGN_VALUES:
                clean[key] = value
        elif key in COLOR_KEYS:
            if isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                clean[key] = value
        elif key == 'font_family':
            clean[key] = value if value in FONT_FAMILIES else DEFAULTS['font_family']
        elif key == 'font_weight':
            try:
                clean[key] = int(value)
            except Exception:
                pass
        elif key == 'quote_position':
            clean[key] = value if value in {'top-right', 'bottom-left'} else DEFAULTS['quote_position']
        elif key == 'heading_styles' and isinstance(value, dict):
            styles = {}
            for level, fallback in DEFAULTS['heading_styles'].items():
                entry = value.get(level, {}) if isinstance(value.get(level, {}), dict) else {}
                styles[level] = {
                    'font_size': _clamp(entry.get('font_size', fallback['font_size']), 8, 28, fallback['font_size']),
                    'font_weight': _normalize_int(entry.get('font_weight', fallback['font_weight']), fallback['font_weight']),
                    'background': _valid_color(entry.get('background', fallback['background']), fallback['background']),
                    'color': _valid_color(entry.get('color', fallback['color']), fallback['color']),
                }
                if level == 'h1':
                    styles[level]['triangle_color'] = _valid_color(
                        entry.get('triangle_color', fallback['triangle_color']),
                        fallback['triangle_color'])
            clean[key] = styles
        elif key == 'chapter_styles' and isinstance(value, dict):
            styles = {}
            for num, style in list(value.items())[:300]:
                if not str(num).isdigit() or not isinstance(style, dict):
                    continue
                styles[str(num)] = {
                    'background': _valid_color(style.get('background', clean['navy']), clean['navy']),
                    'font_size': _clamp(style.get('font_size', 19), 11, 34, 19),
                    'font_weight': _normalize_int(style.get('font_weight', 700), 700),
                }
            clean[key] = styles
        elif key in TEXT_KEYS and isinstance(value, str):
            clean[key] = value[:200]
    # Number badge inherited the book's accent color before this release.
    if 'tab_number_bg_color' not in obj:
        clean['tab_number_bg_color'] = clean['crimson']
    # Previous versions stored a single padding shared across all panels.
    # Convert it only for specific sides that have no v5.9 override.
    if 'odd_tab_text_padding' in obj:
        old_pad = _clamp(obj.get('odd_tab_text_padding'), 0, 5, 0.8)
        for parity in ('odd', 'even'):
            for index in (1, 2):
                for side in ('top', 'bottom', 'left', 'right'):
                    key = f'{parity}_tab_panel_{index}_pad_{side}'
                    if key in obj:
                        continue
                    if side in ('top', 'bottom'):
                        offset = 0.22 if side == 'top' else 0.30
                        clean[key] = max(0, min(8, old_pad + offset))
                    else:
                        offset = 0.18 if parity == 'odd' else 0.22
                        clean[key] = max(0, min(8, old_pad * 0.42 + offset))
    return clean


def _clamp(value, low, high, default):
    try:
        return max(low, min(high, float(value)))
    except Exception:
        return default


def _valid_color(value, fallback):
    return value if isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value) else fallback


def _normalize_int(value, default):
    try:
        return int(value)
    except Exception:
        return default


def save_settings(obj):
    PROJECT.mkdir(exist_ok=True)
    clean = validate_settings(obj)
    temp = SETTINGS.with_suffix('.tmp')
    temp.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(SETTINGS)
    return clean


def extract_footnotes(source: str):
    defs = {}
    kept = []
    current = None
    for line in source.splitlines():
        m = re.match(r'^\[\^([^\]]+)\]:\s*(.*)$', line)
        if m:
            current = m.group(1)
            defs[current] = m.group(2).strip()
            continue
        if current and (line.startswith('    ') or line.startswith('\t')):
            defs[current] += ' ' + line.strip()
            continue
        current = None
        kept.append(line)
    return '\n'.join(kept), defs


def parse_quote_attrs(head: str):
    attrs = {'position': None}
    for token in (head or '').split():
        if '=' not in token:
            continue
        k, v = token.split('=', 1)
        attrs[k.strip()] = v.strip().strip("\"'")
    return attrs



def quote_mark_svg(background: str) -> str:
    """Return an inline, self-contained mark so the grey square travels with marginalia.

    This is intentionally not a CSS background: WeasyPrint can cache CSS
    background paint geometry before we move the marginal box on even pages.
    """
    if not isinstance(background, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', background):
        background = '#b9b9b9'
    return (
        '<svg class="quote-mark-svg" xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 100 100" role="presentation" aria-hidden="true">'
        f'<rect x="0" y="0" width="100" height="100" fill="{background}"/>'
        '<text x="50" y="76" fill="white" text-anchor="middle" '
        'font-family="serif" font-size="78">”</text>'
        '</svg>'
    )


def render_markdown(source: str, cfg: dict | None = None, chapter_start_index: int = 0, chapter_mode: str = 'chapter', *, heading_label_override: str | None = None, opener_label_override: str | None = None, opener_title_override: str | None = None, include_chapter_heading: bool = True):
    cfg = cfg or DEFAULTS
    source, footnotes = extract_footnotes(source)
    lines = source.splitlines()
    segments, buffer = [], []
    chapter_index = chapter_start_index

    def flush_md():
        if buffer:
            segments.append(('md', '\n'.join(buffer)))
            buffer.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.strip() == '<!-- PAGEBREAK -->':
            flush_md(); segments.append(('pagebreak', ''))
        elif line.strip() == '<!-- BLANKPAGE -->':
            flush_md(); segments.append(('blankpage', ''))
        elif line.strip() == '<!-- CHAPTER -->':
            flush_md(); chapter_index += 1
            title = 'فصل ' + str(chapter_index)
            j = index + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].startswith('# '):
                title = lines[j][2:].strip()
                index = j
            segments.append(('chapter', (chapter_index, title)))
            if include_chapter_heading:
                segments.append(('chapter_heading', title))
        elif line.strip().startswith(':::quote'):
            flush_md()
            attrs = parse_quote_attrs(line.strip()[8:].strip())
            qlines = []
            index += 1
            while index < len(lines) and lines[index].strip() != ':::':
                qlines.append(lines[index])
                index += 1
            source_text = ''
            if qlines and qlines[-1].strip().startswith('--'):
                source_text = qlines.pop().strip()[2:].strip()
            segments.append(('quote', {'attrs': attrs, 'lines': qlines, 'source': source_text}))
        else:
            buffer.append(line)
        index += 1
    flush_md()

    footnote_state = {'map': {}, 'counter': 0}
    output = []
    for kind, content in segments:
        if kind == 'pagebreak':
            output.append('<div class="pagebreak" aria-hidden="true"></div>')
        elif kind == 'blankpage':
            output.append('<section class="decor-page"><span class="blank-marker">BLANKPAGE_MARKER</span><div class="decor-slash ds1"></div><div class="decor-slash ds2"></div><div class="decor-slash ds3"></div></section>')
        elif kind == 'chapter':
            number, title = content
            title_clean = re.sub(r'^فصل\s+[^:：-]+[:：-]\s*', '', title)
            style = cfg.get('chapter_styles', {}).get(str(number), {})
            bg = style.get('background', cfg['navy'])
            font_size = style.get('font_size', 19)
            weight = style.get('font_weight', 700)
            opener_label = opener_label_override or {'preface':'پیشگفتار','introduction':'مقدمه'}.get(chapter_mode, 'فصل')
            opener_title = opener_title_override or title_clean
            number_text = persian_number(number) if chapter_mode == 'chapter' else ''
            output.append(f'''<section class="chapter-opener"><div class="slash sl1"></div><div class="slash sl2"></div><div class="slash sl3"></div><div class="slash sl4"></div>
<div class="chapter-card"><div class="chapter-top"><div class="chapter-number">{number_text}</div><div class="corner-triangle"></div></div>
<div class="chapter-label" style="background:{bg};font-size:{font_size}pt;font-weight:{weight}">{html.escape(opener_label)}</div><div class="chapter-title">{html.escape(opener_title)}</div></div></section>''')
        elif kind == 'chapter_heading':
            output.append('<h1 class="content-chapter-label">'+html.escape(heading_label_override if heading_label_override is not None else content)+'</h1>')
            # Override only the generated section H1; additional # headings in
            # the Markdown continue to render from their own source text.
            heading_label_override = None
        elif kind == 'quote':
            qpos = content['attrs'].get('position') or cfg.get('quote_position', 'top-right')
            qpos = qpos if qpos in {'top-right', 'bottom-left'} else cfg.get('quote_position', 'top-right')
            inner = md.render('\n'.join(content['lines'])).strip()
            source_html = f'<div class="quote-source">{html.escape(content["source"])}' + '</div>' if content['source'] else ''
            mark_html = quote_mark_svg(cfg.get('quote_symbol_bg', '#b9b9b9'))
            output.append(f'<aside class="book-quote {qpos}"><div class="quote-side"><div class="quote-mark">{mark_html}</div>{source_html}</div><div class="quote-main">{inner}</div></aside>')
        else:
            block = md.render(content)
            block = replace_footnote_refs(block, footnotes, footnote_state)
            output.append(block)

    rendered = '\n'.join(output)

    # H1: right-aligned label with a full-height, matching right-side triangle.
    # CSS gradient on a stretched flex item scales with multi-line heading height;
    # a fixed-size SVG would keep the old 9mm height even when the label wrapped.
    def style_h1(match):
        attrs, content = match.group(1), match.group(2)
        return (f'<h1{attrs}><span class="h1-decor">'
                f'<span class="h1-wedge" aria-hidden="true"></span>'
                f'<span class="h1-label">{content}</span>'
                f'</span></h1>')
    rendered = re.sub(r'<h1([^>]*)>(.*?)</h1>', style_h1, rendered, flags=re.S)

    def standalone_figure(m):
        tag, suffix = m.group(1), m.group(2)
        src_match = re.search(r'\bsrc="([^"]+)"', tag)
        alt_match = re.search(r'\balt="([^"]*)"', tag)
        if not src_match:
            return m.group(0)
        alt = html.unescape(alt_match.group(1)) if alt_match else ''
        width_match = re.fullmatch(r'\s*\{width=(\d+(?:\.\d+)?)(%|mm)\}\s*', html.unescape(suffix))
        if suffix.strip() and not width_match:
            return m.group(0)
        width_css = ''
        if width_match:
            num = float(width_match.group(1)); unit = width_match.group(2)
            size = max(10, min(100, num)) if unit == '%' else max(15, min(160, num))
            width_css = f' style="width:{size:g}{unit};max-width:100%;height:auto"'
        src = src_match.group(1)
        caption = '<figcaption>'+html.escape(alt)+'</figcaption>' if alt else ''
        return '<figure class="book-figure"><img src="'+src+'" alt="'+html.escape(alt, quote=True)+'"'+width_css+'>'+caption+'</figure>'

    rendered = re.sub(r'<p>\s*(<img\s+[^>]+/?>)(.*?)</p>', standalone_figure, rendered, flags=re.S)
    rendered = re.sub(r'</table>\s*<p>جدول\s*:\s*(.*?)</p>', r'</table><p class="table-caption">\1</p>', rendered)

    figure_i = 0; table_i = 0; chapter_i = chapter_start_index
    def renumber(match):
        nonlocal figure_i, table_i, chapter_i
        block = match.group(0)
        if block.startswith('<section class="chapter-opener"'):
            chapter_i += 1; figure_i = 0; table_i = 0
        elif block.startswith('<section class="decor-page"'):
            pass
        elif block.startswith('<figcaption>'):
            figure_i += 1
            block = '<figcaption>شکل '+persian_number(chapter_i)+'-'+persian_number(figure_i)+': '+block[len('<figcaption>'):]
        elif block.startswith('<p class="table-caption">'):
            table_i += 1
            block = '<p class="table-caption">جدول '+persian_number(chapter_i)+'-'+persian_number(table_i)+': '+block[len('<p class="table-caption">'):]
        return block
    rendered = re.sub(r'<section class="chapter-opener".*?</section>|<section class="decor-page".*?</section>|<figcaption>.*?</figcaption>|<p class="table-caption">.*?</p>', renumber, rendered, flags=re.S)

    images = (PROJECT / 'images').resolve()
    def img_sub(fake_match):
        attributes = fake_match.group(1)
        unquoted = html.unescape(fake_match.group(2))
        target = (PROJECT / unquote(unquoted)).resolve()
        if not target.is_file() or not target.is_relative_to(images):
            return '<div class="missing-image">تصویر نامعتبر یا موجود نیست: '+html.escape(unquoted)+'</div>'
        return '<img '+attributes+' src="'+target.as_uri()+'">'
    rendered = re.sub(r'<img\b([^>]*?)\bsrc="([^"]+)"([^>]*)>', lambda m: _img_reordered(m, img_sub), rendered)
    return rendered


def replace_footnote_refs(html_block: str, defs: dict, state: dict):
    def repl(m):
        key = m.group(1)
        if key not in state['map']:
            state['counter'] += 1
            state['map'][key] = state['counter']
        number = state['map'][key]
        content = defs.get(key, '')
        inner = md.renderInline(content) if content else ''
        return f'<span class="fn-anchor"><sup class="fn-call">{persian_number(number)}</sup><span class="fn-note"><span class="fn-note-no">{persian_number(number)}.</span> {inner}</span></span>'
    return re.sub(r'\[\^([^\]]+)\]', repl, html_block)


def _img_reordered(m, fn):
    attributes = (m.group(1) + ' ' + m.group(3)).strip()
    class FakeMatch:
        def group(self, i):
            return attributes if i == 1 else m.group(2)
    return fn(FakeMatch())


def font_faces_css() -> str:
    rules = []
    for weight, fname in FONT_FAMILIES['Vazirmatn'].items():
        path = resource_path('fonts') / fname
        if path.is_file():
            rules.append(f'@font-face {{font-family:"Vazirmatn";src:url("{path.as_uri()}") format("truetype");font-style:normal;font-weight:{weight};}}')
    ir = FONT_FAMILIES['IRNazanin']
    for weight in (400, 700):
        path = resource_path('fonts') / ir[weight]
        if path.is_file():
            rules.append(f'@font-face {{font-family:"IRNazanin";src:url("{path.as_uri()}") format("truetype");font-style:normal;font-weight:{weight};}}')
    italic_path = resource_path('fonts') / ir['italic']
    if italic_path.is_file():
        rules.append(f'@font-face {{font-family:"IRNazanin";src:url("{italic_path.as_uri()}") format("truetype");font-style:italic;font-weight:400;}}')
    return '\n'.join(rules)


def build_html(source: str, cfg: dict):
    body = render_markdown(source, cfg)
    family = cfg['font_family'] if cfg['font_family'] in FONT_FAMILIES else 'Vazirmatn'
    h1 = cfg['heading_styles']['h1']; h2 = cfg['heading_styles']['h2']; h3 = cfg['heading_styles']['h3']
    css = f'''
{font_faces_css()}
:root {{--navy:{cfg['navy']}; --crimson:{cfg['crimson']}; --muted:{cfg['muted']}; --footnote-line:{cfg['footnote_line_color']}; --footnote-color:{cfg['footnote_color']}; --quote-symbol-bg:{cfg['quote_symbol_bg']}; --quote-color:{cfg['quote_color']}; --quote-meta-color:{cfg['quote_meta_color']};}}
@page {{size:{cfg['page_width']}mm {cfg['page_height']}mm; margin:{cfg['margin_top']}mm {max(25,cfg['margin_outer'])}mm {cfg['margin_bottom']}mm {cfg['margin_inner']}mm;}}
@page :left {{margin-left:{max(25,cfg['margin_outer'])}mm; margin-right:{cfg['margin_inner']}mm;}}
@page :right {{margin-left:{cfg['margin_inner']}mm; margin-right:{max(25,cfg['margin_outer'])}mm;}}
@page chapter-opener {{margin:0;}}
@page {{ @footnote {{border-top:1.2pt solid {cfg['footnote_line_color']}; padding-top:2mm; width:calc(100% - 9mm); margin-right:9mm; }} }}
* {{box-sizing:border-box;}}
html {{font-family:"{family}", serif;}}
body {{margin:0; color:#252525; font-size:{cfg['font_size']}pt; font-weight:{cfg['font_weight']}; line-height:{cfg['line_height']}; direction:rtl; text-align:justify;}}
h1,h2,h3 {{font-family:"{family}", serif; color:var(--navy); text-align:right; line-height:1.45; break-after:avoid;}}
h1 {{font-size:{h1['font_size']}pt; font-weight:{h1['font_weight']}; background:transparent; color:{h1['color']}; padding:0; margin:8mm 0 6mm; display:block; text-align:right;}}
h1.content-chapter-label {{margin:0 0 9mm; text-align:right;}}
h1 .h1-decor {{display:inline-flex; direction:rtl; align-items:stretch; max-width:100%; vertical-align:top;}}
h1 .h1-label {{display:block; min-width:0; direction:rtl; text-align:right; background:{h1['background']}; color:{h1['color']}; padding:1mm 2.5mm; font-size:inherit; font-weight:inherit; line-height:1.55;}}
h1 .h1-wedge {{display:block; flex:0 0 9mm; align-self:stretch; background:linear-gradient(to top right, {h1['triangle_color']} 50%, transparent 50%);}}
h2 {{font-size:{h2['font_size']}pt; font-weight:{h2['font_weight']}; background:{h2['background']}; color:{h2['color']}; padding:1mm 2.5mm; margin:7mm 0 3mm; display:inline-block; min-width:24mm;}}
h3 {{font-size:{h3['font_size']}pt; font-weight:{h3['font_weight']}; background:{h3['background']}; color:{h3['color']}; padding:0.7mm 2mm; margin:5mm 0 2mm; display:inline-block;}}
p {{margin:0 0 2.5mm; orphans:2; widows:2;}}
img {{max-width:100%; height:auto; display:block; margin:3mm auto;}}
figure.book-figure {{display:block; text-align:center; margin:4mm auto; break-inside:avoid;}}
figure.book-figure img {{margin:0 auto 1.5mm;}}
figcaption,.table-caption {{font-size:0.85em; color:var(--navy); text-align:center; line-height:1.5; margin:2mm auto 3mm;}}
.table-caption {{break-before:avoid;}}
p:has(> img) {{break-inside:avoid; text-align:center;}}
table {{width:100%; border-collapse:collapse; font-size:0.85em; margin:4mm 0;}}
thead {{display:table-header-group; background:var(--navy); color:white;}}
tr {{break-inside:avoid;}} td,th {{border:0.4pt solid #aeb1c0; padding:1.5mm 2mm;}}
pre {{direction:ltr; text-align:left; font-size:9pt; white-space:pre-wrap; overflow-wrap:anywhere; background:#f3f3f7; border-left:3pt solid var(--navy); padding:3mm;}}
code {{font-family:monospace;}}
.pagebreak {{break-before:page;}}
.chapter-opener {{page:chapter-opener; position:relative; width:{cfg['page_width']}mm; height:{cfg['page_height']}mm; background:white;}}
.chapter-card {{position:absolute; top:37%; left:22%; width:34mm; text-align:center; direction:rtl; font-family:"{family}";}}
.chapter-top {{height:10mm; position:relative; display:flex; justify-content:flex-start; direction:ltr;}}
.chapter-number {{background:var(--crimson); width:10mm; height:10mm; font-size:15pt; font-weight:bold; color:white; display:flex; align-items:center; justify-content:center;}}
.corner-triangle {{width:0; height:0; border-bottom:10mm solid #9399b5; border-right:10mm solid transparent;}}
.chapter-label {{min-height:18mm; padding:2mm; color:white; background:var(--navy); font-size:19pt; font-weight:bold; line-height:1.35;}}
.chapter-title {{border:0.4pt solid var(--navy); border-top:none; padding:3mm 1.5mm 4mm; min-height:18mm; font-size:10pt; line-height:1.45; color:var(--navy);}}
.slash {{position:absolute; height:0.5mm; width:13mm; background:var(--muted); transform:rotate(-46deg);}}
.sl1 {{left:7%; top:40%;}} .sl2 {{left:2%; top:60%; width:16mm;}} .sl3 {{left:12%; top:57%; width:10mm;}} .sl4 {{left:49%; top:60%; width:7mm;}}
.book-quote {{position:relative; display:block; width:auto; max-width:100%;
  margin:{cfg['quote_margin_top']}mm {cfg['quote_margin_right']}mm {cfg['quote_margin_bottom']}mm {cfg['quote_margin_left']}mm;
  break-inside:avoid; clear:both;}}
.book-quote .quote-side {{position:absolute; left:-22mm; top:0; width:17mm; direction:rtl; text-align:right; color:var(--quote-meta-color);}}
.book-quote .quote-mark {{display:block; margin:0 0 1.5mm auto; width:6.5mm; height:6.5mm;}}
.book-quote .quote-mark-svg {{display:block; width:100%; height:100%;}}
.book-quote .quote-source {{font-size:{cfg['quote_meta_font_size']}pt; color:{cfg['quote_meta_color']}; line-height:1.75; white-space:pre-line; text-align:right;}}
.book-quote .quote-main {{display:block; min-width:0; direction:rtl; text-align:justify;
  font-size:{cfg['quote_font_size']}pt; line-height:1.7; color:{cfg['quote_color']};}}
.book-quote .quote-main p {{margin:0 0 2mm;}}
.book-quote.bottom-left .quote-side {{top:auto; bottom:0;}}
.book-quote.bottom-left .quote-main {{padding-bottom:3mm;}}
.fn-anchor {{display:inline;}}
.fn-call {{font-size:.7em; color:var(--footnote-color); vertical-align:super; margin-right:.3mm;}}
.fn-note {{float:footnote; footnote-display:block; font-size:{cfg['footnote_font_size']}pt; color:var(--footnote_color); line-height:1.7; text-align:right;}}
.fn-note-no {{font-weight:700; margin-left:1mm;}}
.fn-note::footnote-call {{content:'';}}
.fn-note::footnote-marker {{content:'';}}
.missing-image {{color:#a40000; border:1px dashed #a40000; padding:3mm;}}
'''
    return f'<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><style>{css}</style></head><body>{body}</body></html>'


# ----------------- Deterministic physical-page renderer -----------------
# Chapter and blank/special pages are generated as independently-sized PDF
# pages and composed in order. This avoids phantom pages caused by combining
# `break-before`/`break-after` with named pages inside one flowing layout.
from .page_art import decorate as draw_page_art

# Inserted by render_markdown() as distinct structural blocks.
_SPECIAL_PATTERN = re.compile(
    r'<section class="(?:chapter-opener|decor-page)".*?</section>|'
    r'<div class="pagebreak" aria-hidden="true"></div>', re.S)


def split_book_into_pages(body: str):
    chunks = []
    cursor = 0
    for marker in _SPECIAL_PATTERN.finditer(body):
        content = body[cursor:marker.start()].strip()
        if content:
            chunks.append(('flow', content))
        token = marker.group(0)
        if token.startswith('<section class="chapter-opener"'):
            chunks.append(('chapter', token))
        elif token.startswith('<section class="decor-page"'):
            chunks.append(('blank', ''))
        # A PAGEBREAK separates flow chunks, it is not content or an extra page.
        cursor = marker.end()
    tail = body[cursor:].strip()
    if tail:
        chunks.append(('flow', tail))
    return chunks


def _html_shell(cfg: dict) -> str:
    return build_html('', cfg)


def _move_cached_background_with_box(box, dx: float) -> None:
    """Move WeasyPrint's precomputed background painting coordinates.

    Box.translate() moves text and layout coordinates, but WeasyPrint 66-68
    caches background painting rectangles *before* rendering the PDF. In
    particular, the grey quote-mark square would otherwise stay on the left
    even though the marginal note and its quote glyph move to the right.
    """
    # AbsolutePlaceholder exposes layout via ._box, but the cached paint
    # geometry belongs to the actual layout box and its descendants.
    actual = getattr(box, '_box', box)
    for child in actual.descendants():
        background = getattr(child, 'background', None)
        if background is None:
            continue
        layers = []
        for layer in background.layers:
            area = layer.painting_area
            if isinstance(area, tuple):
                area = (area[0] + dx, area[1], *area[2:])
            positioning = layer.positioning_area
            if isinstance(positioning, tuple):
                positioning = (positioning[0] + dx, positioning[1], *positioning[2:])
            clips = [
                (clip[0] + dx, clip[1], *clip[2:])
                for clip in layer.clipped_boxes
            ]
            layers.append(layer._replace(
                painting_area=area,
                positioning_area=positioning,
                clipped_boxes=clips,
            ))
        child.background = background._replace(layers=layers)


def place_quote_notes_in_outer_margin(document, first_folio: int) -> None:
    """Put quotation marginalia in the outside margin of each physical folio.

    WeasyPrint initially positions the note on the left (odd folio default).
    The quote is break-inside:avoid, and its note is absolute-positioned: it
    does not reserve flow width. Once pages have been laid out we can translate
    only the note's positioned box on even folios. This does not reflow text,
    move the quote body, or change pagination/footnotes.

    The page boxes are available in the supported WeasyPrint 66–68 range.
    One renderer fragment can occupy multiple sheets, so the parity must be
    decided for each physical page, not for each fragment.
    """
    css_px_per_mm = 96 / 25.4
    for relative_index, rendered_page in enumerate(document.pages):
        if (first_folio + relative_index) % 2:
            continue  # odd folio: keep the original left-margin placement
        page_box = rendered_page._page_box
        for quote in page_box.descendants():
            if getattr(quote, 'element_tag', None) != 'aside':
                continue
            element = getattr(quote, 'element', None)
            if element is None or 'book-quote' not in element.get('class', '').split():
                continue
            for note in quote.descendants():
                note_element = getattr(note, 'element', None)
                if note_element is None or 'quote-side' not in note_element.get('class', '').split():
                    continue
                # Existing CSS on odd pages uses left:-22mm,width:17mm.
                # The equivalent mirrored position on an even page is
                # right:-22mm => left = content-right + (22-17)mm.
                wanted_left = quote.position_x + quote.width + 5 * css_px_per_mm
                shift = wanted_left - note.position_x
                note.translate(dx=shift)
                # Without this correction only the glyph and the note text
                # move. The cached grey rectangle stays in the LEFT margin.
                _move_cached_background_with_box(note, shift)
                break


def render_pdf():
    # Preserve the historic public renderer entry point for callers that still
    # invoke it directly. V5 projects must be assembled from their MD parts.
    manifest=PROJECT/'bookstudio.project.json'
    if manifest.exists():
        try:
            import json as _json
            if _json.loads(manifest.read_text(encoding='utf-8')).get('version')==2:
                from .book_compose import compose_book
                return compose_book()['pages']
        except (OSError, ValueError):
            pass
    OUTPUT.mkdir(exist_ok=True)
    source = MARKDOWN.read_text(encoding='utf-8') if MARKDOWN.exists() else ''
    cfg = load_settings()
    # Validate at least the required regular and bold font files early, before
    # generating partial output. Embedding works without Windows font install.
    font_path(400, family=cfg['font_family'])
    font_path(700, family=cfg['font_family'])
    body = render_markdown(source, cfg)
    chunks = split_book_into_pages(body)
    if not chunks:
        chunks = [('blank', '')]
    shell = _html_shell(cfg)
    if '<body></body>' not in shell:
        raise RuntimeError('HTML shell is invalid: body injection point missing')

    merged = fitz.open()
    kinds = []
    first_visible_index = None
    try:
        for kind, part in chunks:
            if kind == 'blank':
                merged.new_page(width=mm(cfg['page_width']), height=mm(cfg['page_height']))
                kinds.append('blank')
                continue
            fragment_shell = shell
            if kind == 'flow' and first_visible_index is None:
                first_visible_index = len(merged)
            # Each WeasyPrint fragment considers its first sheet a right/odd
            # page. Swap :left/:right when it is bound into an even folio.
            if kind == 'flow' and (int(cfg['page_number_start']) + len(merged) - first_visible_index) % 2 == 0:
                fragment_shell = (fragment_shell.replace('@page :left', '@page :TEMP')
                                               .replace('@page :right', '@page :left')
                                               .replace('@page :TEMP', '@page :right'))
            full_html = fragment_shell.replace('<body></body>', '<body>' + part + '</body>')
            intermediate = HTML(string=full_html, base_url=PROJECT.as_uri() + '/')
            laid_out = intermediate.render()
            if kind == 'flow':
                first_folio_on_fragment = int(cfg['page_number_start']) + len(merged) - first_visible_index
                place_quote_notes_in_outer_margin(laid_out, first_folio_on_fragment)
            pdfbytes = laid_out.write_pdf()
            with fitz.open(stream=pdfbytes, filetype='pdf') as frag:
                if kind == 'chapter' and len(frag) != 1:
                    raise ValueError('صفحه اختصاصی فصل به بیش از یک صفحه شکسته شد. اندازه عنوان را کاهش دهید.')
                merged.insert_pdf(frag)
                kinds.extend([kind] * len(frag))
        draw_page_art(merged, cfg, kinds)
        temp = PDF.with_suffix('.tmp.pdf')
        merged.save(temp, garbage=3, deflate=True)
        temp.replace(PDF)
        return len(merged)
    finally:
        merged.close()


def page_png(page_no: int, zoom=1.25):
    with fitz.open(PDF) as doc:
        if page_no < 1 or page_no > len(doc):
            raise ValueError('Invalid page')
        return doc[page_no-1].get_pixmap(matrix=fitz.Matrix(zoom,zoom),alpha=False).tobytes('png')


if __name__ == '__main__':
    print('Pages:', render_pdf())
