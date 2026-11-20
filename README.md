# Sistema Web de Consulta de Datos Abiertos

Proyecto integrador de **Desarrollo de Aplicaciones con Acceso a Datos**.

**Integrantes:**
- Owhen Geovanny Padilla Polanco
- Alan Padilla Alvear

Aplicación web en **Python + Flask** que consume una API REST de datos abiertos de Colombia, guarda los registros en **SQL Server** y los muestra en una página con filtros y un resumen numérico. Está organizada con el patrón **MVC**.

Flujo completo:

```
API datos.gov.co  →  Python (requests)  →  SQL Server (pyodbc)  →  Flask  →  Navegador
```

---

## 1. Conjunto de datos

| | |
|---|---|
| **Nombre** | Tráfico de voz en minutos de proveedores móviles |
| **Entidad** | Ministerio de Tecnologías de la Información y las Comunicaciones (MinTIC) |
| **Identificador** | `s5df-6cb7` |
| **Endpoint** | `https://www.datos.gov.co/resource/s5df-6cb7.json` |
| **Tamaño** | 2085 registros (años 2023 a 2026) |

Ejemplo de la respuesta JSON (un registro):

```json
{
  "anno": "2023",
  "trimestre": "4",
  "proveedor": "ALMACENES EXITO INVERSIONES S.A.S.",
  "proveedor_destino": "ALMACENES EXITO INVERSIONES S.A.S.",
  "trafico_prepago": "8858703",
  "trafico_pospago": "0"
}
```

La API entrega **todos los valores como texto**. Por eso, antes de guardarlos, el modelo convierte los números con `int()`.

### Campos utilizados

| Campo | Qué representa | Tipo en SQL Server |
|---|---|---|
| `anno` | Año del reporte | `SMALLINT` |
| `trimestre` | Trimestre del año (1 a 4) | `TINYINT` |
| `proveedor` | Operador móvil que origina las llamadas | `NVARCHAR(150)` |
| `proveedor_destino` | Operador o red que recibe las llamadas | `NVARCHAR(500)` |
| `trafico_prepago` | Minutos de voz de usuarios prepago | `BIGINT` |
| `trafico_pospago` | Minutos de voz de usuarios pospago | `BIGINT` |

Los tráficos usan `BIGINT` porque los valores más altos del dataset (3.266.045.973 minutos prepago y 5.002.289.178 pospago) no caben en `INT`, cuyo máximo es 2.147.483.647.

---

## 2. Requisitos

- Windows con **Python 3.14** (o superior).
- **SQL Server** (se usó SQL Server 2025 Express) con acceso por el puerto 1433.
- **ODBC Driver 18 for SQL Server**.
- Conexión a Internet para consultar la API.

Dependencias de Python (en `requirements.txt`): `Flask`, `requests`, `pyodbc` y `python-dotenv`, junto con las librerías que ellas instalan.

---

## 3. Instalación

Todos los comandos se ejecutan en **PowerShell**, dentro de la carpeta `proyecto_datos_abiertos`.

**1. Crear y activar el entorno virtual**

```powershell
py -3.14 -m venv venv
.\venv\Scripts\Activate.ps1
```

**2. Instalar las dependencias**

```powershell
pip install -r requirements.txt
```

**3. Crear la base de datos y la tabla**

Ejecutar `sql/crear_tabla.sql` en SQL Server (con SSMS o con la extensión *SQL Server (mssql)* de VS Code).

**4. Configurar la conexión**

Copiar `.env.example` como `.env` y completar los datos del servidor:

```powershell
Copy-Item .env.example .env
```

| Variable | Para qué sirve |
|---|---|
| `DB_SERVER` | Dirección del servidor y puerto, por ejemplo `192.168.1.50,1433` o `localhost\SQLEXPRESS` |
| `DB_NAME` | Base de datos (`DatosAbiertosDB`) |
| `DB_DRIVER` | Controlador ODBC instalado |
| `DB_TRUSTED` | `yes` = autenticación de Windows · `no` = login de SQL Server |
| `DB_USER` / `DB_PASSWORD` | Login de SQL Server (solo si `DB_TRUSTED=no`) |
| `API_RESOURCE_ID` | Identificador del dataset (`s5df-6cb7`) |
| `API_LIMIT` | Cuántos registros pedir a la API; `none` = todos |

> El archivo `.env` contiene la contraseña: **no se sube al repositorio** (está en `.gitignore`).

---

## 4. Ejecución

```powershell
python app.py
```

Abrir en el navegador: **http://127.0.0.1:5000**

- La primera vez la tabla está vacía y la aplicación **descarga los datos de la API automáticamente** al abrir la página.
- El botón **«Sincronizar con la API»** vuelve a consultar la API y guarda solo los registros nuevos. Si no hay nada nuevo, muestra *«Nuevos registros guardados: 0»*.
- Los campos de la fila de filtros buscan dentro de cada columna. Se pueden combinar y se aplican con **«Filtrar»**.

---

## 5. Estructura del proyecto (MVC)

```
proyecto_datos_abiertos/
├── app.py                  ← Controlador: rutas de Flask
├── api/
│   └── api_client.py       ← Cliente de la API (petición HTTP y JSON)
├── models/
│   └── datos_model.py      ← Modelo: conexión y consultas a SQL Server
├── templates/
│   └── index.html          ← Vista: página que ve el usuario
├── static/
│   └── estilos.css         ← Estilos de la vista
├── sql/
│   └── crear_tabla.sql     ← Script de la base de datos y la tabla
├── docs/
│   └── capturas/           ← Evidencias
├── .env.example            ← Plantilla de configuración (sin contraseñas)
├── requirements.txt
└── README.md
```

| Capa | Archivo | Responsabilidad |
|---|---|---|
| **Modelo** | `models/datos_model.py` | Se conecta a SQL Server con `pyodbc`, guarda los registros nuevos, consulta con filtros y calcula el resumen. |
| **Vista** | `templates/index.html` | Muestra la tabla, los filtros, el resumen, los mensajes y el botón de sincronizar. No accede a la base de datos. |
| **Controlador** | `app.py` | Recibe las peticiones del navegador, llama al modelo y a la API, y envía los datos a la vista. |
| Cliente de la API | `api/api_client.py` | Hace la petición HTTP a datos.gov.co y devuelve la lista de registros. |

### Rutas

| Ruta | Método | Qué hace |
|---|---|---|
| `/` | GET | Si la tabla tiene menos de 100 registros, sincroniza automáticamente. Después consulta los registros (con los filtros de la URL) y el resumen, y muestra la página. |
| `/sincronizar` | POST | Descarga los datos de la API, guarda los nuevos, avisa cuántos fueron con un mensaje (`flash`) y redirige a `/`. |

`/sincronizar` es **POST** porque cambia datos en la base. Al terminar redirige a `/` (patrón *POST → redirect → GET*): así, si el usuario recarga la página, no se vuelve a sincronizar.

### Funciones principales

| Función | Archivo | Qué hace |
|---|---|---|
| `APIClient.obtener_registros()` | `api_client.py` | Pide los datos a la API por páginas (`$limit` y `$offset`) con un orden fijo (`$order`), hasta traerlos todos. |
| `guardar_registros(datos)` | `datos_model.py` | Inserta solo los registros que no existen y devuelve cuántos guardó. |
| `sincronizar_si_es_necesario()` | `datos_model.py` | Sincroniza solo si la tabla tiene menos de 100 registros. |
| `consultar_registros(filtros)` | `datos_model.py` | `SELECT` con filtros por columna (`LIKE` con parámetros `?`), ordenado por año y trimestre más recientes. |
| `obtener_resumen()` | `datos_model.py` | `COUNT` y `SUM` del tráfico prepago y pospago de toda la tabla. |

---

## 6. Cómo se evitan los duplicados

El dataset no trae un campo identificador propio. Cada registro se identifica con la combinación:

**`anno + trimestre + proveedor + proveedor_destino`**

En palabras: *un proveedor envía tráfico a un destino una sola vez por trimestre de cada año.* Se comprobó con los datos reales que con estas cuatro columnas no se repite ninguna combinación, y que con solo tres sí hay repeticiones.

Hay dos defensas:

1. **En Python:** `guardar_registros()` carga una vez las claves que ya están en la tabla dentro de un `set` (conjunto) e inserta solo las que no están. Así nunca intenta insertar un duplicado.
2. **En SQL Server:** la restricción `UNIQUE (anno, trimestre, proveedor, proveedor_destino)` es la garantía final. Si llegara un duplicado, la base lo rechaza con el **error 2627**.

Por eso, una segunda sincronización da **0 registros nuevos** y la tabla sigue con 2085 filas.

---

## 7. Resumen numérico

La página muestra tres valores calculados en SQL Server sobre **toda la tabla** (no cambian con los filtros):

| Indicador | Consulta |
|---|---|
| Total de registros | `COUNT(*)` |
| Tráfico prepago (minutos) | `COALESCE(SUM(trafico_prepago), 0)` |
| Tráfico pospago (minutos) | `COALESCE(SUM(trafico_pospago), 0)` |

`COALESCE` devuelve 0 cuando la tabla está vacía, porque en ese caso `SUM` da `NULL`.

---

## 8. Seguridad

- Las credenciales se leen del `.env` con `python-dotenv`; no están escritas en el código.
- El `.env` no se sube al repositorio. Se entrega `.env.example` como plantilla, sin contraseña.
- Las consultas usan parámetros `?` (`pyodbc`) para los valores que escribe el usuario. Los nombres de columna de los filtros salen de una lista fija del código, no del usuario.
- `debug=True` se usa solo para desarrollo local.

---

## 9. Evidencias

Las capturas están en [`docs/capturas/`](docs/capturas/):

| Archivo | Muestra |
|---|---|
| `01_json_api.png` | Respuesta JSON de la API en el navegador |
| `02_sql_registros.png` | Registros guardados en la tabla `RegistrosAPI` de SQL Server |
| `03_pagina_principal.png` | Página principal con el resumen y la tabla |
| `04_sincronizacion_0_nuevos.png` | Segunda sincronización: 0 registros nuevos (no se duplican) |
| `05_consulta_filtrada.png` | Consulta con filtros aplicados |
| `06_unique_2627.png` | SQL Server rechaza un registro repetido (error 2627) |

---

## 10. Alcance

Según la guía del proyecto, esta versión **no** incluye CRUD completo, usuarios, panel administrativo, gráficas avanzadas, despliegue en Internet ni pruebas unitarias extensas. Se limita a consultar la API, almacenar los registros y consultarlos desde la web.
