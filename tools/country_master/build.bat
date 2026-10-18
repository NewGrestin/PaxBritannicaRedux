@echo off
rem Builds CountryMaster.exe next to this file. Needs Python 3.10+ on PATH.
rem It uses the file and map code of ../culture_master/culture_master.py.
cd /d "%~dp0"
python -m pip install --quiet --upgrade pyinstaller pillow numpy || goto :error
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
	--name CountryMaster ^
	--icon "%~dp0country_master.ico" ^
	--add-data "%~dp0country_master.ico;." ^
	--paths "%~dp0..\culture_master" ^
	--distpath "%~dp0." ^
	--workpath "%~dp0build" ^
	--specpath "%~dp0build" ^
	country_master.py || goto :error
rmdir /s /q "%~dp0build"
echo.
echo Built %~dp0CountryMaster.exe
goto :eof

:error
echo Build failed.
exit /b 1
