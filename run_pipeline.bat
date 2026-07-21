@echo off
:: ── Self-reinvoke: if running inside PowerShell, relaunch in cmd.exe ──────────
if not "%ComSpec%"=="" if "%PSModulePath%"=="" goto :IS_CMD
if "%PSModulePath%"=="" goto :IS_CMD
cmd.exe /d /c "%~f0" %*
exit /b %ERRORLEVEL%
:IS_CMD

setlocal EnableDelayedExpansion

:: Enable UTF-8 for braille + box-drawing characters
chcp 65001 >nul 2>&1

:: Widen terminal window
mode con cols=120 lines=40

:: Enable ANSI colors (Windows 10+)
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

:: ── ANSI color codes ──────────────────────────────────────────────────────────
set "ESC="
for /f %%a in ('echo prompt $E^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "BLUE=%ESC%[94m"
set "CYAN=%ESC%[96m"
set "WHITE=%ESC%[97m"
set "BOLD=%ESC%[1m"
set "DIM=%ESC%[2m"
set "RESET=%ESC%[0m"

set "MODE=%~1"
if "%MODE%"=="" set "MODE=docker"
set "PROJECT_DIR=%~dp0"
set "API_URL=http://localhost:8000"

cls
echo %CYAN%╔══════════════════════════════════════════════════════════════════════════════════════════╗%RESET%
echo %CYAN%║                                                                                          ║%RESET%
echo %CYAN%║  %RESET%⠀⠀⠀⠀⡀⠀⠀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀%CYAN%              ║%RESET%
echo %CYAN%║  %RESET%⠀⢸⠉⣹⠋⠉⢉⡟⢩⢋⠋⣽⡻⠭⢽⢉⠯⠭⠭⠭⢽⡍⢹⡍⠙⣯⠉⠉⠉⠉⠉⣿⢫⠉⠉⠉⢉⡟⠉⢿⢹⠉⢉⣉⢿⡝⡉⢩⢿⣻⢍⠉⠉⠩⢹⣟⡏⠉⠹⡉⢻⡍⡇%CYAN%  ║%RESET%
echo %CYAN%║  %RESET%⠀⢸⢠⢹⠀⠀⢸⠁⣼⠀⣼⡝⠀⠀⢸⠘⠀⠀⠀⠀⠈⢿⠀⡟⡄⠹⣣⠀⠀⠐⠀⢸⡘⡄⣤⠀⡼⠁⠀⢺⡘⠉⠀⠀⠀⠫⣪⣌⡌⢳⡻⣦⠀⠀⢃⡽⡼⡀⠀⢣⢸⠸⡇%CYAN%      ║%RESET%
echo %CYAN%║  %RESET%⠀⢸⡸⢸⠀⠀⣿⠀⣇⢠⡿⠀⠀⠀⠸⡇⠀⠀⠀⠀⠀⠘⢇⠸⠘⡀⠻⣇⠀⠀⠄⠀⡇⢣⢛⠀⡇⠀⠀⣸⠇⠀⠀⠀⠀⠀⠘⠄⢻⡀⠻⣻⣧⠀⠀⠃⢧⡇⠀⢸⢸⡇⡇%CYAN%  ║%RESET%
echo %CYAN%║  %RESET%⠀⢸⡇⢸⣠⠀⣿⢠⣿⡾⠁⠀⢀⡀⠤⢇⣀⣐⣀⠀⠤⢀⠈⠢⡡⡈⢦⡙⣷⡀⠀⠀⢿⠈⢻⣡⠁⠀⢀⠏⠀⠀⠀⢀⠀⠄⣀⣐⣀⣙⠢⡌⣻⣷⡀⢹⢸⡅⠀⢸⠸⡇⡇%CYAN%  ║%RESET%
echo %CYAN%║  %RESET%⠀⢸⡇⢸⣟⠀⢿⢸⡿⠀⣀⣶⣷⣾⡿⠿⣿⣿⣿⣿⣿⣶⣬⡀⠐⠰⣄⠙⠪⣻⣦⡀⠘⣧⠀⠙⠄⠀⠀⠀⠀⠀⣨⣴⣾⣿⠿⣿⣿⣿⣿⣿⣶⣯⣿⣼⢼⡇⠀⢸⡇⡇⡇%CYAN%  ║%RESET%
echo %CYAN%║  %RESET%⠀⢸⠀⣿⡅⢸⣼⡷⣾⣿⡟⠋⣿⠓⢲⣿⣿⣿⡟⠙⣿⠛⢯⡳⡀⠈⠓⠄⡈⠚⠿⣧⣌⢧⠀⠀⠀⠀⠀⣠⣺⠟⢫⡿⠓⢺⣿⣿⣿⠏⠙⣏⠛⣿⣿⣾⡇⢀⡿⢠⠀⡇%CYAN%  ║%RESET%
echo %CYAN%║  %RESET%⠀⢸⢸⠀⢹⣷⡀⢿⡁⠀⠻⣇⠀⣇⠀⠘⣿⣿⡿⠁⠐⣉⡀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠉⠓⠳⠄⠀⠀⠀⠀⠋⠀⠘⡇⠀⠸⣿⣿⠟⠀⢈⣉⢠⡿⠁⣼⠁⣼⠃⣼⠀⡇%CYAN%  ║%RESET%
echo %CYAN%║  %RESET%⠀⢸⠸⣀⠈⣯⢳⡘⣇⠀⠀⠈⡂⣜⣆⡀⠀⠀⢀⣀⡴⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢽⣆⣀⠀⠀⠀⣀⣜⠕⡊⠀⣸⠇⣼⡟⢠⠏⠀⡇%CYAN%  ║%RESET%
echo %CYAN%║  %RESET%⠀⢸⠀⡟⠀⢸⡆⢹⡜⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠋⣾⡏⡇⡎⡇⠀⡇%CYAN%  ║%RESET%
echo %CYAN%║  %RESET%⠀⢸⠀⢃⡆⠀⢿⡄⠑⢽⣄⠀⠀⠀⢀⠂⠠⢁⠈⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠠⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠄⡐⢀⠂⠀⠀⣠⣮⡟⢹⣯⣸⣱⠁⠀⡇%CYAN%  ║%RESET%
echo %CYAN%║  %RESET%⠀⠈⠉⠉⠋⠉⠉⠋⠉⠉⠉⠋⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠋⡟⠉⠉⡿⠋⠋⠋⠉⠉⠁%CYAN%  ║%RESET%
echo %CYAN%║                                                                                          ║%RESET%
echo %CYAN%║%BOLD%%WHITE%                        Advanced Botnet Detection Tool                                  %RESET%%CYAN%║%RESET%
echo %CYAN%║%DIM%                     One-Shot MLOps Pipeline Runner (Mode: %MODE%)                       %RESET%%CYAN%║%RESET%
echo %CYAN%║%DIM%                          Repo: github.com/Knight-Node64/Botnet-Detection                     %RESET%%CYAN%║%RESET%
echo %CYAN%╚══════════════════════════════════════════════════════════════════════════════════════════╝%RESET%
echo.

:: ── STEP 1: Dependencies ──────────────────────────────────
echo %BLUE%  [STEP 1/6] Installing dependencies...%RESET%
python -m pip install -q -r "%PROJECT_DIR%requirements.txt"
if errorlevel 1 (echo %RED%  [XX] pip install failed%RESET% & exit /b 1)
echo %GREEN%  [OK] Dependencies installed%RESET%

:: ── STEP 2: Check dataset ─────────────────────────────────
echo.
echo %BLUE%  [STEP 2/6] Verifying dataset...%RESET%
if not exist "%PROJECT_DIR%dataset\UNSW_NB15_training-set.csv" (
    echo %RED%  [XX] Training CSV not found in dataset\%RESET%
    echo %YELLOW%       Download from: https://www.kaggle.com/datasets/mrwellsdavid/unsw-nb15%RESET%
    exit /b 1
)
echo %GREEN%  [OK] Dataset found%RESET%

:: ── STEP 3: Train model ───────────────────────────────────
echo.
echo %BLUE%  [STEP 3/6] Training model...%RESET%
python "%PROJECT_DIR%train_model.py"
if errorlevel 1 (echo %RED%  [XX] Training failed%RESET% & exit /b 1)
if not exist "%PROJECT_DIR%models\botnet_detector.joblib" (
    echo %RED%  [XX] Model file not created%RESET%
    exit /b 1
)
echo %GREEN%  [OK] Model saved to models\botnet_detector.joblib%RESET%

:: ── STEP 4: Run tests ─────────────────────────────────────
echo.
echo %BLUE%  [STEP 4/6] Running test suite...%RESET%
python -m pytest "%PROJECT_DIR%tests\" -v -W ignore::DeprecationWarning --tb=short
if errorlevel 1 (echo %RED%  [XX] Tests failed%RESET% & exit /b 1)
echo %GREEN%  [OK] All tests passed%RESET%

:: ── STEP 5: Deploy ────────────────────────────────────────
echo.
echo %BLUE%  [STEP 5/6] Deploying in mode: %MODE%...%RESET%

if "%MODE%"=="local" goto DEPLOY_LOCAL
if "%MODE%"=="docker" goto DEPLOY_DOCKER
if "%MODE%"=="k8s"    goto DEPLOY_K8S
echo %RED%Unknown mode: %MODE%%RESET% & exit /b 1

:DEPLOY_LOCAL
echo %DIM%  Starting API locally (background)...%RESET%
start /b "BotnetAPI" python -m uvicorn app:app --host 0.0.0.0 --port 8000
timeout /t 4 /nobreak >nul
goto STEP6

:DEPLOY_DOCKER
docker --version >nul 2>&1
if errorlevel 1 (echo %RED%  [XX] Docker not installed%RESET% & exit /b 1)
docker stop botnet_detector_service >nul 2>&1
docker rm   botnet_detector_service >nul 2>&1
docker build -t botnet-detector:latest "%PROJECT_DIR%"
if errorlevel 1 (echo %RED%  [XX] Docker build failed%RESET% & exit /b 1)
docker run -d --name botnet_detector_service -p 8000:8000 botnet-detector:latest
if errorlevel 1 (echo %RED%  [XX] Docker run failed%RESET% & exit /b 1)
timeout /t 6 /nobreak >nul
echo %GREEN%  [OK] Docker container running%RESET%
goto STEP6

:DEPLOY_K8S
kubectl version --client >nul 2>&1
if errorlevel 1 (echo %RED%  [XX] kubectl not found%RESET% & exit /b 1)
kubectl apply -f "%PROJECT_DIR%k8s\deployment.yaml"
kubectl apply -f "%PROJECT_DIR%k8s\service.yaml"
kubectl rollout status deployment/botnet-detector-deployment --timeout=90s
start /b "K8s Port-Forward" kubectl port-forward service/botnet-detector-service 8000:80
timeout /t 5 /nobreak >nul
echo %GREEN%  [OK] Kubernetes deployment applied%RESET%
goto STEP6

:: ── STEP 6: Smoke test + Monitor ──────────────────────────
:STEP6
echo.
echo %BLUE%  [STEP 6/6] Running smoke tests and monitoring...%RESET%
python "%PROJECT_DIR%smoke_test.py"
if errorlevel 1 (echo %RED%  [XX] Smoke test failed%RESET% & exit /b 1)
echo %GREEN%  [OK] Smoke test passed%RESET%

python "%PROJECT_DIR%smoke_test.py" --monitor
echo %GREEN%  [OK] Monitoring complete%RESET%

:: ── Summary ───────────────────────────────────────────────
echo.
echo %CYAN%╔══════════════════════════════════════════════════════════════════════════════════════════╗%RESET%
echo %CYAN%║  %BOLD%%WHITE%PIPELINE COMPLETE                                                                       %RESET%%CYAN%║%RESET%
echo %CYAN%║  %GREEN%API:     %WHITE%%API_URL%                                                              %CYAN%║%RESET%
echo %CYAN%║  %GREEN%Health:  %WHITE%%API_URL%/health                                                       %CYAN%║%RESET%
echo %CYAN%║  %GREEN%Docs:    %WHITE%%API_URL%/docs                                                         %CYAN%║%RESET%
echo %CYAN%║  %GREEN%Metrics: %WHITE%%API_URL%/metrics                                                      %CYAN%║%RESET%
echo %CYAN%╚══════════════════════════════════════════════════════════════════════════════════════════╝%RESET%
echo.
exit /b 0
