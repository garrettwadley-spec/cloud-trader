$ErrorActionPreference = 'Stop'
$root = Resolve-Path ".."
$backupDir = Join-Path $root "backups"
$newName = "backup_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".zip"
$dest = Join-Path $backupDir $newName
If (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$items = @("config","models","logs","data\cache",".env")
$zipToOpen = [System.IO.File]::Open($dest, [System.IO.FileMode]::CreateNew)
$archive = New-Object System.IO.Compression.ZipArchive($zipToOpen, [System.IO.Compression.ZipArchiveMode]::Create)
foreach ($item in $items) {
  $path = Join-Path $root $item
  if (Test-Path $path) {
    if ((Get-Item $path).PSIsContainer) {
      Get-ChildItem -Path $path -Recurse | Where-Object {!$_.PSIsContainer} | ForEach-Object {
        $rel = $_.FullName.Substring($root.Path.Length + 1)
        $archive.CreateEntryFromFile($_.FullName, $rel, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
      }
    } else {
      $rel = $path.Substring($root.Path.Length + 1)
      $archive.CreateEntryFromFile($path, $rel, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
  }
}
$archive.Dispose(); $zipToOpen.Dispose()
Write-Host "Backup created at $dest"
