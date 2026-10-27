# Expresiones regulares y reglas de validación de cada novedad.
# Las validaciones van en orden: la primera que falla rechaza la novedad.

import re
from datetime import date, timedelta

from modulos.excepciones import RegistroInvalido


def compilar_patrones(dominio):
    """Compila todas las expresiones regulares una sola vez.
    El correo depende del dominio, por eso se recibe desde la configuración."""
    return {
        # Nombre del archivo de entrada: novedades_AAAAMMDD.json
        "archivo_entrada": re.compile(r"novedades_(\d{8})\.json"),
        # Documento según su tipo
        "documento_CC": re.compile(r"\d{6,10}"),
        "documento_CE": re.compile(r"\d{6,10}|[A-Z]\d{6,9}"),
        "documento_PA": re.compile(r"(?=.*[A-Z])[A-Z0-9]{6,12}"),
        "documento_general": re.compile(r"[A-Z0-9]{6,12}"),
        # Caracteres que se quitan del documento: puntos, guiones y espacios
        "separadores_documento": re.compile(r"[.\-\s]"),
        # Centro de costo con formato CC-0000
        "centro_costo": re.compile(r"CC-\d{4}"),
        # Cada dígito del teléfono (se descartan paréntesis, guiones y espacios)
        "digito": re.compile(r"\d"),
        # Fecha completa en sus dos formatos
        "fecha_dia_mes_anio": re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"),
        "fecha_anio_mes_dia": re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
        # Fechas dentro de un texto libre (extracción, no validación)
        "fechas_en_texto": re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d{4}-\d{1,2}-\d{1,2}\b"),
        # Correo corporativo nombre.apellido@dominio (con número opcional)
        "correo": re.compile(r"[a-z]+\.[a-z]+\d*@" + re.escape(dominio)),
    }


def texto(valor):
    """Convierte cualquier valor del JSON a texto sin espacios a los lados."""
    if valor is None:
        return ""
    return str(valor).strip()


def texto_a_fecha(valor, patrones):
    """Convierte DD/MM/AAAA o AAAA-MM-DD en una fecha.
    Devuelve (fecha, None) si sale bien, o (None, motivo) si falla."""
    coincidencia = patrones["fecha_dia_mes_anio"].fullmatch(valor)
    if coincidencia:
        dia, mes, anio = coincidencia.groups()
    else:
        coincidencia = patrones["fecha_anio_mes_dia"].fullmatch(valor)
        if not coincidencia:
            return None, "Formato de fecha no válido (se acepta DD/MM/AAAA o AAAA-MM-DD)"
        anio, mes, dia = coincidencia.groups()
    try:
        return date(int(anio), int(mes), int(dia)), None
    except ValueError:
        return None, "Fecha imposible"


# ---------------- Validaciones, una por función ----------------

def validar_tipo(novedad, campos_por_tipo):
    tipo = texto(novedad.get("tipo")).upper().replace(" ", "")
    if tipo not in campos_por_tipo:
        raise RegistroInvalido("tipo", "Tipo de novedad desconocido", novedad.get("tipo", ""))
    return tipo


def validar_obligatorios(novedad, campos_exigidos):
    for campo in campos_exigidos:
        if texto(novedad.get(campo)) == "":
            raise RegistroInvalido(campo, "Campo obligatorio vacío o ausente para este tipo de novedad",
                                   novedad.get(campo, ""))


def validar_documento(novedad, patrones):
    original = texto(novedad.get("numero_documento"))
    numero = patrones["separadores_documento"].sub("", original).upper()
    tipo_doc = texto(novedad.get("tipo_documento")).upper()

    if tipo_doc == "":
        # Tipos como RETIRO pueden venir sin tipo de documento: solo se revisa lo básico
        if not patrones["documento_general"].fullmatch(numero):
            raise RegistroInvalido("numero_documento", "Documento con formato no válido", original)
        return tipo_doc, numero

    patron = patrones.get(f"documento_{tipo_doc}")
    if patron is None:
        raise RegistroInvalido("tipo_documento", "Tipo de documento no reconocido", novedad.get("tipo_documento"))

    if not patron.fullmatch(numero):
        if tipo_doc == "CC" and not numero.isdigit():
            motivo = "El documento tipo CC solo admite dígitos"
        elif len(numero) < 6:
            motivo = "El documento tiene menos de 6 caracteres"
        else:
            motivo = f"El documento no cumple el formato del tipo {tipo_doc}"
        raise RegistroInvalido("numero_documento", motivo, original)
    return tipo_doc, numero


def validar_fecha(novedad, patrones, parametros, hoy):
    original = texto(novedad.get("fecha_efectiva"))
    fecha, motivo = texto_a_fecha(original, patrones)
    if fecha is None:
        raise RegistroInvalido("fecha_efectiva", motivo, original)
    if fecha < hoy:
        raise RegistroInvalido("fecha_efectiva", "Fecha vencida: es anterior al día de ejecución", original)
    limite = hoy + timedelta(days=parametros["dias_maximo_futuro"])
    if fecha > limite:
        raise RegistroInvalido("fecha_efectiva",
                               f"Fecha fuera de rango: supera {parametros['dias_maximo_futuro']} días", original)
    return fecha


def validar_centro_costo(codigo, patrones, centros):
    if not patrones["centro_costo"].fullmatch(codigo):
        raise RegistroInvalido("centro_costo", "Formato de centro de costo no válido (debe ser CC-0000)", codigo)
    if codigo not in centros:
        raise RegistroInvalido("centro_costo", "El centro de costo no existe en el catálogo", codigo)


def validar_cargo(codigo, cargos):
    if codigo not in cargos:
        raise RegistroInvalido("cargo", "El cargo no existe en el catálogo", codigo)


def validar_telefono(original, patrones, longitud):
    digitos = "".join(patrones["digito"].findall(original))
    if len(digitos) != longitud:
        raise RegistroInvalido("telefono", f"El teléfono debe tener {longitud} dígitos y tiene {len(digitos)}",
                               original)
    return digitos


# ---------------- Validación completa de una novedad ----------------

def validar_novedad(novedad, config, patrones, hoy=None):
    """Aplica todas las validaciones en orden y devuelve los datos limpios."""
    hoy = hoy or date.today()
    if not isinstance(novedad, dict):
        raise RegistroInvalido("novedad", "La novedad no tiene la estructura esperada", str(novedad))

    tipo = validar_tipo(novedad, config["campos"])
    validar_obligatorios(novedad, config["campos"][tipo])
    tipo_doc, numero = validar_documento(novedad, patrones)
    fecha = validar_fecha(novedad, patrones, config["parametros"], hoy)

    centro = texto(novedad.get("centro_costo")).upper()
    if centro:
        validar_centro_costo(centro, patrones, config["centros"])

    cargo = texto(novedad.get("cargo")).upper()
    if cargo:
        validar_cargo(cargo, config["cargos"])

    telefono = texto(novedad.get("telefono"))
    if telefono:
        telefono = validar_telefono(telefono, patrones, config["parametros"]["longitud_telefono"])

    return {
        "consecutivo": novedad.get("consecutivo", ""),
        "tipo": tipo,
        "tipo_documento": tipo_doc,
        "numero_documento": numero,
        "nombres": texto(novedad.get("nombres")),
        "apellidos": texto(novedad.get("apellidos")),
        "fecha_efectiva": fecha,
        "cargo": cargo,
        "centro_costo": centro,
        "telefono": telefono,
        "observaciones": texto(novedad.get("observaciones")),
    }