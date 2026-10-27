#!/usr/bin/env bash
# ==============================================================================
# SCRIPT PARA CONSULTAR LAS BASES DE DATOS SQLITE DIRECTAMENTE DESDE DOCKER
# ==============================================================================

CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

imprimir_tabla() {
    local contenedor="$1"
    local db_path="$2"
    local tabla="$3"
    
    echo -e "\n${YELLOW}=== Contenedor: $contenedor | Tabla: $tabla ===${NC}"
    docker exec "$contenedor" python -c "
import sqlite3
try:
    conn = sqlite3.connect('$db_path')
    cur = conn.cursor()
    cur.execute('SELECT * FROM $tabla')
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    print(' | '.join(f'{c:<18}' for c in cols))
    print('-' * (21 * len(cols)))
    if not rows:
        print('(Tabla vacía)')
    for r in rows:
        print(' | '.join(f'{str(val):<18}' for val in r))
except Exception as e:
    print(f'Error al consultar: {e}')
"
}

echo -e "${CYAN}====================================================================${NC}"
echo -e "${CYAN}        CONSULTA DIRECTA DE BASES DE DATOS SQLITE EN DOCKER         ${NC}"
echo -e "${CYAN}====================================================================${NC}"

# 1. Catálogo
imprimir_tabla "catalogo_service" "/data/catalogo.db" "autores"
imprimir_tabla "catalogo_service" "/data/catalogo.db" "libros"

# 2. Préstamos
imprimir_tabla "prestamos_service" "/data/prestamos.db" "prestamos"
imprimir_tabla "prestamos_service" "/data/prestamos.db" "multas"

# 3. Notificaciones
imprimir_tabla "notificaciones_service" "/data/notificaciones.db" "notificaciones"

echo -e "\n${GREEN}Consulta finalizada.${NC}\n"
