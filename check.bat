@echo off
title AI1_GEN - Quality Gate
set PYTHONPATH=%CD%\src

echo ======================================================
echo          AI1_GEN OTOMATIK KONTROL SISTEMI
echo ======================================================

echo [1/4] HIZLI UNIT TESTLER (Augment, Validators, Config)...
pytest tests/unit -m fast
if %errorlevel% neq 0 goto :error

echo [2/4] ENTEGRASYON TESTLERI (Pipeline, Meta Sync)...
pytest tests/integration
if %errorlevel% neq 0 goto :error

echo [3/4] CLI VE E2E KONTROLU (Gercek CLI Akisi)...
pytest tests/e2e/test_cli.py
if %errorlevel% neq 0 goto :error

echo [4/4] DAGILIM ANALIZI (1000 Orneklem ile Istatistik Kontrol)...
pytest tests/integration/test_distribution.py
if %errorlevel% neq 0 goto :error

echo ======================================================
echo    TUM TESTLER BASARIYLA TAMAMLANDI! (KOD GUVENLI)
echo ======================================================
pause
exit

:error
echo.
echo ######################################################
echo !! HATA: TESTLERDEN BIRI BASARISIZ OLDU !!
echo ######################################################
pause
exit /b %errorlevel%