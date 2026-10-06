# Sistema de Gestión de Biblioteca (Microservicios)

Este proyecto implementa una arquitectura basada en **microservicios independientes** para la administración de una biblioteca digital. Cada microservicio cuenta con su propia base de datos SQLite aislada, comunicación síncrona mediante REST/HTTP (JSON), despliegue en contenedores Docker y orquestación unificada mediante Docker Compose.

---

## 📐 Arquitectura del Sistema

```text
                                  +-----------------------+
                                  |    Docker Compose     |
                                  +-----------------------+
                                              |
                     +------------------------+------------------------+
                     |                        |                        |
             +---------------+        +---------------+        +---------------+
             |   Catálogo    |        |   Préstamos   |        | Notificaciones|
             |   (Python)    |        |   (Python)    |        |   (Python)    |
             | Puerto: 8001  |        | Puerto: 8002  |        | Puerto: 8003  |
             +-------+-------+        +-------+-------+        +-------+-------+
                     |                        |                        |
              catalogo_data            prestamos_data          notificaciones_data
              (catalogo.db)            (prestamos.db)          (notificaciones.db)
```

### Principales Principios Arquitectónicos
- **Base de Datos por Servicio (Database per Service):** Cada servicio gestiona su persistencia de forma independiente mediante volúmenes nombrados de Docker montados en `/data`.
- **Desacoplamiento y Resiliencia:** El microservicio de Préstamos realiza llamadas HTTP a Catálogo (gestión de stock) y Notificaciones (alertas). Si el servicio de Notificaciones falla, el flujo de devolución no se bloquea (tolerancia a fallos con timeout de 3 segundos).
- **Rollback Transaccional Distribuido:** Si la persistencia local de un préstamo falla tras haber reservado stock en Catálogo, el servicio realiza una llamada de compensación (`PATCH /libros/<id>/disponibilidad` con `{"operacion": "reponer"}`).

---

## 📂 Estructura del Repositorio

```text
.
├── docker-compose.yml
├── README.md
├── .gitignore
├── catalogo/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   └── database.py
├── prestamos/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   └── database.py
└── notificaciones/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py
    └── database.py
```

---

## 🚀 Despliegue con Docker Compose

### Requisitos Previos
- [Docker](https://www.docker.com/) instalado.
- [Docker Compose](https://docs.docker.com/compose/) instalado.

### Comandos de Ejecución

1. **Iniciar todos los microservicios:**
   ```bash
   docker-compose up --build
   ```

2. **Ejecutar en modo desacoplado (Background):**
   ```bash
   docker-compose up -d --build
   ```

3. **Verificar estado de los contenedores:**
   ```bash
   docker-compose ps
   ```

4. **Ver logs del sistema:**
   ```bash
   docker-compose logs -f
   ```

5. **Detener y remover contenedores:**
   ```bash
   docker-compose down
   ```

---

## ⚙️ Configuración y Variables de Entorno

El servicio de **Préstamos** utiliza las siguientes variables de entorno (configuradas en `docker-compose.yml`):

| Variable | Valor por Defecto | Descripción |
| :--- | :--- | :--- |
| `CATALOGO_URL` | `http://catalogo:8001` | URL interna de red Docker para el servicio de Catálogo |
| `NOTIFICACIONES_URL` | `http://notificaciones:8003` | URL interna de red Docker para Notificaciones |
| `DIAS_PRESTAMO` | `7` | Días permitidos por préstamo antes de generar mora |
| `MULTA_POR_DIA` | `5` | Monto acumulado por día de retraso |
| `DIAS_AVISO` | `2` | Ventana de días para alertar préstamos próximos a vencer |

---

## 📖 Especificación de Endpoints y Guía de Uso (cURL)

### 1. Servicio de Catálogo (`http://localhost:8001`)

- **GET `/health`**
  - Estado del servicio.
  ```bash
  curl -X GET http://localhost:8001/health
  ```

- **POST `/autores`**
  - Registrar autor.
  ```bash
  curl -X POST http://localhost:8001/autores \
    -H "Content-Type: application/json" \
    -d '{"nombre": "Gabriel García Márquez", "nacionalidad": "Colombiana"}'
  ```

- **GET `/autores`**
  - Listar autores.
  ```bash
  curl -X GET http://localhost:8001/autores
  ```

- **POST `/libros`**
  - Registrar un nuevo libro en el catálogo.
  ```bash
  curl -X POST http://localhost:8001/libros \
    -H "Content-Type: application/json" \
    -d '{"titulo": "Cien Años de Soledad", "autor_id": 1, "ejemplares_totales": 3}'
  ```

- **GET `/libros`**
  - Obtener lista de libros (Soporta filtro `?disponible=true`).
  ```bash
  # Obtener todos los libros
  curl -X GET http://localhost:8001/libros

  # Filtrar solo libros disponibles
  curl -X GET "http://localhost:8001/libros?disponible=true"
  ```

- **GET `/libros/<id>`**
  - Obtener un libro por su ID.
  ```bash
  curl -X GET http://localhost:8001/libros/1
  ```

- **PUT `/libros/<id>`**
  - Actualizar datos de un libro.
  ```bash
  curl -X PUT http://localhost:8001/libros/1 \
    -H "Content-Type: application/json" \
    -d '{"titulo": "Cien Años de Soledad - Edición Especial", "autor_id": 1, "ejemplares_totales": 5, "ejemplares_disponibles": 5}'
  ```

- **DELETE `/libros/<id>`**
  - Eliminar un libro.
  ```bash
  curl -X DELETE http://localhost:8001/libros/1
  ```

- **PATCH `/libros/<id>/disponibilidad`**
  - Modificar el stock del libro (`descontar` o `reponer`).
  ```bash
  curl -X PATCH http://localhost:8001/libros/1/disponibilidad \
    -H "Content-Type: application/json" \
    -d '{"operacion": "descontar"}'
  ```

---

### 2. Servicio de Préstamos (`http://localhost:8002`)

- **GET `/health`**
  - Estado del servicio.
  ```bash
  curl -X GET http://localhost:8002/health
  ```

- **POST `/prestamos`**
  - Registrar un nuevo préstamo (descuenta automáticamente del catálogo).
  ```bash
  curl -X POST http://localhost:8002/prestamos \
    -H "Content-Type: application/json" \
    -d '{"usuario": "juan.perez", "libro_id": 1}'
  ```

- **GET `/prestamos`**
  - Listar préstamos (filtro opcional `?usuario=juan.perez`).
  ```bash
  curl -X GET "http://localhost:8002/prestamos?usuario=juan.perez"
  ```

- **PUT `/prestamos/<id>/devolucion`**
  - Registrar devolución de un libro (repone stock en Catálogo y calcula multas/notifica si aplica).
  ```bash
  curl -X PUT http://localhost:8002/prestamos/1/devolucion
  ```

- **POST `/prestamos/revisar-vencimientos`**
  - Proceso de revisión batch que busca préstamos por vencer e inicia las notificaciones correspondientes.
  ```bash
  curl -X POST http://localhost:8002/prestamos/revisar-vencimientos
  ```

---

### 3. Servicio de Notificaciones (`http://localhost:8003`)

- **GET `/health`**
  - Estado del servicio.
  ```bash
  curl -X GET http://localhost:8003/health
  ```

- **POST `/notificar`**
  - Recibe un evento de notificación, lo imprime en consola y lo guarda en la BD.
  ```bash
  curl -X POST http://localhost:8003/notificar \
    -H "Content-Type: application/json" \
    -d '{"tipo": "MULTA", "usuario": "juan.perez", "mensaje": "Tienes una multa pendiente de $10.00"}'
  ```

- **GET `/notificaciones`**
  - Historial de notificaciones registradas.
  ```bash
  curl -X GET http://localhost:8003/notificaciones
  ```

---

## 🧪 Pruebas Rápidas de Verificación (Flujo Completo)

1. **Crear autor y libro:**
   ```bash
   curl -X POST http://localhost:8001/autores -H "Content-Type: application/json" -d '{"nombre": "Isabel Allende", "nacionalidad": "Chilena"}'
   curl -X POST http://localhost:8001/libros -H "Content-Type: application/json" -d '{"titulo": "La Casa de los Espíritus", "autor_id": 1, "ejemplares_totales": 1}'
   ```

2. **Solicitar un préstamo:**
   ```bash
   curl -X POST http://localhost:8002/prestamos -H "Content-Type: application/json" -d '{"usuario": "maria.gomez", "libro_id": 1}'
   ```

3. **Verificar que el catálogo marca el libro como AGOTADO:**
   ```bash
   curl -X GET http://localhost:8001/libros/1
   ```

4. **Intentar pedir el mismo libro sin stock (retornará HTTP 409):**
   ```bash
   curl -X POST http://localhost:8002/prestamos -H "Content-Type: application/json" -d '{"usuario": "carlos.lopez", "libro_id": 1}'
   ```

5. **Devolver el libro (repone stock en Catálogo):**
   ```bash
   curl -X PUT http://localhost:8002/prestamos/1/devolucion
   ```

6. **Consultar el historial de notificaciones:**
   ```bash
   curl -X GET http://localhost:8003/notificaciones
   ```
