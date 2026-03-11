<#
.SYNOPSIS
    Multi-Agent System Initialization Script
.DESCRIPTION
    Initializes the multi-agent orchestration system in a new project.
    Creates all required directories, config files, and workflows.
.EXAMPLE
    .\agent-init.ps1
    .\agent-init.ps1 -ProjectName "MyProject"
#>

[CmdletBinding()]
param(
    [string]$ProjectName = "",
    [switch]$Force,
    [switch]$Help
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$ScriptRoot = $PSScriptRoot
$ProjectRoot = $ScriptRoot

# Default skills path (can be overridden)
$DefaultSkillsPath = "c:\Users\user\.tools\antigravity-awesome-skills"

# Directories to create
$DirsToCreate = @(
    ".agent",
    ".agent/workflows",
    ".agent/tasks",
    ".agent/context-cache",
    ".agent/logs",
    ".agent/communication",
    ".agent/adr",
    ".agent-memory"
)

# ============================================================================
# HELP
# ============================================================================

if ($Help) {
    Get-Help $PSCommandPath
    exit 0
}

# ============================================================================
# UTILITIES
# ============================================================================

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# ============================================================================
# INITIALIZATION
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   MULTI-AGENT SYSTEM INITIALIZATION   " -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if already initialized
if ((Test-Path ".agent\tasks\queue.json") -and (Test-Path ".agent-memory\state.md")) {
    if (-not $Force) {
        Write-Warning-Custom "Project already initialized."
        Write-Host "Use -Force to reinitialize.`n" -ForegroundColor Gray
        
        $response = Read-Host "Continue anyway? (y/n)"
        if ($response -ne "y") {
            exit 0
        }
    }
}

# ============================================================================
# CREATE DIRECTORIES
# ============================================================================

Write-Info "Creating directories..."

foreach ($dir in $DirsToCreate) {
    $fullPath = Join-Path $ProjectRoot $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Info "  Created: $dir"
    } else {
        Write-Info "  Exists: $dir"
    }
}

Write-Success "Directories created`n"

# ============================================================================
# CREATE TASK FILES
# ============================================================================

Write-Info "Creating task system files..."

# queue.json
$queueContent = @{
    version = "1.0"
    lastUpdate = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    tasks = @()
} | ConvertTo-Json -Depth 10

$queuePath = Join-Path $ProjectRoot ".agent\tasks\queue.json"
$queueContent | Set-Content $queuePath -Encoding UTF8
Write-Info "  Created: .agent/tasks/queue.json"

# active.json
$activeContent = @{
    activeTasks = @()
    lockedResources = @()
    lastSync = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json -Depth 10

$activePath = Join-Path $ProjectRoot ".agent\tasks\active.json"
$activeContent | Set-Content $activePath -Encoding UTF8
Write-Info "  Created: .agent/tasks/active.json"

# completed.json
$completedContent = @{
    completed = @()
    archivedCount = 0
} | ConvertTo-Json -Depth 10

$completedPath = Join-Path $ProjectRoot ".agent\tasks\completed.json"
$completedContent | Set-Content $completedPath -Encoding UTF8
Write-Info "  Created: .agent/tasks/completed.json"

Write-Success "Task system files created`n"

# ============================================================================
# CREATE MEMORY FILES
# ============================================================================

Write-Info "Creating memory files..."

# state.md
$projectNameToUse = if ($ProjectName) { $ProjectName } else { Split-Path $ProjectRoot -Leaf }

$stateContent = @"
# Agent State

## Last Sync
$((Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))

## Project: $projectNameToUse

## Multi-Agent System Status
- **Active Agents**: 0
- **Pending Tasks**: 0
- **Completed Tasks**: 0

## System Info
- **Auto-Connect**: Enabled
- **Skill Router**: Active
- **Workflows**: auto-connect, skill-router, multi-agent-orchestrate
- **Last Update**: $((Get-Date).ToString("dd MMMM yyyy"))

---

## Current Tasks
*No active tasks*

## Completed
*No completed tasks*

## Next Steps
- Add tasks using: .\agent.ps1 -Task "Description" -Roles Architect,Designer
- Auto-connect agents: .\agent.ps1 -AutoConnect -Role Architect
- Check status: .\agent.ps1 -Status
"@

$statePath = Join-Path $ProjectRoot ".agent-memory\state.md"
$stateContent | Set-Content $statePath -Encoding UTF8
Write-Info "  Created: .agent-memory/state.md"

# knowledge_graph.json
$knowledgeContent = @{
    version = "1.0"
    lastUpdate = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    nodes = @()
    edges = @()
} | ConvertTo-Json -Depth 10

$knowledgePath = Join-Path $ProjectRoot ".agent-memory\knowledge_graph.json"
$knowledgeContent | Set-Content $knowledgePath -Encoding UTF8
Write-Info "  Created: .agent-memory/knowledge_graph.json"

# roles.md
$rolesContent = @"
# Agent Roles

## Available Roles

| Role | Description | Skills |
|------|-------------|--------|
| **Architect** | System design, ADR, structure | architecture, architecture-patterns, ADR |
| **Designer** | UI/UX, styles, themes | ui-ux-design, accessibility, responsive |
| **Coder** | Implementation, features, bugs | app-builder, code-quality, debugging |
| **QA** | Testing, validation, review | agent-evaluation, code-review, test |
| **MemoryKeeper** | Memory sync, context | agent-memory-mcp, knowledge-graph |

## Auto-Detection Keywords

- **Architect**: architecture, design, structure, adr, plan
- **Designer**: ui, ux, design, style, theme, css, interface
- **Coder**: code, implement, function, bug, feature
- **QA**: test, check, validation, review, verify
- **MemoryKeeper**: memory, context, sync, state, knowledge
"@

$rolesPath = Join-Path $ProjectRoot ".agent-memory\roles.md"
$rolesContent | Set-Content $rolesPath -Encoding UTF8
Write-Info "  Created: .agent-memory/roles.md"

Write-Success "Memory files created`n"

# ============================================================================
# COPY WORKFLOWS
# ============================================================================

Write-Info "Setting up workflows..."

$WorkflowsSource = Join-Path $ScriptRoot ".agent\workflows"
$WorkflowsDest = Join-Path $ProjectRoot ".agent\workflows"

if (Test-Path $WorkflowsSource) {
    # Copy workflow files
    Copy-Item -Path "$WorkflowsSource\*" -Destination $WorkflowsDest -Force
    Write-Success "Workflows copied from: $WorkflowsSource"
} else {
    Write-Warning-Custom "Workflows source not found: $WorkflowsSource"
    Write-Info "Creating minimal workflows..."
    
    # Create minimal auto-connect.md
    $autoConnectContent = @"
# Auto-Connect Workflow

Agents auto-connect when:
1. .agent-signal.md exists with high/urgent priority
2. Task in queue.json with status "pending"
3. CLI command: .\agent.ps1 -AutoConnect -Role <Role>

## Process
1. Detect signal
2. Read context (.agent-memory/state.md)
3. Select skills (skill-router.md)
4. Claim task (update queue.json)
5. Execute role
6. Sync memory
"@
    $autoConnectPath = Join-Path $WorkflowsDest "auto-connect.md"
    $autoConnectContent | Set-Content $autoConnectPath -Encoding UTF8
    Write-Info "  Created: .agent/workflows/auto-connect.md"
}

Write-Success "Workflows ready`n"

# ============================================================================
# CREATE COMMUNICATION CHANNEL
# ============================================================================

Write-Info "Creating communication channel..."

$channelContent = @"
# Communication Channel

## Active Session ($((Get-Date).ToString("yyyy-MM-dd")))

---

### [$(Get-Date -Format "HH:mm")] System -> All
> Multi-Agent System initialized.
> Ready for task assignments.

---

## Archived Messages

"@

$channelPath = Join-Path $ProjectRoot ".agent\communication\channel.md"
$channelContent | Set-Content $channelPath -Encoding UTF8
Write-Info "  Created: .agent/communication/channel.md"

Write-Success "Communication channel ready`n"

# ============================================================================
# CREATE AGENT SIGNAL (TEMPLATE)
# ============================================================================

Write-Info "Creating agent signal template..."

$signalContent = @"
# Agent Signal

**Created:** $((Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))

---

## Active Task

**Task description here**

---

## Required Roles

- [ ] **Architect**
- [ ] **Designer**
- [ ] **Coder**
- [ ] **QA**
- [ ] **MemoryKeeper**

---

## Priority

**normal**

> Change to: urgent | high | normal | low

---

## Instructions for Agents

1. Read this file to determine your role
2. Check .agent/tasks/queue.json for pending tasks
3. After work: update .agent-memory/state.md

---

## Auto-Connect Config

```json
{
  "enabled": true,
  "pollInterval": 30000,
  "roles": ["Architect", "Designer", "Coder", "QA", "MemoryKeeper"],
  "skipLowPriority": true
}
```

---

## Session Log

| Time | Agent | Role | Action |
|------|-------|------|--------|
| $((Get-Date).ToString("HH:mm")) | System | - | Signal created |

"@

$signalPath = Join-Path $ProjectRoot ".agent-signal.md"
if (-not (Test-Path $signalPath)) {
    $signalContent | Set-Content $signalPath -Encoding UTF8
    Write-Info "  Created: .agent-signal.md"
} else {
    Write-Info "  Exists: .agent-signal.md"
}

Write-Success "Agent signal ready`n"

# ============================================================================
# CREATE LOG FILE
# ============================================================================

Write-Info "Creating log file..."

$logPath = Join-Path $ProjectRoot ".agent\logs\agent.log"
if (-not (Test-Path $logPath)) {
    $logHeader = "[INFO] $((Get-Date).ToString("yyyy-MM-dd HH:mm:ss")) [INIT] Agent system initialized`n"
    $logHeader | Set-Content $logPath -Encoding UTF8
    Write-Info "  Created: .agent/logs/agent.log"
} else {
    Write-Info "  Exists: .agent/logs/agent.log"
}

Write-Success "Log file ready`n"

# ============================================================================
# CREATE CONTEXT CACHE
# ============================================================================

Write-Info "Creating context cache..."

$cacheContent = @{
    cacheVersion = "1.0"
    lastUpdate = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    projectRoot = $ProjectRoot
    skillsPath = $DefaultSkillsPath
    presets = @{}
} | ConvertTo-Json -Depth 10

$cachePath = Join-Path $ProjectRoot ".agent\context-cache\skill-presets.json"
$cacheContent | Set-Content $cachePath -Encoding UTF8
Write-Info "  Created: .agent/context-cache/skill-presets.json"

Write-Success "Context cache ready`n"

# ============================================================================
# SUMMARY
# ============================================================================

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "   INITIALIZATION COMPLETE            " -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Project: $projectNameToUse`n" -ForegroundColor Cyan

Write-Host "Quick Start:" -ForegroundColor Yellow
Write-Host "  1. Add task:    .\agent.ps1 -Task `"My Task`" -Roles Architect,Designer -Priority high" -ForegroundColor Gray
Write-Host "  2. Connect:     .\agent.ps1 -AutoConnect -Role Architect" -ForegroundColor Gray
Write-Host "  3. Status:      .\agent.ps1 -Status`n" -ForegroundColor Gray

Write-Host "Files created:" -ForegroundColor Yellow
Write-Host "  - agent.ps1 (main CLI)" -ForegroundColor Gray
Write-Host "  - .agent-signal.md (trigger)" -ForegroundColor Gray
Write-Host "  - .agent/tasks/queue.json (task queue)" -ForegroundColor Gray
Write-Host "  - .agent-memory/state.md (memory)" -ForegroundColor Gray
Write-Host "  - .agent/workflows/ (workflows)`n" -ForegroundColor Gray

Write-Host "Documentation:" -ForegroundColor Yellow
Write-Host "  - AGENT_SETUP.md - Full setup guide" -ForegroundColor Gray
Write-Host "  - .agent/workflows/auto-connect.md - Auto-connect details" -ForegroundColor Gray
Write-Host "  - .agent/workflows/skill-router.md - Skill selection`n" -ForegroundColor Gray

Write-Success "Ready to use!`n"
