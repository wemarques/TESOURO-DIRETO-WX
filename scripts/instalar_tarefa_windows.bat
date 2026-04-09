@echo off
REM ============================================================
REM  Instalar tarefa agendada Windows: Tesouro Direto WX
REM ============================================================
REM  Cria uma tarefa que roda o pipeline de ingestao + analytics
REM  diariamente as 20:00. Em finais de semana e feriados, o
REM  proprio script pula a execucao automaticamente.
REM ============================================================

setlocal

set TASK_NAME=TesouroDiretoWX_Atualizacao
set PROJECT_DIR=C:\TESOURO-DIRETO-WX
set PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe
set SCRIPT=%PROJECT_DIR%\scripts\agendar_atualizacao.py

echo.
echo === Instalando tarefa agendada Windows ===
echo Nome:      %TASK_NAME%
echo Horario:   diariamente as 20:00
echo Programa:  %PYTHON_EXE%
echo Script:    %SCRIPT% --agora
echo.

if not exist "%PYTHON_EXE%" (
    echo ERRO: Python do venv nao encontrado em %PYTHON_EXE%
    echo Crie o ambiente virtual primeiro.
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo ERRO: Script nao encontrado em %SCRIPT%
    exit /b 1
)

schtasks /Create ^
  /TN "%TASK_NAME%" ^
  /TR "\"%PYTHON_EXE%\" \"%SCRIPT%\" --agora" ^
  /SC DAILY ^
  /ST 20:00 ^
  /F

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERRO ao criar tarefa.
    exit /b 1
)

echo.
echo OK Tarefa criada com sucesso.
echo.
echo Comandos uteis:
echo   Ver detalhes:    schtasks /Query /TN %TASK_NAME% /V /FO LIST
echo   Executar agora:  schtasks /Run /TN %TASK_NAME%
echo   Desabilitar:     schtasks /Change /TN %TASK_NAME% /DISABLE
echo   Remover:         scripts\desinstalar_tarefa_windows.bat
echo.

endlocal
