@echo off
echo Installing required Python modules...
pip install pyqt5

echo Running the Rocksmith DLC Manager...
python files\main.py
pause
