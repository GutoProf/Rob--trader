@echo off
REM Este script executa o processo de retreinamento da Inteligência Artificial.

echo "--- INICIANDO RETREINAMENTO AUTOMATIZADO DA IA ---"

REM Navega para o diretório onde o script está localizado
cd /d "%~dp0"

REM Executa o script de treinamento do Python
python treinamento_ia.py

echo "--- RETREINAMENTO CONCLUÍDO ---"
pause
