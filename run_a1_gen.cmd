@echo off
setlocal

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

cd /d "%PROJECT_DIR%"

if not exist "%PROJECT_DIR%\.venv\Scripts\activate.bat" (
    echo [HATA] Virtual environment bulunamadi:
    echo %PROJECT_DIR%\.venv\Scripts\activate.bat
    pause
    exit /b 1
)

call "%PROJECT_DIR%\.venv\Scripts\activate.bat"
set "PYTHONPATH=%PROJECT_DIR%\src"

echo.
echo Ortam hazir.
echo Proje klasoru: %PROJECT_DIR%
echo PYTHONPATH=%PYTHONPATH%
echo.
echo Ornek komut:
echo python -m ai1_gen.cli --config configs/default.yaml --pages 100 --workers 4
echo.

cmd /k "cd /d \"%PROJECT_DIR%\" && call \"%PROJECT_DIR%\.venv\Scripts\activate.bat\" && set PYTHONPATH=%PROJECT_DIR%\src"