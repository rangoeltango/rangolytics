@echo off
cd C:\Users\randy\OneDrive\Desktop\Rangolytics
C:\Users\randy\OneDrive\Desktop\Rangolytics\venv\Scripts\python.exe scripts\fetch_fpl.py
C:\Users\randy\OneDrive\Desktop\Rangolytics\venv\Scripts\python.exe scripts\build_site.py
C:\Users\randy\OneDrive\Desktop\Rangolytics\venv\Scripts\python.exe scripts\build_mobile_site.py
git add .
git commit -m "Weekly update: Latest gameweek results"
git push origin main
echo Update complete! Site deployed to www.rango.biz
pause