@echo off
title Detener SportsPredictor
echo  Cerrando SportsPredictor (servidores en los puertos 8000 y 3000)...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
echo  Listo. SportsPredictor se detuvo.
timeout /t 3 /nobreak >nul
