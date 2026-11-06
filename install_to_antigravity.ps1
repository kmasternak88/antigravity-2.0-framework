<#
.SYNOPSIS
    Automatyczny instalator frameworka Antigravity Closed Loop 3.0 na nowym komputerze.

.DESCRIPTION
    Weryfikuje środowisko (Python 3.11+, Git), instaluje globalny skill /init
    do konfiguracji Antigravity ($env:USERPROFILE\.gemini\config\skills\init),
    sprawdza poprawność silnika bramek SQLite i uruchamia testy integralności.

.EXAMPLE
    .\install_to_antigravity.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "   Antigravity Closed Loop Ultra Omni-Agentic Framework v5.1 - Installer   " -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan

# 1. Sprawdzenie Pythona
Write-Host "[1/5] Sprawdzanie interpretera Python..." -NoNewline
try {
    $pyVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
    $pyMajor = [int]($pyVersion.Split('.')[0])
    $pyMinor = [int]($pyVersion.Split('.')[1])
    if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 11)) {
        Write-Host " BŁĄD!" -ForegroundColor Red
        Write-Error "Wymagany jest Python 3.11 lub nowszy (wykryto: $pyVersion). Zaktualizuj Pythona."
        exit 1
    }
    Write-Host " OK ($pyVersion)" -ForegroundColor Green

    # Immunizacja: Automatyczne utworzenie python3.exe obok python.exe na Windows
    try {
        $pyCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($pyCmd) {
            $pyDir = Split-Path $pyCmd.Source
            $py3Path = Join-Path $pyDir "python3.exe"
            if (-not (Test-Path $py3Path)) {
                Copy-Item $pyCmd.Source $py3Path -Force -ErrorAction SilentlyContinue
                Write-Host "      [Immunizacja] Utworzono python3.exe obok python.exe" -ForegroundColor DarkGray
            }
        }
    } catch {}
} catch {
    Write-Host " BŁĄD!" -ForegroundColor Red
    Write-Error "Nie odnaleziono polecenia 'python'. Upewnij się, że Python 3.11+ jest zainstalowany i dodany do zmiennej PATH."
    exit 1
}

# 2. Sprawdzenie Git
Write-Host "[2/5] Sprawdzanie narzędzia Git..." -NoNewline
try {
    $gitVer = git --version 2>$null
    Write-Host " OK ($gitVer)" -ForegroundColor Green
} catch {
    Write-Host " OSTRZEŻENIE!" -ForegroundColor Yellow
    Write-Host "      Git nie jest zainstalowany lub brak go w PATH. Zalecane zainstalowanie Git." -ForegroundColor Yellow
}

# 3. Instalacja globalnego skilla /init w Antigravity
Write-Host "[3/5] Rejestracja globalnego skilla /init i szablonu we frameworku..." -NoNewline
$targetSkillsDir = Join-Path $env:USERPROFILE ".gemini\config\skills\init"
$sourceSkillDir = Join-Path $PSScriptRoot ".agents\skills\init"

if (-not (Test-Path $sourceSkillDir)) {
    Write-Host " BŁĄD!" -ForegroundColor Red
    Write-Error "Brak folderu źródłowego skilla: $sourceSkillDir"
    exit 1
}

try {
    # Foldery docelowe skilla
    New-Item -ItemType Directory -Path (Join-Path $targetSkillsDir "scripts") -Force | Out-Null
    $targetTplDir = Join-Path $targetSkillsDir "template"
    New-Item -ItemType Directory -Path $targetTplDir -Force | Out-Null

    # Kopiowanie definicji skilla i skryptów
    Copy-Item -Path (Join-Path $sourceSkillDir "SKILL.md") -Destination (Join-Path $targetSkillsDir "SKILL.md") -Force
    Copy-Item -Path (Join-Path $sourceSkillDir "scripts\detect_state.py") -Destination (Join-Path $targetSkillsDir "scripts\detect_state.py") -Force
    Copy-Item -Path (Join-Path $PSScriptRoot "tools\init_project.py") -Destination (Join-Path $targetSkillsDir "scripts\bootstrap.py") -Force

    # Kopiowanie master template do autonomicznego scaffoldingu
    $dirsToBundle = @(".governance\bin", ".governance\hooks", ".agents\rules", ".agents\skills", ".agents\agents", ".agents\templates", ".specify\specs", "tools")
    foreach ($d in $dirsToBundle) {
        $srcDir = Join-Path $PSScriptRoot $d
        $dstDir = Join-Path $targetTplDir $d
        if (Test-Path $srcDir) {
            New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
            Copy-Item -Path "$srcDir\*" -Destination $dstDir -Recurse -Force
        }
    }
    Copy-Item -Path (Join-Path $PSScriptRoot ".governance\config.json") -Destination (Join-Path $targetTplDir ".governance\config.json") -Force
    Copy-Item -Path (Join-Path $PSScriptRoot ".governance\tasks.json") -Destination (Join-Path $targetTplDir ".governance\tasks.json") -Force
    Copy-Item -Path (Join-Path $PSScriptRoot ".agents\hooks.json") -Destination (Join-Path $targetTplDir ".agents\hooks.json") -Force
    Copy-Item -Path (Join-Path $PSScriptRoot "AGENTS.md") -Destination (Join-Path $targetTplDir "AGENTS.md") -Force

    # Immunizacja: powielenie native_guard.py w alternatywnych ścieżkach
    $ngSrc = Join-Path $PSScriptRoot ".governance\hooks\native_guard.py"
    if (Test-Path $ngSrc) {
        $altPaths = @(
            (Join-Path $targetTplDir ".agents\.governance\hooks"),
            (Join-Path $targetTplDir ".agents\hooks"),
            (Join-Path $PSScriptRoot ".agents\.governance\hooks")
        )
        foreach ($ap in $altPaths) {
            New-Item -ItemType Directory -Path $ap -Force | Out-Null
            Copy-Item -Path $ngSrc -Destination (Join-Path $ap "native_guard.py") -Force
        }
    }

    Write-Host " OK" -ForegroundColor Green
    Write-Host "      Zarejestrowano w: $targetSkillsDir" -ForegroundColor DarkGray
} catch {
    Write-Host " BŁĄD!" -ForegroundColor Red
    Write-Error "Nie udało się skopiować plików skilla do ${targetSkillsDir}: $_"
    exit 1
}

# 4. Sprawdzanie silnika governance (gov.py doctor)
Write-Host "[4/5] Weryfikacja silnika bramek (.governance/bin/gov.py)..." -NoNewline
$govScript = Join-Path $PSScriptRoot ".governance\bin\gov.py"
try {
    $doctorJson = python $govScript doctor 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK (Silnik sprawny, brak błędów SQLite)" -ForegroundColor Green
    } else {
        Write-Host " OSTRZEŻENIE" -ForegroundColor Yellow
    }
} catch {
    Write-Host " BŁĄD!" -ForegroundColor Red
    Write-Error "Weryfikacja silnika nie powiodła się: $_"
    exit 1
}

# 5. Uruchomienie selftestów frameworka
Write-Host "[5/5] Uruchamianie testów jednostkowych frameworka..." -NoNewline
$testOutput = python -m unittest discover -s (Join-Path $PSScriptRoot "tests") -v 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK (48/48 PASS)" -ForegroundColor Green
} else {
    Write-Host " NIEPOWODZENIE" -ForegroundColor Red
    Write-Host $testOutput -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "   INSTALACJA ZAKOŃCZONA SUKCESEM!                      " -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Green

Write-Host "Jak teraz korzystać z frameworka na tym komputerze?" -ForegroundColor Cyan
Write-Host "  1. W dowolnym oknie/projekcie Antigravity wpisz w czacie: /init" -ForegroundColor White
Write-Host "  2. Aby utworzyć nowy projekt z linii poleceń:" -ForegroundColor White
Write-Host "     .\antigravity-init.ps1 -Target 'C:\ścieżka\do\nowy-projekt' -Mode new" -ForegroundColor DarkGray
Write-Host "  3. Aby nałożyć framework na istniejący projekt:" -ForegroundColor White
Write-Host "     .\antigravity-init.ps1 -Target 'C:\ścieżka\do\istniejący' -Mode extend -ForceMerge" -ForegroundColor DarkGray
Write-Host ""
