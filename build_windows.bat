@echo off
setlocal
cd /d "%~dp0"
if not exist "bookstudio\fonts\Vazirmatn-Regular.ttf" (echo Missing bundled Vazirmatn-Regular.ttf & exit /b 1)
if not exist "bookstudio\fonts\Vazirmatn-Bold.ttf" (echo Missing bundled Vazirmatn-Bold.ttf & exit /b 1)
py -m PyInstaller --noconfirm --clean --onedir --name BookStudioLite ^
 --add-data "bookstudio\templates;bookstudio\templates" ^
 --add-data "bookstudio\static;bookstudio\static" ^
 --add-data "bookstudio\fonts;bookstudio\fonts" ^
 --add-data "bookstudio\starter_project;bookstudio\starter_project" run.py
if errorlevel 1 exit /b 1
mkdir dist\BookStudioLite\_internal\bookstudio\project 2>nul
mkdir dist\BookStudioLite\_internal\bookstudio\output 2>nul
 echo Output: dist\BookStudioLite
