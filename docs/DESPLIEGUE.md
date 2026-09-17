# QReaper — arquitectura de despliegue (IDE → GitHub → VPS por SSH)

Documenta el flujo completo pedido en la práctica (requisito 5): del editor al
servidor con IP pública, autenticación por clave SSH y publicación por HTTPS.

## Flujo de extremo a extremo

```
   [IDE local]                [GitHub]                 [VPS Hetzner]
   VS Code / Claude Code  →   repo qreaper      →      167.233.28.102 (ubuntu-4gb-fsn1-1)
        │  git push            (privado)                    │
        │                                                   │  Traefik (TLS Let's Encrypt)
        ▼                                                   ▼
   commit firmado ──────────── git pull ─────────►  Docker: qreaper-web:8000
                                                           │
                                              https://qreaper.b-dev.es  ◄── usuario
```

- **Autenticación:** SSH con par de claves (privada en el portátil, pública en
  `~/.ssh/authorized_keys` del VPS). El servidor es **publickey-only**, sin
  contraseña. Puerto SSH filtrado por `ufw` + `fail2ban`.
- **Puerta pública:** el contenedor **no expone puertos**; la única entrada es
  **Traefik**, que termina el TLS (certificado Let's Encrypt automático,
  `certresolver=le`) y enruta `qreaper.b-dev.es` al puerto 8000 del contenedor.
- **DNS:** registro `qreaper` en la zona `b-dev.es` (Cloudflare) apuntando a la
  IP del VPS.

## Requisitos en el servidor

Ya presentes en el VPS de b-dev.es: Docker + Docker Compose y el stack de
Traefik corriendo en `/opt/bdev` con la red externa `bdev_default` y el
entrypoint `websecure`.

## Pasos

### 1. DNS (una vez)

Crear en Cloudflare un registro **A** `qreaper.b-dev.es` → IP del VPS
(proxy activado, naranja).

### 2. Traer el código al servidor

```bash
ssh root@167.233.28.102
git clone https://github.com/bdjoseluis/qreaper.git /opt/qreaper   # primera vez
# actualizaciones posteriores:
cd /opt/qreaper && git pull
```

### 3. Levantar el servicio

```bash
cd /opt/qreaper
docker compose -f deploy/docker-compose.vps.yml up -d --build
```

Traefik detecta el contenedor por sus *labels*, pide el certificado y publica
`https://qreaper.b-dev.es`. La primera emisión del certificado tarda unos
segundos.

### 4. Comprobar

```bash
curl -s https://qreaper.b-dev.es/salud
# {"estado":"ok","version":"0.1.0"}
```

Web de uso: <https://qreaper.b-dev.es/app> · API docs: `/docs`.

## Notas de seguridad

- **Sandbox desactivado en producción** (`QREAPER_SANDBOX=off`): el análisis
  usa señales de URL + scoring + BD + informe, pero **no detona** las URLs. La
  detonación real (que ejecuta contenido potencialmente hostil) solo se usa en
  local/entorno aislado, y es lo que se enseña en el vídeo demo.
- El contenedor corre con límite de memoria (400 MB) y logs rotados.
- La base de datos SQLite persiste en el volumen `qreaper-data`.

## Actualizar una versión ya desplegada

```bash
cd /opt/qreaper && git pull
docker compose -f deploy/docker-compose.vps.yml up -d --build
```
