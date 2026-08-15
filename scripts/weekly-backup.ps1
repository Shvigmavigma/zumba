param(
  [string]$BackupRoot = "backups",
  [ValidateRange(1, 30)]
  [int]$Keep = 3,
  [switch]$InstallWeeklyTask,
  [string]$TaskName = "BMRL Weekly Backup",
  [ValidateSet("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]
  [string]$WeeklyDay = "Sunday",
  [string]$At = "03:00"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Invoke-Compose {
  docker compose @args
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose $($args -join ' ') failed with exit code $LASTEXITCODE"
  }
}

function Wait-Postgres {
  Invoke-Compose exec -T postgres sh -lc 'until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do sleep 1; done'
}

function Get-ProjectPath([string]$Path) {
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return $Path
  }
  return Join-Path $ProjectRoot $Path
}

function Remove-TreeInside([string]$Target, [string]$Root) {
  $RootFull = (Resolve-Path -LiteralPath $Root).Path
  $TargetFull = (Resolve-Path -LiteralPath $Target).Path
  if (-not $TargetFull.StartsWith($RootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove path outside backup root: $TargetFull"
  }
  Remove-Item -LiteralPath $TargetFull -Recurse -Force
}

Set-Location $ProjectRoot

$BackupRootPath = Get-ProjectPath $BackupRoot
New-Item -ItemType Directory -Force -Path $BackupRootPath | Out-Null

if ($InstallWeeklyTask) {
  try {
    $AtTime = [datetime]::ParseExact($At, "HH:mm", [Globalization.CultureInfo]::InvariantCulture)
  } catch {
    throw "Use -At in HH:mm format, for example 03:00"
  }

  $ScriptPath = Join-Path $PSScriptRoot "weekly-backup.ps1"
  $Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" -BackupRoot `"$BackupRootPath`" -Keep $Keep"
  $Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $Arguments -WorkingDirectory $ProjectRoot
  $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $WeeklyDay -At $AtTime
  Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Description "BMRL weekly Docker backup. Keeps last $Keep successful backups." -Force | Out-Null
  Write-Host "Scheduled task installed: $TaskName ($WeeklyDay at $At)"
  exit 0
}

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$FinalDir = Join-Path $BackupRootPath "bmrl-weekly-$Timestamp"
$TempDir = Join-Path $BackupRootPath ".bmrl-weekly-$Timestamp.tmp"
$DbInContainer = "/tmp/bmrl-weekly-$Timestamp.dump"
$UploadsInContainer = "/tmp/bmrl-weekly-$Timestamp-uploads.tar.gz"

if (Test-Path -LiteralPath $TempDir) {
  Remove-TreeInside $TempDir $BackupRootPath
}
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

try {
  Invoke-Compose up -d postgres backend
  Wait-Postgres

  $DbFile = Join-Path $TempDir "database.dump"
  $UploadsFile = Join-Path $TempDir "uploads.tar.gz"

  Invoke-Compose exec -T postgres sh -lc "rm -f '$DbInContainer' && pg_dump -U `"`$POSTGRES_USER`" -d `"`$POSTGRES_DB`" --format=custom --no-owner --no-privileges --file '$DbInContainer'"
  Invoke-Compose cp "postgres:$DbInContainer" $DbFile
  Invoke-Compose exec -T postgres sh -lc "rm -f '$DbInContainer'"

  Invoke-Compose exec -T backend sh -lc "rm -f '$UploadsInContainer' && tar -czf '$UploadsInContainer' -C /app/uploads ."
  Invoke-Compose cp "backend:$UploadsInContainer" $UploadsFile
  Invoke-Compose exec -T backend sh -lc "rm -f '$UploadsInContainer'"

  $DbSize = (Get-Item -LiteralPath $DbFile).Length
  $UploadsSize = (Get-Item -LiteralPath $UploadsFile).Length
  $Manifest = @(
    "created_at_utc=$((Get-Date).ToUniversalTime().ToString('o'))",
    "database=database.dump",
    "database_bytes=$DbSize",
    "uploads=uploads.tar.gz",
    "uploads_bytes=$UploadsSize",
    "keep=$Keep"
  )
  Set-Content -Encoding UTF8 -Path (Join-Path $TempDir "manifest.txt") -Value $Manifest

  Rename-Item -LiteralPath $TempDir -NewName (Split-Path -Leaf $FinalDir)

  $Backups = Get-ChildItem -LiteralPath $BackupRootPath -Directory -Filter "bmrl-weekly-*" |
    Sort-Object LastWriteTime -Descending
  $Backups | Select-Object -Skip $Keep | ForEach-Object {
    Remove-TreeInside $_.FullName $BackupRootPath
  }

  Write-Host "Backup created: $FinalDir"
  Write-Host "Kept latest $Keep successful backup(s)."
} catch {
  if (Test-Path -LiteralPath $TempDir) {
    Remove-TreeInside $TempDir $BackupRootPath
  }
  throw
}
