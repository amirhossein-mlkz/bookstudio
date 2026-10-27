"""Confirm every launch restores the starter and never opens recent projects."""
from __future__ import annotations
import os, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bookstudio import project_storage as ps


def verify():
    old_home = os.environ.get('LOCALAPPDATA')
    old_active = ps.active_folder()
    try:
        with tempfile.TemporaryDirectory(prefix='bookstudio-startup-') as dirname:
            base = Path(dirname)
            os.environ['LOCALAPPDATA'] = str(base / 'LocalAppData')
            starter = Path(__file__).resolve().parents[1] / 'bookstudio' / 'starter_project'
            workspace = base / 'workspace'
            workspace.mkdir()
            (workspace / 'book.md').write_text('UNSAVED NOTE',encoding='utf-8')
            (workspace / 'settings.json').write_text('{}',encoding='utf-8')
            images = workspace / 'images'
            images.mkdir()
            (images / 'unsaved.jpg').write_bytes(b'test scratch')
            previous = base / 'last-project'
            previous.mkdir()
            (previous / 'book.md').write_text('PERSISTED PROJECT', encoding='utf-8')
            pdf = base / 'preview.pdf'
            pdf.write_bytes(b'test older preview')
            ps._set_active(previous)
            ps.restore_starter_project(starter, workspace, pdf)
            assert ps.active_folder() is None
            assert not pdf.exists()
            assert (workspace / 'book.md').read_bytes() == (starter / 'book.md').read_bytes()
            assert (previous / 'book.md').read_text(encoding='utf-8') == 'PERSISTED PROJECT'
            recovered = list((ps.state_file().parent / 'recovery').glob('*/book.md'))
            assert recovered and recovered[0].read_text(encoding='utf-8') == 'UNSAVED NOTE'
            # Pretend another project was edited and save, then restart.
            (workspace / 'book.md').write_text('CHANGED AFTER STARTUP', encoding='utf-8')
            ps._set_active(previous)
            ps.restore_starter_project(starter, workspace, pdf)
            assert ps.active_folder() is None
            assert (workspace / 'book.md').read_bytes() == (starter / 'book.md').read_bytes()
            assert len(list((ps.state_file().parent / 'recovery').glob('*/book.md'))) >= 2
            print('PASS: fixed starter on every launch; external folders safe; scratch backup; preview cleared')
    finally:
        if old_home is None:
            os.environ.pop('LOCALAPPDATA', None)
        else:
            os.environ['LOCALAPPDATA'] = old_home
        ps._active = old_active

if __name__ == '__main__':
    verify()
