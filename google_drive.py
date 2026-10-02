import os
import io

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


# =========================================================
# CONFIGURACIÓN
# =========================================================

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive.file"
]


# =========================================================
# CONEXIÓN CON GOOGLE DRIVE
# =========================================================

def conectar_google_drive():

    credenciales = None

    # -----------------------------------------
    # Cargar token existente
    # -----------------------------------------

    if os.path.exists(TOKEN_FILE):

        credenciales = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    # -----------------------------------------
    # Si no hay credenciales o están vencidas
    # -----------------------------------------

    if not credenciales or not credenciales.valid:

        if (
            credenciales
            and credenciales.expired
            and credenciales.refresh_token
        ):

            credenciales.refresh(Request())

        else:

            flujo = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )

            credenciales = flujo.run_local_server(
                port=0
            )

        # Guardar autorización
        with open(TOKEN_FILE, "w") as token:

            token.write(
                credenciales.to_json()
            )

    # -----------------------------------------
    # Crear servicio
    # -----------------------------------------

    servicio = build(
        "drive",
        "v3",
        credentials=credenciales
    )

    return servicio


# =========================================================
# OBTENER / CREAR CARPETA
# =========================================================

def obtener_o_crear_carpeta(
    servicio,
    nombre,
    carpeta_padre_id=None
):

    # -----------------------------------------
    # Construir consulta
    # -----------------------------------------

    consulta = (
        f"name = '{nombre}' "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )

    # Si tiene carpeta padre
    if carpeta_padre_id:

        consulta += (
            f" and '{carpeta_padre_id}' in parents"
        )

    # -----------------------------------------
    # Buscar carpeta
    # -----------------------------------------

    resultado = servicio.files().list(
        q=consulta,
        spaces="drive",
        fields="files(id, name)"
    ).execute()

    carpetas = resultado.get(
        "files",
        []
    )

    # -----------------------------------------
    # Si ya existe
    # -----------------------------------------

    if carpetas:

        return carpetas[0]["id"]

    # -----------------------------------------
    # Crear carpeta
    # -----------------------------------------

    metadata = {

        "name": nombre,

        "mimeType":
            "application/vnd.google-apps.folder"
    }

    if carpeta_padre_id:

        metadata["parents"] = [
            carpeta_padre_id
        ]

    carpeta = servicio.files().create(

        body=metadata,

        fields="id"
    ).execute()

    return carpeta["id"]


# =========================================================
# CARPETA PRINCIPAL DEL SISTEMA
# =========================================================

def obtener_carpeta_dicyt(servicio):

    return obtener_o_crear_carpeta(

        servicio,

        "Sistema DICyT"
    )


# =========================================================
# CARPETA DOCUMENTOS
# =========================================================

def obtener_carpeta_documentos(servicio):

    carpeta_dicyt = obtener_carpeta_dicyt(
        servicio
    )

    return obtener_o_crear_carpeta(

        servicio,

        "DOCUMENTOS",

        carpeta_dicyt
    )


# =========================================================
# CARPETA SOLICITUDES
# =========================================================

def obtener_carpeta_solicitudes(servicio):

    carpeta_dicyt = obtener_carpeta_dicyt(
        servicio
    )

    return obtener_o_crear_carpeta(

        servicio,

        "SOLICITUDES",

        carpeta_dicyt
    )


# =========================================================
# CARPETA INVESTIGACIÓN
# =========================================================

def obtener_carpeta_investigacion(servicio):

    carpeta_dicyt = obtener_carpeta_dicyt(
        servicio
    )

    return obtener_o_crear_carpeta(

        servicio,

        "INVESTIGACIÓN",

        carpeta_dicyt
    )

# =========================================================
# CARPETA ARTÍCULOS
# =========================================================

def obtener_carpeta_articulos(servicio):

    carpeta_investigacion = obtener_carpeta_investigacion(
        servicio
    )

    return obtener_o_crear_carpeta(

        servicio,

        "ARTICULOS",

        carpeta_investigacion
    )

# =========================================================
# CARPETA REVISTAS
# =========================================================

def obtener_carpeta_revistas(servicio):

    carpeta_investigacion = obtener_carpeta_investigacion(servicio)

    return obtener_o_crear_carpeta(

        servicio,
        "REVISTAS",
        carpeta_investigacion
    )

# =========================================================
# CARPETA LIBROS
# =========================================================

def obtener_carpeta_libros(servicio):

    carpeta_investigacion = obtener_carpeta_investigacion(
        servicio
    )

    return obtener_o_crear_carpeta(

        servicio,

        "LIBROS",

        carpeta_investigacion
    )


# =========================================================
# CARPETA CAPÍTULOS DE LIBRO
# =========================================================

def obtener_carpeta_capitulos_libro(servicio):

    carpeta_investigacion = obtener_carpeta_investigacion(
        servicio
    )

    return obtener_o_crear_carpeta(

        servicio,

        "CAPITULOS_DE_LIBRO",

        carpeta_investigacion
    )

# =========================================================
# CARPETA TEXTOS EN ASIGNATURA
# =========================================================

def obtener_carpeta_textos_asignatura(servicio):

    carpeta_investigacion = obtener_carpeta_investigacion(
        servicio
    )

    return obtener_o_crear_carpeta(

        servicio,

        "TEXTOS_ASIGNATURA",

        carpeta_investigacion
    )

# =========================================================
# CARPETA SOCIEDADES CIENTÍFICAS
# =========================================================

def obtener_carpeta_sociedades_cientificas(servicio):
    carpeta_investigacion = obtener_carpeta_investigacion(servicio)

    return obtener_o_crear_carpeta(
        servicio,
        "SOCIEDADES_CIENTIFICAS",
        carpeta_investigacion
    )

# =========================================================
# CARPETA INVESTIGADORES
# =========================================================

def obtener_carpeta_investigadores(servicio):

    carpeta_investigacion = obtener_carpeta_investigacion(
        servicio
    )

    return obtener_o_crear_carpeta(

        servicio,

        "INVESTIGADORES",

        carpeta_investigacion
    )

# =========================================================
# CARPETA POR CATEGORÍA
# =========================================================

def obtener_carpeta_categoria(
    servicio,
    categoria
):

    carpeta_documentos = obtener_carpeta_documentos(
        servicio
    )

    return obtener_o_crear_carpeta(

        servicio,

        categoria,

        carpeta_documentos
    )


# =========================================================
# SUBIR ARCHIVO
# =========================================================

def subir_archivo(
    servicio,
    ruta_archivo,
    nombre_archivo,
    carpeta_id
):

    metadata = {

        "name": nombre_archivo,

        "parents": [
            carpeta_id
        ]
    }

    media = MediaFileUpload(

        ruta_archivo,

        resumable=True
    )

    archivo = servicio.files().create(

        body=metadata,

        media_body=media,

        fields="id, name, webViewLink"
    ).execute()

    return archivo


# =========================================================
# ELIMINAR ARCHIVO
# =========================================================

def eliminar_archivo(
    servicio,
    archivo_id
):

    if not archivo_id:
        return

    servicio.files().delete(
        fileId=archivo_id
    ).execute()

# =========================================================
# DESCARGAR ARCHIVO
# =========================================================

def descargar_archivo(
    servicio,
    archivo_id
):

    informacion = servicio.files().get(
        fileId=archivo_id,
        fields="name,mimeType"
    ).execute()

    nombre = informacion.get(
        "name",
        "documento"
    )

    mime_type = informacion.get(
        "mimeType",
        "application/octet-stream"
    )

    solicitud = servicio.files().get_media(
        fileId=archivo_id
    )

    contenido = io.BytesIO()

    descargador = MediaIoBaseDownload(
        contenido,
        solicitud
    )

    terminado = False

    while not terminado:

        estado, terminado = descargador.next_chunk()

    contenido.seek(0)

    return contenido, nombre, mime_type