#!/usr/bin/env bash
# Publica los resultados preliminares sin chocar con otros flujos (misma lógica que publicar.sh: los archivos propios se
# copian aparte y se reponen sobre la versión más reciente de main en cada intento).
set -euo pipefail
MSG="$1"
git config user.name  "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
TMP="$(mktemp -d)"
cp -a resultados/salidas "$TMP/salidas"
cp -a resultados/pronosticos_finales "$TMP/finales"
cp -a tablero/datos/resultados.json "$TMP/resultados.json"
for intento in 1 2 3 4 5; do
  git fetch -q origin main
  git reset -q --hard origin/main
  rm -rf resultados/salidas
  cp -a "$TMP/salidas" resultados/salidas
  mkdir -p resultados/pronosticos_finales
  cp -a "$TMP/finales/." resultados/pronosticos_finales/
  cp -a "$TMP/resultados.json" tablero/datos/resultados.json
  git add -A resultados/salidas resultados/pronosticos_finales tablero/datos/resultados.json
  if git diff --cached --quiet; then
    echo "Sin cambios"; exit 0
  fi
  git commit -q -m "$MSG"
  if git push -q origin HEAD:main; then
    echo "Publicado (intento $intento)"; exit 0
  fi
  sleep $((intento * 5))
done
echo "No se pudo publicar tras 5 intentos" >&2
exit 1
