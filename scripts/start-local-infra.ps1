[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$composeFiles = @('compose.yaml', 'compose.local-access.yaml', 'compose.neo4j-browser.yaml', 'compose.tracking.yaml')
$envFiles = @('.env', '.env.secrets')
foreach ($file in ($composeFiles + $envFiles)) {
    if (-not (Test-Path -LiteralPath (Join-Path $repo $file) -PathType Leaf)) {
        throw "Отсутствует обязательный файл: $file"
    }
}

# Compose отдаёт приоритет окружению процесса; запрещаем неоднозначные источники.
$names = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($file in $composeFiles) {
    $content = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $repo $file)
    foreach ($match in [regex]::Matches($content, '(?<!\$)\$\{([A-Za-z_][A-Za-z0-9_]*)')) {
        [void]$names.Add($match.Groups[1].Value)
    }
}
foreach ($name in @('COMPOSE_FILE', 'COMPOSE_PROJECT_NAME', 'COMPOSE_PROFILES', 'COMPOSE_ENV_FILES', 'COMPOSE_DISABLE_ENV_FILE')) {
    [void]$names.Add($name)
}
$conflicts = @($names | Where-Object { $null -ne [Environment]::GetEnvironmentVariable($_, 'Process') } | Sort-Object)
if ($conflicts.Count -gt 0) {
    throw "Удалите переменные процесса перед запуском: $($conflicts -join ', ')"
}

$common = @('--project-directory', $repo, '--env-file', (Join-Path $repo '.env'), '--env-file', (Join-Path $repo '.env.secrets'))
$main = @('compose') + $common + @('-p', 'article-analysis', '-f', (Join-Path $repo 'compose.yaml'), '-f', (Join-Path $repo 'compose.local-access.yaml'), '-f', (Join-Path $repo 'compose.neo4j-browser.yaml'), '--profile', 'local-access', '--profile', 'browser')
$tracking = @('compose') + $common + @('-p', 'article-tracking', '-f', (Join-Path $repo 'compose.tracking.yaml'), '--profile', 'airflow', '--profile', 'observability')

function Invoke-Compose([string[]] $Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose завершился с кодом $LASTEXITCODE" }
}
# Проверяем, что первичная инициализация уже завершена; существующие контейнеры не пересоздаём.
function Get-TrackingContainer([string] $Service) {
    $ids = @(& docker ps -aq --filter 'label=com.docker.compose.project=article-tracking' --filter "label=com.docker.compose.service=$Service")
    if ($LASTEXITCODE -ne 0 -or $ids.Count -ne 1 -or -not $ids[0]) { throw "Нужен ровно один существующий контейнер tracking: $Service" }
    return $ids[0]
}
$trackingContainers = @{}
foreach ($service in @('airflow-db', 'mlflow-db', 'airflow-webserver', 'mlflow', 'airflow-db-provision', 'airflow-init', 'mlflow-db-provision')) {
    $trackingContainers[$service] = Get-TrackingContainer $service
}
foreach ($service in @('airflow-db-provision', 'airflow-init', 'mlflow-db-provision')) {
    $state = & docker inspect --format '{{.State.Status}} {{.State.ExitCode}}' $trackingContainers[$service]
    if ($LASTEXITCODE -ne 0 -or $state -ne 'exited 0') { throw "Инициализация tracking не подтверждена: $service" }
}
Invoke-Compose ($main + @('config', '--quiet'))
Invoke-Compose ($tracking + @('config', '--quiet'))
Invoke-Compose ($main + @('up', '-d', '--no-recreate', '--no-build', 'postgres', 'redis', 'neo4j', 'qdrant', 'qdrant-local-proxy', 'postgres-local-proxy', 'redis-local-proxy', 'redis-insight', 'neo4j-browser-proxy', 'neo4j-bolt-proxy'))
# Запускаем только уже созданные контейнеры без зависимостей, bootstrap и scheduler.
foreach ($service in @('airflow-db', 'mlflow-db', 'airflow-webserver', 'mlflow')) {
    $running = & docker inspect --format '{{.State.Running}}' $trackingContainers[$service]
    if ($LASTEXITCODE -ne 0) { throw "Не удалось проверить tracking: $service" }
    if ($running -ne 'true') {
        & docker start $trackingContainers[$service] | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Не удалось запустить tracking: $service" }
    }
    if ($service -in @('airflow-db', 'mlflow-db')) {
        $healthy = $false
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            $status = & docker inspect --format '{{.State.Health.Status}}' $trackingContainers[$service]
            if ($LASTEXITCODE -ne 0) { throw "Не удалось проверить готовность tracking: $service" }
            if ($status -eq 'healthy') { $healthy = $true; break }
            Start-Sleep -Seconds 1
        }
        if (-not $healthy) { throw "База tracking не готова: $service" }
    }
}
