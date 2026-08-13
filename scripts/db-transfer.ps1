param(
  [ValidateSet("export", "import")]
  [string]$Action = "export",

  [string]$File = "backups/bmrl-db-transfer.dump"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DumpInContainer = "/tmp/bmrl-db-transfer.dump"

function Invoke-Compose {
  docker compose @args
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose $($args -join ' ') failed with exit code $LASTEXITCODE"
  }
}

function Wait-Postgres {
  Invoke-Compose exec -T postgres sh -lc 'until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do sleep 1; done'
}

function Get-TransferPath([string]$Path) {
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return $Path
  }
  return Join-Path $ProjectRoot $Path
}

Set-Location $ProjectRoot

switch ($Action) {
  "export" {
    Invoke-Compose up -d postgres
    Wait-Postgres

    $Target = Get-TransferPath $File
    $TargetDir = Split-Path -Parent $Target
    if ($TargetDir) {
      New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
    }

    Invoke-Compose exec -T postgres sh -lc "rm -f '$DumpInContainer' && pg_dump -U `"`$POSTGRES_USER`" -d `"`$POSTGRES_DB`" --format=custom --no-owner --no-privileges --file '$DumpInContainer'"
    Invoke-Compose cp "postgres:$DumpInContainer" $Target
    Invoke-Compose exec -T postgres sh -lc "rm -f '$DumpInContainer'"

    Write-Host "Database exported to $Target"
  }

  "import" {
    $Source = Get-TransferPath $File
    if (!(Test-Path $Source)) {
      throw "Dump file not found: $Source"
    }

    Invoke-Compose up -d postgres
    Wait-Postgres
    Invoke-Compose stop backend web
    Invoke-Compose cp $Source "postgres:$DumpInContainer"
    Invoke-Compose exec -T postgres sh -lc "pg_restore -U `"`$POSTGRES_USER`" -d `"`$POSTGRES_DB`" --clean --if-exists --no-owner --no-privileges '$DumpInContainer'"
    Invoke-Compose exec -T postgres sh -lc "rm -f '$DumpInContainer'"
    Invoke-Compose up -d

    Write-Host "Database imported from $Source"
  }
}
