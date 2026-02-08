# ============================================================
# notd - intentional clipboard capture
# Company: Deze Tingz
# Author: Val John @ Deze Tingz
# ============================================================

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('capture','config','status','open','hotkey')]
    [string]$Command = 'capture',

    [switch]$AutoType,
    [switch]$Silent
)

# ---------- STA RELAUNCH (needed for WinForms commands) ----------
if ($Command -in @('config','hotkey')) {
    if ([System.Threading.Thread]::CurrentThread.ApartmentState -ne 'STA') {
        Start-Process powershell.exe -ArgumentList @(
            '-STA',
            '-ExecutionPolicy', 'Bypass',
            '-File', $PSCommandPath,
            $Command
        )
        exit
    }
}

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================
# CONFIG
# ============================================================
$script:ConfigHome = 'C:\notd'
$script:ConfigDir  = Join-Path $script:ConfigHome 'config'
$script:ConfigPath = Join-Path $script:ConfigDir 'notd.config.json'

$script:DefaultConfig = @{
    project        = 'notd'
    owner          = 'Deze Tingz'
    root_dir       = 'C:\notd_data'
    text_file_type = 'txt'
    code_file_type = 'md'
    schema_enabled = $true
    auto_type      = $true
    sounds_enabled = $true
    success_sound  = 'C:\Windows\Media\Windows Hardware Insert.wav'
    fail_sound     = 'C:\Windows\Media\Windows Hardware Fail.wav'
    max_clip_chars = 200000
    hotkey = @{
        enabled = $false
        ctrl    = $true
        alt     = $true
        shift   = $false
        win     = $false
        key     = 'N'
    }
}

function Ensure-Dir([string]$p) {
    if (-not (Test-Path $p)) {
        New-Item -ItemType Directory -Path $p | Out-Null
    }
}

Ensure-Dir $script:ConfigHome
Ensure-Dir $script:ConfigDir

if (-not (Test-Path $script:ConfigPath)) {
    $script:DefaultConfig | ConvertTo-Json -Depth 8 | Set-Content $script:ConfigPath -Encoding UTF8
}

$script:Cfg = Get-Content $script:ConfigPath -Raw | ConvertFrom-Json
if ($Silent) { $script:Cfg.sounds_enabled = $false }

# ============================================================
# AUDIO
# ============================================================
function Play-Sound([string]$path) {
    if (-not $script:Cfg.sounds_enabled) { return }
    if (Test-Path $path) {
        try { (New-Object System.Media.SoundPlayer $path).Play() } catch {}
    }
}

# ============================================================
# CLIPBOARD
# ============================================================
Add-Type -AssemblyName PresentationCore

function Get-ClipboardText {
    try {
        $t = [Windows.Clipboard]::GetText()
        if ($null -eq $t) { return '' }
        if ($t.Length -gt $script:Cfg.max_clip_chars) {
            return $t.Substring(0, $script:Cfg.max_clip_chars)
        }
        return $t
    } catch {
        return ''
    }
}

# ============================================================
# TYPE INFERENCE
# ============================================================
function Infer-Type([string]$t) {
    $s = $t.Trim()
    if ($s -match '^https?://|^www\.') { return 'url' }
    if ($s -match '^(git |cd |ls |dir |npm |pnpm |yarn |python |pip |pwsh |powershell |curl |docker )') { return 'command' }
    if ($s -match '(```|^\s*(function|class|def|import|using|#include)\b)') { return 'code' }
    if ($s -match '(Exception|Traceback|Error|ERR_|FATAL)') { return 'error' }
    return 'text'
}

# ============================================================
# FILES
# ============================================================
function Get-CapturesDir {
    Join-Path $script:Cfg.root_dir 'captures'
}

function Resolve-File([string]$bucket) {
    $ext = if ($bucket -eq 'code') { $script:Cfg.code_file_type } else { $script:Cfg.text_file_type }
    Join-Path (Get-CapturesDir) "notd_raw.$ext"
}

function Format-Entry([string]$content, [string]$type) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $sep = [string]::new([char]0x2501, 26)
    @"
$sep
PROJECT: notd
OWNER: Deze Tingz
TIMESTAMP: $ts
TYPE: $type

$content
$sep
"@
}

# ============================================================
# COMMANDS
# ============================================================
function Cmd-Capture {
    Ensure-Dir $script:Cfg.root_dir
    Ensure-Dir (Get-CapturesDir)

    $content = Get-ClipboardText
    if ([string]::IsNullOrWhiteSpace($content)) {
        Play-Sound $script:Cfg.fail_sound
        return
    }

    $type   = if ($script:Cfg.auto_type -or $AutoType) { Infer-Type $content } else { 'capture' }
    $bucket = if ($type -eq 'code') { 'code' } else { 'text' }
    $file   = Resolve-File $bucket

    if ($file.EndsWith('.jsonl')) {
        @{ timestamp = (Get-Date).ToString('s'); type = $type; content = $content } |
            ConvertTo-Json -Compress |
            Add-Content $file -Encoding UTF8
    } else {
        Format-Entry $content $type | Add-Content $file -Encoding UTF8
    }

    Play-Sound $script:Cfg.success_sound
}

function Cmd-Status {
    $hk = $script:Cfg.hotkey
    Write-Host 'notd - Deze Tingz'
    Write-Host "Config: $script:ConfigPath"
    Write-Host "Data:   $($script:Cfg.root_dir)"
    Write-Host "Hotkey: ctrl=$($hk.ctrl) alt=$($hk.alt) key=$($hk.key) enabled=$($hk.enabled)"
}

function Cmd-Open {
    Ensure-Dir (Get-CapturesDir)
    Start-Process explorer.exe (Get-CapturesDir)
}

# ============================================================
# HOTKEY (Win32)
# ============================================================
$script:MOD_ALT = 1
$script:MOD_CTRL = 2
$script:MOD_SHIFT = 4
$script:MOD_WIN = 8
$script:HK_ID = 9001

try {
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public class HotKey {
    [DllImport("user32.dll")]
    public static extern bool RegisterHotKey(IntPtr hWnd, int id, uint mods, uint vk);
    [DllImport("user32.dll")]
    public static extern bool UnregisterHotKey(IntPtr hWnd, int id);
}
'@
} catch {}

function Cmd-Hotkey {
    if (-not $script:Cfg.hotkey.enabled) {
        Write-Host 'Hotkey disabled in config.'
        return
    }

    Add-Type -AssemblyName System.Windows.Forms

    [uint32]$mods = 0
    if ($script:Cfg.hotkey.ctrl)  { $mods += $script:MOD_CTRL }
    if ($script:Cfg.hotkey.alt)   { $mods += $script:MOD_ALT }
    if ($script:Cfg.hotkey.shift) { $mods += $script:MOD_SHIFT }
    if ($script:Cfg.hotkey.win)   { $mods += $script:MOD_WIN }

    $vk = [byte][System.Windows.Forms.Keys]::($script:Cfg.hotkey.key)
    [HotKey]::RegisterHotKey([IntPtr]::Zero, $script:HK_ID, $mods, $vk) | Out-Null

    Write-Host 'notd hotkey active. Press shortcut to capture.'

    while ($true) {
        $msg = New-Object System.Windows.Forms.Message
        if ([System.Windows.Forms.Application]::PeekMessage([ref]$msg, [IntPtr]::Zero, 0, 0, 1)) {
            if ($msg.Msg -eq 0x0312) { Cmd-Capture }
        }
        Start-Sleep -Milliseconds 40
    }
}

# ============================================================
# CONFIG UI (WinForms)
# ============================================================
function Cmd-Config {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $f = New-Object System.Windows.Forms.Form
    $f.Text = 'notd Settings - Deze Tingz'
    $f.Size = '540,420'
    $f.StartPosition = 'CenterScreen'

    # -- Helper: label
    function Add-Label([string]$text, [int]$x, [int]$y) {
        $l = New-Object System.Windows.Forms.Label
        $l.Text = $text
        $l.Location = "$x,$y"
        $l.AutoSize = $true
        $f.Controls.Add($l)
    }

    # -- Helper: textbox
    function Add-TextBox([int]$x, [int]$y, [int]$w) {
        $t = New-Object System.Windows.Forms.TextBox
        $t.Location = "$x,$y"
        $t.Size = "$w,22"
        $f.Controls.Add($t)
        return $t
    }

    # Data folder
    Add-Label 'Data folder' 20 20
    $tbRoot = Add-TextBox 20 45 380
    $tbRoot.Text = $script:Cfg.root_dir

    $btnBrowse = New-Object System.Windows.Forms.Button
    $btnBrowse.Text = 'Browse'
    $btnBrowse.Location = '410,43'
    $f.Controls.Add($btnBrowse)
    $btnBrowse.Add_Click({
        $d = New-Object System.Windows.Forms.FolderBrowserDialog
        if ($d.ShowDialog() -eq 'OK') { $tbRoot.Text = $d.SelectedPath }
    })

    # Hotkey section
    Add-Label 'Keyboard hotkey' 20 90
    $tbKey = Add-TextBox 20 115 80
    $tbKey.ReadOnly = $true
    $tbKey.Text = $script:Cfg.hotkey.key
    $tbKey.Add_KeyDown({ $tbKey.Text = $_.KeyCode.ToString() })

    $chkCtrl = New-Object System.Windows.Forms.CheckBox
    $chkCtrl.Text = 'Ctrl'
    $chkCtrl.Location = '120,118'
    $chkCtrl.Checked = $script:Cfg.hotkey.ctrl
    $f.Controls.Add($chkCtrl)

    $chkAlt = New-Object System.Windows.Forms.CheckBox
    $chkAlt.Text = 'Alt'
    $chkAlt.Location = '180,118'
    $chkAlt.Checked = $script:Cfg.hotkey.alt
    $f.Controls.Add($chkAlt)

    $chkShift = New-Object System.Windows.Forms.CheckBox
    $chkShift.Text = 'Shift'
    $chkShift.Location = '240,118'
    $chkShift.Checked = $script:Cfg.hotkey.shift
    $f.Controls.Add($chkShift)

    $chkEnable = New-Object System.Windows.Forms.CheckBox
    $chkEnable.Text = 'Enable hotkey'
    $chkEnable.Location = '320,118'
    $chkEnable.Checked = $script:Cfg.hotkey.enabled
    $f.Controls.Add($chkEnable)

    # Save button
    $btnSave = New-Object System.Windows.Forms.Button
    $btnSave.Text = 'Save'
    $btnSave.Location = '340,320'
    $f.Controls.Add($btnSave)

    $btnSave.Add_Click({
        $script:Cfg.root_dir = $tbRoot.Text
        $script:Cfg.hotkey = @{
            enabled = $chkEnable.Checked
            ctrl    = $chkCtrl.Checked
            alt     = $chkAlt.Checked
            shift   = $chkShift.Checked
            win     = $false
            key     = $tbKey.Text
        }
        $script:Cfg | ConvertTo-Json -Depth 8 | Set-Content $script:ConfigPath -Encoding UTF8
        $f.Close()
    })

    [void]$f.ShowDialog()
}

# ============================================================
# DISPATCH
# ============================================================
switch ($Command) {
    'capture' { Cmd-Capture }
    'config'  { Cmd-Config }
    'status'  { Cmd-Status }
    'open'    { Cmd-Open }
    'hotkey'  { Cmd-Hotkey }
}
