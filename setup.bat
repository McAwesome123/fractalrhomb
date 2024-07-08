@echo off

echo Creating venv
python -m venv .venv

echo Activating venv
call .venv\Scripts\activate.bat

echo Installing requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Creating .env
if exist src\.env move /-Y src\.env src\.env.bak
echo FRACTALTHORNS_USER_AGENT="Fractal-RHOMB" > src/.env

echo Setup complete
pause
