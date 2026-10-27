# ==============================================================================
# SCRIPT POWERSHELL PARA CONSULTAR BASES DE DATOS SQLITE EN DOCKER
# ==============================================================================

function Show-Table {
    param([string]$container, [string]$dbPath, [string]$table)
    Write-Host "`n=== Contenedor: $container | Tabla: $table ===" -ForegroundColor Yellow
    docker exec $container python -c "
import sqlite3
try:
    conn = sqlite3.connect('$dbPath')
    cur = conn.cursor()
    cur.execute('SELECT * FROM $table')
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    print(' | '.join(f'{c:<18}' for c in cols))
    print('-' * (21 * len(cols)))
    if not rows:
        print('(Tabla vacia)')
    for r in rows:
        print(' | '.join(f'{str(val):<18}' for val in r))
except Exception as e:
    print(f'Error al consultar: {e}')
"
}

Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host "        CONSULTA DIRECTA DE BASES DE DATOS SQLITE EN DOCKER         " -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan

Show-Table "catalogo_service" "/data/catalogo.db" "autores"
Show-Table "catalogo_service" "/data/catalogo.db" "libros"
Show-Table "prestamos_service" "/data/prestamos.db" "prestamos"
Show-Table "prestamos_service" "/data/prestamos.db" "multas"
Show-Table "notificaciones_service" "/data/notificaciones.db" "notificaciones"

Write-Host "`nConsulta finalizada.`n" -ForegroundColor Green
