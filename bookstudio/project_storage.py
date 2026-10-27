"""Local Book Studio project folders; supports reading legacy one-file projects."""
from __future__ import annotations
import json
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

from .book_project import load_workspace, save_workspace

MANIFEST='bookstudio.project.json'
LOCK=threading.RLock()
_active:Path|None=None

def state_file():
    base=Path(os.environ.get('LOCALAPPDATA') or (Path.home()/'.bookstudio-lite'))/'BookStudioLite'
    base.mkdir(parents=True,exist_ok=True)
    return base/'recent_project.json'

def active_folder():return _active

def _write_atomic(path:Path,data:bytes):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.bookstudio-tmp')
    temp.write_bytes(data);temp.replace(path)

def _set_active(folder):
    global _active
    _active=folder
    _write_atomic(state_file(),json.dumps({'last_project':str(folder) if folder else None},ensure_ascii=False).encode('utf-8'))

def clear_active():
    with LOCK:_set_active(None)

def _safe_images(folder):
    images=[];src=folder/'images'
    if not src.is_dir():return images
    for file in src.iterdir():
        if file.is_symlink() or not file.is_file() or file.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:continue
        if file.stat().st_size>8*1024*1024:raise ValueError('حجم تصویر بیش از حد مجاز است.')
        images.append(file)
    if len(images)>250:raise ValueError('تعداد تصاویر بیش از حد مجاز است.')
    return images

def validate_folder(folder:Path):
    if not folder.is_dir():raise ValueError('پوشه وجود ندارد.')
    if not (folder/MANIFEST).is_file():raise ValueError('فایل مشخصات پروژه وجود ندارد.')
    manifest=json.loads((folder/MANIFEST).read_text(encoding='utf-8'))
    if manifest.get('application')!='bookstudio-lite' or manifest.get('version') not in (1,2):
        raise ValueError('قالب پروژه پشتیبانی نمی‌شود.')
    parts,front=load_workspace(folder)
    from .renderer import validate_settings
    raw=json.loads((folder/'settings.json').read_text(encoding='utf-8')) if (folder/'settings.json').exists() else {}
    cfg=validate_settings(raw)
    return {'sections':parts,'frontmatter':front,'settings':cfg,'images':_safe_images(folder)}

def _sync_images(source:Path,dest:Path):
    dest.mkdir(parents=True,exist_ok=True)
    files=_safe_images(source)
    for image in files:
        _write_atomic(dest/image.name,image.read_bytes())
    names={file.name for file in files}
    for old in dest.iterdir():
        if old.is_file() and old.name not in names:old.unlink()

def open_folder(folder:Path,workspace:Path,pdf:Path):
    with LOCK:
        folder=folder.expanduser().resolve()
        if folder==workspace.resolve() or workspace.resolve() in folder.parents:raise ValueError('پوشه داخلی برنامه انتخاب نشود.')
        obj=validate_folder(folder)
        workspace.mkdir(parents=True,exist_ok=True)
        _sync_images(folder,workspace/'images')
        save_workspace(workspace,obj['sections'],obj['frontmatter'])
        _write_atomic(workspace/'settings.json',json.dumps(obj['settings'],ensure_ascii=False,indent=2).encode('utf-8'))
        pdf.unlink(missing_ok=True)
        _set_active(folder)
        return {'sections':obj['sections'],'frontmatter':obj['frontmatter'],'settings':obj['settings'],'folder':str(folder)}

def save_folder(folder:Path,workspace:Path):
    with LOCK:
        folder=folder.expanduser().resolve()
        if folder==workspace.resolve() or workspace.resolve() in folder.parents:raise ValueError('محل ذخیره داخلی نرم‌افزار مجاز نیست.')
        folder.mkdir(parents=True,exist_ok=True)
        if (folder/MANIFEST).exists():validate_folder(folder)
        elif any(folder.iterdir()):raise ValueError('برای جلوگیری از بازنویسی فایل‌ها، پوشه خالی انتخاب کنید.')
        parts,front=load_workspace(workspace)
        # Write contents before manifest; an incomplete copy does not validate.
        save_workspace(folder,parts,front)
        _write_atomic(folder/'settings.json',(workspace/'settings.json').read_bytes())
        _sync_images(workspace,folder/'images')
        _set_active(folder)
        return str(folder)

def native_dialog(kind):
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    try:
        initial=str(_active) if _active else str(Path.home()/'Documents')
        if kind=='save':r=filedialog.askdirectory(parent=root,title='انتخاب پوشه پروژه',initialdir=initial,mustexist=True)
        elif kind=='open':r=filedialog.askopenfilename(parent=root,title='باز کردن پروژه',initialdir=initial,filetypes=[('BookStudio','bookstudio.project.json'),('JSON','*.json')])
        elif kind=='folder':r=filedialog.askdirectory(parent=root,title='باز کردن پوشه پروژه',initialdir=initial,mustexist=True)
        else:raise ValueError('Unknown dialog')
        return Path(r) if r else None
    finally:root.destroy()

def restore_starter_project(starter:Path,workspace:Path,pdf:Path):
    """Always load the packaged multi-part demo; preserve old unsaved workspace."""
    with LOCK:
        parts,front=load_workspace(starter)
        workspace.mkdir(parents=True,exist_ok=True)
        current=workspace/'bookstudio.project.json'
        demo=starter/'bookstudio.project.json'
        def tree_signature(path):
            out={}
            for p in path.rglob('*'):
                if p.is_file() and not p.name.endswith(('.pdf','.tmp')):
                    if p.relative_to(path).parts[0] in ('chapters','images') or p.name in ('book.md','settings.json',MANIFEST):
                        out[str(p.relative_to(path))]=p.read_bytes()
            return out
        if (workspace/'book.md').exists() or current.exists():
            if tree_signature(workspace)!=tree_signature(starter):
                rec=state_file().parent/'recovery'/datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
                rec.mkdir(parents=True,exist_ok=True)
                for file in workspace.iterdir():
                    if file.name in ('settings.json','book.md',MANIFEST) and file.is_file():shutil.copy2(file,rec/file.name)
                for name in ('chapters','images'):
                    if (workspace/name).is_dir():shutil.copytree(workspace/name,rec/name)
                all_rec=sorted((p for p in rec.parent.iterdir() if p.is_dir()),reverse=True)
                for p in all_rec[5:]:shutil.rmtree(p)
        save_workspace(workspace,parts,front)
        (workspace/'book.md').unlink(missing_ok=True)
        if (starter/'settings.json').is_file():
            _write_atomic(workspace/'settings.json',(starter/'settings.json').read_bytes())
        _sync_images(starter,workspace/'images')
        pdf.unlink(missing_ok=True)
        _set_active(None)
