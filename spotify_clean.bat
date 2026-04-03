@echo off
echo ============================================
echo  Spotify Residue Cleaner
echo  Run AFTER uninstalling Spotify
echo  Will NOT touch spotipy_scripts
echo ============================================
echo.

:: Kill any lingering Spotify processes
echo [1/6] Killing Spotify processes...
taskkill /F /IM Spotify.exe /T 2>nul
taskkill /F /IM SpotifyCrashService.exe /T 2>nul
taskkill /F /IM SpotifyWebHelper.exe /T 2>nul
timeout /t 2 /nobreak >nul
echo    Done.

:: AppData\Roaming\Spotify  (cache, settings, offline data)
echo [2/6] Removing %%APPDATA%%\Spotify...
if exist "%APPDATA%\Spotify" (
    rd /s /q "%APPDATA%\Spotify"
    echo    Removed.
) else (
    echo    Not found - skipping.
)

:: AppData\Local\Spotify  (installation files for non-Store installs)
echo [3/6] Removing %%LOCALAPPDATA%%\Spotify...
if exist "%LOCALAPPDATA%\Spotify" (
    rd /s /q "%LOCALAPPDATA%\Spotify"
    echo    Removed.
) else (
    echo    Not found - skipping.
)

:: Microsoft Store version package (if it was ever installed that way)
echo [4/6] Checking for Microsoft Store Spotify package...
set "found_store=0"
for /d %%i in ("%LOCALAPPDATA%\Packages\SpotifyAB.SpotifyMusic_*") do (
    echo    Removing %%i
    rd /s /q "%%i"
    set "found_store=1"
)
if "%found_store%"=="0" echo    Not found - skipping.

:: Start Menu + Desktop shortcuts
echo [5/6] Removing shortcuts...
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Spotify.lnk" (
    del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Spotify.lnk"
    echo    Removed Start Menu shortcut.
)
if exist "%USERPROFILE%\Desktop\Spotify.lnk" (
    del /f /q "%USERPROFILE%\Desktop\Spotify.lnk"
    echo    Removed Desktop shortcut.
)

:: Registry keys
echo [6/6] Cleaning registry...
reg delete "HKCU\Software\Spotify" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\Spotify" /f 2>nul
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Spotify" /f 2>nul
echo    Done.

echo.
echo ============================================
echo  All clear. Safe to reinstall.
echo  Get the installer from: spotify.com/download
echo  (Use that, NOT the Microsoft Store version)
echo ============================================
echo.
pause
