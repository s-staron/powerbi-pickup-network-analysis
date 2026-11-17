# Parses the TMDL semantic model with the same serializer that Power BI Desktop uses to open a project.
# Needs Power BI Desktop for Windows (Microsoft Store version). It checks TMDL syntax and object
# structure; it does not run Power Query or DAX.
#
# Run:  powershell -ExecutionPolicy Bypass -File validation\tmdl_parse_check.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$definition = Join-Path $root "PickupNetwork.SemanticModel\definition"

$bin = Join-Path (Get-AppxPackage Microsoft.MicrosoftPowerBIDesktop).InstallLocation "bin"
$work = Join-Path $env:TEMP "tmdl_parse_check"
New-Item -ItemType Directory -Force $work | Out-Null
Get-ChildItem $bin -File -Filter "*.dll" | Where-Object { $_.Name -match "^(Microsoft\.|Newtonsoft|System\.)" } |
    ForEach-Object { Copy-Item $_.FullName $work -Force }

[AppDomain]::CurrentDomain.add_AssemblyResolve({
    param($sender, $e)
    $path = Join-Path $work (($e.Name -split ",")[0] + ".dll")
    if (Test-Path $path) { [Reflection.Assembly]::LoadFrom($path) } else { $null }
})
$assembly = [Reflection.Assembly]::LoadFrom((Join-Path $work "Microsoft.PowerBI.Tabular.dll"))
$serializer = $assembly.GetType("Microsoft.AnalysisServices.Tabular.TmdlSerializer")

try {
    $db = $serializer.GetMethod("DeserializeDatabaseFromFolder", [Type[]]@([string])).Invoke($null, @([string]$definition))
} catch {
    $ex = $_.Exception
    while ($ex.InnerException) { $ex = $ex.InnerException }
    Write-Host "TMDL PARSE FAILED: $($ex.Message)"
    foreach ($p in "Document", "LineNumber", "LineText") {
        if ($ex.GetType().GetProperty($p)) { Write-Host "  $p : $($ex.GetType().GetProperty($p).GetValue($ex))" }
    }
    exit 1
}
$measures = 0
foreach ($t in $db.Model.Tables) { $measures += $t.Measures.Count }
Write-Host ("TMDL parsed: {0} tables, {1} relationships, {2} roles, {3} expressions, {4} measures" -f `
    $db.Model.Tables.Count, $db.Model.Relationships.Count, $db.Model.Roles.Count, $db.Model.Expressions.Count, $measures)
