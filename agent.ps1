<#
.SYNOPSIS
    Multi-Agent Orchestration CLI for automatic agent management
.DESCRIPTION
    Allows agents to automatically connect to the project, take tasks from queue,
    sync memory and coordinate work between each other.

    Works in any project after initialization with agent-init.ps1
.EXAMPLE
    .\agent.ps1 -AutoConnect -Role Architect
    .\agent.ps1 -Status
    .\agent.ps1 -Task "New feature" -Roles Architect,Designer -Priority high
    .\agent.ps1 -Init
.PARAMETER Init
    Run initialization in current project
.PARAMETER ProjectPath
    Path to project for initialization (default: current directory)
#>

[CmdletBinding()]
param(
    [switch]$AutoConnect,
    [switch]$Status,
    [switch]$Orchestrate,
    [switch]$SyncMemory,
    [switch]$Conflicts,
    [switch]$Init,
    [string]$ProjectPath,
    [string]$Role,
    [string]$Task,
    [string[]]$Roles,
    [string]$Priority = "normal",
    [string]$ReassignTaskId,
    [string]$UnlockFile,
    [switch]$Force,
    [switch]$Help
)

# ============================================================================
# CONFIGURATION & PATH DETECTION
# ============================================================================

$ScriptRoot = $PSScriptRoot
# Detect if we are in the Core Engine or in a project
$isCore = Test-Path (Join-Path $ScriptRoot "CORE_MANIFESTO.md")

if ($isCore) {
    $CorePath = $ScriptRoot
    $ProjectRoot = Get-Location
}
else {
    # If copied to a project, it might not know where the core is
    # We'll try to find it via environment variable or default path
    $CorePath = [Environment]::GetEnvironmentVariable("JARVIS_CORE", "User")
    if (-not $CorePath) { $CorePath = "d:\!AiSite\_agent_core" } # Fallback
    $ProjectRoot = $ScriptRoot
}

$AgentDir = Join-Path $ProjectRoot ".agent"
$TasksDir = Join-Path $AgentDir "tasks"
$MemoryDir = Join-Path $ProjectRoot ".agent-memory"
$LogsDir = Join-Path $AgentDir "logs"
$CacheDir = Join-Path $AgentDir "context-cache"

$QueueFile = Join-Path $TasksDir "queue.json"
$ActiveFile = Join-Path $TasksDir "active.json"
$CompletedFile = Join-Path $TasksDir "completed.json"
$StateFile = Join-Path $MemoryDir "state.md"
$SignalFile = Join-Path $ProjectRoot ".agent-signal.md"
$LogFile = Join-Path $LogsDir "agent.log"

$GlobalWorkflows = Join-Path $CorePath ".agent\workflows"
$DashboardDataFile = Join-Path $ProjectRoot "agent-data.js"

# ============================================================================
# ============================================================================
# UTILITIES
# ============================================================================

function Play-Sound {
    param([string]$SoundName)
    $SoundPath = Join-Path $CorePath "sounds\$SoundName.wav"
    if (Test-Path $SoundPath) {
        try {
            [System.Media.SoundPlayer]::new($SoundPath).Play()
        }
        catch {}
    }
}

function Update-Dashboard {
    $queue = Get-JsonFile $QueueFile
    $active = Get-JsonFile $ActiveFile
    $completed = Get-JsonFile $CompletedFile
    $logs = if (Test-Path $LogFile) { Get-Content $LogFile | Select-Object -Last 10 } else { @() }
    
    $pending = if ($queue.tasks) { ($queue.tasks | Where-Object { $_.status -eq "pending" }).Count } else { 0 }
    $activeCount = if ($active.activeTasks) { $active.activeTasks.Count } else { 0 }
    $doneCount = if ($completed.completed) { $completed.completed.Count } else { 0 }
    
    $agents = @()
    if ($active.activeTasks) {
        foreach ($at in $active.activeTasks) {
            $agents += @{ id = $at.agentId; role = $at.role; status = $at.currentStep }
        }
    }
    
    $data = @{
        project = @{ name = (Split-Path $ProjectRoot -Leaf); lastSync = (Get-Date -Format "HH:mm:ss") }
        stats   = @{ pending = $pending; active = $activeCount; completed = $doneCount }
        agents  = $agents
        logs    = $logs
    }
    
    $json = $data | ConvertTo-Json -Depth 10
    $jsContent = "window.JARVIS_DATA = $json;"
    $jsContent | Set-Content $DashboardDataFile -Encoding UTF8
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Component = "CLI"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$Level] $timestamp [$Component] $Message"
    
    # Console output
    switch ($Level) {
        "ERROR" { Write-Host $logEntry -ForegroundColor Red }
        "WARN" { Write-Host $logEntry -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $logEntry -ForegroundColor Green }
        default { Write-Host $logEntry -ForegroundColor Cyan }
    }
    
    # File logging
    try {
        if (-not (Test-Path $LogFile)) {
            New-Item -ItemType File -Path $LogFile -Force | Out-Null
        }
        Add-Content -Path $LogFile -Value $logEntry -Encoding UTF8 -ErrorAction SilentlyContinue
    }
    catch {}
}

function Get-JsonFile {
    param([string]$Path)
    if (Test-Path $Path) {
        return Get-Content $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    return $null
}

function Set-JsonFile {
    param(
        [string]$Path,
        [object]$Data
    )
    $Data | ConvertTo-Json -Depth 10 | Set-Content $Path -Encoding UTF8
}

function Get-ISOTimestamp {
    return Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
}

function Get-TaskId {
    return "task-{0:D3}" -f (Get-Random -Maximum 999)
}

# ============================================================================
# TASK MANAGEMENT FUNCTIONS
# ============================================================================

function Add-Task {
    param(
        [string]$Title,
        [string]$Description,
        [string[]]$RequiredRoles,
        [string]$Priority = "normal"
    )

    $queue = Get-JsonFile $QueueFile
    if (-not $queue) {
        $queue = @{
            version    = "1.0"
            lastUpdate = (Get-ISOTimestamp)
            tasks      = @()
        }
    }

    # Convert RequiredRoles to ArrayList for proper handling
    $rolesList = New-Object System.Collections.ArrayList
    foreach ($r in $RequiredRoles) {
        # Split by comma in case roles are passed as single string
        $r.Split(',') | ForEach-Object {
            $trimmed = $_.Trim()
            if ($trimmed) {
                $rolesList.Add($trimmed) | Out-Null
            }
        }
    }

    $newTask = @{
        id            = (Get-TaskId)
        title         = $Title
        description   = $Description
        status        = "pending"
        priority      = $Priority
        requiredRoles = $rolesList.ToArray()
        assignedTo    = $null
        createdAt     = (Get-ISOTimestamp)
        dueAt         = (Get-Date).AddHours(8).ToString("yyyy-MM-ddTHH:mm:ssZ")
        dependencies  = @()
        metadata      = @{
            files = @()
            tags  = @("manual")
        }
    }

    $queue.tasks += $newTask
    $queue.lastUpdate = (Get-ISOTimestamp)
    Set-JsonFile $QueueFile $queue

    Update-Dashboard
    Write-Log "Task added: $($newTask.id) - $Title" "SUCCESS" "TASK"
    Play-Sound "Есть"
    return $newTask.id
}

function Get-NextPendingTask {
    param(
        [string]$Role
    )
    
    $queue = Get-JsonFile $QueueFile
    if (-not $queue -or -not $queue.tasks) {
        return $null
    }
    
    # Sort by priority
    $priorityOrder = @{ "urgent" = 0; "high" = 1; "normal" = 2; "low" = 3 }
    
    $pendingTasks = $queue.tasks | Where-Object { 
        $_.status -eq "pending" -and 
        $_.requiredRoles -contains $Role
    } | Sort-Object { $priorityOrder[$_.priority] }
    
    if ($pendingTasks) {
        return $pendingTasks[0]
    }
    return $null
}

function Claim-Task {
    param(
        [string]$TaskId,
        [string]$AgentId,
        [string]$Role
    )
    
    $queue = Get-JsonFile $QueueFile
    $active = Get-JsonFile $ActiveFile
    
    if (-not $active) {
        $active = @{
            activeTasks     = @()
            lockedResources = @()
            lastSync        = (Get-ISOTimestamp)
        }
    }
    
    # Update queue
    $task = $queue.tasks | Where-Object { $_.id -eq $TaskId }
    if ($task) {
        $task.status = "active"
        $task.assignedTo = $AgentId
    }
    
    # Add to active
    $activeTask = @{
        taskId            = $TaskId
        agentId           = $AgentId
        role              = $Role
        startedAt         = (Get-ISOTimestamp)
        estimatedDuration = 3600
        currentStep       = "Initialization"
        progress          = 0
    }
    
    $active.activeTasks += $activeTask
    $active.lastSync = (Get-ISOTimestamp)
    
    Set-JsonFile $QueueFile $queue
    Set-JsonFile $ActiveFile $active
    
    Update-Dashboard
    Write-Log "Task $TaskId assigned to $AgentId ($Role)" "SUCCESS" "ORCHESTRATE"
}

function Complete-Task {
    param(
        [string]$TaskId,
        [string]$AgentId,
        [string]$Result = "success"
    )
    
    $queue = Get-JsonFile $QueueFile
    $active = Get-JsonFile $ActiveFile
    $completed = Get-JsonFile $CompletedFile
    
    if (-not $completed) {
        $completed = @{ completed = @(); archivedCount = 0 }
    }
    
    # Find task in queue
    $task = $queue.tasks | Where-Object { $_.id -eq $TaskId }
    if ($task) {
        $task.status = "completed"
        
        # Move to completed
        $completedTask = @{
            taskId      = $TaskId
            title       = $task.title
            completedAt = (Get-ISOTimestamp)
            agent       = $AgentId
            result      = $Result
            artifacts   = @()
            timeSpent   = 0
        }
        
        $completed.completed += $completedTask
        $completed.archivedCount = $completed.completed.Count
        
        # Remove from active
        $active.activeTasks = $active.activeTasks | Where-Object { $_.taskId -ne $TaskId }
        
        $queue.lastUpdate = (Get-ISOTimestamp)
        $active.lastSync = (Get-ISOTimestamp)
        
        Set-JsonFile $QueueFile $queue
        Set-JsonFile $ActiveFile $active
        Set-JsonFile $CompletedFile $completed
        
        Update-Dashboard
        Write-Log "Task $TaskId completed ($Result)" "SUCCESS" "ORCHESTRATE"
        Play-Sound "Запрос выполнен, сэр"
    }
}

# ============================================================================
# AUTO-CONNECT FUNCTIONS
# ============================================================================

function Test-AgentSignal {
    if (Test-Path $SignalFile) {
        $content = Get-Content $SignalFile -Raw -Encoding UTF8
        # Check priority
        if ($content -match "Priority:\s*(urgent|high)") {
            return $true
        }
    }
    return $false
}

function Get-AgentRole {
    param([string]$TaskDescription)
    
    $keywords = @{
        "Architect"    = @("architecture", "design", "structure", "adr", "plan")
        "Designer"     = @("ui", "ux", "design", "style", "theme", "css", "interface")
        "Coder"        = @("code", "implement", "function", "bug", "feature")
        "QA"           = @("test", "check", "validation", "review", "verify")
        "MemoryKeeper" = @("memory", "context", "sync", "state", "knowledge")
        "DevOps"       = @("deploy", "ci", "cd", "docker", "pipeline", "env", "infrastructure")
        "Copywriter"   = @("text", "documentation", "readme", "content", "write", "label")
        "Security"     = @("security", "audit", "vulnerability", "auth", "encryption", "leak")
        "Researcher"   = @("research", "compare", "benchmark", "study", "feasibility")
    }
    
    $lowerDesc = $TaskDescription.ToLower()
    
    foreach ($role in $keywords.Keys) {
        foreach ($keyword in $keywords[$role]) {
            if ($lowerDesc -like "*$keyword*") {
                return $role
            }
        }
    }
    
    return "Coder" # Default role
}

function Load-Skills {
    param(
        [string]$Role,
        [string]$TaskDescription
    )
    
    Write-Log "Loading skills for role: $Role" "INFO" "SKILL-ROUTER"
    
    # 1. Start with presets
    $presets = @{
        "Architect"    = @("architecture", "architecture-patterns", "architecture-decision-records", "architect-review", "api-design-principles")
        "Designer"     = @("ui-ux-design", "accessibility-compliance-accessibility-audit", "responsive-design")
        "Coder"        = @("app-builder", "code-quality", "refactoring", "debugging")
        "QA"           = @("agent-evaluation", "api-fuzzing-bug-bounty", "code-review")
        "MemoryKeeper" = @("agent-memory-mcp", "agent-memory-systems", "knowledge-graph")
        "DevOps"       = @("infrastructure", "deployment", "github-actions", "docker-optimization")
        "Copywriter"   = @("documentation-generator", "content-strategy", "seo-optimization")
        "Security"     = @("security-audit", "encryption-standards", "auth-protocols")
        "Researcher"   = @("tech-comparison", "feasibility-study", "lit-review")
    }
    
    $skills = New-Object System.Collections.Generic.List[string]
    foreach ($s in $presets[$Role]) { $skills.Add($s) }
    
    # 2. Smart Search from Global Index
    $indexPath = Join-Path $CorePath "skills_index.json"
    if (Test-Path $indexPath) {
        $index = Get-Content $indexPath -Raw | ConvertFrom-Json
        $lowerDesc = $TaskDescription.ToLower()
        
        foreach ($skill in $index.skills) {
            $sName = $skill.name.ToLower()
            if ($lowerDesc -like "*$sName*" -and -not $skills.Contains($skill.name)) {
                $skills.Add($skill.name)
                Write-Log "  Smart Match: $($skill.name) (found in index)" "SUCCESS" "SKILL-ROUTER"
            }
        }
    }
    
    if ($skills.Count -gt 0) {
        Write-Log "Total skills identified: $($skills.Count)" "INFO" "SKILL-ROUTER"
        
        # Check if workflows exist locally or globally
        foreach ($s in $skills) {
            $localWf = Join-Path $AgentDir "workflows\$s.md"
            $globalWf = Join-Path $GlobalWorkflows "$s.md"
            
            if (-not (Test-Path $localWf) -and (Test-Path $globalWf)) {
                # In the future we could symlink here
                Write-Log "  Global Skill: $s (Available in Core)" "INFO" "SKILL-ROUTER"
            }
        }
        
        # Cache skills
        $cache = @{
            cacheVersion = "1.0"
            lastUpdate   = (Get-ISOTimestamp)
            role         = $Role
            skills       = $skills.ToArray()
            coreInfo     = @{ path = $CorePath; version = "1.0-alpha" }
        }
        
        $cacheFile = Join-Path $CacheDir "skill-presets.json"
        $cache | ConvertTo-Json | Set-Content $cacheFile -Encoding UTF8
        
        return $skills.ToArray()
    }
    
    return @()
}

function Connect-Agent {
    param(
        [string]$AgentId,
        [string]$Role
    )
    
    Write-Log "=== AGENT CONNECT ===" "INFO" "CONNECT"
    Write-Log "Agent: $AgentId" "INFO" "CONNECT"
    Write-Log "Role: $Role" "INFO" "CONNECT"
    
    # Check task queue
    $task = Get-NextPendingTask -Role $Role
    
    if ($task) {
        Write-Log "Found task: $($task.id) - $($task.title)" "INFO" "CONNECT"
        Write-Log "Priority: $($task.priority)" "INFO" "CONNECT"
        
        # Load skills
        Load-Skills -Role $Role -TaskDescription $task.description
        
        # Claim task
        Claim-Task -TaskId $task.id -AgentId $AgentId -Role $Role
        
        # Persona Guidance
        $personaPath = Join-Path $CorePath ".agent\personas\$Role.md"
        if (Test-Path $personaPath) {
            Write-Log "Persona found: $Role. Please read your instructions in $personaPath" "INFO" "CONNECT"
        }

        Write-Log "=== AGENT CONNECTED AND READY ===" "SUCCESS" "CONNECT"
        Play-Sound "К вашим услугам сэр"
        return @{
            connected = $true
            task      = $task
            role      = $Role
        }
    }
    else {
        Write-Log "No pending tasks for role $Role" "WARN" "CONNECT"
        return @{
            connected = $false
            task      = $null
            role      = $Role
        }
    }
}

# ============================================================================
# MEMORY SYNC FUNCTIONS
# ============================================================================

function Sync-Memory {
    Write-Log "Syncing memory..." "INFO" "MEMORY"
    
    # Get stats
    $queue = Get-JsonFile $QueueFile
    $active = Get-JsonFile $ActiveFile
    $completed = Get-JsonFile $CompletedFile
    
    $pendingCount = if ($queue.tasks) { ($queue.tasks | Where-Object { $_.status -eq "pending" }).Count } else { 0 }
    $activeCount = if ($active.activeTasks) { $active.activeTasks.Count } else { 0 }
    $completedCount = if ($completed.completed) { $completed.completed.Count } else { 0 }
    
    $content = @"
# Agent State

## Last Sync
$((Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))

## Multi-Agent System Status
- **Active Agents**: $activeCount
- **Pending Tasks**: $pendingCount
- **Completed Tasks**: $completedCount

## Current Tasks
$(if ($active.activeTasks) {
    $active.activeTasks | ForEach-Object {
        "- **$($_.taskId)**: $($_.role) - $($_.currentStep) ($($_.progress)%)"
    } | Out-String
} else {
    "*No active tasks*"
})

## System Info
- **Auto-Connect**: Enabled
- **Skill Router**: Active
- **Workflows**: auto-connect, skill-router, multi-agent-orchestrate
- **Last Update**: $((Get-Date).ToString("dd MMMM yyyy"))

---

## Completed
$(if ($completed.completed) {
    $completed.completed | Select-Object -Last 5 | ForEach-Object {
        "- [x] $($_.title) - $($_.agent)"
    } | Out-String
} else {
    "*No completed tasks*"
})

## Next Steps
- Monitor queue for new tasks
- Auto-connect agents based on task requirements
- Sync memory after each task completion
"@
    
    $content | Set-Content $StateFile -Encoding UTF8
    Update-Dashboard
    Write-Log "Memory synced: $StateFile" "SUCCESS" "MEMORY"
}

# ============================================================================
# STATUS AND MONITORING FUNCTIONS
# ============================================================================

function Show-Status {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "   MULTI-AGENT ORCHESTRATION STATUS   " -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    # Tasks
    $queue = Get-JsonFile $QueueFile
    $active = Get-JsonFile $ActiveFile
    $completed = Get-JsonFile $CompletedFile
    
    Write-Host "TASKS:" -ForegroundColor Yellow
    if ($queue.tasks) {
        $pending = ($queue.tasks | Where-Object { $_.status -eq "pending" }).Count
        $activeTasks = ($queue.tasks | Where-Object { $_.status -eq "active" }).Count
        $done = ($queue.tasks | Where-Object { $_.status -eq "completed" }).Count
        Write-Host "   Pending:   $pending" -ForegroundColor Gray
        Write-Host "   Active:    $activeTasks" -ForegroundColor Green
        Write-Host "   Completed: $done" -ForegroundColor Cyan
    }
    else {
        Write-Host "   No tasks" -ForegroundColor Gray
    }
    
    Write-Host "`nACTIVE AGENTS:" -ForegroundColor Yellow
    if ($active.activeTasks) {
        foreach ($agentTask in $active.activeTasks) {
            $emoji = switch ($agentTask.role) {
                "Architect" { "[ARCH]" }
                "Designer" { "[DSN]" }
                "Coder" { "[COD]" }
                "QA" { "[QA]" }
                "MemoryKeeper" { "[MEM]" }
                default { "[AGT]" }
            }
            Write-Host "   $emoji $($agentTask.agentId): $($agentTask.role) - $($agentTask.currentStep)" -ForegroundColor Cyan
        }
    }
    else {
        Write-Host "   No active agents" -ForegroundColor Gray
    }
    
    Write-Host "`nFILES:" -ForegroundColor Yellow
    Write-Host "   Signal:  $(if (Test-Path $SignalFile) { '[OK]' } else { '[--]' }) $SignalFile"
    Write-Host "   Queue:   $(if (Test-Path $QueueFile) { '[OK]' } else { '[--]' }) $QueueFile"
    Write-Host "   Memory:  $(if (Test-Path $StateFile) { '[OK]' } else { '[--]' }) $StateFile"
    
    Write-Host "`n========================================`n" -ForegroundColor Cyan
}

# ============================================================================
# MAIN LOGIC
# ============================================================================

function Main {
    # Initialize
    if (-not (Test-Path $LogsDir)) {
        New-Item -ItemType Directory -Path $LogsDir | Out-Null
    }

    Write-Log "Agent CLI started" "INFO" "CLI"

    if ($Help) {
        Get-Help $PSCommandPath
        return
    }

    # Init command - run initialization script
    if ($Init) {
        $initScript = Join-Path $ProjectRoot "agent-init.ps1"
        if (Test-Path $initScript) {
            Write-Log "Running initialization..." "INFO" "INIT"
            & $initScript
        }
        else {
            Write-Log "agent-init.ps1 not found!" "ERROR" "INIT"
            Write-Host "Download from: d:\!AiSite\toplivo\agent-init.ps1" -ForegroundColor Yellow
        }
        return
    }

    if ($Status) {
        Show-Status
        return
    }

    if ($SyncMemory) {
        Sync-Memory
        return
    }

    if ($Task) {
        Add-Task -Title $Task -Description $Task -RequiredRoles $Roles -Priority $Priority
        return
    }

    if ($AutoConnect) {
        # Determine role from task or use specified
        $detectedRole = if ($Role) { $Role } else { "Coder" }
        $agentId = "agent-$detectedRole-$(Get-Random -Maximum 99)"

        $result = Connect-Agent -AgentId $agentId -Role $detectedRole

        if ($result.connected) {
            Write-Host "`n[OK] Agent connected successfully!" -ForegroundColor Green
            Write-Host "   ID: $($result.agentId)" -ForegroundColor Cyan
            Write-Host "   Task: $($result.task.title)" -ForegroundColor Cyan
            Write-Host "   Role: $($result.role)" -ForegroundColor Cyan
        }
        else {
            Write-Host "`n[WARN] No pending tasks for connection" -ForegroundColor Yellow
        }

        # Sync memory after connect
        Sync-Memory
        return
    }

    if ($Orchestrate) {
        Write-Log "Starting orchestration..." "INFO" "ORCHESTRATE"
        Sync-Memory
        Show-Status
        return
    }

    # Default: show status
    Show-Status
}

# Run
Main
