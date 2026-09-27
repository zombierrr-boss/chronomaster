# Erzeugt src\<ModName>.txt aus src\hotfixes.txt.
#
# hotfixes.txt:   ein Hotfix pro Zeile  "ID | Objekt | Eigenschaft | Wert", Kommentare mit '#'.
# <ModName>.txt:  alle Kommentarzeilen der Quelle (zur Dokumentation) plus die zwei set-Zeilen,
#                 die Keys und Values des Micropatch-Dienstes setzen.
#
# Aufruf:  tools\build.ps1     (deploy.ps1 macht das automatisch)
#
# Uebernommen aus dem FL4K-Projekt (tools\build-fl4k.ps1); Modname und Key-Praefix sind Parameter,
# damit die Umbenennung des Charakters (Platzhalter "Chronomaster") die Dateinamen nicht beruehrt.

param(
    [string]$ModName = "zeitbombe",
    [string]$Source = (Join-Path $PSScriptRoot "..\src\hotfixes.txt"),
    [string]$Target = $null,
    [string]$Package = "GD_Assassin_Streaming",
    [string]$Service = "Transient.SparkServiceConfiguration_5"
)

if (-not $Target) { $Target = Join-Path $PSScriptRoot "..\src\$ModName.txt" }
if (-not (Test-Path $Source)) { Write-Error "Quelle fehlt: $Source"; exit 1 }

$prefix = $ModName.ToUpper()
$keys = New-Object System.Collections.Generic.List[string]
$vals = New-Object System.Collections.Generic.List[string]
$seen = @{}
$out  = New-Object System.Collections.Generic.List[string]
$lineNo = 0

foreach ($line in (Get-Content $Source -Encoding UTF8)) {
    $lineNo++
    $t = $line.Trim()
    if ($t -eq "" -or $t.StartsWith("#")) { $out.Add($line); continue }

    $parts = $t.Split("|", 4)
    if ($parts.Count -ne 4) { Write-Error "Zeile ${lineNo}: erwartet 'ID | Objekt | Eigenschaft | Wert'"; exit 1 }
    $id = $parts[0].Trim(); $obj = $parts[1].Trim(); $prop = $parts[2].Trim(); $val = $parts[3].Trim()

    if ($id -notmatch '^[A-Za-z0-9]+$') { Write-Error "Zeile ${lineNo}: ID '$id' darf nur Buchstaben/Ziffern enthalten (kein '-')"; exit 1 }
    if ($seen.ContainsKey($id)) { Write-Error "Zeile ${lineNo}: ID '$id' doppelt"; exit 1 }
    if ($val.Contains('"')) { Write-Error "Zeile ${lineNo}: Wert darf kein '`"' enthalten"; exit 1 }
    $seen[$id] = $true

    $keys.Add("`"SparkOnDemandPatchEntry-${prefix}_$id`"")
    $vals.Add("`"$Package,$obj,$prop,,$val`"")
    $out.Add("# -> $id  $obj  $prop")
}

$out.Add("")
$out.Add("# ---- generiert von tools\build.ps1 aus src\hotfixes.txt, $($keys.Count) Hotfixes. Nicht von Hand aendern. ----")
$out.Add("")
$out.Add("set $Service Keys (" + ($keys -join ",") + ")")
$out.Add("")
$out.Add("set $Service Values (" + ($vals -join ",") + ")")

# UTF-8 ohne BOM, damit exec keine Sonderzeichen am Dateianfang sieht
$enc = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($Target), ($out -join "`r`n") + "`r`n", $enc)
Write-Output "$ModName.txt gebaut: $($keys.Count) Hotfixes"
