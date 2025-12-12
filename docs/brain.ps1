param(
    [Parameter(Position=0)]
    [ValidateSet("dev", "prod", "test-local", "test-docker", "logs-dev", "logs-prod", "down-dev", "down-prod", "help")]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

$composeBase = "docker-compose.yml"
$composeDev  = "docker-compose.dev.yml"
$composeProd = "docker-compose.prod.yml"

function Show-Help {
    Write-Host ""
    Write-Host "BRAIN Backend – PowerShell Helper" -ForegroundColor Cyan
    Write-Host "----------------------------------"
    Write-Host "brain.ps1 dev          # Dev-Stack starten (Reload, Port 8010)"
    Write-Host "brain.ps1 down-dev     # Dev-Stack stoppen"
    Write-Host "brain.ps1 logs-dev     # Dev-Backend-Logs verfolgen"
    Write-Host ""
    Write-Host "brain.ps1 prod         # Prod-Stack starten (Port 8000, detached)"
    Write-Host "brain.ps1 down-prod    # Prod-Stack stoppen"
    Write-Host "brain.ps1 logs-prod    # Prod-Backend-Logs verfolgen"
    Write-Host ""
    Write-Host "brain.ps1 test-local   # PyTests lokal im venv ausführen"
    Write-Host "brain.ps1 test-docker  # PyTests im Backend-Container ausführen"
    Write-Host ""
}

switch ($Command) {
    "dev" {
        Write-Host "Starte DEV-Stack..." -ForegroundColor Green
        docker compose -f $composeBase -f $composeDev up --build
    }
    "down-dev" {
        Write-Host "Stoppe DEV-Stack..." -ForegroundColor Yellow
        docker compose -f $composeBase -f $composeDev down
    }
    "logs-dev" {
        Write-Host "Zeige DEV-Backend-Logs..." -ForegroundColor Cyan
        docker compose -f $composeBase -f $composeDev logs -f backend
    }
    "prod" {
        Write-Host "Starte PROD-Stack (detached)..." -ForegroundColor Green
        docker compose -f $composeBase -f $composeProd up -d --build
    }
    "down-prod" {
        Write-Host "Stoppe PROD-Stack..." -ForegroundColor Yellow
        docker compose -f $composeBase -f $composeProd down
    }
    "logs-prod" {
        Write-Host "Zeige PROD-Backend-Logs..." -ForegroundColor Cyan
        docker compose -f $composeBase -f $composeProd logs -f backend
    }
    "test-local" {
        Write-Host "Führe PyTests lokal im venv aus..." -ForegroundColor Green
        # Annahme: du hast vorher .\.venv\Scripts\Activate.ps1 ausgeführt
        pytest
    }
    "test-docker" {
        Write-Host "Führe PyTests im Backend-Container aus..." -ForegroundColor Green
        docker compose -f $composeBase -f $composeDev run --rm backend pytest
    }
    Default {
        Show-Help
    }
}
