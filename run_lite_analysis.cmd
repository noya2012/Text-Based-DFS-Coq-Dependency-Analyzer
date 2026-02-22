@echo off
chcp 65001 >nul

echo ============================================
echo Coq Dependency Analyzer - Lite Version
echo ============================================
echo.

cd /d "%~dp0"

REM Check required files exist
if not exist "dependency_extractor.py" (
    echo [ERROR] dependency_extractor.py not found
    pause
    exit /b 1
)

if not exist "code_lite_generator.py" (
    echo [ERROR] code_lite_generator.py not found
    pause
    exit /b 1
)

if not exist "major_theorem_dependency_analyzer.py" (
    echo [ERROR] major_theorem_dependency_analyzer.py not found
    pause
    exit /b 1
)

echo Step 1: Running dependency extractor...
echo.
python "dependency_extractor.py"

if %errorlevel% neq 0 (
    echo [ERROR] Dependency extractor execution failed
    pause
    exit /b 1
)

echo.
echo Dependency extraction completed!
echo.

echo Step 2: Running Code Lite generator...
echo.
python "code_lite_generator.py"

if %errorlevel% neq 0 (
    echo [ERROR] Code Lite generator execution failed
    pause
    exit /b 1
)

echo.
echo Code Lite generation completed!
echo.

echo Step 3: Running major theorem dependency analyzer...
echo.
echo Note: This script requires a theorem name argument.
echo Usage: python major_theorem_dependency_analyzer.py ^<theorem_name^> [--to-file]
echo.
echo Example: python major_theorem_dependency_analyzer.py "your_theorem_name" --to-file
echo.

set /p THEOREM_NAME="Enter theorem name (or press Enter to skip): "

if not "%THEOREM_NAME%"=="" (
    python "major_theorem_dependency_analyzer.py" "%THEOREM_NAME%" --to-file
    if %errorlevel% neq 0 (
        echo [WARN] Major theorem analyzer execution failed or theorem not found
    )
)

echo.
echo ============================================
echo Lite analysis completed!
echo ============================================
echo.
pause
