# Reglas de negocio. Solo se aplican a las novedades que pasaron la validación.
# También recorre el lote completo y separa válidas de rechazadas.

from datetime import date

from modulos.excepciones import ErrorRegistro, ErrorReglaNegocio
from modulos.validacion import texto, texto_a_fecha, validar_novedad

# Equivalencias para quitar tildes al generar el correo
SIN_TILDES = str.maketrans("áéíóúüñ", "aeiouun")


def normalizar_nombre(valor):
    """Quita espacios sobrantes y deja cada palabra con mayúscula inicial."""
    return " ".join(palabra.capitalize() for palabra in valor.split())


def parte_para_correo(valor):
    """Primera palabra, en minúscula, sin tildes y solo con letras."""
    palabras = valor.lower().split()
    if not palabras:
        return ""
    palabra = palabras[0].translate(SIN_TILDES)
    return "".join(letra for letra in palabra if "a" <= letra <= "z")


def generar_correo(datos, dominio, patrones, correos_asignados, colisiones):
    """Arma nombre.apellido@dominio. Si ya existe, agrega 2, 3, ... antes del @."""
    base = f"{parte_para_correo(datos['nombres'])}.{parte_para_correo(datos['apellidos'])}"
    correo = f"{base}@{dominio}"

    if correo in correos_asignados:
        numero = 2
        while f"{base}{numero}@{dominio}" in correos_asignados:
            numero += 1
        correo_final = f"{base}{numero}@{dominio}"
        colisiones.append({
            "correo_base": correo,
            "consecutivo_con_correo_base": correos_asignados[correo],
            "consecutivo_nuevo": datos["consecutivo"],
            "correo_final": correo_final,
        })
        correo = correo_final

    if not patrones["correo"].fullmatch(correo):
        raise ErrorReglaNegocio("correo_corporativo", "No se pudo generar un correo válido con el nombre", correo)

    correos_asignados[correo] = datos["consecutivo"]
    return correo


def asignar_perfil(datos, config):
    """Revisa que el área del cargo y del centro de costo coincidan
    y busca el perfil en la matriz. Devuelve (area, perfil, requiere_aprobacion)."""
    cargo, centro = datos["cargo"], datos["centro_costo"]
    area_centro = config["centros"][centro]["area"] if centro else ""

    if not (cargo and centro):
        return area_centro, "", ""

    area_cargo = config["cargos"][cargo]["area"]
    if area_cargo != area_centro:
        raise ErrorReglaNegocio(
            "cargo",
            f"El área del cargo ({area_cargo}) no coincide con el área del centro de costo ({area_centro})",
            f"{cargo} / {centro}")

    rol = config["matriz"].get((cargo, area_centro))
    if rol is None:
        raise ErrorReglaNegocio("cargo", f"La combinación {cargo} + {area_centro} no existe en Matriz_Roles",
                                f"{cargo} / {centro}")
    return area_centro, rol["perfil"], rol["requiere_aprobacion"]


def extraer_fecha_previa(observaciones, patrones):
    """Busca todas las fechas citadas en el texto y devuelve la más antigua."""
    fechas = []
    for encontrada in patrones["fechas_en_texto"].findall(observaciones):
        fecha, _ = texto_a_fecha(encontrada, patrones)
        if fecha:
            fechas.append(fecha)
    return min(fechas) if fechas else None


def aplicar_reglas(datos, config, patrones, correos_asignados, colisiones):
    """Aplica las reglas de negocio y devuelve la fila para Carga_Sistema."""
    parametros = config["parametros"]
    formato = parametros["formato_fecha_python"]

    area, perfil, requiere = asignar_perfil(datos, config)
    cargo_info = config["cargos"].get(datos["cargo"], {})
    fecha_previa = extraer_fecha_previa(datos["observaciones"], patrones)

    # El correo va de último: si algo falla antes, no se gasta un correo
    correo = ""
    if datos["tipo"] == "ALTA":
        correo = generar_correo(datos, parametros["dominio_correo"], patrones, correos_asignados, colisiones)

    return {
        "consecutivo": datos["consecutivo"],
        "tipo_novedad": datos["tipo"],
        "tipo_documento": datos["tipo_documento"],
        "numero_documento": datos["numero_documento"],
        "nombre_completo": normalizar_nombre(f"{datos['nombres']} {datos['apellidos']}"),
        "correo_corporativo": correo,
        "codigo_cargo": datos["cargo"],
        "nombre_cargo": cargo_info.get("nombre", ""),
        "nivel": cargo_info.get("nivel", ""),
        "centro_costo": datos["centro_costo"],
        "area": area,
        "perfil_sistema": perfil,
        "requiere_aprobacion": requiere,
        "fecha_efectiva": datos["fecha_efectiva"].strftime(formato),
        "telefono": datos["telefono"],
        "fecha_vinculacion_previa": fecha_previa.strftime(formato) if fecha_previa else "",
    }


def armar_rechazo(novedad, error):
    """Fila para la hoja Rechazados, con los datos tal como llegaron."""
    if not isinstance(novedad, dict):
        novedad = {}
    nombre = f"{texto(novedad.get('nombres'))} {texto(novedad.get('apellidos'))}".strip()
    return {
        "consecutivo": novedad.get("consecutivo", ""),
        "tipo": texto(novedad.get("tipo")),
        "numero_documento": texto(novedad.get("numero_documento")),
        "nombre": nombre,
        "clasificacion": error.clasificacion,
        "campo": error.campo,
        "motivo": error.motivo,
        "valor_recibido": texto(error.valor),
    }


def procesar_lote(novedades, config, patrones, registro, hoy=None):
    """Recorre todas las novedades. Una novedad con error se descarta
    y se sigue con la siguiente; nunca se detiene el lote completo."""
    hoy = hoy or date.today()
    validas, rechazados, colisiones = [], [], []
    correos_asignados = {}  # {correo: consecutivo que lo tiene}

    for novedad in novedades:
        consecutivo = novedad.get("consecutivo", "") if isinstance(novedad, dict) else ""
        try:
            datos = validar_novedad(novedad, config, patrones, hoy)
            fila = aplicar_reglas(datos, config, patrones, correos_asignados, colisiones)
            validas.append(fila)
            registro.registrar("INFO", "procesamiento", "procesar_lote", "Novedad válida", consecutivo)
        except ErrorRegistro as error:
            rechazados.append(armar_rechazo(novedad, error))
            registro.registrar_error("WARNING", error,
                                     f"Rechazada por {error.clasificacion}: {error.motivo}", consecutivo)

    for colision in colisiones:
        registro.registrar("INFO", "procesamiento", "generar_correo",
                           f"Colisión resuelta: {colision['correo_base']} -> {colision['correo_final']}",
                           colision["consecutivo_nuevo"])
    return validas, rechazados, colisiones


def calcular_resumen(config, validas, rechazados):
    """Cantidades por tipo de novedad, totales y motivo de rechazo más frecuente."""
    por_tipo = {tipo: {"recibidas": 0, "validas": 0, "rechazadas": 0} for tipo in config["campos"]}

    for fila in validas:
        por_tipo[fila["tipo_novedad"]]["validas"] += 1
    for fila in rechazados:
        tipo = fila["tipo"].upper().replace(" ", "") or "SIN_TIPO"
        por_tipo.setdefault(tipo, {"recibidas": 0, "validas": 0, "rechazadas": 0})
        por_tipo[tipo]["rechazadas"] += 1

    totales = {"recibidas": 0, "validas": 0, "rechazadas": 0}
    for cantidades in por_tipo.values():
        cantidades["recibidas"] = cantidades["validas"] + cantidades["rechazadas"]
        cantidades["porcentaje"] = (round(cantidades["validas"] / cantidades["recibidas"] * 100, 1)
                                    if cantidades["recibidas"] else 0.0)
        for clave in totales:
            totales[clave] += cantidades[clave]
    totales["porcentaje"] = (round(totales["validas"] / totales["recibidas"] * 100, 1)
                             if totales["recibidas"] else 0.0)

    conteo_motivos = {}
    for fila in rechazados:
        conteo_motivos[fila["motivo"]] = conteo_motivos.get(fila["motivo"], 0) + 1
    if conteo_motivos:
        motivo = max(conteo_motivos, key=conteo_motivos.get)
        motivo_frecuente = (motivo, conteo_motivos[motivo])
    else:
        motivo_frecuente = ("Sin rechazos", 0)

    return {"por_tipo": por_tipo, "totales": totales, "motivo_frecuente": motivo_frecuente}