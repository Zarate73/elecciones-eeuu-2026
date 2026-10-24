#!/usr/bin/env bash
# Publica los resultados de un estado sin chocar con otros flujos que publican casi al mismo tiempo.
# Uso (desde la raíz, en GitHub Actions):  bash scripts/publicar.sh <estado> "<mensaje del commit>"
#
# Solo los archivos propios del estado (<estado>/produccion/salidas y <estado>/README.md) viajan de la corrida: se
# copian aparte una vez y en cada intento se reponen SOBRE la versión más reciente de main. Los compartidos (README
# principal y tablero/datos) se regeneran en cada intento, así que nunca hay conflictos entre estados. Si otro flujo
# publica entre el fetch y el push, se reintenta desde cero (sin stash: un stash pop puede fallar tras un reset).
set -euo pipefail
E="$1"
MSG="$2"
git config user.name  "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
TMP="$(mktemp -d)"
cp -a "$E/produccion/salidas" "$TMP/salidas"
cp -a "$E/README.md" "$TMP/README.md"
for intento in 1 2 3 4 5; do
  git fetch -q origin main
  git reset -q --hard origin/main
  rm -rf "$E/produccion/salidas"
  cp -a "$TMP/salidas" "$E/produccion/salidas"
  cp -a "$TMP/README.md" "$E/README.md"
  (cd "$E/produccion" && python scripts/actualizar_readme.py)
  python scripts/exportar_tablero.py
  git add -A tablero/datos "$E/produccion/salidas" "$E/README.md" README.md
  if git diff --cached --quiet; then
    echo "Sin cambios"
    exit 0
  fi
  git commit -q -m "$MSG"
  if git push -q origin HEAD:main; then
    echo "Publicado (intento $intento)"
    exit 0
  fi
  echo "Push rechazado: otro flujo publicó antes (intento $intento). Reintento sobre la nueva versión de main."
  sleep $((intento * 7))
done
echo "No se pudo publicar tras 5 intentos" >&2
exit 1
