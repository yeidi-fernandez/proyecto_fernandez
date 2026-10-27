# Único punto de entrada del programa.
# Solo llama a los módulos en orden, controla el flujo general y cierra el log.

import os

from modulos import configuracion, lectura, procesamiento, reporte, validacion
from modulos.excepciones import ErrorProyecto
from modulos.registro import PREFIJO_RESPALDO, Registro

CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    rutas = configuracion.obtener_rutas(CARPETA_BASE)
    registro = Registro()
    prefijo_log, archivo_entrada, totales = PREFIJO_RESPALDO, "", {}
    try:
        registro.registrar("INFO", "main", "main", "Inicio de la ejecución")
        configuracion.crear_carpetas(rutas)
        config = configuracion.cargar_configuracion(rutas["parametros"])
        parametros = config["parametros"]
        registro.nivel_minimo = parametros["nivel_log_minimo"]
        prefijo_log = parametros["prefijo_log"]
        registro.registrar("INFO", "main", "main", "Configuración cargada")

        patrones = validacion.compilar_patrones(parametros["dominio_correo"])
        ruta_json = lectura.buscar_json_mas_reciente(rutas["entrada"], patrones["archivo_entrada"])
        archivo_entrada = os.path.basename(ruta_json)
        novedades = lectura.leer_novedades(ruta_json)
        registro.registrar("INFO", "main", "main", f"Se leyeron {len(novedades)} novedades de {archivo_entrada}")

        validas, rechazados, colisiones = procesamiento.procesar_lote(novedades, config, patrones, registro)
        resumen = procesamiento.calcular_resumen(config, validas, rechazados)
        totales = resumen["totales"]
        ruta_salida = reporte.escribir_salida(rutas["salida"], config, validas, rechazados,
                                              colisiones, resumen, archivo_entrada)
        registro.registrar("INFO", "main", "main", f"Archivo de salida generado: {os.path.basename(ruta_salida)}")

        print(f"Proceso terminado. Archivo procesado: {archivo_entrada}")
        print(f"Novedades: {totales['recibidas']} recibidas, {totales['validas']} válidas, "
              f"{totales['rechazadas']} rechazadas")
        print(f"Archivo de salida: {ruta_salida}")
    except ErrorProyecto as error:
        registro.registrar_error("CRITICAL", error, "La ejecución se detuvo")
        print(f"ERROR: {error}")
    except (Exception, KeyboardInterrupt) as error:
        registro.registrar_error("CRITICAL", error, "Error inesperado")
        print("Ocurrió un error inesperado. Revise el archivo de log para ver el detalle.")
    finally:
        try:
            ruta_log = registro.guardar(rutas["logs"], prefijo_log, archivo_entrada, totales)
            print(f"Log de la ejecución: {ruta_log}")
        except Exception as error:
            print(f"No se pudo escribir el log: {error}")


if __name__ == "__main__":
    main()
    
