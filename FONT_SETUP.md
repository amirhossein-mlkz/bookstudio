# فونت‌های لازم

فایل‌های واقعی فونت باید در پوشه `bookstudio/fonts` کپی شوند.

برای Vazirmatn حداقل:
- `Vazirmatn-Regular.ttf`
- `Vazirmatn-Bold.ttf`

در صورت نیاز به وزن‌های بیشتر، ۹ وزن را با نام‌های `Vazirmatn-Thin.ttf` تا `Vazirmatn-Black.ttf` داخل همان پوشه اضافه کنید.

برای IR Nazanin:
- `IRNazanin.ttf`
- `IRNazaninBold.ttf`
- `IRNazaninIranic.ttf`

اگر فایل‌های فونت از قبل در یک پوشه هستند، از ریشه پروژه:

```powershell
python prepare_fonts.py "C:\\Path\\To\\Your\\FontFolder"
```

فایل‌های فونت واقعی داخل این ZIP **وجود ندارند**. به‌جای نصب روی ویندوز، خود برنامه فایل‌های موجود در این پوشه را به موتور PDF معرفی می‌کند.
