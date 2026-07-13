param(
    [Parameter(Mandatory = $true)]
    [string]$Source,
    [Parameter(Mandatory = $true)]
    [string]$ContentId,
    [string]$Repository = "bnuzjq-ops/threads-publish-feed"
)

$ErrorActionPreference = "Stop"
$sourcePath = (Resolve-Path -LiteralPath $Source).Path
$raw = [IO.File]::ReadAllText($sourcePath, [Text.Encoding]::UTF8)
if (-not $raw.StartsWith("---")) { throw "Source must start with YAML frontmatter." }
$parts = $raw -split "`n---`r?`n", 2
if ($parts.Count -ne 2) { throw "Source frontmatter is incomplete." }
$frontmatter = $parts[0]
$body = $parts[1].Trim()
if ($frontmatter -notmatch "(?m)^platform:[ ]*threads[ ]*$") { throw "platform must be threads." }
if ($frontmatter -notmatch "(?m)^editorial_status:[ ]*ready[ ]*$") { throw "editorial_status must be ready." }
if ([string]::IsNullOrWhiteSpace($body)) { throw "Post body is empty." }

$temp = Join-Path ([IO.Path]::GetTempPath()) ("threads-feed-" + [guid]::NewGuid())
gh repo clone $Repository $temp -- --depth 1 | Out-Null
try {
    $relative = "posts/queue/$ContentId.md"
    $target = Join-Path $temp ($relative -replace '/', '\\')
    New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
    $timestamp = [DateTimeOffset]::Now.ToString("yyyy-MM-ddTHH:mm:sszzz")
    $sourceRef = $sourcePath.Replace("C:\\jq\\OBS\\", "").Replace('\', '/')
    $snapshot = @("---", "content_id: $ContentId", "platform: threads", "editorial_status: ready", "source_ref: $sourceRef", "content_version: 1", "exported_at: $timestamp", "---", "", $body) -join "`n"
    [IO.File]::WriteAllText($target, $snapshot, [Text.UTF8Encoding]::new($false))
    git -C $temp add -- $relative
    git -C $temp commit -m "Export Threads post $ContentId" | Out-Null
    git -C $temp push origin HEAD:main | Out-Null
    Write-Output "Exported $ContentId to $Repository/$relative"
}
finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
}
