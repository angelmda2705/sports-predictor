@echo off
title SportsPredictor
cd /d "%~dp0"

echo ================================================
echo                SportsPredictor
echo ================================================
echo.
echo  Iniciando los servidores (espera unos segundos)...
echo.

REM --- Actualizar datos del Mundial (solo si estan viejos; no rompe sin internet) ---
echo  Buscando datos del Mundial al dia...
pushd "%~dp0apps\api"
.venv\Scripts\python.exe -m scripts.refresh_data
popd
echo.

REM --- Backend (FastAPI) en el puerto 8000 ---
start "SportsPredictor Backend" /min /d "%~dp0apps\api" cmd /c ".venv\Scripts\python.exe -m uvicorn src.main:app --port 8000"

REM --- Frontend (Next.js) en el puerto 3000 ---
start "SportsPredictor Frontend" /min /d "%~dp0apps\web" cmd /c "npm run dev"

REM --- Esperar a que el frontend responda en :3000 (hasta ~40s) ---
echo  Esperando a que la app este lista...
set /a tries=0
:wait
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://localhost:3000' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 goto ready
set /a tries+=1
if %tries% geq 20 goto ready
timeout /t 2 /nobreak >nul
goto wait

:ready
echo  Abriendo la aplicacion en el navegador...
start "" http://localhost:3000

echo.
echo ================================================
echo  La app esta abierta en:  http://localhost:3000
echo ================================================
echo.
echo  Usuario de prueba (opcional):
echo     correo:      demo@example.com
echo     contrasena:  password123
echo.
echo  DEJA ESTA VENTANA ABIERTA mientras uses la app.
echo  Para CERRAR la app, vuelve aqui y presiona una tecla.
echo.
pause >nul

echo.
echo  Cerrando servidores...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
echo  Listo. Puedes cerrar esta ventana.
timeout /t 3 /nobreak >nul
