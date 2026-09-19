# Guía de Despliegue 24/7
## Simulador Integral de Sistema Contable

Este documento explica cómo dejar el sistema **funcionando de forma continua**, con las tres
opciones válidas según los recursos disponibles. El código ya está preparado para producción:
configuración por variables de entorno, servidor WSGI `waitress`, generación automática de la base
en el primer arranque, respaldos y arranque automático.

---

## 1. Antes de publicar: lista de verificación de seguridad

| # | Acción | Por qué |
|---|---|---|
| 1 | **Cambiar las contraseñas de demostración** | `admin/admin123`, `docente/docente123`, `estudiante/estudiante123`, `auditor/auditor123` son públicas (están en el manual y en el código). Ejecute: `python deploy/cambiar_credenciales.py` |
| 2 | **Definir `SECRET_KEY`** con una cadena aleatoria larga | Sin ella las sesiones se firman con la clave por defecto del código. `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| 3 | **Servir por HTTPS** y poner `SESSION_COOKIE_SECURE=true` | Evita que la cookie de sesión viaje en claro |
| 4 | **Programar respaldos** de la base (`deploy/backup_db.py`) | Todo el sistema vive en un archivo SQLite |
| 5 | **No exponer** `database/`, `docs/`, `deploy/` como archivos estáticos | Ya no se sirven: Flask solo publica `static/` y las rutas de la aplicación |
| 6 | **Revisar la carga de trabajo esperada** | SQLite soporta bien decenas de usuarios concurrentes de aula; para cientos simultáneos hay que migrar a PostgreSQL |

---

## 2. Variables de entorno

| Variable | Por defecto | Descripción |
|---|---|---|
| `SECRET_KEY` | valor del código (inseguro) | Clave de firma de sesiones. **Obligatoria en producción** |
| `DATABASE_PATH` | `database/simulator.db` | Ruta del archivo SQLite de **control**. Apunte a un disco persistente |
| `RUTA_AULAS` | `database/aulas` | Carpeta con las **aulas** de los estudiantes (`<paralelo>/<usuario>.db`) |
| `RUTA_PLANTILLA` | `database/plantilla/aula_base.db` | Plantilla desde la que se clona cada aula nueva |
| `HOST` | `127.0.0.1` | Dirección de escucha. Use `0.0.0.0` en contenedores/hosting |
| `PORT` | `5000` | Puerto. Los PaaS lo inyectan automáticamente |
| `THREADS` | `8` | Hilos del servidor de producción |
| `SIMULADOR_DEBUG` | desactivado | `1` activa el modo desarrollo (no usar en producción) |
| `SIMULADOR_MULTIESTUDIANTE` | activado | Un aula (base de datos) por estudiante |
| `SESSION_COOKIE_SECURE` | `false` | `true` cuando el sitio se sirve por HTTPS |
| `SESSION_COOKIE_SAMESITE` | `Lax` | Política de la cookie de sesión |
| `SESSION_COOKIE_NAME` | `session` | Nombre de la cookie (permite aislar varias instancias) |
| `SESSION_HORAS` | `8` | Duración de la sesión |
| `MAX_CONTENT_MB` | `16` | Tamaño máximo de petición |

Para desarrollo local hay una plantilla lista: **`.env.example`** (copiar como `.env`; el proyecto
lo lee solo, sin dependencias externas, y **el entorno real siempre manda**). El archivo `.env`
no se publica en Git.

Ejemplo de archivo `/etc/simulador/secrets.env` en el VPS (permisos `600`; el instalador lo genera
solo con una clave aleatoria):

```
SECRET_KEY=pega-aqui-una-cadena-aleatoria-larga
SESSION_COOKIE_SECURE=true
SESSION_HORAS=8
MAX_CONTENT_MB=16
DATABASE_PATH=/var/datos/simulator.db
RUTA_AULAS=/var/datos/aulas
RUTA_PLANTILLA=/var/datos/plantilla/aula_base.db
```

---

## 3. Arranque del servidor de producción

```bash
python serve.py                     # waitress, HOST/PORT del entorno
HOST=0.0.0.0 PORT=8080 python serve.py      # accesible desde la red
```

En **Windows** el servidor de producción es waitress (multiplataforma, ya incluido). En un
**VPS Linux** puede usar el mismo waitress o Gunicorn:

```bash
.venv/bin/pip install -r deploy/hostinger/requirements-vps.txt   # instala Gunicorn (no existe en Windows)
.venv/bin/gunicorn --workers 3 --threads 4 --bind 127.0.0.1:8080 --timeout 120 wsgi:application
```

El punto de entrada WSGI es `wsgi.py` (`application` y `app`). En el instalador de Hostinger se
elige con `--servidor gunicorn` (por defecto `waitress`).

En el **primer arranque**, si no existe la base, `serve.py` ejecuta la generación de datos de
demostración automáticamente: el sistema queda operativo sin pasos manuales.

Para probar antes de publicar:

```bash
curl http://127.0.0.1:8080/api/health     # {"estado": "OPERATIVO", ...}
curl -I http://127.0.0.1:8080/manual      # 200 OK
python deploy/verificar_produccion.py     # 11 comprobaciones funcionales con evidencia
```

---

## 4. Opción A — Este equipo Windows, encendido 24/7

Es la vía más rápida: el simulador corre como tarea programada con waitress, arranca solo y se
reinicia si falla.

```powershell
# 1) Dependencias de producción
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2) Instalar el arranque automático (genera la SECRET_KEY aleatoria y arranca el servicio)
powershell -ExecutionPolicy Bypass -File deploy\windows\instalar_arranque_automatico.ps1 -Puerto 8080

# 3) Cambiar las contraseñas de demostración
.venv\Scripts\python.exe deploy\cambiar_credenciales.py
```

* Acceso desde el propio equipo: `http://127.0.0.1:8080`
* Acceso desde la red de la universidad: `http://<nombre-del-equipo>:8080`
* Log: `logs\servidor.log`
* Detener / desinstalar: `powershell -ExecutionPolicy Bypass -File deploy\windows\detener_servidor.ps1 -Desinstalar`

**Para que sea accesible desde Internet** hace falta, además, abrir el puerto en el router
(redirección de puertos) o publicar el equipo por un túnel. Limitaciones reales de esta opción:
el servicio se cae si el equipo se apaga, duerme o cambia de red, y la dirección IP del hogar o de
la oficina puede cambiar. Es adecuada para pruebas y para uso dentro de la misma red; para servicio
público permanente conviene la opción B.

---

## 5. Opción B — VPS con dominio (recomendado para servicio público)

Requisitos: un servidor Linux (Ubuntu 22.04+ o Debian 12+), 1 vCPU / 1 GB de RAM, y un subdominio
(por ejemplo `contabilidad.utm.edu.ec`).

```bash
# 1) Usuario y dependencias del sistema
sudo adduser --disabled-password --gecos "" simulador
sudo apt update && sudo apt install -y python3-venv python3-pip nginx

# 2) Código en /opt/simulador
sudo mkdir -p /opt/simulador /var/datos /var/log/simulador
sudo chown -R simulador:simulador /opt/simulador /var/datos /var/log/simulador
# (copie el proyecto a /opt/simulador: git clone o rsync/scp)

# 3) Entorno virtual y dependencias
sudo -u simulador python3 -m venv /opt/simulador/.venv
sudo -u simulador /opt/simulador/.venv/bin/pip install -r /opt/simulador/requirements.txt

# 4) Secretos
sudo mkdir -p /etc/simulador
sudo tee /etc/simulador/secrets.env >/dev/null <<'EOF'
SECRET_KEY=CAMBIE-ESTA-CADENA-POR-UNA-ALEATORIA-LARGA
SESSION_COOKIE_SECURE=true
EOF
sudo chmod 600 /etc/simulador/secrets.env && sudo chown simulador:simulador /etc/simulador/secrets.env

# 5) Primer arranque (crea la base en /var/datos)
sudo -u simulador bash -c 'cd /opt/simulador && DATABASE_PATH=/var/datos/simulator.db .venv/bin/python serve.py' &
sleep 45 && curl -s http://127.0.0.1:8080/api/health

# 6) Servicio systemd
sudo cp /opt/simulador/deploy/systemd/simulador-contable.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now simulador-contable
sudo systemctl status simulador-contable --no-pager

# 7) Nginx + HTTPS
sudo cp /opt/simulador/deploy/nginx/simulador-contable.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/simulador-contable.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d contabilidad.utm.edu.ec     # HTTPS y renovación automática

# 8) Respaldos diarios a las 22:00
sudo -u simulador crontab -e
# 0 22 * * * cd /opt/simulador && DATABASE_PATH=/var/datos/simulator.db .venv/bin/python deploy/backup_db.py --conservar 30 >> logs/respaldo.log 2>&1

# 9) Contraseñas de demostración
sudo -u simulador bash -c 'cd /opt/simulador && DATABASE_PATH=/var/datos/simulator.db .venv/bin/python deploy/cambiar_credenciales.py'
```

Operación diaria:

```bash
sudo systemctl restart simulador-contable       # reiniciar
sudo journalctl -u simulador-contable -n 50     # ver registros del servicio
tail -f /var/log/simulador/servidor.log         # log de la aplicación
```

---

## 5.b Opción B2 — Hostinger VPS (paso a paso)

> **Importante:** en Hostinger solo los planes **VPS** pueden servir esta aplicación. Los planes de
> *Web hosting* y *Cloud hosting* están orientados a PHP/WordPress: allí no se puede mantener un
> proceso Python en ejecución ni configurar un WSGI con proxy inverso. Si su plan es de Web o Cloud
> hosting, el simulador no funcionará ahí y necesita contratar un VPS.

**Requisitos**

| Elemento | Valor recomendado |
|---|---|
| Plan | Hostinger **VPS** (KVM 1 o superior; KVM 2 para varias aulas simultáneas) |
| Sistema operativo | **Ubuntu 24.04 LTS** (o 22.04 LTS) — se elige al crear el VPS |
| Acceso | Terminal del navegador de hPanel (*VPS → Administrador* / *Terminal*) o SSH como `root` |
| Dominio | Un dominio o subdominio apuntando al VPS (por ejemplo `contabilidad.utm.edu.ec`) |

### Paso 1 — Crear el VPS y entrar

1. En hPanel: *VPS → Crear* → plantilla **Ubuntu 24.04 LTS** → elija la ubicación más cercana
   (Brasil/EE. UU. para Ecuador) → defina una contraseña de `root` robusta.
2. Copie la **IP pública** del VPS.
3. Entre por *Terminal* de hPanel o por SSH: `ssh root@<IP-DEL-VPS>`.

### Paso 2 — Apuntar el dominio (DNS)

En hPanel (o en el proveedor del dominio) cree un registro **A**:

```
Tipo: A    Nombre: contabilidad    Valor: <IP-DEL-VPS>    TTL: 300
```

Si todavía no tiene dominio configurado, puede probar primero con el subdominio que Hostinger le
asigna al VPS (`srvXXXXXX.hostinger.com`) y cambiar el dominio después.

> Configure el DNS **antes** de emitir el certificado: Let's Encrypt valida que el dominio resuelva
> a la IP del VPS. La propagación suele tardar de minutos a un par de horas.

### Paso 3 — Subir el proyecto

**Opción rápida (paquete):** desde su equipo ejecute

```bash
bash deploy/hostinger/empaquetar.sh          # genera dist/simulador-contable-<fecha>.tar.gz
```

Súbalo con el *Administrador de archivos* de hPanel (o `scp dist/simulador-contable-*.tar.gz root@<IP>:/tmp/`)
y en el VPS:

```bash
mkdir -p /tmp/simulador-contable
tar -xzf /tmp/simulador-contable-*.tar.gz -C /tmp/simulador-contable
cd /tmp/simulador-contable
```

**Alternativa con Git:**

```bash
apt-get update && apt-get install -y git
git clone <URL-DE-SU-REPOSITORIO> /tmp/simulador-contable
cd /tmp/simulador-contable
```

### Paso 4 — Instalar (un solo comando)

```bash
sudo bash deploy/hostinger/instalar_vps.sh \
     --dominio contabilidad.utm.edu.ec \
     --correo docente@utm.edu.ec
```

El instalador hace todo y es idempotente (se puede volver a ejecutar para actualizar):

| Paso | Qué hace |
|---|---|
| 1 | Instala Python 3, venv, nginx, rsync, curl, ufw y certbot |
| 2 | Crea el usuario de sistema `simulador` y las carpetas `/opt/simulador`, `/var/datos`, `/var/log/simulador` |
| 3 | Copia la aplicación a `/opt/simulador` (sin las bases ni las aulas: son datos suyos, no código) |
| 4 | Crea el entorno virtual e instala las dependencias (+ Gunicorn si elige `--servidor gunicorn`) |
| 5 | Genera `/etc/simulador/secrets.env` con **SECRET_KEY aleatoria** y las rutas de datos (permisos 600) |
| 6 | Registra y arranca el servicio systemd `simulador-contable` (se reinicia solo si falla) |
| 7 | Configura Nginx como proxy inverso del dominio y habilita el cortafuegos (SSH + HTTP/HTTPS) |
| 8 | Espera el primer arranque, que **genera la base de datos de demostración automáticamente** |
| 8b | Crea la **plantilla de aulas** en `/var/datos/plantilla/` y un respaldo completo de prueba |
| 9 | Emite el certificado **HTTPS** con Let's Encrypt y activa `SESSION_COOKIE_SECURE` |
| 10 | Programa el **respaldo diario** (22:00) de control + plantilla + **todas las aulas** (conserva 30) |

Opciones útiles: `--puerto 8080`, `--ruta /opt/simulador`, `--datos /var/datos`,
`--usuario simulador`, `--servidor gunicorn`, `--sin-firewall`.

El **dominio no está fijado en ningún archivo**: se pasa con `--dominio` y el instalador escribe
él mismo el bloque de Nginx. La plantilla del repositorio
(`deploy/nginx/simulador-contable.conf`) usa el marcador `__DOMINIO__`.

### Paso 5 — Contraseñas y verificación

```bash
# Cambiar las contraseñas de demostración (obligatorio antes de usar en clase)
sudo -u simulador bash -c 'cd /opt/simulador && DATABASE_PATH=/var/datos/simulator.db .venv/bin/python deploy/cambiar_credenciales.py'

# Cargar la nómina del paralelo (suba el CSV aparte: no viaja con el código)
sudo -u simulador env DATABASE_PATH=/var/datos/simulator.db RUTA_AULAS=/var/datos/aulas \
     RUTA_PLANTILLA=/var/datos/plantilla/aula_base.db \
     /opt/simulador/.venv/bin/python /opt/simulador/database/importar_nomina.py --csv /root/nomina.csv --paralelo B
```

Desde su equipo:

```bash
python deploy/verificar_despliegue.py --url https://SU-DOMINIO
python deploy/verificar_produccion.py --base https://SU-DOMINIO
```

### Operación del VPS

```bash
systemctl status simulador-contable --no-pager      # estado
systemctl restart simulador-contable                # reiniciar
journalctl -u simulador-contable -n 50              # registros del servicio
tail -f /var/log/simulador/servidor.log             # registro de la aplicación
certbot renew --dry-run                             # probar la renovación del certificado
```

Para actualizar una versión nueva: vuelva a subir el paquete y ejecute el instalador otra vez
(paso 4). Los archivos de `/var/datos` y `/etc/simulador` **no se tocan**, por lo que los datos y la
clave de sesión se conservan.

> Recomendaciones de recursos: 1 vCPU / 2 GB de RAM sirve cómodamente para una clase; para varios
> grupos simultáneos use KVM 2 (2 vCPU / 8 GB). Activar los *snapshots/backups* del VPS en hPanel
> añade una segunda capa de protección sobre los respaldos diarios de la base.

---

## 5.c Opción B3 — Abrir el sistema desde GitHub en el navegador (Codespaces)

Es la vía más directa **sin servidor propio y sin instalar nada en el equipo**: GitHub crea un entorno
en la nube con el proyecto ya instalado y publica el puerto de la aplicación.

> **Aclaración necesaria:** GitHub Pages (la portada del repositorio) **no puede ejecutar** esta
> aplicación — solo publica contenido estático, y el simulador necesita un proceso Python y una base
> de datos. La forma de “abrirlo desde GitHub” es Codespaces, no Pages.

**Cómo funciona** (ya está configurado en el repositorio, carpeta `.devcontainer/`):

| Archivo | Función |
|---|---|
| `.devcontainer/devcontainer.json` | Define el entorno (Python 3.12), publica el puerto **5000** y abre la vista previa automáticamente |
| `.devcontainer/instalar.sh` | Al crear el entorno: instala dependencias, genera la empresa simulada y corre las 113 pruebas |
| `.devcontainer/arrancar.sh` | Al iniciar el entorno: arranca `serve.py` con una `SECRET_KEY` propia (no versionada) |

**Para el estudiante**

1. **https://codespaces.new/AngelicaGuillen1/simulador-contable-utm**
   (o *Code → Codespaces → Create codespace on main*).
2. Esperar 1–3 minutos y el simulador se abre en una pestaña
   (`https://<codespace>-5000.app.github.dev`).
3. Iniciar sesión con `estudiante / estudiante123`.
4. Al terminar: *Codespaces → Stop codespace* para no consumir cuota.

**Límites honestos**

* Es un entorno **individual**: cada estudiante tiene su propia base de datos; no hay una URL única
  compartida para todo el curso.
* La cuenta personal gratuita incluye **120 horas-núcleo/mes** (≈ 60 h reales en un entorno de
  2 núcleos). Detener el entorno al terminar es lo que hace sostenible el semestre.
* Los puertos se publican como **privados** (solo su cuenta accede). Si necesita mostrar el sistema al
  docente durante una clase, en el panel *Ports* puede cambiar la visibilidad a *Public* de forma
  temporal.
* GitHub puede solicitar verificación de la cuenta la primera vez que se usa Codespaces.

---

## 5.d Opción B4 — URL pública gratuita con PythonAnywhere (sin Hostinger)

Si lo que se busca es **una sola dirección web para todo el curso**, sin contratar un VPS, el plan
gratuito de **PythonAnywhere** ejecuta aplicaciones Flask con SQLite y entrega una URL del tipo
`https://usuario.pythonanywhere.com`.

1. Cree una cuenta gratuita (*Beginner*) en **pythonanywhere.com**.
2. Abra una consola **Bash** y suba el proyecto:

   ```bash
   git clone https://github.com/AngelicaGuillen1/simulador-contable-utm.git
   cd simulador-contable-utm
   python3.10 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python database/seed_data.py
   ```

3. **Web → Add a new web app → Manual configuration → Python 3.10**.
4. En *Virtualenv* escriba: `/home/USUARIO/simulador-contable-utm/.venv`
5. En *WSGI configuration file* pegue **todo** el contenido de
   `deploy/pythonanywhere/wsgi.py` (ajustando `USUARIO` y la ruta del proyecto).
6. Pulse **Reload** y abra `https://USUARIO.pythonanywhere.com`.
7. Antes de usarlo con estudiantes:
   `python deploy/cambiar_credenciales.py` (cambiar las contraseñas demo).

**Límites honestos del plan gratuito:** la aplicación se “duerme” si nadie la usa durante un rato y
despierta en unos segundos al primer acceso; hay cuota diaria de CPU (suficiente para una clase, no
para cientos de usuarios simultáneos), y el almacenamiento es limitado (~512 MB). Para uso intensivo,
la opción B (VPS) sigue siendo la adecuada.

---

## 6. Opción C — Plataforma gestionada (Render, Railway, Fly.io)

El repositorio ya incluye lo necesario: `Procfile`, `Dockerfile` y `render.yaml`.

**Render (con `render.yaml`)**

1. Suba el proyecto a un repositorio Git (GitHub/GitLab).
2. En Render: *New → Blueprint* y seleccione el repositorio. Render lee `render.yaml`, crea el
   servicio web, el **disco persistente** en `/var/datos` y genera `SECRET_KEY` automáticamente.
3. Al terminar el despliegue, verifique `https://<nombre>.onrender.com/api/health`.
4. Cambie las contraseñas de demostración: en la consola del servicio, `python deploy/cambiar_credenciales.py`.

**Docker (cualquier proveedor o servidor propio)**

```bash
docker build -t simulador-contable .
docker run -d --name simulador -p 8080:8080 \
  -e SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
  -e SESSION_COOKIE_SECURE=false \
  -v simulador_datos:/datos \
  --restart unless-stopped \
  simulador-contable
```

> **Aviso honesto sobre los planes gratuitos:** el plan gratuito de estas plataformas usa
> almacenamiento efímero. Sin disco persistente, la base SQLite se regenera con los datos de
> demostración en cada despliegue o reinicio y **todo el trabajo de los estudiantes se pierde**.
> Para uso real: plan con disco persistente (Render Starter o superior) o la opción B.

---

## 7. Respaldos y restauración

El sistema usa **varias** bases SQLite: la de **control**, la **plantilla** y un **aula por
estudiante**. El respaldo completo (`--todas`) las incluye todas:

```bash
python deploy/backup_db.py --todas               # COMPLETO: control + plantilla + todas las aulas
python deploy/backup_db.py --todas --conservar 30
python deploy/backup_db.py --todas --destino /var/backups/simulador
python deploy/backup_db.py                       # solo la base de control (rápido)
python deploy/backup_db.py --origen /var/datos/simulator.db --destino /var/backups/simulador
```

En el VPS, con las rutas de datos fuera del código:

```bash
sudo -u simulador env DATABASE_PATH=/var/datos/simulator.db \
     RUTA_AULAS=/var/datos/aulas RUTA_PLANTILLA=/var/datos/plantilla/aula_base.db \
     /opt/simulador/.venv/bin/python /opt/simulador/deploy/backup_db.py --todas
```

El respaldo completo crea una carpeta con marca de tiempo:

```
deploy/respaldos/20260919_2200/
    simulator.db
    plantilla/aula_base.db
    aulas/B/ealcivar4002.db
    aulas/B/javiles8757.db
```

### Restaurar

```bash
python deploy/restaurar_db.py --listar                          # ver qué respaldos hay
python deploy/restaurar_db.py --desde deploy/respaldos/20260919_2200          # SIMULA (no escribe)
python deploy/restaurar_db.py --desde deploy/respaldos/20260919_2200 --si     # restaura de verdad
```

Antes de sobrescribir, el script copia el estado actual a
`deploy/respaldos/antes_de_restaurar_<marca>/`, de modo que la restauración se puede deshacer.
Nunca borra aulas que no estén en el respaldo. Después, reinicie el servicio.

El respaldo usa la API de copia en caliente de SQLite, por lo que puede ejecutarse con el sistema en
funcionamiento. Los archivos `-wal` y `-shm` no hace falta copiarlos: la API los consolida.

---

## 8. Actualizar una versión desplegada

```bash
cd /opt/simulador
git pull                                  # o rsync de los archivos modificados
.venv/bin/pip install -r requirements.txt # si cambiaron dependencias
sudo systemctl restart simulador-contable
curl -s http://127.0.0.1:8080/api/health
```

En Hostinger, la vía más simple es volver a ejecutar el instalador con el paquete nuevo: es
**idempotente** (conserva `/etc/simulador/secrets.env`, la base y las aulas de `/var/datos`):

```bash
sudo bash deploy/hostinger/instalar_vps.sh --dominio TU-DOMINIO
```

Las migraciones de esquema se resuelven con `database/db_init.py` (crea tablas faltantes) y, si se
requiere reiniciar los datos de demostración, con `python database/seed_data.py` — **esto último
borra la base**: haga respaldo antes.

---

## 9. Diagnóstico rápido

| Síntoma | Causa | Solución |
|---|---|---|
| `Address already in use` | Otro proceso usa el puerto | `netstat -ano \| grep <puerto>` y detenga el PID, o cambie `PORT` |
| 502 Bad Gateway en el VPS | El servicio no está escuchando | `systemctl status simulador-contable`; revise `/var/log/simulador/servidor.log` |
| La base se reinicia sola | Almacenamiento efímero (plan gratuito de PaaS) | Use disco persistente o VPS |
| `database is locked` | Muchas escrituras simultáneas sobre SQLite | Aumente `THREADS` con moderación; para carga alta migre a PostgreSQL |
| El sitio responde por HTTP pero no por HTTPS | Falta el certificado o el proxy | `sudo certbot --nginx -d <dominio>` y revise `nginx -t` |
| Sesiones que se cierran al recargar | `SESSION_COOKIE_SECURE=true` sin HTTPS | Sirva por HTTPS o desactive la variable |
| La tarea de Windows no arranca el servicio | No se ejecutó como Administrador (opción `-Cuando AlInicio`) | Use `-Cuando AlIniciarSesion` o abra PowerShell como Administrador |

---

## 10. Comprobación final del despliegue

```bash
curl -s https://<su-dominio>/api/health          # estado OPERATIVO y período activo
curl -s -o /dev/null -w "%{http_code}\n" https://<su-dominio>/login
curl -s -o /dev/null -w "%{http_code}\n" https://<su-dominio>/manual
```

Y en el navegador: iniciar sesión con la cuenta administrador ya protegida, registrar una venta de
prueba y comprobar en **Estados Financieros → Situación Financiera** que aparece el banner verde
*Activo = Pasivo + Patrimonio ✓*.
