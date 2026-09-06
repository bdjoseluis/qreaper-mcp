# Dataset QReaper — 30 QR legítimos + 30 QR maliciosos (simulados)

Generado con `reportlab` (QR real, no imágenes de relleno). Cada QR legítimo
tiene su pareja "typosquat" en `maliciosos/` con el mismo número de archivo,
para poder comparar señales fácilmente (ver `manifest.csv`).

⚠️ Los dominios maliciosos son **inventados** (no son enlaces de phishing
reales), tal y como pide `docs/equipo/JUANFRAN.md`.

## Cómo instalarlo en tu repo

1. Copia el contenido de `datasets/legitimos/` y `datasets/maliciosos/` a las
   carpetas del mismo nombre en tu clon local de `qreaper` (sustituye o
   añade, sin tocar el `.gitkeep` ni el `ejemplo*.png` que ya había).
2. Copia `datasets/manifest.csv` a `datasets/manifest.csv` en el repo.
3. Desde tu rama:
   ```powershell
   git checkout feat/informe-juanfran
   git add datasets/
   git commit -m "dataset: 30 QR legitimos + 30 maliciosos simulados"
   git push origin feat/informe-juanfran
   ```
4. Abre el Pull Request en GitHub para que Jose lo revise.
