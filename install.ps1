# notd installer — Deze Tingz
# Usage: irm https://raw.githubusercontent.com/Deze-Tingz/notd/main/install.ps1 | iex

$ErrorActionPreference = 'Stop'
$repo = 'https://raw.githubusercontent.com/Deze-Tingz/notd/main'
$installDir = 'C:\notd'

Write-Host 'notd installer — Deze Tingz' -ForegroundColor Cyan
Write-Host ''

# Create directories
foreach ($dir in @($installDir, "$installDir\config", "$installDir\bin")) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "  Created $dir"
    }
}

# Download source files
$files = @{
    'src/notd.py'  = "$installDir\bin\notd.py"
    'src/notd.ps1' = "$installDir\bin\notd.ps1"
}

foreach ($entry in $files.GetEnumerator()) {
    $url = "$repo/$($entry.Key)"
    Write-Host "  Downloading $($entry.Key)..."
    Invoke-WebRequest -Uri $url -OutFile $entry.Value -UseBasicParsing
}

# Run first-time config generation
Write-Host ''
Write-Host 'Running first-time setup...'
python "$installDir\bin\notd.py" status

Write-Host ''
Write-Host 'notd installed to C:\notd\bin\' -ForegroundColor Green
Write-Host 'Run: python C:\notd\bin\notd.py capture' -ForegroundColor Gray
