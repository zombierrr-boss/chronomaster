# Decodiert einen BehaviorProviderDefinition-Dump (eine BehaviorSequences(0)-Zeile)
# in einen lesbaren Graphen: Ereignisse -> Bausteine -> Ausgaenge.
param([Parameter(Mandatory=$true)][string]$File)

$text = [IO.File]::ReadAllText($File)
$line = @($text -split "`n" | Where-Object { $_.StartsWith("BehaviorSequences(0)=") })[0]

function Get-Balanced([string]$s, [int]$start) {
    # $start zeigt auf eine oeffnende Klammer; gibt Inhalt ohne aeussere Klammern zurueck
    $depth = 0
    for ($i = $start; $i -lt $s.Length; $i++) {
        $c = $s[$i]
        if ($c -eq '(') { $depth++ }
        elseif ($c -eq ')') { $depth--; if ($depth -eq 0) { return $s.Substring($start + 1, $i - $start - 1) } }
    }
    throw "unbalanced"
}
function Get-Section([string]$s, [string]$key) {
    $idx = $s.IndexOf("$key=(")
    if ($idx -lt 0) { return $null }
    return Get-Balanced $s ($idx + $key.Length + 1)
}
function Split-TopLevel([string]$s) {
    # trennt "(a),(b),(c)" oder "1,2,3" auf oberster Ebene
    $items = @(); $depth = 0; $cur = ""
    foreach ($c in $s.ToCharArray()) {
        if ($c -eq '(') { $depth++ }
        if ($c -eq ')') { $depth-- }
        if ($c -eq ',' -and $depth -eq 0) { $items += $cur; $cur = ""; continue }
        $cur += $c
    }
    if ($cur -ne "") { $items += $cur }
    return $items | ForEach-Object { $_.Trim() -replace '^\((.*)\)$', '$1' }
}
function Unpack-IdxLen([int]$v) { return @{ Index = ($v -shr 16); Length = ($v -band 0xFFFF) } }

$events    = Split-TopLevel (Get-Section $line "EventData2")
$behaviors = Split-TopLevel (Get-Section $line "BehaviorData2")
$vars      = Split-TopLevel (Get-Section $line "VariableData")
$olinks    = Split-TopLevel (Get-Section $line "ConsolidatedOutputLinkData")
$vlinks    = Split-TopLevel (Get-Section $line "ConsolidatedVariableLinkData")
$lvars     = Split-TopLevel (Get-Section $line "ConsolidatedLinkedVariables")

function Fmt-Links([int]$packed) {
    $r = Unpack-IdxLen $packed
    if ($r.Length -eq 0) { return "(keine)" }
    $out = @()
    for ($k = 0; $k -lt $r.Length; $k++) {
        $e = $olinks[$r.Index + $k]
        $m = [regex]::Match($e, 'LinkIdAndLinkedBehavior=(-?\d+),ActivateDelay=([\d.]+)')
        $v = [int64]$m.Groups[1].Value
        if ($v -lt 0) { $v = $v + 4294967296 }
        $linkId = ($v -shr 24) -band 0xFF
        $bIdx   = $v -band 0xFFFFFF
        $delay  = [double]$m.Groups[2].Value
        $name = ($behaviors[$bIdx] -replace ".*Behavior=Behavior_([A-Za-z]+)'[^']*\.(Behavior_[A-Za-z_0-9]+)'.*", '$2')
        $d = if ($delay -gt 0) { " +${delay}s" } else { "" }
        $out += "[pin $linkId] -> #$bIdx $name$d"
    }
    return ($out -join "  |  ")
}
function Fmt-Vars([int]$packed) {
    $r = Unpack-IdxLen $packed
    if ($r.Length -eq 0) { return "" }
    $out = @()
    for ($k = 0; $k -lt $r.Length; $k++) {
        $e = $vlinks[$r.Index + $k]
        $pn = [regex]::Match($e, 'PropertyName="([^"]*)"').Groups[1].Value
        $lt = [regex]::Match($e, 'VariableLinkType=BVARLINK_([A-Za-z]+)').Groups[1].Value
        $lv = [int][regex]::Match($e, 'LinkedVariables=\(ArrayIndexAndLength=(\d+)\)').Groups[1].Value
        $rr = Unpack-IdxLen $lv
        $ids = @(); for ($j = 0; $j -lt $rr.Length; $j++) { $ids += $lvars[$rr.Index + $j] }
        $out += "$pn($lt)=v" + ($ids -join ",v")
    }
    return "  vars: " + ($out -join "; ")
}

"=== VARIABLEN ==="
for ($i = 0; $i -lt $vars.Count; $i++) {
    $n = [regex]::Match($vars[$i], 'Name="?([^",]*)"?').Groups[1].Value
    $t = [regex]::Match($vars[$i], 'Type=BVAR_([A-Za-z]+)').Groups[1].Value
    "  v$i : $t $n"
}
""
"=== EREIGNISSE ==="
foreach ($e in $events) {
    $name = [regex]::Match($e, 'EventName="([^"]*)"').Groups[1].Value
    $en   = [regex]::Match($e, 'bEnabled=([A-Za-z]+)').Groups[1].Value
    $ol   = [int][regex]::Match($e, 'OutputLinks=\(ArrayIndexAndLength=(\d+)\)').Groups[1].Value
    "  $name (enabled=$en)"
    "      " + (Fmt-Links $ol)
}
""
"=== BAUSTEINE ==="
for ($i = 0; $i -lt $behaviors.Count; $i++) {
    $b = $behaviors[$i]
    $name = ($b -replace ".*Behavior=Behavior_([A-Za-z]+)'[^']*\.(Behavior_[A-Za-z_0-9]+)'.*", '$2')
    $lv = [int][regex]::Match($b, 'LinkedVariables=\(ArrayIndexAndLength=(\d+)\)').Groups[1].Value
    $ol = [int][regex]::Match($b, 'OutputLinks=\(ArrayIndexAndLength=(\d+)\)').Groups[1].Value
    "  #$i $name"
    "      out: " + (Fmt-Links $ol)
    $vv = Fmt-Vars $lv
    if ($vv) { "    $vv" }
}
