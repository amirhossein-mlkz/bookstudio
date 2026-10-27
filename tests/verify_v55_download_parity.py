"""Standalone route-level regression without installing Flask in the build container.

Stubs only HTTP plumbing; tested endpoint logic and PDF bytes are the actual app.py.
"""
from __future__ import annotations
import hashlib
import io
import logging
import sys
import types
from pathlib import Path

import pymupdf as fitz

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

class HTTPAbort(Exception):
    def __init__(self,code,description=None):
        self.code=code
        super().__init__(description)

class Response:
    def __init__(self,src,**kw):
        self.data=src.getvalue() if isinstance(src,io.BytesIO) else Path(src).read_bytes()
        self.headers={}
        self.meta=kw

def fake_flask():
    module=types.ModuleType('flask')
    class Flask:
        def __init__(self,*args,**kwargs):
            self.json=types.SimpleNamespace(ensure_ascii=True)
            self.logger=logging.getLogger('test')
        def get(self,*args,**kwargs):return lambda f:f
        def post(self,*args,**kwargs):return lambda f:f
    module.Flask=Flask
    module.jsonify=lambda **kw:kw
    module.render_template=lambda *a,**k:None
    module.request=types.SimpleNamespace(args={})
    module.send_file=lambda source,**kwargs:Response(source,**kwargs)
    module.abort=lambda code,description=None:(_ for _ in ()).throw(HTTPAbort(code,description))
    sys.modules['flask']=module

fake_flask()
from bookstudio import app as A
from bookstudio.book_compose import SECTION_OUTPUT
from bookstudio.renderer import PDF

def build_fake_book():
    PDF.parent.mkdir(parents=True,exist_ok=True)
    SECTION_OUTPUT.mkdir(parents=True,exist_ok=True)
    doc=fitz.open()
    for label in ('PREVIEW FIRST PAGE','PREVIEW SECOND PAGE'):
        p=doc.new_page()
        p.insert_text((70,80),label,fontsize=20)
    doc.save(PDF)
    doc.close()
    sid='123456789abc'
    part=SECTION_OUTPUT/(sid+'.pdf')
    with fitz.open(PDF) as full:
        cut=fitz.open();cut.insert_pdf(full,from_page=0,to_page=0)
        cut.save(part);cut.close()
    return sid,part

def run():
    sid,part=build_fake_book()
    A.compose_book=lambda: {'pages':2,'sections':[{'id':sid}], 'toc_entries':0}
    A.load_workspace=lambda project:([{'id':sid,'title':'تست بخش'}],{})
    from bookstudio import book_project
    book_project.load_workspace=A.load_workspace
    first=A.render()
    assert first['ok'] and first['pages']==2
    version=first['revision']
    A.request.args={'v':version}
    preview=A.preview_page(1)
    assert preview.data.startswith(b'\x89PNG\r\n\x1a\n')
    downloaded=A.download_pdf()
    assert downloaded.data==PDF.read_bytes()
    with fitz.open(stream=downloaded.data,filetype='pdf') as identical_book:
        assert preview.data == identical_book[0].get_pixmap(
            matrix=fitz.Matrix(1.45,1.45),alpha=False).tobytes('png')
    assert 'no-store' in downloaded.headers['Cache-Control']
    assert '202' in downloaded.meta['download_name'] and downloaded.meta['download_name'].endswith('.pdf')
    with fitz.open(stream=downloaded.data,filetype='pdf') as book:
        assert len(book)==2 and 'PREVIEW FIRST PAGE' in book[0].get_text()
    downloaded_again=A.download_pdf()
    assert downloaded_again.meta['download_name'] != downloaded.meta['download_name']
    section=A.download_section(sid)
    assert section.data == part.read_bytes()
    assert section.meta['download_name'] != downloaded.meta['download_name']
    assert section.meta['download_name'].endswith('.pdf')
    with open(part,'ab') as f:f.write(b'\n%altered section\n')
    try:A.download_section(sid);raise AssertionError('modified section PDF should fail')
    except HTTPAbort as e:assert e.code==409
    A.request.args={'v':'old-preview'}
    for f in [A.download_pdf, lambda:A.download_section(sid), lambda:A.preview_page(1)]:
        try:f();raise AssertionError('stale preview should fail')
        except HTTPAbort as e:assert e.code==409
    A.request.args={'v':version}
    with open(PDF,'ab') as f:f.write(b'\n%edited outside preview\n')
    try:A.download_pdf();raise AssertionError('modified PDF should fail')
    except HTTPAbort as e:assert e.code==409
    A.invalidate_render_snapshot()
    try:A.download_pdf();raise AssertionError('invalidated preview should fail')
    except HTTPAbort as e:assert e.code==409
    print('PASS: same PDF bytes as preview; timestamp uniqueness; 409 on stale or changed PDF; section export; no-store')

if __name__=='__main__':run()
