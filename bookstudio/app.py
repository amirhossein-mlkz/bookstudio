"""Book Studio Lite: local Flask app. Not intended for public Internet hosting."""
from __future__ import annotations
# Supports both `python -m bookstudio.app` and accidental direct execution.
# Relative imports require a package context; initialize it before importing.
if __name__ == '__main__' and not __package__:
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
    __package__ = 'bookstudio'

import io
import re
import json
import threading
import webbrowser
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_file, abort
from .paths import resource_path, fonts_available, EMBEDDED_FONT_FILES
from .project_storage import active_folder, open_folder, save_folder, restore_starter_project, native_dialog, clear_active, _write_atomic
from .renderer import PROJECT, MARKDOWN, PDF, SETTINGS, DEFAULTS, load_settings, save_settings, page_png
from .book_project import new_section, load_workspace, save_workspace, validate_sections, validate_front
from .book_compose import compose_book, SECTION_OUTPUT

app = Flask(__name__, template_folder=str(resource_path("templates")), static_folder=str(resource_path("static")))
app.json.ensure_ascii = False
MAX_MARKDOWN_BYTES = 3 * 1024 * 1024
render_lock = threading.Lock()
# Each preview belongs to exactly one successfully generated PDF. A saved or
# reopened project invalidates it; an older browser tab cannot download a
# different output while showing a previous preview.
render_snapshot = {'revision': None, 'sha256': None, 'sections': {}}


def invalidate_render_snapshot():
    render_snapshot['revision'] = None
    render_snapshot['sha256'] = None
    render_snapshot['sections'] = {}


def snapshot_bytes(path: Path):
    """Return *exactly* the bytes approved during preview generation."""
    revision = render_snapshot['revision']
    if not revision or request.args.get('v') != revision:
        abort(409, description='پیش‌نمایش قدیمی است؛ دوباره پیش‌نمایش را بسازید.')
    try:
        data = path.read_bytes()
    except OSError:
        abort(409, description='خروجی فعلی موجود نیست؛ دوباره پیش‌نمایش را بسازید.')
    known_hash = (render_snapshot['sha256'] if path == PDF
                  else render_snapshot['sections'].get(path.name))
    if not known_hash or hashlib.sha256(data).hexdigest() != known_hash:
        abort(409, description='فایل PDF بعد از پیش‌نمایش تغییر کرده است؛ دوباره پیش‌نمایش را بسازید.')
    return data


def attachment_name(prefix: str) -> str:
    # Local time with microseconds ensures repeated downloads have unique names.
    stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')
    return f'{prefix}_{stamp}.pdf'


def pdf_attachment(data: bytes, filename: str):
    response = send_file(io.BytesIO(data), mimetype='application/pdf',
                         as_attachment=True, download_name=filename,
                         conditional=False, etag=False, max_age=0)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/assets/fonts/<name>')
def embedded_font(name):
    if name not in EMBEDDED_FONT_FILES:
        abort(404)
    f = resource_path('fonts') / name
    if not f.is_file():
        abort(404)
    return send_file(f, mimetype='font/ttf', max_age=86400)

@app.get('/api/fonts/status')
def embedded_font_status():
    return jsonify(ok=fonts_available())

@app.get('/api/project')
def get_project():
    sections,frontmatter=load_workspace(PROJECT)
    return jsonify({'sections':sections,'frontmatter':frontmatter,'settings':load_settings(), 'has_pdf':PDF.exists(), 'project_folder':str(active_folder()) if active_folder() else None})

@app.post('/api/project')
def save_project():
    if render_lock.locked():return jsonify(error='رندر در حال اجراست.'),409
    data = request.get_json(silent=True) or {}
    try:
        sections=validate_sections(data.get('sections'))
        frontmatter=validate_front(data.get('frontmatter'))
        settings=save_settings(data.get('settings') if isinstance(data.get('settings'),dict) else {})
        save_workspace(PROJECT,sections,frontmatter)
        invalidate_render_snapshot()
        PDF.unlink(missing_ok=True)
        for old in SECTION_OUTPUT.glob('*.pdf'):old.unlink()
        if active_folder():save_folder(active_folder(),PROJECT)
        return jsonify(ok=True,settings=settings,project_folder=str(active_folder()) if active_folder() else None)
    except (ValueError,OSError,UnicodeError) as exc:
        app.logger.exception('Saving project failed')
        return jsonify(error='ذخیره پروژه ناموفق بود: '+str(exc)),400

@app.post('/api/project/new')
def new_project():
    if render_lock.locked():return jsonify(error='رندر در حال اجراست.'),409
    try:
        cfg=save_settings(DEFAULTS)
        image_dir=PROJECT/'images'
        if image_dir.exists():
            for old in image_dir.iterdir():
                if old.is_file():old.unlink()
        sections,frontmatter=save_workspace(PROJECT,[new_section('فصل اول')],{})
        invalidate_render_snapshot()
        PDF.unlink(missing_ok=True)
        for old in SECTION_OUTPUT.glob('*.pdf'):old.unlink()
        clear_active()
        return jsonify(ok=True,sections=sections,frontmatter=frontmatter,settings=cfg,project_folder=None,has_pdf=False)
    except (OSError,ValueError) as exc:
        return jsonify(error=str(exc)),500

@app.post('/api/project/save-as')
def project_save_as():
    folder = native_dialog('save')
    if folder is None:
        return jsonify(cancelled=True, project_folder=str(active_folder()) if active_folder() else None)
    try:
        selected = save_folder(folder, PROJECT)
        return jsonify(ok=True, project_folder=selected)
    except (OSError, ValueError) as exc:
        return jsonify(error=str(exc)), 400

@app.post('/api/project/open')
def project_open():
    if render_lock.locked():
        return jsonify(error='ابتدا منتظر پایان رندر بمانید.'), 409
    mode = (request.get_json(silent=True) or {}).get('mode', 'file')
    if mode not in ('file', 'folder'):
        return jsonify(error='روش انتخاب پروژه نامعتبر است.'), 400
    selection = native_dialog('folder' if mode == 'folder' else 'open')
    if selection is None:
        return jsonify(cancelled=True)
    if mode == 'file' and selection.name != 'bookstudio.project.json':
        return jsonify(error='فایل bookstudio.project.json را انتخاب کنید.'), 400
    folder = selection if mode == 'folder' else selection.parent
    try:
        data = open_folder(folder, PROJECT, PDF)
        invalidate_render_snapshot()
        return jsonify(ok=True, **data)
    except (OSError, ValueError, UnicodeError) as exc:
        return jsonify(error='باز کردن پروژه موفق نبود: '+str(exc)), 400

@app.post('/api/render')
def render():
    if not render_lock.acquire(blocking=False):
        return jsonify(error='عملیات رندر دیگری در حال اجرا است.'),409
    try:
        invalidate_render_snapshot()  # A failed render must not expose the old PDF.
        result=compose_book()
        pdf_bytes=PDF.read_bytes()
        render_snapshot['sha256'] = hashlib.sha256(pdf_bytes).hexdigest()
        render_snapshot['sections'] = {
            entry['id'] + '.pdf': hashlib.sha256(
                (SECTION_OUTPUT / (entry['id'] + '.pdf')).read_bytes()
            ).hexdigest() for entry in result['sections']
        }
        render_snapshot['revision'] = secrets.token_urlsafe(18)
        return jsonify(ok=True,revision=render_snapshot['revision'],**result)
    except Exception as exc:
        app.logger.exception('Rendering failed')
        return jsonify(error='خطا در رندر: '+str(exc)[:250]),500
    finally:
        render_lock.release()

@app.get('/api/page/<int:number>.png')
def preview_page(number):
    if not render_snapshot['revision'] or request.args.get('v') != render_snapshot['revision']:
        abort(409, description='پیش‌نمایش قدیمی است؛ دوباره آن را بسازید.')
    if not PDF.exists(): abort(404)
    try: image=page_png(number,zoom=1.45)
    except ValueError: abort(404)
    response=send_file(io.BytesIO(image),mimetype='image/png')
    response.headers['Cache-Control']='no-store, no-cache, must-revalidate, private'
    return response

@app.get('/api/pdf')
def download_pdf():
    if render_lock.locked(): abort(409, description='رندر در حال انجام است.')
    data = snapshot_bytes(PDF)
    return pdf_attachment(data, attachment_name('BookStudio'))

@app.get('/api/pdf/section/<section_id>')
def download_section(section_id):
    if not re.fullmatch(r'[a-f0-9]{12}',section_id):abort(404)
    if render_lock.locked():abort(409, description='رندر در حال انجام است.')
    file=SECTION_OUTPUT/(section_id+'.pdf')
    data=snapshot_bytes(file)
    from .book_project import load_workspace
    sections,_=load_workspace(PROJECT)
    matching=next((s for s in sections if s['id']==section_id),None)
    if matching is None:abort(404)
    name=re.sub(r'[\\/:*?"<>|]+','-',matching['title']).strip()[:90] or 'section'
    return pdf_attachment(data,attachment_name(name))

@app.post('/api/upload-image')
def upload_image():
    f=request.files.get('file')
    if not f: return jsonify(error='فایلی انتخاب نشده است.'),400
    name=Path(f.filename or '').name
    if not re.fullmatch(r'[\w.\- ]+\.(png|jpg|jpeg|webp|svg)',name,re.I):
        return jsonify(error='نام یا نوع تصویر مجاز نیست.'),400
    content=f.read(8*1024*1024+1)
    if len(content)>8*1024*1024:return jsonify(error='حجم فایل زیاد است.'),400
    # SVG deliberately forbidden: can embed external URLs/scripts.
    if name.lower().endswith('.svg'): return jsonify(error='SVG در این نسخه پشتیبانی نمی‌شود.'),400
    from PIL import Image
    try:
        im=Image.open(io.BytesIO(content));im.verify()
    except Exception:return jsonify(error='فایل تصویر معتبر نیست.'),400
    target=PROJECT/'images'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(content)
    return jsonify(path='images/'+name,markdown=f'![توضیح تصویر]({"images/"+name})')

def main():
    PROJECT.mkdir(exist_ok=True)
    restore_starter_project(resource_path('starter_project'), PROJECT, PDF)
    threading.Timer(1.2, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)


if __name__ == '__main__':
    main()

