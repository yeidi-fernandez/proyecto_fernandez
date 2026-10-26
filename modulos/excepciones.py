# Excepciones propias del proyecto.
# Hay dos grupos:
#   - Las que DETIENEN el programa (configuración, entrada, escritura).
#   - Las que solo DESCARTAN una novedad y el programa sigue con la otra.


class ErrorProyecto(Exception):
    """Excepción base. Todas las demás heredan de esta."""
    detiene_ejecucion = True


# ---------- Errores que detienen la ejecución ----------

class ErrorConfiguracion(ErrorProyecto):
    """El Excel de configuración no existe, le falta una hoja o una clave."""


class ErrorArchivoEntrada(ErrorProyecto):
    """No hay JSON en entrada/, o el archivo está dañado."""


class ErrorEscritura(ErrorProyecto):
    """No se pudo guardar el Excel de salida."""


# ---------- Errores que descartan una novedad ----------

class ErrorRegistro(ErrorProyecto):
    """Base para los rechazos. Guarda qué campo falló, por qué y qué valor llegó."""
    detiene_ejecucion = False
    clasificacion = ""

    def __init__(self, campo, motivo, valor=""):
        self.campo = campo
        self.motivo = motivo
        self.valor = valor
        super().__init__(f"{campo}: {motivo} (valor recibido: '{valor}')")


class RegistroInvalido(ErrorRegistro):
    """La novedad no pasa una validación de formato o le falta un campo."""
    clasificacion = "VALIDACION"


class ErrorReglaNegocio(ErrorRegistro):
    """La novedad está bien escrita, pero incumple una regla de negocio."""
    clasificacion = "REGLA_NEGOCIO"