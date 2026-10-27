# Busca el JSON más reciente en entrada/ y lee sus novedades.
# El archivo solo se abre en modo lectura: nunca se modifica ni se borra.

import json
import os
from datetime import datetime

from modulos.excepciones import ErrorArchivoEntrada


def buscar_json_mas_reciente(carpeta, patron_nombre):
    """Entre los archivos novedades_AAAAMMDD.json devuelve la ruta del de
    fecha más reciente. La fecha se saca del nombre, no del código."""
    if not os.path.isdir(carpeta):
        raise ErrorArchivoEntrada(f"No existe la carpeta de entrada: {carpeta}")

    candidatos = {}  # {fecha: nombre_archivo}
    for nombre in os.listdir(carpeta):
        coincidencia = patron_nombre.fullmatch(nombre)
        if not coincidencia:
            continue
        try:
            fecha = datetime.strptime(coincidencia.group(1), "%Y%m%d")
        except ValueError:
            continue  # nombre con fecha imposible, como novedades_20261345.json
        candidatos[fecha] = nombre

    if not candidatos:
        raise ErrorArchivoEntrada("No hay archivo de novedades para procesar en la carpeta entrada")

    fecha_mayor = max(candidatos)
    return os.path.join(carpeta, candidatos[fecha_mayor])


def leer_novedades(ruta_archivo):
    """Lee el JSON y devuelve la lista de novedades."""
    nombre = os.path.basename(ruta_archivo)
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as archivo:
            contenido = json.load(archivo)
    except json.JSONDecodeError as error:
        raise ErrorArchivoEntrada(
            f"El archivo {nombre} no es un JSON válido (línea {error.lineno}, columna {error.colno})")
    except (OSError, UnicodeDecodeError) as error:
        raise ErrorArchivoEntrada(f"No se pudo leer el archivo {nombre}: {error}")

    if not isinstance(contenido, dict) or "novedades" not in contenido:
        raise ErrorArchivoEntrada(f"El archivo {nombre} no tiene la lista 'novedades'")

    novedades = contenido["novedades"]
    if not isinstance(novedades, list):
        raise ErrorArchivoEntrada(f"En el archivo {nombre}, 'novedades' no es una lista")
    if not novedades:
        raise ErrorArchivoEntrada(f"El archivo {nombre} no trae ninguna novedad")

    return novedades