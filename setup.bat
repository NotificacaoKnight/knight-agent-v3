@echo off
REM Script de setup rápido para Knight Agent (Windows)

echo 🚀 Configurando Knight Agent...

REM Backend setup
echo 📦 Configurando Backend...
cd backend

REM Criar e ativar ambiente virtual
if not exist "venv" (
    echo Criando ambiente virtual...
    python -m venv venv
)

REM Ativar venv e instalar dependências
echo Ativando ambiente virtual...
call venv\Scripts\activate
echo Instalando dependencias do backend...
pip install -r requirements.txt

REM Aplicar migrações
echo Aplicando migracoes do banco de dados...
python manage.py migrate

echo ✅ Backend configurado!

REM Frontend setup
echo 📦 Configurando Frontend...
cd ..\frontend

REM Instalar dependências
if not exist "node_modules" (
    echo Instalando dependencias do frontend...
    npm install
)

echo ✅ Frontend configurado!

REM Instruções finais
echo.
echo 🎉 Setup completo!
echo.
echo Para iniciar o projeto:
echo.
echo Terminal 1 - Backend:
echo   cd backend
echo   venv\Scripts\activate
echo   python manage.py runserver
echo.
echo Terminal 2 - Frontend:
echo   cd frontend
echo   npm start
echo.
echo Acesse http://localhost:3000 e clique em 'Modo Desenvolvedor' para entrar!
pause