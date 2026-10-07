@echo off
title Actualizar datos del Mundial
cd /d "%~dp0"

echo  Actualizando los datos del Mundial AHORA (forzado)...
echo.

REM Cerrar el backend para liberar el archivo del historial (si la app esta abierta).
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

pushd "%~dp0apps\api"
.venv\Scripts\python.exe -m scripts.refresh_data --force
popd

echo.
echo  Listo. Vuelve a abrir SportsPredictor para ver los datos al dia.
timeout /t 5 /nobreak >nul
