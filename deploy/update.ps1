#requires -Version 5
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$ServerFile = Join-Path $PSScriptRoot "server.env"
$ServerHost = ""
$UserName = "root"
$RemoteDir = "/opt/katin-bot"

Get-Content $ServerFile | ForEach-Object {
    if ($_ -match "^\s*#" -or $_ -notmatch "=") { return }
    $k, $v = $_.Split("=", 2)
    $k = $k.Trim()
    $v = $v.Trim()
    if ($k -eq "HOST") { $ServerHost = $v }
    if ($k -eq "USER") { $UserName = $v }
    if ($k -eq "REMOTE_DIR") { $RemoteDir = $v }
}

if (-not $ServerHost -or $ServerHost -eq "REPLACE_WITH_SERVER_IP") {
    throw "Сначала впиши IP в deploy/server.env (HOST=1.2.3.4)"
}

$Key = Join-Path $env:USERPROFILE ".ssh\katin_bot"
$SshOpts = @("-i", $Key, "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=accept-new")
$Target = "$UserName@$ServerHost"

Write-Host "Подключаюсь к $Target ..."
ssh @SshOpts $Target "mkdir -p $RemoteDir/deploy $RemoteDir/media $RemoteDir/data"

foreach ($item in @("bot", "run.py", "requirements.txt")) {
    scp @SshOpts -r (Join-Path $Root $item) "${Target}:${RemoteDir}/"
}
scp @SshOpts (Join-Path $PSScriptRoot "katin-bot.service") "${Target}:${RemoteDir}/deploy/"
scp @SshOpts (Join-Path $PSScriptRoot "prepare_videos.sh") "${Target}:${RemoteDir}/deploy/"

Write-Host "Копирую media (видео могут идти долго) ..."
scp @SshOpts -r (Join-Path $Root "media") "${Target}:${RemoteDir}/"

$envLocal = Join-Path $Root ".env"
if (Test-Path $envLocal) {
    scp @SshOpts $envLocal "${Target}:${RemoteDir}/.env"
}

Write-Host "Готовлю HEVC-видео под Telegram (это может занять несколько минут) ..."
ssh @SshOpts $Target "chmod +x $RemoteDir/deploy/prepare_videos.sh; bash $RemoteDir/deploy/prepare_videos.sh"
ssh @SshOpts $Target "set -e; cd $RemoteDir; python3 -m venv .venv; .venv/bin/pip install -q -r requirements.txt; mkdir -p data; cp -f deploy/katin-bot.service /etc/systemd/system/katin-bot.service; systemctl daemon-reload; systemctl enable --now katin-bot; systemctl restart katin-bot; systemctl is-active katin-bot"

Write-Host "Готово. Бот должен отвечать в Telegram."
