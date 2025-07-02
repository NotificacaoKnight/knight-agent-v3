@echo off
REM Script para corrigir as migrações (Windows)

echo 🔧 Corrigindo migracoes do banco de dados...

REM Ativar ambiente virtual
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate
) else (
    echo ❌ Ambiente virtual nao encontrado. Execute setup.bat primeiro.
    exit /b 1
)

REM Criar migrações
echo 📝 Criando arquivos de migracao...
python manage.py makemigrations

REM Aplicar migrações
echo 🗄️ Aplicando migracoes ao banco de dados...
python manage.py migrate

REM Perguntar sobre superusuário
echo.
echo ✅ Migracoes aplicadas com sucesso!
echo.
set /p response="Deseja criar um superusuario para o Django Admin? (s/n): "
if /i "%response%"=="s" (
    python manage.py createsuperuser
)

echo.
echo 🎉 Pronto! Agora voce pode iniciar o servidor:
echo python manage.py runserver
pause