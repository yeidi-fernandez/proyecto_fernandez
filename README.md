# Preparador de carga masiva de novedades de personal

Proyecto final del Módulo de Python — Semillero de Automatización RPA e Inteligencia Artificial.
Autora: Yeidi Fernández.

## 1. Descripción del proyecto

Es una aplicación de consola en Python. Lee un archivo JSON con novedades de personal (ingresos, cambios de cargo, traslados y retiros). Valida cada novedad con la configuración que está en un Excel. Aplica las reglas de negocio: normaliza el nombre, genera el correo corporativo, asigna el perfil del sistema y revisa que el área del cargo coincida con la del centro de costo. Al final genera un Excel listo para que lo use un robot, con las novedades válidas, las rechazadas con su motivo, las colisiones de correo y un resumen. Todo lo que pasa queda en un log en Excel.

## 2. Requisitos previos

- Python 3.10 o superior.
- Librería `openpyxl`. El resto es librería estándar.

```
pip install openpyxl
```

## 3. Instrucciones de ejecución

1. Descomprimir la carpeta `proyecto_fernandez` en cualquier ubicación.
2. Revisar que exista `config/parametros.xlsx`.
3. Poner el archivo de novedades en la carpeta `entrada/` con el nombre `novedades_AAAAMMDD.json`. Si hay varios, el programa toma el de fecha más reciente según el nombre.
4. Abrir una terminal dentro de `proyecto_fernandez` y ejecutar:

```
python main.py
```

5. El resultado queda en `salida/` y el log en `logs/`. Si esas carpetas no existen, el programa las crea.

Importante: antes de volver a ejecutar, cerrar el Excel de salida si está abierto.

## 4. Estructura del proyecto

```
proyecto_fernandez/
├── main.py                 # único punto de entrada
├── config/
│   └── parametros.xlsx     # toda la parametrización
├── entrada/
│   └── novedades_<fecha>.json
├── salida/                 # se crea si no existe
├── logs/                   # se crea si no existe
├── modulos/
│   ├── __init__.py
│   ├── configuracion.py
│   ├── lectura.py
│   ├── validacion.py
│   ├── procesamiento.py
│   ├── reporte.py
│   ├── registro.py
│   └── excepciones.py
└── README.md
```

| Módulo | Responsabilidad |
|---|---|
| `main.py` | Solo organiza: llama a los módulos en orden, atrapa los errores que detienen el programa y siempre escribe el log en el `finally`. |
| `configuracion.py` | Arma las rutas desde la carpeta de `main.py`, crea `salida/` y `logs/`, lee `parametros.xlsx`, revisa que estén las 5 hojas y las claves, y pasa cada hoja a diccionarios. |
| `lectura.py` | Busca el JSON más reciente por la fecha del nombre y lo lee solo en modo lectura. |
| `validacion.py` | Compila las expresiones regulares una sola vez y tiene una función por cada validación. |
| `procesamiento.py` | Reglas de negocio: nombre, correo con colisiones, perfil, área cruzada, fecha previa. Recorre el lote y calcula el resumen. |
| `reporte.py` | Escribe el Excel de salida con sus 4 hojas y formato. |
| `registro.py` | Registro de eventos en memoria. Al final lo guarda en Excel con las hojas Detalle y Resumen. No usa `logging`. |
| `excepciones.py` | Excepciones propias del proyecto. |

## 5. Descripción del archivo de configuración

`config/parametros.xlsx` tiene 5 hojas:

| Hoja | Qué contiene | Efecto de cambiarla |
|---|---|---|
| Parametros | Claves y valores de la ejecución | Ver tabla de abajo |
| Cargos | Código, nombre, nivel y área de cada cargo | Un cargo nuevo se reconoce sin tocar el código |
| Centros_Costo | Código, nombre y área de cada centro de costo | Un centro nuevo deja de ser rechazado por "no existe" |
| Matriz_Roles | Cargo + área → perfil y si requiere aprobación | Define qué combinaciones son válidas y qué perfil reciben |
| Campos_Obligatorios | Campos exigidos por cada tipo de novedad, separados por `;` | Cambia qué campos se exigen a cada tipo. También define qué tipos existen |

| Clave | Valor | Efecto |
|---|---|---|
| dominio_correo | empresa.com | Dominio de los correos generados |
| archivo_salida | carga_novedades | Prefijo del Excel de salida |
| prefijo_log | log_ejecucion | Prefijo del Excel de log |
| formato_fecha_salida | AAAA-MM-DD | Formato de las fechas en la salida |
| dias_maximo_futuro | 90 | Días máximos hacia adelante de la fecha efectiva |
| longitud_telefono | 10 | Cantidad exacta de dígitos del teléfono |
| nivel_log_minimo | INFO | Nivel mínimo que se guarda en el log (INFO, WARNING, ERROR, CRITICAL) |

Agregué el cargo `SOP-01` (Técnico de Soporte, TECNOLOGIA) sin fila en Matriz_Roles. Lo hice para poder probar el rechazo por combinación que no existe en la matriz.

## 6. Reglas de validación implementadas

Las validaciones van en este orden. La primera que falla rechaza la novedad.

| Validación | Expresión regular | Mensaje de rechazo |
|---|---|---|
| Tipo de novedad | (se compara con la hoja Campos_Obligatorios) | Tipo de novedad desconocido |
| Campos obligatorios | (se leen de Campos_Obligatorios) | Campo obligatorio vacío o ausente para este tipo de novedad |
| Limpieza del documento | `[.\-\s]` | — |
| Documento CC | `\d{6,10}` | El documento tipo CC solo admite dígitos / El documento tiene menos de 6 caracteres |
| Documento CE | `\d{6,10}\|[A-Z]\d{6,9}` | El documento no cumple el formato del tipo CE |
| Documento PA | `(?=.*[A-Z])[A-Z0-9]{6,12}` | El documento no cumple el formato del tipo PA |
| Fecha efectiva | `(\d{1,2})/(\d{1,2})/(\d{4})` y `(\d{4})-(\d{1,2})-(\d{1,2})` | Formato de fecha no válido / Fecha imposible / Fecha vencida / Fecha fuera de rango |
| Centro de costo | `CC-\d{4}` | Formato de centro de costo no válido / El centro de costo no existe en el catálogo |
| Cargo | (se busca en la hoja Cargos) | El cargo no existe en el catálogo |
| Teléfono | `\d` (se extraen los dígitos) | El teléfono debe tener 10 dígitos y tiene N |
| Fechas en observaciones (extracción) | `\b\d{1,2}/\d{1,2}/\d{4}\b\|\b\d{4}-\d{1,2}-\d{1,2}\b` | Nunca rechaza |
| Correo corporativo | `[a-z]+\.[a-z]+\d*@empresa\.com` (el dominio sale de la configuración) | No se pudo generar un correo válido con el nombre |
| Archivo de entrada | `novedades_(\d{8})\.json` | No hay archivo de novedades para procesar |

Reglas de negocio (se rechazan como REGLA_NEGOCIO):

- El área del cargo debe ser igual al área del centro de costo.
- La combinación cargo + área debe existir en Matriz_Roles.

## 7. Diagrama de flujo del proceso principal

El diagrama completo está en el documento PDD. Este es el flujo en pseudocódigo:

```
INICIO
  crear registro de eventos en memoria
  INTENTAR
      crear carpetas salida/ y logs/ si no existen
      cargar parametros.xlsx            -> si falla: ErrorConfiguracion (se detiene)
      buscar el JSON más reciente       -> si falla: ErrorArchivoEntrada (se detiene)
      PARA CADA novedad
          INTENTAR
              validar tipo, campos obligatorios, documento, fecha,
              centro de costo, cargo y teléfono   -> RegistroInvalido
              revisar área cruzada y Matriz_Roles  -> ErrorReglaNegocio
              normalizar nombre y extraer fecha previa
              SI es ALTA: generar correo y resolver colisiones
              agregar a VÁLIDAS
          SI FALLA: agregar a RECHAZADOS y seguir con la siguiente
      calcular resumen
      escribir Excel de salida          -> si falla: ErrorEscritura (se detiene)
  SI FALLA con error que detiene: registrar CRITICAL y mostrar mensaje sin traceback
  AL FINAL SIEMPRE: escribir el log en Excel
FIN
```

## 8. Manejo de excepciones

| Excepción | Hereda de | Cuándo se lanza | Comportamiento |
|---|---|---|---|
| ErrorProyecto | Exception | Base de todas | — |
| ErrorConfiguracion | ErrorProyecto | No existe el Excel, falta una hoja, una columna o una clave | Detiene la ejecución |
| ErrorArchivoEntrada | ErrorProyecto | No hay JSON, el JSON está dañado o no trae novedades | Detiene la ejecución |
| ErrorEscritura | ErrorProyecto | No se puede guardar el Excel de salida (por ejemplo, está abierto) | Detiene la ejecución, pero el log sí se escribe |
| ErrorRegistro | ErrorProyecto | Clase intermedia. Guarda campo, motivo y valor recibido | — |
| RegistroInvalido | ErrorRegistro | Falla una validación de formato o falta un campo | Descarta la novedad y sigue. Clasificación VALIDACION |
| ErrorReglaNegocio | ErrorRegistro | La novedad está bien escrita pero incumple una regla de negocio | Descarta la novedad y sigue. Clasificación REGLA_NEGOCIO |

El `try` que descarta novedades está dentro del ciclo `for`. Por eso una novedad mala no detiene el lote. Los errores que detienen se atrapan en `main.py`. Cualquier otro error inesperado también se atrapa ahí, para que nunca se vea un traceback. El log se escribe en el `finally`.

## 9. Evidencias de ejecución

Las capturas están en la carpeta `evidencias/`.

**Ejecución exitosa**

```
Proceso terminado. Archivo procesado: novedades_20261026.json
Novedades: 22 recibidas, 9 válidas, 13 rechazadas
Archivo de salida: ...\salida\carga_novedades_20261026.xlsx
Log de la ejecución: ...\logs\log_ejecucion_20261026_213528.xlsx
```

- `evidencias/log_exitoso.png`: hoja Detalle del log exitoso.
- `evidencias/salida_carga_sistema.png`: Excel de salida.

**Ejecución con error** (sin `parametros.xlsx`)

```
ERROR: No se encontró el archivo ...\config\parametros.xlsx
Log de la ejecución: ...\logs\log_ejecucion_20261026_213902.xlsx
```

- `evidencias/consola_error.png`: consola de la ejecución con error.
- `evidencias/log_error.png`: log con la fila CRITICAL en rojo.

## 10. Dificultades encontradas

- Al principio no sabía cómo hacer que una novedad con error no detuviera todo el programa. Lo resolví separando los errores en dos grupos: los graves y los de una sola novedad.
- Necesitaba que el log se guardara aunque el programa fallara, incluso si no se podía leer la configuración. Lo resolví guardándolo en un bloque que siempre se ejecuta al final (`finally`).
- Con las personas que se llaman igual, los correos se repetían. Lo resolví agregando un número al final del nombre: juan.perez2, juan.perez3.
- Algunas expresiones regulares aceptaban datos de más. Por ejemplo, un documento muy largo pasaba como válido. Lo resolví exigiendo que todo el texto cumpla el patrón (`fullmatch`).
- Una fecha como 31/13/2026 tiene la forma correcta, pero el mes 13 no existe. Tuve que revisar primero la forma y después si la fecha es real.
- Sacar fechas de un texto libre fue difícil, porque pueden venir en dos formatos y varias en el mismo texto.
- Con los datos del enunciado no podía probar el rechazo por la matriz de roles. Agregué un cargo de prueba (`SOP-01`) para lograrlo.
- En VS Code creé carpetas como si fueran archivos, y una carpeta me quedó dentro de otra. Aprendí a fijarme en la flechita de las carpetas.
- Me salió un error porque no había guardado un archivo. Aprendí a revisar el punto que aparece en la pestaña cuando falta guardar.

## 11. Qué mejoraría

- Haría pruebas automáticas para no tener que probar todo a mano.
- Si el Excel de salida está abierto, guardaría una copia con otro nombre en vez de detener el programa.
- Pasaría más reglas al Excel de configuración, como los tipos de documento.
- Empezaría a subir los cambios a GitHub desde el primer día.