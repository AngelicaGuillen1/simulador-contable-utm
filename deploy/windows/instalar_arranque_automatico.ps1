<#
    Instala el Simulador Integral de Sistema Contable como servicio 24/7 en este equipo Windows.

    Metodos de arranque automatico disponibles:
      Tarea          -> tarea programada de Windows (Requiere PowerShell como Administrador)
      Inicio         -> acceso directo en la carpeta de Inicio del usuario (no requiere permisos)
      Auto           -> intenta Tarea y, si no hay permisos, usa Inicio (por defecto)

    Ademas genera deploy\windows\entorno.local.cmd con una SECRET_KEY aleatoria (no versionada).

    Uso:
        powershell -ExecutionPolicy Bypass -File deploy\windows\instalar_arranque_automatico.ps1
        powershell -ExecutionPolicy Bypass -File deploy\windows\instalar_arranque_automatico.ps1 -Metodo Inicio -Puerto 8080
        powershell -ExecutionPolicy Bypass -File deploy\windows\instalar_arranque_automatico.ps1 -Metodo Tarea -Cuando AlInicio
#>
param(
    [string]$Proyecto = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [int]$Puerto = 8080,
    [ValidateSet("Auto", "Tarea", "Inicio")][string]$Metodo = "Auto",
    [ValidateSet("AlIniciarSesion", "AlInicio")][string]$Cuando = "AlIniciarSesion",
    [string]$NombreTarea = "SimuladorContableUTM",
    [switch]$NoArrancar
)

$ErrorActionPreference = "Stop"

$python = Join-Path $Proyecto ".venv\Scripts\python.exe"
$lanzador = Join-Path $Proyecto "deploy\windows\iniciar_servidor.cmd"
$entorno = Join-Path $Proyecto "deploy\windows\entorno.local.cmd"

Write-Host "Proyecto : $Proyecto" -ForegroundColor Cyan
if (-not (Test-Path $python)) { throw "No se encontro el interprete del entorno virtual: $python" }
if (-not (Test-Path $lanzador)) { throw "No se encontro el lanzador: $lanzador" }

# ---------------------------------------------------------------- 1) Clave de sesion
if (-not (Test-Path $entorno)) {
    $bytes = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $clave = [Convert]::ToBase64String($bytes)
    @(
        "REM Generado por instalar_arranque_automatico.ps1 - NO versionar este archivo.",
        "set `"SECRET_KEY=$clave`"",
        "set `"PORT=$Puerto`"",
        "set `"SESSION_COOKIE_SECURE=false`""
    ) | Set-Content -Path $entorno -Encoding ASCII
    Write-Host "Clave de sesion generada en deploy\windows\entorno.local.cmd" -ForegroundColor Green
} else {
    Write-Host "Se conserva la clave de sesion existente en deploy\windows\entorno.local.cmd"
}

# --------------------------------------------------- 2) Arranque automatico al iniciar
$metodoUsado = $null

if ($Metodo -eq "Auto" -or $Metodo -eq "Tarea") {
    try {
        if (Get-ScheduledTask -TaskName $NombreTarea -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $NombreTarea -Confirm:$false
            Write-Host "Tarea anterior eliminada."
        }
        $accion = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$lanzador`"" -WorkingDirectory $Proyecto
        $disparador = if ($Cuando -eq "AlInicio") { New-ScheduledTaskTrigger -AtStartup } else { New-ScheduledTaskTrigger -AtLogOn }
        $ajustes = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
            -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable

        Register-ScheduledTask -TaskName $NombreTarea -Action $accion -Trigger $disparador -Settings $ajustes `
            -Description "Simulador Integral de Sistema Contable - servidor waitress 24/7" -Force | Out-Null

        $metodoUsado = "Tarea programada '$NombreTarea' ($Cuando)"
        Write-Host "Tarea programada registrada: $metodoUsado" -ForegroundColor Green
    } catch {
        if ($Metodo -eq "Tarea") { throw }
        Write-Host "No fue posible crear la tarea programada (se requiere PowerShell como Administrador)." -ForegroundColor Yellow
        Write-Host "Se usara la carpeta de Inicio del usuario." -ForegroundColor Yellow
    }
}

if (-not $metodoUsado) {
    $inicio = [Environment]::GetFolderPath("Startup")
    $acceso = Join-Path $inicio "Simulador Contable UTM.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $enlace = $shell.CreateShortcut($acceso)
    $enlace.TargetPath = "cmd.exe"
    $enlace.Arguments = "/c `"$lanzador`""
    $enlace.WorkingDirectory = $Proyecto
    $enlace.WindowStyle = 7           # minimizado
    $enlace.Description = "Simulador Integral de Sistema Contable (waitress 24/7)"
    $enlace.Save()
    $metodoUsado = "Carpeta de Inicio: $acceso"
    Write-Host "Arranque automatico instalado en la carpeta de Inicio." -ForegroundColor Green
}

# ------------------------------------------------------------------ 3) Arranque ya
if (-not $NoArrancar) {
    if ($metodoUsado -like "Tarea*") {
        Start-ScheduledTask -TaskName $NombreTarea
    } else {
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$lanzador`"" -WorkingDirectory $Proyecto -WindowStyle Minimized
    }
    Write-Host "Iniciando el servidor..."
    Start-Sleep -Seconds 10
}

$escucha = Get-NetTCPConnection -State Listen -LocalPort $Puerto -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Metodo de arranque : $metodoUsado"
if ($escucha) {
    Write-Host "Estado             : ESCUCHANDO en el puerto $Puerto" -ForegroundColor Green
    Write-Host "Acceso local       : http://127.0.0.1:$Puerto"
    Write-Host "Acceso en la red   : http://$($env:COMPUTERNAME):$Puerto"
    Write-Host "Manual de usuario  : http://127.0.0.1:$Puerto/manual"
    Write-Host "Registro           : logs\servidor.log"
} else {
    Write-Host "Estado             : el puerto $Puerto aun no responde." -ForegroundColor Yellow
    Write-Host "Revise logs\servidor.log para ver el detalle del arranque."
}
Write-Host ""
Write-Host "Para detenerlo: powershell -ExecutionPolicy Bypass -File deploy\windows\detener_servidor.ps1 -Desinstalar"
