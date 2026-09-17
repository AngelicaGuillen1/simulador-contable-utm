<#
    Detiene el Simulador Contable y (opcionalmente) elimina el arranque automatico.

    Uso:
        powershell -ExecutionPolicy Bypass -File deploy\windows\detener_servidor.ps1
        powershell -ExecutionPolicy Bypass -File deploy\windows\detener_servidor.ps1 -Desinstalar
#>
param(
    [string]$NombreTarea = "SimuladorContableUTM",
    [switch]$Desinstalar
)

$ErrorActionPreference = "Continue"

if (Get-ScheduledTask -TaskName $NombreTarea -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $NombreTarea -ErrorAction SilentlyContinue
    Write-Host "Tarea '$NombreTarea' detenida."
    if ($Desinstalar) {
        Unregister-ScheduledTask -TaskName $NombreTarea -Confirm:$false
        Write-Host "Tarea '$NombreTarea' eliminada: el servidor ya no arrancara solo."
    }
} else {
    Write-Host "No existe la tarea '$NombreTarea'."
}

# Procesos de serve.py que hayan quedado vivos
$procesos = Get-CimInstance Win32_Process -Filter "name='python.exe'" |
    Where-Object { $_.CommandLine -like "*serve.py*" }
foreach ($proceso in $procesos) {
    Stop-Process -Id $proceso.ProcessId -Force
    Write-Host "Proceso detenido: PID $($proceso.ProcessId)"
}

if ($procesos) { Write-Host "Servidor detenido." } else { Write-Host "No habia procesos del servidor en ejecucion." }
