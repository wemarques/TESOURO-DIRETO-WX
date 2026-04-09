@echo off
REM ============================================================
REM  Task Scheduler entry point - Tesouro Direto WX
REM ============================================================
REM  Este arquivo eh chamado pelo Windows Task Scheduler.
REM  Ativa o venv, executa o pipeline e registra saida no log.
REM ============================================================

REM Ir para o diretorio do projeto (paths absolutos)
cd /d C:\TESOURO-DIRETO-WX

REM Timestamp inicial
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set DATA=%%c-%%b-%%a
for /f "tokens=1-2 delims=:" %%a in ('time /t') do set HORA=%%a:%%b
set TIMESTAMP=%DATA% %HORA%

REM Arquivo de log
set LOG_FILE=C:\TESOURO-DIRETO-WX\data\audit\task_scheduler.log

REM Garantir que o diretorio de log existe
if not exist "C:\TESOURO-DIRETO-WX\data\audit" mkdir "C:\TESOURO-DIRETO-WX\data\audit"

REM Cabecalho da execucao
echo. >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"
echo [%TIMESTAMP%] Iniciando execucao agendada >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

REM Ativar ambiente virtual
call C:\TESOURO-DIRETO-WX\.venv\Scripts\activate.bat

REM Garantir encoding UTF-8 para evitar erros no Windows
set PYTHONIOENCODING=utf-8

REM Executar pipeline e capturar saida no log
python C:\TESOURO-DIRETO-WX\scripts\agendar_atualizacao.py --agora >> "%LOG_FILE%" 2>&1

REM Capturar codigo de saida
set EXIT_CODE=%ERRORLEVEL%

REM Timestamp final
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set DATA=%%c-%%b-%%a
for /f "tokens=1-2 delims=:" %%a in ('time /t') do set HORA=%%a:%%b
set TIMESTAMP=%DATA% %HORA%

echo [%TIMESTAMP%] Execucao finalizada com codigo %EXIT_CODE% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

exit /b %EXIT_CODE%
