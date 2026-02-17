@echo off
TITLE Wemo Ops - HOOBS Installer Builder
COLOR 0A

echo ========================================================
echo    WEMO OPS - HOOBS COMPATIBILITY LAYER BUILDER
echo ========================================================
echo.

:: 1. Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    COLOR 0C
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ and check "Add to PATH".
    pause
    exit /b
)

:: 2. Install PyInstaller if missing
echo [*] Checking build dependencies...
python -m pip show pyinstaller >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [+] Installing PyInstaller...
    python -m pip install pyinstaller
) else (
    echo [*] PyInstaller is already installed.
)

:: 3. Clean previous builds
echo.
echo [*] Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /f /q "*.spec"

:: 4. Check for Icon (Optional)
set ICON_CMD=
if exist "images\app_icon.ico" (
    echo [*] Icon found, applying to executable...
    set ICON_CMD=--icon="images\app_icon.ico"
)

:: 5. Build the Executable
echo.
echo [*] Compiling Setup Executable...
echo     This may take a minute...
echo.

:: FIX: Use 'python -m PyInstaller' instead of just 'pyinstaller' to avoid PATH errors
python -m PyInstaller --noconfirm --onefile --console --clean --uac-admin --name "Wemo_HOOBS_Integration_Setup" %ICON_CMD% "hoobs_installer.py"

:: 6. Verify and Cleanup
IF %ERRORLEVEL% EQ 0 (
    echo.
    echo ========================================================
    echo    BUILD SUCCESSFUL!
    echo ========================================================
    echo.
    echo Your installer is located at:
    echo    dist\Wemo_HOOBS_Integration_Setup.exe
    echo.
    
    :: Move it to the root folder for easy access
    move "dist\Wemo_HOOBS_Integration_Setup.exe" ".\" >nul
    
    :: Cleanup build folders
    rmdir /s /q "build"
    rmdir /s /q "dist"
    del /f /q "*.spec"
    
    echo File moved to root directory.
) ELSE (
    COLOR 0C
    echo.
    echo [!] Build Failed. Check the error messages above.
)

pause