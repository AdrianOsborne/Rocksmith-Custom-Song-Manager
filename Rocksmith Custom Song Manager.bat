@echo off
echo Installing dependencies...
pip install PyQt5 PyMuPDF

echo Running Rocksmith DLC Manager...
cd files
python rocksmith_CDLC_manager.py

pause
