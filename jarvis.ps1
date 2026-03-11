<#
.SYNOPSIS
    Global Multi-Agent Activator — "JARVIS"
.DESCRIPTION
    Run this from ANY project to instantly activate the multi-agent system.
    Copies all files, initializes memory, and starts agents automatically.
    
    The magic word is: jarvis
.EXAMPLE
    .\jarvis.ps1
    .\jarvis.ps1 -ProjectPath "C:\MyNewProject"
    .\jarvis.ps1 -Quiet
#>

[CmdletBinding()]
param(
    [string]$ProjectPath = ".",
    [switch]$Quiet,
    [switch]$Setup,
    [switch]$GlobalStatus,
    [switch]$Help
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$MasterRoot = $PSScriptRoot
$ActivateScript = Join-Path $MasterRoot "agent-activate.ps1"

function Play-Sound {
    param([string]$SoundName)
    $SoundPath = Join-Path $MasterRoot "sounds\$SoundName.wav"
    if (Test-Path $SoundPath) {
        try {
            [System.Media.SoundPlayer]::new($SoundPath).Play()
        } catch {}
    }
}

# Setup logic
if ($Setup) {
    Write-Host "[SETUP] Configuring JARVIS Core System..." -ForegroundColor Cyan
    $MasterRoot = $PSScriptRoot
    
    # 1. Add to PATH
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$MasterRoot*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$MasterRoot", "User")
        Write-Host "[OK] JARVIS added to PATH." -ForegroundColor Green
    }
    else {
        Write-Host "[INFO] JARVIS already in PATH." -ForegroundColor Gray
    }
    
    # 2. Set JARVIS_CORE variable
    [Environment]::SetEnvironmentVariable("JARVIS_CORE", $MasterRoot, "User")
    Write-Host "[OK] JARVIS_CORE set to $MasterRoot" -ForegroundColor Green
    
    # 3. Run Indexer
    Write-Host "[INDEX] Updating Skills Index..." -ForegroundColor Cyan
    $indexer = Join-Path $MasterRoot "index_skills.ps1"
    if (Test-Path $indexer) {
        & $indexer
    }
    
    Write-Host "`n[COMPLETED] JARVIS Core is ready!" -ForegroundColor Green
    Write-Host "Please RESTART your terminal to use 'jarvis' command from anywhere." -ForegroundColor Yellow
    Play-Sound "Как пожелаете "
    exit 0
}

# ============================================================================
# MAIN
# ============================================================================

if ($Help) {
    Get-Help $PSCommandPath
    exit 0
}

# ASCII Art Banner
Write-Host @"

   ██╗ █████╗ ███╗   ██╗    ██████╗ ██████╗ ███╗   ██╗████████╗███████╗
   ██║██╔══██╗████╗  ██║    ██╔══██╗██╔══██╗████╗  ██║╚══██╔══╝██╔════╝
   ██║███████║██╔██╗ ██║    ██████╔╝██████╔╝██╔██╗ ██║   ██║   █████╗  
██╗ ██║██╔══██║██║╚██╗██║    ██╔══██╗██╔══██╗██║╚██╗██║   ██║   ██╔══╝  
╚█╚██╔╝██║  ██║██║ ╚████║    ██████╔╝██║  ██║██║ ╚████║   ██║   ███████╗
 ╚══╝ ╚═╝  ╚═╝╚═╝  ╚═══╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝
                        Multi-Agent System Activator

"@ -ForegroundColor Cyan

Write-Host "  Magic Word: JARVIS" -ForegroundColor Gray
Write-Host "  Master: $MasterRoot" -ForegroundColor Gray
Write-Host "  Target: $(Resolve-Path $ProjectPath)`n" -ForegroundColor Gray

# Check master exists
if (-not (Test-Path $MasterRoot)) {
    Write-Host "[ERROR] Master directory not found: $MasterRoot" -ForegroundColor Red
    Write-Host "`nUpdate `$MasterRoot in jarvis.ps1 to point to your master installation." -ForegroundColor Yellow
    exit 1
}

# Global Status logic
if ($GlobalStatus) {
    $registryPath = Join-Path $MasterRoot "projects.json"
    if (-not (Test-Path $registryPath)) {
        Write-Host "[INFO] No projects registered yet." -ForegroundColor Gray
        exit 0
    }
    
    $registry = Get-Content $registryPath | ConvertFrom-Json
    $globalData = @{ projects = @() }
    
    Write-Host "`n--- GLOBAL AGENT STATUS ---" -ForegroundColor Cyan
    
    foreach ($p in $registry.projects) {
        Write-Host "`nProject: $($p.name)" -ForegroundColor White
        Write-Host "Path:    $($p.path)" -ForegroundColor Gray
        
        $pStats = @{ pending = 0; active = 0; completed = 0 }
        $pAgents = @()
        
        $tasksDir = Join-Path $p.path ".agent\tasks"
        if (Test-Path $tasksDir) {
            # Queue
            $qFile = Join-Path $tasksDir "queue.json"
            if (Test-Path $qFile) {
                $q = Get-Content $qFile | ConvertFrom-Json
                $pStats.pending = if ($q.tasks) { ($q.tasks | Where-Object { $_.status -eq "pending" }).Count } else { 0 }
            }
            # Active
            $aFile = Join-Path $tasksDir "active.json"
            if (Test-Path $aFile) {
                $a = Get-Content $aFile | ConvertFrom-Json
                $pStats.active = if ($a.activeTasks) { $a.activeTasks.Count } else { 0 }
                if ($a.activeTasks) {
                    foreach ($at in $a.activeTasks) { $pAgents += @{ role = $at.role; id = $at.agentId } }
                }
            }
            # Completed
            $cFile = Join-Path $tasksDir "completed.json"
            if (Test-Path $cFile) {
                $c = Get-Content $cFile | ConvertFrom-Json
                $pStats.completed = if ($c.completed) { $c.completed.Count } else { 0 }
            }
            
            $statusColor = if ($pStats.active -gt 0) { "Green" } else { "Gray" }
            Write-Host "Status:  $($pStats.active) agents working, $($pStats.pending) in queue" -ForegroundColor $statusColor
        }
        else {
            Write-Host "Status:  Not initialized" -ForegroundColor Red
        }
        
        $globalData.projects += @{
            name       = $p.name
            path       = $p.path
            lastActive = $p.lastActive
            stats      = $pStats
            agents     = $pAgents
        }
    }
    
    # Generate global-data.js for Dashboard
    $jsPath = Join-Path $MasterRoot "global-data.js"
    $json = $globalData | ConvertTo-Json -Depth 10
    "window.PROJECTS_DATA = $json;" | Set-Content $jsPath -Encoding UTF8
    
    Write-Host "`n[OK] Global Dashboard data updated." -ForegroundColor Green
    Write-Host "    Open: file://$MasterRoot\global-dashboard.html" -ForegroundColor Gray
    Write-Host "`n--- END ---" -ForegroundColor Cyan
    exit 0
}

# Run activator
if (Test-Path $ActivateScript) {
    $mode = if ($Setup) { "Update/Setup" } else { "Activation" }
    Write-Host "[INFO] Running $mode...`n" -ForegroundColor Cyan
    
    & $ActivateScript -ProjectPath $ProjectPath -Quiet:$Quiet
    
    # Activation complete - show success
    Play-Sound "Мы подключены и готовы"
    Write-Host "`n  ╔════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║  JARVIS: System Ready & Syncronized     ║" -ForegroundColor Green
    Write-Host "  ╚════════════════════════════════════════╝`n" -ForegroundColor Green
}
else {
    Write-Host "`n[ERROR] Activator not found: $ActivateScript" -ForegroundColor Red
    exit 1
}
