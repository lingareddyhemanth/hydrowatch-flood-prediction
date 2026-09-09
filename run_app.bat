@echo off
echo =======================================================
echo   HydroWatch AI - Flood Inundation Prediction System
echo =======================================================
echo.

IF NOT EXIST ".venv" (
    echo [1/3] Creating virtual environment (.venv)...
    python -m venv .venv
)

echo [2/3] Installing dependencies...
.venv\Scripts\pip install -r requirements.txt

echo [3/3] Launching Streamlit Interactive Dashboard...
.venv\Scripts\streamlit run app.py
pause
