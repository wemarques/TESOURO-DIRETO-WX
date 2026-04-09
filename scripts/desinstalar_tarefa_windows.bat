@echo off
REM ============================================================
REM  Remover tarefa agendada Windows: Tesouro Direto WX
REM ============================================================

setlocal

set TASK_NAME=TesouroDiretoWX_Atualizacao

echo.
echo === Removendo tarefa agendada ===
echo Nome: %TASK_NAME%
echo.

schtasks /Delete /TN "%TASK_NAME%" /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo OK Tarefa removida.
) else (
    echo.
    echo ERRO ao remover tarefa (talvez nao exista).
    exit /b 1
)

endlocal
