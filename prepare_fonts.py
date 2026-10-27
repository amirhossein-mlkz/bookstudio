"""Validate and copy Vazirmatn and IRNazanin fonts from a local folder.

Usage: python prepare_fonts.py "C:\\path\\to\\downloaded-fonts"
Only actual TrueType/OpenType files are accepted. No network is used.
"""
from pathlib import Path
import shutil
import sys
from PIL import ImageFont
from bookstudio.paths import FONT_FAMILIES


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python prepare_fonts.py <folder-containing-font-files>')
    source=Path(sys.argv[1]).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f'Folder not found: {source}')
    target=Path(__file__).resolve().parent / 'bookstudio' / 'fonts'
    target.mkdir(exist_ok=True)
    filenames=set()
    for mapping in FONT_FAMILIES.values():
        filenames.update(mapping.values())
    copied=[]
    for filename in sorted(filenames):
        found=next((f for f in source.rglob(filename) if f.is_file()),None)
        if found is None:
            continue
        try:
            ImageFont.truetype(str(found), 20)
        except OSError as exc:
            raise SystemExit(f'Invalid font {filename}: {exc}') from exc
        destination=target/filename
        if found != destination:
            shutil.copy2(found,destination)
        copied.append(filename)
    if not copied:
        raise SystemExit('No matching font filenames found. See FONT_SETUP.md.')
    print('Copied and validated:',', '.join(copied))
    for family, weight in [('Vazirmatn',400),('Vazirmatn',700),('IRNazanin',400),('IRNazanin',700)]:
        required=FONT_FAMILIES[family][weight]
        if not (target/required).is_file():
            print('Warning: missing', required)
    for candidate in ('OFL.txt','OFL-1.1.txt','LICENSE.txt','LICENSE'):
        found=next((f for f in source.rglob(candidate) if f.is_file()),None)
        if found:
            shutil.copy2(found,target / f'{found.parent.name}-{found.name}')


if __name__=='__main__':
    main()
