@echo off

REM Define the virtual environment directory
SET VENV_DIR=venv

REM Check if the virtual environment directory exists
IF NOT EXIST "%VENV_DIR%" (
    echo Virtual environment not found, creating one.
    py -3.12 -m venv %VENV_DIR%
)

REM Activate the virtual environment
CALL "%VENV_DIR%\Scripts\activate.bat"

REM Install dependencies if requirements.txt exists
IF EXIST "requirements.txt" (
    echo Installing dependencies from requirements.txt.
    py -3.12 -m pip install --upgrade pip --quiet --no-warn-script-location
    py -3.12 -m pip install wheel --quiet --no-warn-script-location
    py -3.12 -m pip install -r requirements.txt --quiet --no-warn-script-location
)

echo Starting Legilo.

REM Run Legilo
py -3.12 main.py --no-warn-script-location

REM Deactivate the virtual environment
deactivate