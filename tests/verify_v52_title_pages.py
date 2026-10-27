"""v5.2: title-banner, section-title-page switch and style defaults.

Run from the application root: python tests/verify_v52_title_pages.py
No system fonts required. For PDF integration test, install your own fonts,
then run tests/verify_v5_pdf.py and toggle sections in the UI.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from bookstudio.book_project import load_workspace, save_workspace, new_section
from bookstudio.renderer import DEFAULTS, validate_settings, render_markdown, build_html


def run():
    root = Path(__file__).resolve().parents[1]
    settings = validate_settings({})
    assert settings['heading_styles']['h2']['background'].lower() == '#575a84'
    assert settings['heading_styles']['h2']['color'].lower() == '#ffffff'
    assert settings['heading_styles']['h3']['background'].lower() == '#d1d1e0'
    assert settings['heading_styles']['h3']['color'].lower() == '#575a84'
    body = render_markdown('# فصل اول\n\n## بخش\n\n### زیربخش',settings)
    assert 'h1-wedge' in body and '<h2>' in body and '<h3>' in body
    css = build_html('',settings)
    assert '.h1-wedge' in css
    sections,front = load_workspace(root/'bookstudio/starter_project')
    assert all(s['include_title_page'] for s in sections)
    with TemporaryDirectory() as temp:
        sections[2]['include_title_page'] = False
        save_workspace(Path(temp), sections, front)
        reloaded,_ = load_workspace(Path(temp))
        assert reloaded[2]['include_title_page'] is False
        assert reloaded[1]['include_title_page'] is True
    assert new_section()['include_title_page'] is True
    html = (root/'bookstudio/templates/index.html').read_text(encoding='utf-8')
    js = (root/'bookstudio/static/app.js').read_text(encoding='utf-8')
    assert 'sectionTitlePage' in html and "$('sectionTitlePage')" in js
    print('PASS: heading design, colors, per-section checkbox persistence')

if __name__ == '__main__':
    run()
