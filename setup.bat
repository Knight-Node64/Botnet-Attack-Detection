@echo off
setlocal EnableDelayedExpansion

:: Set console title
title Botnet Detection - MLOps Pipeline Launcher

:: Change directory to script folder
cd /d "%~dp0"

:: Enable ANSI colors for Windows 10+
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

:: Project settings
set "PROJECT_DIR=%~dp0"
set "API_PORT=8000"
set "API_URL=http://localhost:%API_PORT%"
set "DOCKER_IMAGE=botnet-detector"

:MAIN_MENU
cls
call :SHOW_BANNER

echo.
echo   SELECT AN OPTION:
echo.
echo   [1]  Full Auto Pipeline       (Run ALL steps M1 to M5)
echo   --------------------------------------------------------
echo   [2]  M1 ^| Install Dependencies
echo   [3]  M1 ^| Train Model
echo   [4]  M3 ^| Run Tests (pytest)
echo   [5]  M2 ^| Start API Locally
echo   [6]  M2 ^| Docker Build + Run
echo   [7]  M4 ^| Kubernetes Deploy
echo   [8]  M5 ^| Smoke Test + Monitor
echo   [9]  M1 ^| MLflow Experiment Tracking
echo  [10]     ^| Open API Docs in Browser
echo  [11]     ^| Check GitHub Actions Status
echo  [12]     ^| Check Prerequisites
echo   --------------------------------------------------------
echo   [0]  Exit
echo.
set "CHOICE="
set /p "CHOICE=  Enter choice: "

if "%CHOICE%"=="1"  goto RUN_ALL
if "%CHOICE%"=="2"  goto INSTALL_DEPS
if "%CHOICE%"=="3"  goto TRAIN_MODEL
if "%CHOICE%"=="4"  goto RUN_TESTS
if "%CHOICE%"=="5"  goto START_API
if "%CHOICE%"=="6"  goto DOCKER_RUN
if "%CHOICE%"=="7"  goto K8S_DEPLOY
if "%CHOICE%"=="8"  goto SMOKE_MONITOR
if "%CHOICE%"=="9"  goto MLFLOW_TRAIN
if "%CHOICE%"=="10" goto OPEN_BROWSER
if "%CHOICE%"=="11" goto GITHUB_ACTIONS
if "%CHOICE%"=="12" goto CHECK_PREREQS
if "%CHOICE%"=="0"  goto EXIT
goto MAIN_MENU

:: ==============================================================================
:RUN_ALL
call :SECTION "FULL AUTO PIPELINE (M1 to M5)"
echo   This will run ALL steps sequentially.
echo   Press Ctrl+C anytime to abort.
echo.
pause

call :CHECK_PREREQS_SILENT
call :DO_INSTALL_DEPS
call :DO_TRAIN_MODEL
call :DO_RUN_TESTS
call :DO_DOCKER_BUILD_RUN
call :DO_SMOKE_TEST

call :SUCCESS "Full MLOps Pipeline Complete!"
echo.
echo   * API running at:   %API_URL%
echo   * Health endpoint:  %API_URL%/health
echo   * Swagger UI:       %API_URL%/docs
echo   * Metrics:          %API_URL%/metrics
echo.
pause
goto MAIN_MENU

:: ==============================================================================
:INSTALL_DEPS
call :DO_INSTALL_DEPS
pause
goto MAIN_MENU

:DO_INSTALL_DEPS
call :SECTION "M1 -- Installing Dependencies"
call :STEP "Checking Python version..."
python --version >nul 2>&1
if errorlevel 1 (
    call :ERROR "Python not found! Install from https://python.org"
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do call :SUCCESS "Found: %%v"

call :STEP "Installing packages from requirements.txt..."
python -m pip install --upgrade pip -q
python -m pip install -r "%PROJECT_DIR%requirements.txt"
if errorlevel 1 (
    call :ERROR "pip install failed!"
    exit /b 1
)
call :SUCCESS "All dependencies installed successfully!"
exit /b 0

:: ==============================================================================
:TRAIN_MODEL
call :DO_TRAIN_MODEL
pause
goto MAIN_MENU

:DO_TRAIN_MODEL
call :SECTION "M1 -- Training Model on UNSW-NB15 Dataset"

if not exist "%PROJECT_DIR%dataset\UNSW_NB15_training-set.csv" (
    call :ERROR "Training dataset not found!"
    echo   Expected: %PROJECT_DIR%dataset\UNSW_NB15_training-set.csv
    echo   Download: https://www.kaggle.com/datasets/mrwellsdavid/unsw-nb15
    exit /b 1
)
if not exist "%PROJECT_DIR%dataset\UNSW_NB15_testing-set.csv" (
    call :ERROR "Testing dataset not found!"
    exit /b 1
)
call :SUCCESS "Datasets found"

call :STEP "Running feature engineering + model training..."
echo   (RandomForest vs XGBoost -- best F1 model saved)
echo.
python "%PROJECT_DIR%train_model.py"
if errorlevel 1 (
    call :ERROR "Training failed!"
    exit /b 1
)
if not exist "%PROJECT_DIR%models\botnet_detector.joblib" (
    call :ERROR "Model file was not saved!"
    exit /b 1
)
call :SUCCESS "Model saved to models\botnet_detector.joblib"
exit /b 0

:: ==============================================================================
:RUN_TESTS
call :DO_RUN_TESTS
pause
goto MAIN_MENU

:DO_RUN_TESTS
call :SECTION "M3 -- Running Test Suite (pytest)"

if not exist "%PROJECT_DIR%models\botnet_detector.joblib" (
    call :WARN "Model not found -- running training first..."
    call :DO_TRAIN_MODEL
)
call :STEP "Running all tests..."
python -m pytest "%PROJECT_DIR%tests\" -v -W ignore::DeprecationWarning
if errorlevel 1 (
    call :ERROR "Tests FAILED! Check output above."
    exit /b 1
)
call :SUCCESS "All tests passed!"
exit /b 0

:: ==============================================================================
:START_API
call :SECTION "M2 -- Starting FastAPI Server Locally"

if not exist "%PROJECT_DIR%models\botnet_detector.joblib" (
    call :WARN "Model not found -- running training first..."
    call :DO_TRAIN_MODEL
)
call :STEP "Starting uvicorn on port %API_PORT%..."
echo   Press Ctrl+C to stop the server
echo.
echo   Access points:
echo     API:      %API_URL%
echo     Docs:     %API_URL%/docs
echo     Health:   %API_URL%/health
echo     Metrics:  %API_URL%/metrics
echo.

start /b cmd /c "timeout /t 3 /nobreak >nul & start %API_URL%/docs"
python -m uvicorn app:app --host 0.0.0.0 --port %API_PORT% --reload
goto MAIN_MENU

:: ==============================================================================
:DOCKER_RUN
call :DO_DOCKER_BUILD_RUN
pause
goto MAIN_MENU

:DO_DOCKER_BUILD_RUN
call :SECTION "M2/M4 -- Docker Build + Run"

docker --version >nul 2>&1
if errorlevel 1 (
    call :ERROR "Docker not found! Install Docker Desktop from https://docker.com"
    exit /b 1
)
for /f "tokens=*" %%v in ('docker --version 2^>^&1') do call :SUCCESS "Found: %%v"

call :STEP "Stopping any existing container..."
docker stop botnet_detector_service >nul 2>&1
docker rm   botnet_detector_service >nul 2>&1

call :STEP "Building Docker image: %DOCKER_IMAGE%:latest"
docker build -t %DOCKER_IMAGE%:latest "%PROJECT_DIR%"
if errorlevel 1 (
    call :ERROR "Docker build failed!"
    exit /b 1
)
call :SUCCESS "Docker image built"

call :STEP "Starting container on port %API_PORT%..."
docker run -d --name botnet_detector_service -p %API_PORT%:8000 --restart unless-stopped %DOCKER_IMAGE%:latest
if errorlevel 1 (
    call :ERROR "Failed to start container!"
    exit /b 1
)

call :STEP "Waiting for container to be ready..."
timeout /t 5 /nobreak >nul
call :DO_HEALTH_CHECK

echo.
echo   Container running! Useful commands:
echo     docker logs botnet_detector_service    (view logs)
echo     docker stop botnet_detector_service    (stop)
echo     docker-compose up -d                   (compose mode)
call :SUCCESS "Docker container is live at %API_URL%"
exit /b 0

:: ==============================================================================
:K8S_DEPLOY
call :SECTION "M4 -- Kubernetes Deployment"

kubectl version --client >nul 2>&1
if errorlevel 1 (
    call :ERROR "kubectl not found! Install from https://kubernetes.io/docs/tasks/tools/"
    echo   Tip: Enable Kubernetes in Docker Desktop Settings
    pause
    goto MAIN_MENU
)
call :SUCCESS "kubectl found"

call :STEP "Checking cluster connection..."
kubectl cluster-info >nul 2>&1
if errorlevel 1 (
    call :ERROR "Cannot connect to Kubernetes cluster!"
    echo   Enable Kubernetes in Docker Desktop Settings or run: minikube start
    pause
    goto MAIN_MENU
)
call :SUCCESS "Connected to cluster"

docker image inspect %DOCKER_IMAGE%:latest >nul 2>&1
if errorlevel 1 (
    call :WARN "Docker image not found -- building now..."
    call :DO_DOCKER_BUILD_RUN
)

call :STEP "Applying K8s manifests..."
kubectl apply -f "%PROJECT_DIR%k8s\deployment.yaml"
if errorlevel 1 (call :ERROR "Failed to apply deployment.yaml!" & pause & goto MAIN_MENU)
kubectl apply -f "%PROJECT_DIR%k8s\service.yaml"
if errorlevel 1 (call :ERROR "Failed to apply service.yaml!" & pause & goto MAIN_MENU)

call :STEP "Waiting for pods to be ready (up to 60s)..."
kubectl rollout status deployment/botnet-detector-deployment --timeout=60s
if errorlevel 1 (call :WARN "Rollout timed out -- checking pod status...")

echo.
echo   Pod Status:
kubectl get pods -l app=botnet-detector
echo.
echo   Service Status:
kubectl get svc 2>nul
echo.

call :STEP "Setting up port-forward for local access..."
start "K8s Port-Forward" cmd /k "kubectl port-forward service/botnet-detector-service %API_PORT%:80 & pause"
timeout /t 3 /nobreak >nul
call :DO_HEALTH_CHECK

call :SUCCESS "Kubernetes deployment live!"
echo.
echo   Useful kubectl commands:
echo     kubectl get pods                                              (status)
echo     kubectl logs -l app=botnet-detector                          (logs)
echo     kubectl scale deploy/botnet-detector-deployment --replicas=3 (scale)
echo     kubectl delete -f k8s/                                       (teardown)
pause
goto MAIN_MENU

:: ==============================================================================
:SMOKE_MONITOR
call :DO_SMOKE_TEST
pause
goto MAIN_MENU

:DO_SMOKE_TEST
call :SECTION "M5 -- Smoke Test + Live Monitoring"

call :STEP "Running smoke test against %API_URL%..."
python "%PROJECT_DIR%smoke_test.py"
if errorlevel 1 (
    call :ERROR "Smoke test FAILED! Is the API running?"
    echo   Start API first with option [5] or [6]
    exit /b 1
)
call :SUCCESS "Smoke test passed!"

echo.
call :STEP "Running live monitoring batch (50 flows)..."
python "%PROJECT_DIR%smoke_test.py" --monitor
if errorlevel 1 (call :WARN "Monitor run encountered issues")
exit /b 0

:: ==============================================================================
:MLFLOW_TRAIN
call :SECTION "M1 -- MLflow Experiment Tracking"

python -c "import mlflow" >nul 2>&1
if errorlevel 1 (
    call :STEP "Installing MLflow..."
    python -m pip install mlflow -q
)
if not exist "%PROJECT_DIR%dataset\UNSW_NB15_training-set.csv" (
    call :ERROR "Dataset not found in dataset\ folder!"
    pause
    goto MAIN_MENU
)

call :STEP "Running training with MLflow logging..."
python "%PROJECT_DIR%train_with_mlflow.py"
if errorlevel 1 (
    call :ERROR "MLflow training failed!"
    pause
    goto MAIN_MENU
)
call :SUCCESS "MLflow run completed!"

echo.
set "LAUNCH_MLFLOW="
set /p "LAUNCH_MLFLOW=  Launch MLflow UI? [y/n]: "
if /i "%LAUNCH_MLFLOW%"=="y" (
    call :STEP "Starting MLflow UI at http://localhost:5000..."
    start "MLflow UI" cmd /k "mlflow ui --host 0.0.0.0 --port 5000"
    timeout /t 2 /nobreak >nul
    start http://localhost:5000
)
pause
goto MAIN_MENU

:: ==============================================================================
:OPEN_BROWSER
call :SECTION "Opening API Endpoints in Browser"
call :STEP "Checking if API is running..."
call :DO_HEALTH_CHECK
if errorlevel 1 (
    call :WARN "API not running. Start it first with option [5] or [6]"
    pause
    goto MAIN_MENU
)
echo.
echo   Opening browser tabs...
start %API_URL%/docs
timeout /t 1 /nobreak >nul
start %API_URL%/health
timeout /t 1 /nobreak >nul
start %API_URL%/metrics
call :SUCCESS "Opened: /docs  /health  /metrics"
pause
goto MAIN_MENU

:: ==============================================================================
:GITHUB_ACTIONS
call :SECTION "GitHub Actions -- CI/CD Pipeline Status"
echo   Repo: Knight-Node64/Botnet-Detection
echo.

gh --version >nul 2>&1
if not errorlevel 1 (
    call :STEP "Fetching workflow runs via gh CLI..."
    gh run list --repo Knight-Node64/Botnet-Detection --limit 5
    echo.
    set "OPEN_GH="
    set /p "OPEN_GH=  Open latest run in browser? [y/n]: "
    if /i "!OPEN_GH!"=="y" gh run view --repo Knight-Node64/Botnet-Detection --web
) else (
    call :STEP "GitHub CLI not found -- opening browser..."
    start https://github.com/Knight-Node64/Botnet-Detection/actions
    call :SUCCESS "Opened GitHub Actions page"
    echo.
    echo   Install GitHub CLI: winget install GitHub.cli  then: gh auth login
)

echo.
echo   CI/CD Pipeline Stages (on push to main):
echo     1. Setup Python 3.11
echo     2. pip install -r requirements.txt
echo     3. pytest -v tests/          (all must pass)
echo     4. docker build              (image created)
echo     5. docker run + /health      (container verified)
echo.
pause
goto MAIN_MENU

:: ==============================================================================
:CHECK_PREREQS
call :CHECK_PREREQS_SILENT
echo.
pause
goto MAIN_MENU

:CHECK_PREREQS_SILENT
call :SECTION "Prerequisites Check"
set "ALL_OK=1"

call :STEP "Python..."
python --version >nul 2>&1
if errorlevel 1 (
    call :FAIL "  X Python      -- NOT FOUND  (install: python.org)"
    set "ALL_OK=0"
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do call :PASS "  OK %%v"
)

call :STEP "pip..."
python -m pip --version >nul 2>&1
if errorlevel 1 (call :FAIL "  X pip         -- NOT FOUND") else (call :PASS "  OK pip")

call :STEP "Docker..."
docker --version >nul 2>&1
if errorlevel 1 (
    call :FAIL "  X Docker      -- NOT FOUND  (install: docker.com)"
    set "ALL_OK=0"
) else (
    for /f "tokens=1-3" %%a in ('docker --version') do call :PASS "  OK %%a %%b %%c"
)

call :STEP "kubectl..."
kubectl version --client >nul 2>&1
if errorlevel 1 (
    call :WARN "  ! kubectl    -- Not found  (optional, needed for K8s only)"
) else (
    call :PASS "  OK kubectl"
)

call :STEP "git..."
git --version >nul 2>&1
if errorlevel 1 (
    call :FAIL "  X git         -- NOT FOUND  (install: git-scm.com)"
) else (
    for /f "tokens=*" %%v in ('git --version') do call :PASS "  OK %%v"
)

call :STEP "GitHub CLI..."
gh --version >nul 2>&1
if errorlevel 1 (
    call :WARN "  ! GitHub CLI  -- Not found  (optional: winget install GitHub.cli)"
) else (
    call :PASS "  OK GitHub CLI"
)

call :STEP "Dataset files..."
if exist "%PROJECT_DIR%dataset\UNSW_NB15_training-set.csv" (
    if exist "%PROJECT_DIR%dataset\UNSW_NB15_testing-set.csv" (
        call :PASS "  OK Dataset CSVs found"
    ) else (
        call :FAIL "  X Testing CSV missing in dataset\"
        set "ALL_OK=0"
    )
) else (
    call :FAIL "  X Dataset CSVs missing in dataset\"
    echo       Download: https://www.kaggle.com/datasets/mrwellsdavid/unsw-nb15
    set "ALL_OK=0"
)

call :STEP "Trained model..."
if exist "%PROJECT_DIR%models\botnet_detector.joblib" (
    call :PASS "  OK models\botnet_detector.joblib"
) else (
    call :WARN "  ! Model not trained yet  (run option [3] to train)"
)

echo.
if "%ALL_OK%"=="1" (
    call :SUCCESS "All required prerequisites are satisfied!"
) else (
    call :ERROR "Some prerequisites are missing. Fix them before running the pipeline."
)
exit /b 0

:: ==============================================================================
:DO_HEALTH_CHECK
powershell -Command "try { $r = Invoke-RestMethod -Uri '%API_URL%/health' -TimeoutSec 5; if ($r.model_loaded) { Write-Host '  API healthy -- model: ' + $r.model_name } else { exit 1 } } catch { exit 1 }" 2>nul
exit /b %errorlevel%

:: ==============================================================================
:SHOW_BANNER
:: Switch to UTF-8 so braille + box-drawing chars render correctly
chcp 65001 >nul 2>&1
if exist "%PROJECT_DIR%banner.txt" (
    type "%PROJECT_DIR%banner.txt"
) else (
    echo +------------------------------------------------------------------------------------------+
    echo ^|                  Advanced Botnet Detection Tool -- MLOps Pipeline                        ^|
    echo ^|                   Repo: github.com/Knight-Node64/Botnet-Detection                        ^|
    echo +------------------------------------------------------------------------------------------+
)
echo.
exit /b 0

:: ==============================================================================
:SECTION
echo.
echo   +----------------------------------------------------------+
echo   ^|  %~1
echo   +----------------------------------------------------------+
echo.
exit /b 0

:STEP
echo   --^>  %~1
exit /b 0

:SUCCESS
echo   [OK]  %~1
exit /b 0

:WARN
echo   [!!]  %~1
exit /b 0

:ERROR
echo   [XX]  %~1
exit /b 0

:PASS
echo   %~1
exit /b 0

:FAIL
echo   %~1
exit /b 0

:EXIT
echo.
echo   Goodbye!
echo.
exit /b 0
