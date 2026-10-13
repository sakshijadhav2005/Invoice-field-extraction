@echo off
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt
if "%PORT%"=="" set PORT=8000
echo Starting invoice extraction service on port %PORT%...
uvicorn app.main:app --host 0.0.0.0 --port %PORT%
