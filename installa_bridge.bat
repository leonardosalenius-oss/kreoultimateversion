@echo off
cd /d %~dp0
python -m pip install -r requirements.txt
copy config.example.json config.json
echo Configura ora config.json con i dati del dispositivo.
pause
