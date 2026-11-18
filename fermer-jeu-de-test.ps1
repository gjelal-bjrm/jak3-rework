# Ferme le jeu seulement s'il a ete lance par un test (pas une partie lancee par l'utilisateur avec le lanceur).
# Code de sortie : 0 = rien ou jeu de test ferme ; 2 = partie de l'utilisateur en cours (non fermee).
$user = $false
foreach ($p in @(Get-CimInstance Win32_Process -Filter "Name='gk.exe'")) {
  $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)"
  $grand = if ($parent) { Get-CimInstance Win32_Process -Filter "ProcessId=$($parent.ParentProcessId)" }
  if ($grand -and $grand.CommandLine -match 'lanceur\.pyw') { $user = $true; continue }
  Stop-Process -Id $p.ProcessId -Force
  if ($parent -and $parent.CommandLine -match 'launch\.py') {
    foreach ($c in @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($parent.ProcessId)")) {
      if ($c.Name -eq 'goalc.exe') { Stop-Process -Id $c.ProcessId -Force }
    }
  }
}
if ($user) { Write-Output "Partie de l'utilisateur en cours : non fermee."; exit 2 }
exit 0
