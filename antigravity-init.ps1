<#
.SYNOPSIS
    Jednoklikowy bootstrapper frameworka Antigravity Closed Loop 3.0.

.DESCRIPTION
    Automatycznie kopiuje i konfiguruje reguły, agentów, silnik governance,
    bramki i zadania w nowym lub istniejącym projekcie.
    Wspiera autodetekcję stacku (Node/TS, Python, Rust, Go) oraz bezpieczne scalanie reguł.

.PARAMETER Target
    Ścieżka docelowa do projektu (nowego lub istniejącego).

.PARAMETER Mode
    Tryb pracy: 'auto' (domyślny), 'new' (czysty nowy projekt), 'extend' (rozbudowa istniejącego).

.PARAMETER ForceMerge
    Bezpiecznie dołącza reguły v3 do istniejącego pliku AGENTS.md z kopią zapasową (.md.bak).

.PARAMETER DryRun
    Podgląd planu instalacji bez dokonywania zmian na dysku.

.EXAMPLE
    .\antigravity-init.ps1 -Target "C:\projekty\nowa-aplikacja" -Mode new
    .\antigravity-init.ps1 -Target "C:\projekty\istniejacy-system" -Mode extend -ForceMerge
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Target,

    [ValidateSet("auto", "new", "extend")]
    [string]$Mode = "auto",

    [switch]$ForceMerge,
    [switch]$DryRun
)

$scriptPath = Join-Path $PSScriptRoot "tools\init_project.py"
if (-not (Test-Path $scriptPath)) {
    Write-Error "Nie odnaleziono narzędzia: $scriptPath"
    exit 1
}

$cliArgs = @($scriptPath, "--target", $Target, "--mode", $Mode)
if ($ForceMerge) { $cliArgs += "--force-merge" }
if ($DryRun) { $cliArgs += "--dry-run" }

python @cliArgs
