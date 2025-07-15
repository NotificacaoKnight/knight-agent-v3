@echo off
echo 🚀 Configurando Local Tunnel para Knight Agent...

REM Verificar se o Node.js está instalado
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Node.js não está instalado. Por favor, instale o Node.js primeiro.
    exit /b 1
)

REM Instalar localtunnel globalmente se não estiver instalado
where lt >nul 2>nul
if %errorlevel% neq 0 (
    echo 📦 Instalando localtunnel...
    npm install -g localtunnel
)

echo.
echo Escolha o que deseja expor:
echo 1) Apenas Backend (API)
echo 2) Apenas Frontend
echo 3) Backend e Frontend
set /p choice="Opcao: "

if "%choice%"=="1" (
    echo 🔧 Iniciando tunnel para o Backend (porta 8000)...
    start cmd /k "lt --port 8000 --subdomain knight-backend-%random%"
    timeout /t 5 /nobreak >nul
    echo ✅ Backend tunnel iniciado!
    echo 📌 URL do Backend: https://knight-backend-*.loca.lt
    echo.
    echo 🔗 Compartilhe a URL do Backend com seus testers!
    echo ⚠️  Lembre-se de atualizar o CORS no Django settings para aceitar requisições do tunnel
) else if "%choice%"=="2" (
    echo 🎨 Iniciando tunnel para o Frontend (porta 3000)...
    start cmd /k "lt --port 3000 --subdomain knight-frontend-%random%"
    timeout /t 5 /nobreak >nul
    echo ✅ Frontend tunnel iniciado!
    echo 📌 URL do Frontend: https://knight-frontend-*.loca.lt
    echo.
    echo 🔗 Compartilhe a URL do Frontend com seus testers!
    echo ⚠️  Certifique-se de que o backend está acessível
) else if "%choice%"=="3" (
    echo 🔧 Iniciando tunnel para o Backend (porta 8000)...
    start cmd /k "lt --port 8000 --subdomain knight-backend-%random%"
    timeout /t 3 /nobreak >nul
    echo 🎨 Iniciando tunnel para o Frontend (porta 3000)...
    start cmd /k "lt --port 3000 --subdomain knight-frontend-%random%"
    timeout /t 5 /nobreak >nul
    echo ✅ Backend e Frontend tunnels iniciados!
    echo 📌 URL do Backend: https://knight-backend-*.loca.lt
    echo 📌 URL do Frontend: https://knight-frontend-*.loca.lt
    echo.
    echo 🔗 Compartilhe as URLs com seus testers!
    echo ⚠️  Atualize as configurações de CORS e API_URL conforme necessário
) else (
    echo ❌ Opção inválida
    exit /b 1
)

echo.
echo 📝 Notas importantes:
echo - As URLs serão válidas enquanto as janelas do cmd estiverem abertas
echo - Feche as janelas do cmd para parar os tunnels
echo - Você pode precisar aceitar os termos do localtunnel na primeira vez
echo.
pause