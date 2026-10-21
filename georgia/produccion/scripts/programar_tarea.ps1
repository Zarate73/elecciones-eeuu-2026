<#
ODISEO Georgia - tarea programada de Windows.
  .\programar_tarea.ps1                      # diaria a las 08:00
  .\programar_tarea.ps1 -Horas 08:00,20:00   # varias veces al día
  .\programar_tarea.ps1 -Eliminar            # quitar la tarea
Si PowerShell bloquea el script:  powershell -ExecutionPolicy Bypass -File .\programar_tarea.ps1
#>
param(
    [string[]]$Horas = @('08:00'),
    [switch]$Eliminar,
    [string]$Nombre = 'ODISEO_Georgia'
)
$raiz = Split-Path -Parent $PSScriptRoot
$bat = Join-Path $PSScriptRoot 'correr_pronostico.bat'
if ($Eliminar) {
    Unregister-ScheduledTask -TaskName $Nombre -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tarea '$Nombre' eliminada."
    return
}
if (-not (Test-Path (Join-Path $raiz '.venv\Scripts\python.exe'))) {
    Write-Error 'Primero ejecuta scripts\instalar.bat'; return
}
$accion = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$bat`"" -WorkingDirectory $raiz
$disparadores = $Horas | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ }
$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
           -MultipleInstances IgnoreNew -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName $Nombre -Action $accion -Trigger $disparadores -Settings $ajustes `
    -Description 'Pronóstico diario ODISEO Georgia (V11)' -Force | Out-Null
Write-Host "Tarea '$Nombre' programada a las: $($Horas -join ', '). Corre con tu usuario cuando hayas iniciado sesión."
Write-Host "Probar ahora:  Start-ScheduledTask -TaskName $Nombre"
