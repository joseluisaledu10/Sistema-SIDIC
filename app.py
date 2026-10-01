from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, send_file, flash
from datetime import datetime
from werkzeug.utils import secure_filename
import sqlite3
import os
import uuid
import tempfile

from werkzeug.security import generate_password_hash, check_password_hash

from google_drive import (

    conectar_google_drive,

    obtener_carpeta_categoria,

    obtener_carpeta_solicitudes,

    obtener_carpeta_articulos,

    obtener_carpeta_libros,

    obtener_carpeta_capitulos_libro,

    obtener_carpeta_revistas,

    obtener_carpeta_textos_asignatura,

    obtener_carpeta_sociedades_cientificas,

    subir_archivo,

    eliminar_archivo,

    descargar_archivo,

)


# =========================
# VALIDAR CONTRASEÑA
# =========================

def contraseña_segura(contraseña):

    if len(contraseña) < 8:
        return False

    if not any(c.isupper() for c in contraseña):
        return False

    if not any(c.islower() for c in contraseña):
        return False

    if not any(c.isdigit() for c in contraseña):
        return False

    if not any(not c.isalnum() for c in contraseña):
        return False

    return True

app = Flask(__name__)

# =========================
# TIPOS DE ACTIVIDAD
# =========================

TIPOS_ACTIVIDAD = [
    "Reunión",
    "Coordinación",
    "Capacitación",
    "Taller",
    "Seminario",
    "Evento",
    "Seguimiento",
    "Organización",
    "Difusión",
    "Investigación",
    "Trámite",
    "Otro"
]

# =========================
# CONFIGURACIÓN DE ARCHIVOS
# =========================

UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "static",
    "uploads"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

EXTENSIONES_PERMITIDAS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "jpg",
    "jpeg",
    "png"
}

# =========================
# EXTENSIONES PARA LOGOS
# =========================

EXTENSIONES_LOGO_PERMITIDAS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

DATABASE = "dicyt.db"

def archivo_permitido(nombre_archivo):

    return (
        "." in nombre_archivo
        and nombre_archivo.rsplit(".", 1)[1].lower()
        in EXTENSIONES_PERMITIDAS
    )

def conectar_bd():
    conexion = sqlite3.connect(DATABASE)
    conexion.row_factory = sqlite3.Row

    # Activar claves foráneas
    conexion.execute("PRAGMA foreign_keys = ON")

    return conexion

def crear_bd():

    conexion = conectar_bd()

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            usuario TEXT NOT NULL UNIQUE,
            contraseña TEXT NOT NULL,
            rol TEXT NOT NULL,
            estado INTEGER DEFAULT 1
        )
    """)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            fecha TEXT NOT NULL,
            descripcion TEXT,
            archivo TEXT,
            usuario TEXT NOT NULL
        )
    """)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            categoria TEXT NOT NULL UNIQUE,
            descripcion TEXT
        )
    """)

    # =========================
    # TABLA GESTIONES
    # =========================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS gestiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL,
            asunto TEXT NOT NULL,
            descripcion TEXT,
            responsable TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_limite TEXT,
            estado TEXT NOT NULL DEFAULT 'Pendiente',
            prioridad TEXT NOT NULL DEFAULT 'Media',
            observaciones TEXT,
            usuario TEXT NOT NULL
        )
    """)

    # =========================
    # TABLA SOLICITUDES
    # =========================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            solicitante TEXT NOT NULL,
            tipo TEXT NOT NULL,
            asunto TEXT NOT NULL,
            fecha TEXT NOT NULL,
            estado TEXT NOT NULL,
            descripcion TEXT,
            archivo TEXT,
            usuario TEXT
        )
    """)

    # =========================================================
    # AGREGAR COLUMNA ARCHIVO SI TODAVÍA NO EXISTE
    # =========================================================

    columnas = conexion.execute("""
        PRAGMA table_info(solicitudes)
    """).fetchall()

    nombres_columnas = [
        columna["name"] for columna in columnas
    ]

    if "archivo" not in nombres_columnas:

        conexion.execute("""
            ALTER TABLE solicitudes
            ADD COLUMN archivo TEXT
        """)

    # =========================================================
    # AGREGAR COLUMNA ARCHIVO_ID SI TODAVÍA NO EXISTE
    # =========================================================

    columnas = conexion.execute("""
        PRAGMA table_info(solicitudes)
    """).fetchall()

    nombres_columnas = [
        columna["name"] for columna in columnas
    ]

    if "archivo_id" not in nombres_columnas:

        conexion.execute("""
            ALTER TABLE solicitudes
            ADD COLUMN archivo_id TEXT
        """)

    # =========================================================
    # TABLA INVESTIGADORES
    # =========================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS investigadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            tipo TEXT NOT NULL,
            ci TEXT,
            correo TEXT,
            telefono TEXT,
            carrera_area TEXT,
            cargo TEXT,
            facultad TEXT,
            institucion TEXT,
            grado_academico TEXT,
            especialidad TEXT,
            orcid TEXT,
            google_scholar TEXT,
            scopus TEXT,
            researcher_id TEXT,
            estado TEXT NOT NULL DEFAULT 'Activo',
            observaciones TEXT,

            usuario TEXT
        )
    """)

    # =========================================================
    # AGREGAR COLUMNA TIPO SI TODAVÍA NO EXISTE
    # =========================================================

    columnas_investigadores = conexion.execute("""
        PRAGMA table_info(investigadores)
    """).fetchall()

    nombres_columnas_investigadores = [
        columna["name"] for columna in columnas_investigadores
    ]

    if "tipo" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN tipo TEXT NOT NULL DEFAULT 'Docente Investigador'
        """)

    # =========================================================
    # ACTUALIZAR COLUMNAS DE INVESTIGADORES
    # =========================================================

    columnas_investigadores = conexion.execute("""
        PRAGMA table_info(investigadores)
    """).fetchall()

    nombres_columnas_investigadores = [
        columna["name"] for columna in columnas_investigadores
    ]


    # ---------------------------------------------------------
    # TIPO
    # ---------------------------------------------------------

    if "tipo" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN tipo TEXT NOT NULL
            DEFAULT 'Docente Investigador'
        """)


    # ---------------------------------------------------------
    # APELLIDO
    # ---------------------------------------------------------

    if "apellido" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN apellido TEXT
        """)


    # ---------------------------------------------------------
    # CI
    # ---------------------------------------------------------

    if "ci" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN ci TEXT
        """)


    # ---------------------------------------------------------
    # CORREO
    # ---------------------------------------------------------

    if "correo" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN correo TEXT
        """)


    # ---------------------------------------------------------
    # TELÉFONO
    # ---------------------------------------------------------

    if "telefono" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN telefono TEXT
        """)


    # ---------------------------------------------------------
    # CARRERA / ÁREA
    # ---------------------------------------------------------

    if "carrera_area" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN carrera_area TEXT
        """)


    # ---------------------------------------------------------
    # CARGO
    # ---------------------------------------------------------

    if "cargo" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN cargo TEXT
        """)


    # ---------------------------------------------------------
    # FACULTAD
    # ---------------------------------------------------------

    if "facultad" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN facultad TEXT
        """)


    # ---------------------------------------------------------
    # INSTITUCIÓN
    # ---------------------------------------------------------

    if "institucion" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN institucion TEXT
        """)


    # ---------------------------------------------------------
    # GRADO ACADÉMICO
    # ---------------------------------------------------------

    if "grado_academico" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN grado_academico TEXT
        """)


    # ---------------------------------------------------------
    # ESPECIALIDAD
    # ---------------------------------------------------------

    if "especialidad" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN especialidad TEXT
        """)


    # ---------------------------------------------------------
    # ORCID
    # ---------------------------------------------------------

    if "orcid" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN orcid TEXT
        """)


    # ---------------------------------------------------------
    # GOOGLE SCHOLAR
    # ---------------------------------------------------------

    if "google_scholar" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN google_scholar TEXT
        """)


    # ---------------------------------------------------------
    # SCOPUS
    # ---------------------------------------------------------

    if "scopus" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN scopus TEXT
        """)


    # ---------------------------------------------------------
    # RESEARCHER ID
    # ---------------------------------------------------------

    if "researcher_id" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN researcher_id TEXT
        """)


    # ---------------------------------------------------------
    # ESTADO
    # ---------------------------------------------------------

    if "estado" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN estado TEXT
            DEFAULT 'Activo'
        """)


    # ---------------------------------------------------------
    # OBSERVACIONES
    # ---------------------------------------------------------

    if "observaciones" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN observaciones TEXT
        """)


    # ---------------------------------------------------------
    # USUARIO
    # ---------------------------------------------------------

    if "usuario" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN usuario TEXT
        """)

    # ---------------------------------------------------------
    # SEMESTRE
    # ---------------------------------------------------------

    if "semestre" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN semestre TEXT
        """)


    # ---------------------------------------------------------
    # MATRÍCULA / CÓDIGO UNIVERSITARIO
    # ---------------------------------------------------------

    if "matricula" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN matricula TEXT
        """)


    # ---------------------------------------------------------
    # TUTOR / DOCENTE RESPONSABLE
    # ---------------------------------------------------------

    if "tutor" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN tutor TEXT
        """)


    # ---------------------------------------------------------
    # LÍNEA DE INVESTIGACIÓN
    # ---------------------------------------------------------

    if "linea_investigacion" not in nombres_columnas_investigadores:

        conexion.execute("""
            ALTER TABLE investigadores
            ADD COLUMN linea_investigacion TEXT
        """)

    # =========================================================

    # TABLA PUBLICACIONES

    # =========================================================
   
    # =========================================================
    # TABLA REVISTAS
    # =========================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS revistas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,

            issn TEXT,
            issn_electronico TEXT,

            editorial TEXT,
            institucion TEXT,

            pais TEXT,
            ciudad TEXT,

            periodicidad TEXT,
            area_tematica TEXT,

            url TEXT,
            doi TEXT,

            indexacion TEXT,

            fecha_inicio TEXT,

            estado INTEGER NOT NULL DEFAULT 1,

            archivo TEXT,

            observaciones TEXT,

            usuario TEXT NOT NULL
        )
    """)

    # =========================================================
    # TABLA LIBROS
    # =========================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS libros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            codigo TEXT NOT NULL UNIQUE,
            titulo TEXT NOT NULL,
            subtitulo TEXT,

            isbn TEXT,
            editorial TEXT,
            edicion TEXT,
            lugar_publicacion TEXT,

            fecha_publicacion TEXT,
            anio INTEGER NOT NULL,

            paginas INTEGER,

            doi TEXT,
            url TEXT,

            tipo_libro TEXT,

            archivo TEXT,

            estado INTEGER NOT NULL DEFAULT 1,

            observaciones TEXT,

            usuario TEXT NOT NULL
        )
    """)

    # =========================================================
    # TABLA ARTÍCULOS
    # =========================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS articulos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            codigo TEXT NOT NULL UNIQUE,
            titulo TEXT NOT NULL,

            resumen TEXT,
            palabras_clave TEXT,

            fecha_publicacion TEXT,
            anio INTEGER NOT NULL,

            revista_id INTEGER,

            volumen TEXT,
            numero TEXT,
            paginas TEXT,

            doi TEXT,
            issn TEXT,
            url TEXT,

            archivo TEXT,

            estado INTEGER NOT NULL DEFAULT 1,

            observaciones TEXT,

            usuario TEXT NOT NULL,

            FOREIGN KEY (revista_id)
                REFERENCES revistas(id)
                ON UPDATE CASCADE
                ON DELETE SET NULL
        )
    """)

    # =========================================================
    # RELACIÓN ARTÍCULOS - INVESTIGADORES
    # =========================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS articulo_investigadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            articulo_id INTEGER NOT NULL,
            investigador_id INTEGER NOT NULL,

            orden_autor INTEGER DEFAULT 1,

            FOREIGN KEY (articulo_id)
                REFERENCES articulos(id)
                ON DELETE CASCADE,

            FOREIGN KEY (investigador_id)
                REFERENCES investigadores(id)
                ON DELETE CASCADE,

            UNIQUE(articulo_id, investigador_id)
        )
    """)

    # =========================================================
    # RELACIÓN LIBROS - INVESTIGADORES
    # =========================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS libro_investigadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            libro_id INTEGER NOT NULL,
            investigador_id INTEGER NOT NULL,

            orden_autor INTEGER DEFAULT 1,

            FOREIGN KEY (libro_id)
                REFERENCES libros(id)
                ON DELETE CASCADE,

            FOREIGN KEY (investigador_id)
                REFERENCES investigadores(id)
                ON DELETE CASCADE,

            UNIQUE(libro_id, investigador_id)
        )
    """)

    # =========================================================
    # TABLA TEXTOS EN ASIGNATURA
    # =========================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS textos_asignatura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            codigo TEXT NOT NULL UNIQUE,
            asignatura TEXT NOT NULL,

            carrera TEXT,
            facultad TEXT,

            editorial TEXT,
            institucion TEXT,

            edicion TEXT,
            lugar_publicacion TEXT,
            fecha_publicacion TEXT,

            anio INTEGER NOT NULL,

            paginas INTEGER,

            isbn TEXT,
            doi TEXT,
            url TEXT,

            archivo TEXT,

            estado INTEGER NOT NULL DEFAULT 1,

            observaciones TEXT,

            usuario TEXT NOT NULL
        )
    """)

    # =========================================================
    # RELACIÓN TEXTOS EN ASIGNATURA - INVESTIGADORES
    # =========================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS texto_asignatura_investigadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            texto_asignatura_id INTEGER NOT NULL,
            investigador_id INTEGER NOT NULL,

            orden_autor INTEGER DEFAULT 1,

            FOREIGN KEY (texto_asignatura_id)
                REFERENCES textos_asignatura(id)
                ON DELETE CASCADE,

            FOREIGN KEY (investigador_id)
                REFERENCES investigadores(id)
                ON DELETE CASCADE,

            UNIQUE(texto_asignatura_id, investigador_id)
        )
    """)

    
    # =========================================================
    # TABLA AUDITORÍA
    # =========================================================

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            usuario TEXT NOT NULL,

            accion TEXT NOT NULL,

            modulo TEXT NOT NULL,

            registro_id INTEGER,

            descripcion TEXT,

            fecha TEXT NOT NULL
        )
    """)
    
    # =========================================================
    # ACTUALIZAR ESTADO DE PUBLICACIONES
    # 1 = ACTIVO
    # 0 = INACTIVO
    # =========================================================

    tablas_publicaciones = [
        "revistas",
        "libros",
        "articulos",
        "textos_asignatura"
    ]

    for tabla in tablas_publicaciones:

        columnas = conexion.execute(
            f"PRAGMA table_info({tabla})"
        ).fetchall()

        nombres_columnas = [
            columna["name"]
            for columna in columnas
        ]

        # -----------------------------------------------------
        # SI LA COLUMNA ESTADO NO EXISTE
        # -----------------------------------------------------

        if "estado" not in nombres_columnas:

            conexion.execute(
                f"""
                ALTER TABLE {tabla}
                ADD COLUMN estado INTEGER NOT NULL DEFAULT 1
                """
            )

        else:

            # -------------------------------------------------
            # CONVERTIR LOS VALORES ACTUALES
            #
            # Activo   -> 1
            # Inactivo -> 0
            # -------------------------------------------------

            conexion.execute(
                f"""
                UPDATE {tabla}
                SET estado = 1
                WHERE estado = 'Activo'
                """
            )

            conexion.execute(
                f"""
                UPDATE {tabla}
                SET estado = 0
                WHERE estado = 'Inactivo'
                """
            )

            # -------------------------------------------------
            # ASEGURAR VALORES NULOS
            # -------------------------------------------------

            conexion.execute(
                f"""
                UPDATE {tabla}
                SET estado = 1
                WHERE estado IS NULL
                """
            )
    


    conexion.commit()
    conexion.close()

# Clave secreta para las sesiones
app.secret_key = "dicyt_clave_secreta_2026"



# =========================
# CONTROL DE CONTRASEÑA TEMPORAL
# =========================

@app.before_request
def verificar_cambio_password():

    # Rutas que deben quedar permitidas
    rutas_permitidas = [
        "login",
        "cambiar_password",
        "static"
    ]

    # Si la ruta actual está permitida, continuar
    if request.endpoint in rutas_permitidas:
        return

    # Si no hay usuario conectado, continuar
    if "usuario_id" not in session:
        return

    conexion = conectar_bd()

    usuario = conexion.execute(
        "SELECT cambiar_password FROM usuarios WHERE id = ?",
        (session["usuario_id"],)
    ).fetchone()

    conexion.close()

    # Si el usuario debe cambiar la contraseña,
    # enviarlo obligatoriamente al formulario
    if usuario and usuario["cambiar_password"] == 1:

        return redirect(url_for("cambiar_password"))

# =========================
# LOGIN
# =========================


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]

        conexion = conectar_bd()

        usuario_bd = conexion.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND estado = 1",
            (usuario,)
        ).fetchone()

        conexion.close()

        if usuario_bd and check_password_hash(
            usuario_bd["contraseña"],
            contraseña
        ):

            session["usuario_id"] = usuario_bd["id"]
            session["usuario"] = usuario_bd["nombre"]
            session["rol"] = usuario_bd["rol"]

            # Verificar si debe cambiar la contraseña
            if usuario_bd["cambiar_password"] == 1:

                return redirect(url_for("cambiar_password"))

            return redirect(url_for("inicio"))

        else:

            return render_template(
                "login.html",
                error="Usuario o contraseña incorrectos"
            )

    return render_template("login.html")


# =========================
# CERRAR SESIÓN
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

# =========================
# USUARIOS
# =========================

@app.route("/usuarios")
def usuarios():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "Administrador":
        return "Acceso no autorizado", 403

    conexion = conectar_bd()

    usuarios = conexion.execute(
        "SELECT id, nombre, usuario, rol, estado FROM usuarios"
    ).fetchall()

    conexion.close()

    return render_template(
        "usuarios.html",
        usuarios=usuarios,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

@app.route("/usuarios/restablecer-password/<int:id>", methods=["GET", "POST"])
def restablecer_password(id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "Administrador":
        return "Acceso no autorizado", 403

    conexion = conectar_bd()

    usuario = conexion.execute(
        "SELECT id, nombre, usuario FROM usuarios WHERE id = ?",
        (id,)
    ).fetchone()

    if usuario is None:
        conexion.close()
        return "Usuario no encontrado", 404

    if request.method == "POST":

        nueva_password = request.form["nueva_password"]
        confirmar_password = request.form["confirmar_password"]

        # Verificar si se solicitó cambio obligatorio
        cambiar_password = 1 if request.form.get("cambiar_password") else 0

        if not contraseña_segura(nueva_password):

            conexion.close()

            return render_template(
                "restablecer_password.html",
                usuario=usuario,
                error=(
                    "La contraseña debe tener mínimo 8 caracteres, "
                    "una mayúscula, una minúscula, un número "
                    "y un carácter especial."
                ),
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol")
            )

        # =========================
        # VALIDAR CONTRASEÑA
        # =========================

        if not nueva_password:

            conexion.close()

            return render_template(
                "restablecer_password.html",
                usuario=usuario,
                error="La contraseña no puede estar vacía.",
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol")
            )


        if nueva_password != confirmar_password:

            conexion.close()

            return render_template(
                "restablecer_password.html",
                usuario=usuario,
                error="Las contraseñas no coinciden.",
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol")
            )


        if not contraseña_segura(nueva_password):

            conexion.close()

            return render_template(
                "restablecer_password.html",
                usuario=usuario,
                error=(
                    "La contraseña debe tener mínimo 8 caracteres, "
                    "una mayúscula, una minúscula, un número "
                    "y un carácter especial."
                ),
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol")
            )


        password_hash = generate_password_hash(nueva_password)

        conexion.execute("""
            UPDATE usuarios
            SET contraseña = ?,
                cambiar_password = ?
            WHERE id = ?
        """, (
            password_hash,
            cambiar_password,
            id
        ))

        conexion.commit()
        conexion.close()

        flash(
            f"La contraseña del usuario {usuario['nombre']} fue restablecida correctamente.",
            "success"
        )

        return redirect(url_for("usuarios"))

    conexion.close()

    return render_template(
        "restablecer_password.html",
        usuario=usuario,
        usuario_sesion=session.get("usuario"),
        rol=session.get("rol")
    )

@app.route("/cambiar-password", methods=["GET", "POST"])
def cambiar_password():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    usuario = conexion.execute(
        "SELECT * FROM usuarios WHERE id = ?",
        (session["usuario_id"],)
    ).fetchone()

    if usuario is None:
        conexion.close()
        session.clear()
        return redirect(url_for("login"))

    # Verificar si realmente debe cambiar la contraseña
    if usuario["cambiar_password"] != 1:
        conexion.close()
        return redirect(url_for("inicio"))

    if request.method == "POST":

        nueva_password = request.form["nueva_password"]
        confirmar_password = request.form["confirmar_password"]

        if not nueva_password:

            conexion.close()

            return render_template(
                "cambiar_password.html",
                error="La contraseña no puede estar vacía",
                usuario=usuario,
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol")
            )

        if nueva_password != confirmar_password:

            conexion.close()

            return render_template(
                "cambiar_password.html",
                error="Las contraseñas no coinciden",
                usuario=usuario,
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol")
            )

        if not contraseña_segura(nueva_password):

            conexion.close()

            return render_template(
                "cambiar_password.html",
                error=(
                    "La contraseña debe tener mínimo 8 caracteres, "
                    "una mayúscula, una minúscula, un número "
                    "y un carácter especial."
                ),
                usuario=usuario,
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol")
            )

        password_hash = generate_password_hash(nueva_password)

        conexion.execute("""
            UPDATE usuarios
            SET contraseña = ?,
                cambiar_password = 0
            WHERE id = ?
        """, (
            password_hash,
            session["usuario_id"]
        ))

        conexion.commit()
        conexion.close()

        flash(
            "Contraseña actualizada correctamente.",
            "success"
        )

        return redirect(url_for("inicio"))

    conexion.close()

    return render_template(
        "cambiar_password.html",
        usuario=usuario,
        usuario_sesion=session.get("usuario"),
        rol=session.get("rol")
    )


@app.route("/usuarios/editar/<int:id>", methods=["GET", "POST"])
def editar_usuario(id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "Administrador":
        return "Acceso no autorizado", 403

    conexion = conectar_bd()

    usuario = conexion.execute(
        "SELECT * FROM usuarios WHERE id = ?",
        (id,)
    ).fetchone()

    if usuario is None:
        conexion.close()
        return "Usuario no encontrado", 404

    if request.method == "POST":

        nombre = request.form["nombre"]
        usuario_nombre = request.form["usuario"]
        estado = request.form["estado"]

        # El administrador no puede cambiar su propio rol
        if id == session["usuario_id"]:
            rol = usuario["rol"]
        else:
            rol = request.form["rol"]
 
            conexion.execute("""
                    UPDATE usuarios
                    SET nombre = ?,
                        usuario = ?,
                        rol = ?,
                        estado = ?
                    WHERE id = ?
                """, (
                    nombre,
                    usuario_nombre,
                    rol,
                    estado,
                    id
                ))

        conexion.commit()

        # =========================
        # ACTUALIZAR SESIÓN
        # =========================

        if session.get("usuario_id") == id:

            session["usuario"] = nombre
            session["rol"] = rol

        conexion.close()

        return redirect(url_for("usuarios"))

    conexion.close()

    return render_template(
        "editar_usuario.html",
        usuario=usuario,
        usuario_sesion=session.get("usuario"),
        rol=session.get("rol")
    )

@app.route("/usuarios/eliminar/<int:id>", methods=["POST"])
def eliminar_usuario(id):

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "Administrador":
        return "Acceso no autorizado", 403

    # Evitar que el administrador elimine su propia cuenta
    if session.get("usuario_id") == id:
        return "No puedes eliminar tu propia cuenta", 400

    conexion = conectar_bd()

    conexion.execute(
        "DELETE FROM usuarios WHERE id = ?",
        (id,)
    )

    conexion.commit()
    conexion.close()

    return redirect(url_for("usuarios"))



# =========================
# CREAR USUARIO
# =========================

@app.route("/usuarios/nuevo", methods=["GET", "POST"])
def nuevo_usuario():

    # Verificar sesión
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    # Verificar que sea Administrador
    if session.get("rol") != "Administrador":
        return "Acceso no autorizado", 403

    if request.method == "POST":

        nombre = request.form["nombre"]
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]
        confirmar_contraseña = request.form["confirmar_contraseña"]
        rol = request.form["rol"]

        if not contraseña_segura(contraseña):

            return render_template(
                "nuevo_usuario.html",
                error=(
                    "La contraseña debe tener mínimo 8 caracteres, "
                    "una mayúscula, una minúscula, un número "
                    "y un carácter especial."
                ),
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )
        contraseña_hash = generate_password_hash(contraseña)

        # =========================
        # VALIDAR CONTRASEÑA
        # =========================

        if not contraseña:

            return render_template(
                "nuevo_usuario.html",
                error="La contraseña no puede estar vacía.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


        if contraseña != confirmar_contraseña:

            return render_template(
                "nuevo_usuario.html",
                error="Las contraseñas no coinciden.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


        if not contraseña_segura(contraseña):

            return render_template(
                "nuevo_usuario.html",
                error=(
                    "La contraseña debe tener mínimo 8 caracteres, "
                    "una mayúscula, una minúscula, un número "
                    "y un carácter especial."
                ),
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # =========================
        # GENERAR HASH
        # =========================

        contraseña_hash = generate_password_hash(contraseña)

        conexion = conectar_bd()

        try:

            conexion.execute("""
                INSERT INTO usuarios
                (nombre, usuario, contraseña, rol, estado)
                VALUES (?, ?, ?, ?, ?)
            """, (
                nombre,
                usuario,
                contraseña_hash,
                rol,
                1
            ))

            conexion.commit()

        except sqlite3.IntegrityError:

            conexion.close()

            return render_template(
                "nuevo_usuario.html",
                error="El nombre de usuario ya existe.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        conexion.close()

        return redirect(url_for("usuarios"))

    return render_template(
        "nuevo_usuario.html",
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# CONFIGURACIÓN
# =========================

@app.route("/configuracion")
def configuracion():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    institucion = conexion.execute("""
        SELECT *
        FROM configuracion_institucional
        WHERE id = 1
    """).fetchone()

    conexion.close()

    return render_template(
        "configuracion.html",
        usuario=session.get("usuario"),
        rol=session.get("rol"),
        institucion=institucion
    )


# =========================
# EDITAR INFORMACIÓN INSTITUCIONAL
# =========================

@app.route("/configuracion/institucional/editar", methods=["GET", "POST"])
def editar_informacion_institucional():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    institucion = conexion.execute("""
        SELECT *
        FROM configuracion_institucional
        WHERE id = 1
    """).fetchone()

    # =========================
    # PROCESAR FORMULARIO
    # =========================

    if request.method == "POST":

        universidad = request.form["universidad"].strip()
        direccion = request.form["direccion"].strip()
        nombre_sistema = request.form["nombre_sistema"].strip()
        sigla_sistema = request.form["sigla_sistema"].strip()

        # =========================
        # LOGO INSTITUCIONAL
        # =========================

        archivo_logo = request.files.get("logo")

        nombre_logo = institucion["logo"]

        if archivo_logo and archivo_logo.filename:

            nombre_original = secure_filename(
                archivo_logo.filename
            )

            extension = nombre_original.rsplit(
                ".", 1
            )[1].lower()

            if extension not in EXTENSIONES_LOGO_PERMITIDAS:

                conexion.close()

                flash(
                    "El formato del logo no es válido.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "editar_informacion_institucional"
                    )
                )

            nombre_logo = "logo_institucional." + extension

            ruta_logo = os.path.join(
                app.config["UPLOAD_FOLDER"],
                "logos",
                nombre_logo
            )

            archivo_logo.save(ruta_logo)

        conexion.execute("""
            UPDATE configuracion_institucional
            SET
                universidad = ?,
                direccion = ?,
                nombre_sistema = ?,
                sigla_sistema = ?,
                logo = ?,
                usuario = ?,
                fecha_actualizacion = ?
            WHERE id = 1
        """, (
            universidad,
            direccion,
            nombre_sistema,
            sigla_sistema,
            nombre_logo,
            session.get("usuario"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conexion.commit()
        conexion.close()

        flash(
            "Información institucional actualizada correctamente.",
            "success"
        )

        return redirect(url_for("configuracion"))

    conexion.close()

    return render_template(
        "editar_informacion_institucional.html",
        institucion=institucion,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# AUDITORIA
# =========================

@app.route("/auditoria")
def auditoria():

    # Solo usuarios autenticados
    if "usuario" not in session:
        return redirect(url_for("login"))

    # Solo Administradores
    if session.get("rol") != "Administrador":
        flash("No tienes permisos para acceder a la auditoría.", "error")
        return redirect(url_for("inicio"))

    conexion = conectar_bd()

    # =========================================================
    # FILTROS
    # =========================================================

    buscar = request.args.get("buscar", "").strip()
    usuario = request.args.get("usuario", "").strip()
    accion = request.args.get("accion", "").strip()
    modulo = request.args.get("modulo", "").strip()
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()

    # =========================================================
    # CONSULTA PRINCIPAL
    # =========================================================

    consulta = """
        SELECT
            id,
            usuario,
            accion,
            modulo,
            registro_id,
            descripcion,
            fecha
        FROM auditoria
        WHERE 1 = 1
    """

    parametros = []

    # Buscar en descripción, usuario o módulo
    if buscar:
        consulta += """
            AND (
                usuario LIKE ?
                OR modulo LIKE ?
                OR descripcion LIKE ?
            )
        """

        texto_busqueda = f"%{buscar}%"

        parametros.extend([
            texto_busqueda,
            texto_busqueda,
            texto_busqueda
        ])

    # Filtro por usuario
    if usuario:
        consulta += """
            AND usuario = ?
        """

        parametros.append(usuario)

    # Filtro por acción
    if accion:
        consulta += """
            AND accion = ?
        """

        parametros.append(accion)

    # Filtro por módulo
    if modulo:
        consulta += """
            AND modulo = ?
        """

        parametros.append(modulo)

    # Filtro desde fecha
    if fecha_desde:
        consulta += """
            AND date(fecha) >= date(?)
        """

        parametros.append(fecha_desde)

    # Filtro hasta fecha
    if fecha_hasta:
        consulta += """
            AND date(fecha) <= date(?)
        """

        parametros.append(fecha_hasta)

    consulta += """
        ORDER BY id DESC
    """

    registros = conexion.execute(
        consulta,
        parametros
    ).fetchall()

    # =========================================================
    # OPCIONES PARA LOS FILTROS
    # =========================================================

    usuarios = conexion.execute("""
        SELECT DISTINCT usuario
        FROM auditoria
        WHERE usuario IS NOT NULL
          AND usuario != ''
        ORDER BY usuario ASC
    """).fetchall()

    acciones = conexion.execute("""
        SELECT DISTINCT accion
        FROM auditoria
        WHERE accion IS NOT NULL
          AND accion != ''
        ORDER BY accion ASC
    """).fetchall()

    modulos = conexion.execute("""
        SELECT DISTINCT modulo
        FROM auditoria
        WHERE modulo IS NOT NULL
          AND modulo != ''
        ORDER BY modulo ASC
    """).fetchall()

    conexion.close()

    # =========================================================
    # VISTA
    # =========================================================

    return render_template(
        "auditoria.html",
        registros=registros,
        usuarios=usuarios,
        acciones=acciones,
        modulos=modulos,
        buscar=buscar,
        usuario_filtro=usuario,
        accion=accion,
        modulo=modulo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# CAMBIAR CONTRASEÑA
# =========================

@app.route("/cambiar_contraseña", methods=["GET", "POST"])
def cambiar_contraseña():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    # =========================
    # DETERMINAR ORIGEN
    # =========================

    origen = request.args.get(
        "origen",
        request.form.get("origen", "inicio")
    )

    # =========================
    # RUTA DE REGRESO
    # =========================

    ruta_regreso = None

    if origen == "configuracion":
        ruta_regreso = url_for("configuracion")

    elif origen.startswith("/"):
        ruta_regreso = origen

    else:
        ruta_regreso = url_for("inicio")

    # =========================
    # PROCESAR FORMULARIO
    # =========================

    if request.method == "POST":

        contraseña_actual = request.form["contraseña_actual"]
        nueva_contraseña = request.form["nueva_contraseña"]
        confirmar_contraseña = request.form["confirmar_contraseña"]

        conexion = conectar_bd()

        # =========================
        # OBTENER USUARIO ACTUAL
        # =========================

        usuario = conexion.execute(
            "SELECT * FROM usuarios WHERE id = ?",
            (session["usuario_id"],)
        ).fetchone()

        if usuario is None:

            conexion.close()
            session.clear()

            return redirect(url_for("login"))

        # =========================
        # VERIFICAR CONTRASEÑA ACTUAL
        # =========================

        if not check_password_hash(
            usuario["contraseña"],
            contraseña_actual
        ):

            conexion.close()

            return render_template(
                "cambiar_contraseña.html",
                error="La contraseña actual es incorrecta.",
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol"),
                origen=origen
            )

        # =========================
        # VERIFICAR QUE NO ESTÉ VACÍA
        # =========================

        if not nueva_contraseña:

            conexion.close()

            return render_template(
                "cambiar_contraseña.html",
                error="La nueva contraseña no puede estar vacía.",
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol"),
                origen=origen
            )

        # =========================
        # VERIFICAR COINCIDENCIA
        # =========================

        if nueva_contraseña != confirmar_contraseña:

            conexion.close()

            return render_template(
                "cambiar_contraseña.html",
                error="Las nuevas contraseñas no coinciden.",
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol"),
                origen=origen
            )

        # =========================
        # VERIFICAR SEGURIDAD
        # =========================

        if not contraseña_segura(nueva_contraseña):

            conexion.close()

            return render_template(
                "cambiar_contraseña.html",
                error=(
                    "La contraseña debe tener mínimo 8 caracteres, "
                    "una mayúscula, una minúscula, un número "
                    "y un carácter especial."
                ),
                usuario_sesion=session.get("usuario"),
                rol=session.get("rol"),
                origen=origen
            )

        # =========================
        # GENERAR HASH
        # =========================

        nueva_contraseña_hash = generate_password_hash(
            nueva_contraseña
        )

        # =========================
        # ACTUALIZAR CONTRASEÑA
        # =========================

        conexion.execute("""
            UPDATE usuarios
            SET contraseña = ?
            WHERE id = ?
        """, (
            nueva_contraseña_hash,
            session["usuario_id"]
        ))

        conexion.commit()
        conexion.close()

        flash(
            "Contraseña actualizada correctamente.",
            "success"
        )

        return redirect(ruta_regreso)

    # =========================
    # MOSTRAR FORMULARIO
    # =========================

    return render_template(
        "cambiar_contraseña.html",
        usuario_sesion=session.get("usuario"),
        rol=session.get("rol"),
        origen=origen
    )

# =========================
# INICIO
# =========================

@app.route("/")
def inicio():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("dicyt.db")
    conn.row_factory = sqlite3.Row

    # =========================================================
    # DOCUMENTOS
    # =========================================================

    total_documentos = conn.execute("""
        SELECT COUNT(*)
        FROM documentos
    """).fetchone()[0]


    # =========================================================
    # INVESTIGADORES
    # =========================================================

    total_investigadores = conn.execute("""
        SELECT COUNT(*)
        FROM investigadores
    """).fetchone()[0]


    docentes = conn.execute("""
        SELECT COUNT(*)
        FROM investigadores
        WHERE tipo = 'Docente Investigador'
    """).fetchone()[0]


    estudiantes = conn.execute("""
        SELECT COUNT(*)
        FROM investigadores
        WHERE tipo = 'Estudiante Investigador'
    """).fetchone()[0]


    # =========================================================
    # PRODUCCIÓN CIENTÍFICA
    # =========================================================

    total_articulos = conn.execute("""
        SELECT COUNT(*)
        FROM articulos
    """).fetchone()[0]


    total_libros = conn.execute("""
        SELECT COUNT(*)
        FROM libros
    """).fetchone()[0]


    total_revistas = conn.execute("""
        SELECT COUNT(*)
        FROM revistas
    """).fetchone()[0]


    total_textos = conn.execute("""
        SELECT COUNT(*)
        FROM textos_asignatura
    """).fetchone()[0]


    total_sociedades = conn.execute("""
        SELECT COUNT(*)
        FROM sociedades_cientificas
    """).fetchone()[0]


    # =========================================================
    # TOTAL PUBLICACIONES
    # =========================================================

    total_publicaciones = (
        total_articulos
        + total_libros
        + total_revistas
        + total_textos
        + total_sociedades
    )


    # =========================================================
    # GESTIONES
    # =========================================================

    total_gestiones = conn.execute("""
        SELECT COUNT(*)
        FROM gestiones
    """).fetchone()[0]


    conn.close()


    # =========================================================
    # ENVIAR DATOS AL INICIO
    # =========================================================

    return render_template(
        "index.html",

        usuario=session["usuario"],
        rol=session["rol"],

        total_documentos=total_documentos,

        total_investigadores=total_investigadores,
        docentes=docentes,
        estudiantes=estudiantes,

        total_publicaciones=total_publicaciones,

        total_articulos=total_articulos,
        total_libros=total_libros,
        total_revistas=total_revistas,
        total_textos=total_textos,
        total_sociedades=total_sociedades,

        total_gestiones=total_gestiones
    )


# =========================
# DOCUMENTOS
# =========================

@app.route("/documentos")
def documentos():

    if "usuario" not in session:
        return redirect(url_for("login"))

    busqueda = request.args.get("buscar", "").strip()
    categoria_seleccionada = request.args.get("categoria", "").strip()

    conexion = conectar_bd()

    # Obtener categorías existentes
    categorias = conexion.execute("""
        SELECT categoria
        FROM categorias
        ORDER BY categoria ASC
    """).fetchall()

    # Consulta de documentos
    consulta = """
        SELECT *
        FROM documentos
        WHERE 1=1
    """

    parametros = []

    # Filtro de búsqueda
    if busqueda:

        consulta += """
            AND (
                codigo LIKE ?
                OR nombre LIKE ?
                OR categoria LIKE ?
                OR descripcion LIKE ?
            )
        """

        texto = f"%{busqueda}%"

        parametros.extend([
            texto,
            texto,
            texto,
            texto
        ])

    # Filtro por categoría
    if categoria_seleccionada:

        consulta += """
            AND categoria = ?
        """

        parametros.append(categoria_seleccionada)

    consulta += """
        ORDER BY id DESC
    """

    documentos = conexion.execute(
        consulta,
        parametros
    ).fetchall()

    conexion.close()

    return render_template(
        "documentos.html",
        documentos=documentos,
        busqueda=busqueda,
        categorias=categorias,
        categoria_seleccionada=categoria_seleccionada,
        usuario=session["usuario"],
        rol=session["rol"]
    )

@app.route("/categorias")
def categorias():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    categorias = conexion.execute("""
        SELECT *
        FROM categorias
        ORDER BY id DESC
    """).fetchall()

    conexion.close()

    return render_template(
        "categorias.html",
        categorias=categorias,
        usuario=session["usuario"],
        rol=session["rol"]
    )

# =========================
# GESTIONES
# =========================

@app.route("/gestiones")
def gestiones():

    if "usuario" not in session:
        return redirect(url_for("login"))

    buscar = request.args.get("buscar", "").strip()

    conexion = conectar_bd()

    if buscar:

        texto = f"%{buscar}%"

        gestiones = conexion.execute("""
            SELECT *
            FROM gestiones
            WHERE
                codigo LIKE ?
                OR tipo LIKE ?
                OR asunto LIKE ?
                OR descripcion LIKE ?
                OR responsable LIKE ?
                OR estado LIKE ?
                OR prioridad LIKE ?
                OR observaciones LIKE ?
                OR usuario LIKE ?
            ORDER BY id DESC
        """, (
            texto,
            texto,
            texto,
            texto,
            texto,
            texto,
            texto,
            texto,
            texto
        )).fetchall()

    else:

        gestiones = conexion.execute("""
            SELECT *
            FROM gestiones
            ORDER BY id DESC
        """).fetchall()

    conexion.close()

    return render_template(
        "gestiones.html",
        gestiones=gestiones,
        buscar=buscar,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# VER GESTIÓN
# =========================

@app.route("/gestiones/ver/<int:id>")
def ver_gestion(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    gestion = conexion.execute("""
        SELECT *
        FROM gestiones
        WHERE id = ?
    """, (id,)).fetchone()

    conexion.close()

    if gestion is None:
        return "Gestión no encontrada", 404

    return render_template(
        "ver_actividad.html",
        gestion=gestion,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# EDITAR GESTIÓN
# =========================

@app.route("/gestiones/editar/<int:id>", methods=["GET", "POST"])
def editar_gestion(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    gestion = conexion.execute("""
        SELECT *
        FROM gestiones
        WHERE id = ?
    """, (id,)).fetchone()

    if gestion is None:
        conexion.close()
        return "Gestión no encontrada", 404

    if request.method == "POST":

        codigo = request.form["codigo"]
        tipo = request.form["tipo"]
        asunto = request.form["asunto"]
        descripcion = request.form["descripcion"]
        responsable = request.form["responsable"]
        fecha_inicio = request.form["fecha_inicio"]
        fecha_limite = request.form["fecha_limite"]
        estado = request.form["estado"]
        prioridad = request.form["prioridad"]
        observaciones = request.form["observaciones"]

        conexion.execute("""
            UPDATE gestiones
            SET codigo = ?,
                tipo = ?,
                asunto = ?,
                descripcion = ?,
                responsable = ?,
                fecha_inicio = ?,
                fecha_limite = ?,
                estado = ?,
                prioridad = ?,
                observaciones = ?
            WHERE id = ?
        """, (
            codigo,
            tipo,
            asunto,
            descripcion,
            responsable,
            fecha_inicio,
            fecha_limite,
            estado,
            prioridad,
            observaciones,
            id
        ))

        conexion.commit()
        conexion.close()

        flash(
            "Gestión actualizada correctamente.",
            "success"
        )

        return redirect(url_for("gestiones"))

    conexion.close()

    return render_template(
        "editar_actividad.html",
        gestion=gestion,
        usuario=session.get("usuario"),
        rol=session.get("rol"),
        tipos_actividad=TIPOS_ACTIVIDAD
    )

# =========================
# ELIMINAR GESTIÓN
# =========================

@app.route("/gestiones/eliminar/<int:id>", methods=["POST"])
def eliminar_gestion(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "Administrador":
        return "Acceso no autorizado", 403

    conexion = conectar_bd()

    gestion = conexion.execute(
        "SELECT * FROM gestiones WHERE id = ?",
        (id,)
    ).fetchone()

    if gestion is None:
        conexion.close()
        return "Gestión no encontrada", 404

    conexion.execute(
        "DELETE FROM gestiones WHERE id = ?",
        (id,)
    )

    conexion.commit()
    conexion.close()

    return redirect(url_for("gestiones"))

# =========================
# NUEVA ACTIVIDAD
# =========================

@app.route("/actividades/nueva", methods=["GET", "POST"])
def nueva_actividad():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "Administrador":
        return "Acceso no autorizado", 403

    if request.method == "POST":

        codigo = request.form["codigo"]
        tipo = request.form["tipo"]
        asunto = request.form["asunto"]
        descripcion = request.form["descripcion"]
        responsable = request.form["responsable"]
        fecha_inicio = request.form["fecha_inicio"]
        fecha_limite = request.form["fecha_limite"]
        estado = request.form["estado"]
        prioridad = request.form["prioridad"]
        observaciones = request.form["observaciones"]

        conexion = conectar_bd()

        conexion.execute("""
            INSERT INTO gestiones (
                codigo,
                tipo,
                asunto,
                descripcion,
                responsable,
                fecha_inicio,
                fecha_limite,
                estado,
                prioridad,
                observaciones,
                usuario
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            codigo,
            tipo,
            asunto,
            descripcion,
            responsable,
            fecha_inicio,
            fecha_limite,
            estado,
            prioridad,
            observaciones,
            session["usuario"]
        ))

        conexion.commit()
        conexion.close()

        return redirect(url_for("gestiones"))

    return render_template(
        "nueva_actividad.html",
        usuario=session.get("usuario"),
        rol=session.get("rol"),
        tipos_actividad=TIPOS_ACTIVIDAD
    )

# =========================
# SOLICITUDES
# =========================

@app.route("/solicitudes")
def solicitudes():

    if "usuario" not in session:
        return redirect(url_for("login"))

    buscar = request.args.get("buscar", "").strip()

    conexion = conectar_bd()

    if buscar:

        texto = f"%{buscar}%"

        solicitudes = conexion.execute("""
            SELECT *
            FROM solicitudes
            WHERE
                codigo LIKE ?
                OR solicitante LIKE ?
                OR tipo LIKE ?
                OR asunto LIKE ?
                OR fecha LIKE ?
                OR estado LIKE ?
                OR descripcion LIKE ?
                OR usuario LIKE ?
            ORDER BY id DESC
        """, (
            texto,
            texto,
            texto,
            texto,
            texto,
            texto,
            texto,
            texto
        )).fetchall()

    else:

        solicitudes = conexion.execute("""
            SELECT *
            FROM solicitudes
            ORDER BY id DESC
        """).fetchall()

    conexion.close()

    return render_template(
        "solicitudes.html",
        solicitudes=solicitudes,
        buscar=buscar,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# NUEVA SOLICITUD
# =========================

@app.route("/solicitudes/nueva", methods=["GET", "POST"])
def nueva_solicitud():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        codigo = request.form["codigo"].strip()
        solicitante = request.form["solicitante"].strip()
        tipo = request.form["tipo"].strip()
        asunto = request.form["asunto"].strip()
        fecha = request.form["fecha"].strip()
        estado = request.form["estado"].strip()
        descripcion = request.form["descripcion"].strip()

        # =========================
        # ARCHIVO
        # =========================

        archivo_subido = request.files.get("archivo")

        nombre_archivo = None
        archivo_id = None

        # =========================
        # SUBIR ARCHIVO A DRIVE
        # =========================

        if archivo_subido and archivo_subido.filename:

            nombre_original = secure_filename(
                archivo_subido.filename
            )

            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(
                delete=False
            ) as archivo_temporal:

                ruta_temporal = archivo_temporal.name

            archivo_subido.save(ruta_temporal)

            try:

                # Conectar con Google Drive
                servicio = conectar_google_drive()

                # Obtener carpeta SOLICITUDES
                carpeta_solicitudes = obtener_carpeta_solicitudes(
                    servicio
                )

                # Subir archivo
                archivo_drive = subir_archivo(
                    servicio,
                    ruta_temporal,
                    nombre_original,
                    carpeta_solicitudes
                )

                # Guardar información del archivo
                nombre_archivo = archivo_drive.get(
                    "name"
                )

                archivo_id = archivo_drive.get(
                    "id"
                )

            finally:

                # Eliminar archivo temporal
                if os.path.exists(ruta_temporal):

                    os.remove(ruta_temporal)

        # =========================
        # GUARDAR SOLICITUD
        # =========================

        conexion = conectar_bd()

        conexion.execute("""
            INSERT INTO solicitudes (
                codigo,
                solicitante,
                tipo,
                asunto,
                fecha,
                estado,
                descripcion,
                usuario,
                archivo,
                archivo_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            codigo,
            solicitante,
            tipo,
            asunto,
            fecha,
            estado,
            descripcion,
            session.get("usuario"),
            nombre_archivo,
            archivo_id
        ))

        conexion.commit()
        conexion.close()

        return redirect(
            url_for("solicitudes")
        )

    return render_template(
        "nueva_solicitud.html",
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# VER SOLICITUD
# =========================

@app.route("/solicitudes/ver/<int:id>")
def ver_solicitud(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    solicitud = conexion.execute("""
        SELECT *
        FROM solicitudes
        WHERE id = ?
    """, (id,)).fetchone()

    conexion.close()

    if solicitud is None:
        return redirect(url_for("solicitudes"))

    print("===================================")
    print("ID SOLICITUD:", solicitud["id"])
    print("ARCHIVO:", solicitud["archivo"])
    print(
        "URL ARCHIVO:",
        url_for(
            "archivo_solicitud",
            id=solicitud["id"]
        )
    )
    print("===================================")

    return render_template(
        "ver_solicitud.html",
        solicitud=solicitud,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# ARCHIVO DE SOLICITUD
# =========================

@app.route("/solicitudes/archivo/<int:id>")
def archivo_solicitud(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    solicitud = conexion.execute("""
        SELECT archivo
        FROM solicitudes
        WHERE id = ?
    """, (id,)).fetchone()

    conexion.close()

    if solicitud is None:
        return redirect(url_for("solicitudes"))

    nombre_archivo = solicitud["archivo"]

    if not nombre_archivo:
        return redirect(
            url_for("ver_solicitud", id=id)
        )

    # =========================
    # CONECTAR GOOGLE DRIVE
    # =========================

    servicio = conectar_google_drive()

    carpeta_solicitudes = obtener_carpeta_solicitudes(
        servicio
    )

    # =========================
    # BUSCAR ARCHIVO
    # =========================

    resultado = servicio.files().list(
        q=f"'{carpeta_solicitudes}' in parents "
          f"and name = '{nombre_archivo}' "
          f"and trashed = false",
        spaces="drive",
        fields="files(id, name)"
    ).execute()

    archivos = resultado.get("files", [])

    if not archivos:
        return "Archivo no encontrado en Google Drive", 404

    archivo_drive = archivos[0]

    # =========================
    # ENVIAR ARCHIVO
    # =========================

    from googleapiclient.http import MediaIoBaseDownload
    import io

    request_drive = servicio.files().get_media(
        fileId=archivo_drive["id"]
    )

    archivo_memoria = io.BytesIO()

    downloader = MediaIoBaseDownload(
        archivo_memoria,
        request_drive
    )

    terminado = False

    while not terminado:

        _, terminado = downloader.next_chunk()

    archivo_memoria.seek(0)

    return send_file(
        archivo_memoria,
        download_name=archivo_drive["name"],
        as_attachment=False
    )

# =========================
# EDITAR SOLICITUD
# =========================

@app.route("/solicitudes/editar/<int:id>", methods=["GET", "POST"])
def editar_solicitud(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    solicitud = conexion.execute("""
        SELECT *
        FROM solicitudes
        WHERE id = ?
    """, (id,)).fetchone()

    if solicitud is None:
        conexion.close()
        return redirect(url_for("solicitudes"))

    # =========================
    # POST
    # =========================

    if request.method == "POST":

        codigo = request.form["codigo"].strip()
        solicitante = request.form["solicitante"].strip()
        tipo = request.form["tipo"].strip()
        asunto = request.form["asunto"].strip()
        fecha = request.form["fecha"].strip()
        estado = request.form["estado"].strip()
        descripcion = request.form["descripcion"].strip()

        # =========================
        # ARCHIVO ACTUAL
        # =========================

        archivo_actual = solicitud["archivo"]
        archivo_id_actual = solicitud["archivo_id"]

        # =========================
        # ARCHIVO NUEVO
        # =========================

        archivo_subido = request.files.get("archivo")

        nuevo_nombre_archivo = archivo_actual
        nuevo_archivo_id = archivo_id_actual

        # Indica si realmente se reemplazó
        archivo_reemplazado = False

        # =========================
        # SI SE SELECCIONÓ ARCHIVO
        # =========================

        if archivo_subido and archivo_subido.filename:

            nombre_original = secure_filename(
                archivo_subido.filename
            )

            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(
                delete=False
            ) as archivo_temporal:

                ruta_temporal = archivo_temporal.name

            archivo_subido.save(ruta_temporal)

            try:

                # =========================
                # CONECTAR CON GOOGLE DRIVE
                # =========================

                servicio = conectar_google_drive()

                # Obtener carpeta SOLICITUDES
                carpeta_solicitudes = obtener_carpeta_solicitudes(
                    servicio
                )

                # =========================
                # SUBIR NUEVO ARCHIVO
                # =========================

                archivo_drive = subir_archivo(
                    servicio,
                    ruta_temporal,
                    nombre_original,
                    carpeta_solicitudes
                )

                # =========================
                # OBTENER DATOS DEL NUEVO
                # =========================

                nuevo_nombre_archivo = archivo_drive.get(
                    "name"
                )

                nuevo_archivo_id = archivo_drive.get(
                    "id"
                )

                archivo_reemplazado = True

            finally:

                # =========================
                # ELIMINAR TEMPORAL
                # =========================

                if os.path.exists(ruta_temporal):

                    os.remove(ruta_temporal)

        # =========================
        # ACTUALIZAR BASE DE DATOS
        # =========================

        conexion.execute("""
            UPDATE solicitudes
            SET
                codigo = ?,
                solicitante = ?,
                tipo = ?,
                asunto = ?,
                fecha = ?,
                estado = ?,
                descripcion = ?,
                archivo = ?,
                archivo_id = ?
            WHERE id = ?
        """, (
            codigo,
            solicitante,
            tipo,
            asunto,
            fecha,
            estado,
            descripcion,
            nuevo_nombre_archivo,
            nuevo_archivo_id,
            id
        ))

        conexion.commit()
        conexion.close()

        # =========================
        # ELIMINAR ARCHIVO ANTERIOR
        # =========================

        if (
            archivo_reemplazado
            and archivo_id_actual
            and archivo_id_actual != nuevo_archivo_id
        ):

            try:

                servicio = conectar_google_drive()

                eliminar_archivo(
                    servicio,
                    archivo_id_actual
                )

            except Exception as error:

                print(
                    "No se pudo eliminar el archivo anterior:",
                    error
                )

        return redirect(
            url_for("solicitudes")
        )

    # =========================
    # GET
    # =========================

    conexion.close()

    return render_template(
        "editar_solicitud.html",
        solicitud=solicitud,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# ELIMINAR SOLICITUD
# =========================

@app.route("/solicitudes/eliminar/<int:id>", methods=["POST"])
def eliminar_solicitud(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    # Solo el administrador puede eliminar
    if session.get("rol") != "Administrador":
        return redirect(url_for("solicitudes"))

    conexion = conectar_bd()

    conexion.execute("""
        DELETE FROM solicitudes
        WHERE id = ?
    """, (id,))

    conexion.commit()
    conexion.close()

    return redirect(url_for("solicitudes"))

@app.route("/categorias/nueva", methods=["GET", "POST"])
def nueva_categoria():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "Administrador":
        return redirect(url_for("categorias"))

    if request.method == "POST":

        codigo = request.form["codigo"]
        categoria = request.form["categoria"]
        descripcion = request.form["descripcion"]

        conexion = conectar_bd()

        conexion.execute("""
            INSERT INTO categorias
            (codigo, categoria, descripcion)
            VALUES (?, ?, ?)
        """, (
            codigo,
            categoria,
            descripcion
        ))

        conexion.commit()
        conexion.close()

        return redirect(url_for("categorias"))

    return render_template(
        "nueva_categoria.html",
        usuario=session["usuario"],
        rol=session["rol"]
    )

@app.route("/categorias/editar/<int:id>", methods=["GET", "POST"])
def editar_categoria(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "Administrador":
        return redirect(url_for("categorias"))

    conexion = conectar_bd()

    categoria = conexion.execute(
        "SELECT * FROM categorias WHERE id = ?",
        (id,)
    ).fetchone()

    if categoria is None:
        conexion.close()
        return redirect(url_for("categorias"))

    if request.method == "POST":

        codigo = request.form["codigo"]
        nombre_categoria = request.form["categoria"]
        descripcion = request.form["descripcion"]

        conexion.execute("""
            UPDATE categorias
            SET codigo = ?,
                categoria = ?,
                descripcion = ?
            WHERE id = ?
        """, (
            codigo,
            nombre_categoria,
            descripcion,
            id
        ))

        conexion.commit()
        conexion.close()

        return redirect(url_for("categorias"))

    conexion.close()

    return render_template(
        "editar_categoria.html",
        categoria=categoria,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

@app.route("/categorias/eliminar/<int:id>", methods=["POST"])
def eliminar_categoria(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "Administrador":
        return redirect(url_for("categorias"))

    conexion = conectar_bd()

    conexion.execute(
        "DELETE FROM categorias WHERE id = ?",
        (id,)
    )

    conexion.commit()
    conexion.close()

    return redirect(url_for("categorias"))

# =========================
# VER DOCUMENTO
# =========================

@app.route("/documentos/ver/<int:id>")
def ver_documento(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    documento = conexion.execute(
        "SELECT * FROM documentos WHERE id = ?",
        (id,)
    ).fetchone()

    conexion.close()

    if documento is None:
        return "Documento no encontrado", 404

    return render_template(
        "ver_documento.html",
        documento=documento,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# ABRIR ARCHIVO DESDE DRIVE
# =========================

@app.route("/documentos/archivo/<archivo_id>")
def abrir_archivo(archivo_id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    try:

        servicio_drive = conectar_google_drive()

        contenido, nombre, mime_type = descargar_archivo(
            servicio_drive,
            archivo_id
        )

        return send_file(
            contenido,
            mimetype=mime_type,
            download_name=nombre,
            as_attachment=False
        )

    except Exception as e:

        print("ERROR GOOGLE DRIVE:", e)

        return "No se pudo abrir el archivo", 500

# =========================
# EDITAR DOCUMENTO
# =========================

@app.route("/documentos/editar/<int:id>", methods=["GET", "POST"])
def editar_documento(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    documento = conexion.execute(
        "SELECT * FROM documentos WHERE id = ?",
        (id,)
    ).fetchone()

    if documento is None:
        conexion.close()
        return "Documento no encontrado", 404

    if request.method == "POST":

        codigo = request.form["codigo"]
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        fecha = request.form["fecha"]
        descripcion = request.form["descripcion"]

        archivo_nuevo = request.files.get("archivo")

        # ==========================================
        # DATOS DEL ARCHIVO ACTUAL
        # ==========================================

        archivo_id_actual = documento["archivo"]
        nombre_archivo_actual = documento["nombre_archivo"]

        archivo_id_nuevo = archivo_id_actual
        nombre_archivo_nuevo = nombre_archivo_actual

        try:

            # ==========================================
            # SI SE SELECCIONÓ UN NUEVO ARCHIVO
            # ==========================================

            if archivo_nuevo and archivo_nuevo.filename:

                if not archivo_permitido(archivo_nuevo.filename):
                    conexion.close()
                    return "Tipo de archivo no permitido", 400

                # --------------------------------------
                # Guardar temporalmente
                # --------------------------------------

                extension = archivo_nuevo.filename.rsplit(
                    ".",
                    1
                )[1].lower()

                nombre_temporal = (
                    f"{uuid.uuid4().hex}.{extension}"
                )

                ruta_temporal = os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    nombre_temporal
                )

                archivo_nuevo.save(ruta_temporal)

                # --------------------------------------
                # Conectar con Google Drive
                # --------------------------------------

                servicio_drive = conectar_google_drive()

                carpeta = obtener_carpeta_categoria(
                    servicio_drive,
                    categoria
                )

                # --------------------------------------
                # Subir nuevo archivo
                # --------------------------------------

                archivo_drive = subir_archivo(
                    servicio_drive,
                    ruta_temporal,
                    archivo_nuevo.filename,
                    carpeta
                )

                archivo_id_nuevo = archivo_drive["id"]

                nombre_archivo_nuevo = (
                    archivo_nuevo.filename
                )

                # --------------------------------------
                # Eliminar archivo anterior de Drive
                # --------------------------------------

                if archivo_id_actual:

                    eliminar_archivo(
                        servicio_drive,
                        archivo_id_actual
                    )

                # --------------------------------------
                # Eliminar temporal de la PC
                # --------------------------------------

                if os.path.exists(ruta_temporal):

                    os.remove(ruta_temporal)

            # ==========================================
            # ACTUALIZAR SQLITE
            # ==========================================

            conexion.execute("""
                UPDATE documentos

                SET
                    codigo = ?,
                    nombre = ?,
                    categoria = ?,
                    fecha = ?,
                    descripcion = ?,
                    archivo = ?,
                    nombre_archivo = ?

                WHERE id = ?
            """, (
                codigo,
                nombre,
                categoria,
                fecha,
                descripcion,
                archivo_id_nuevo,
                nombre_archivo_nuevo,
                id
            ))

            conexion.commit()
            conexion.close()

            return redirect(
                url_for("documentos")
            )

        except Exception as e:

            conexion.close()

            print(
                "ERROR AL EDITAR DOCUMENTO:",
                e
            )

            return (
                "No se pudo editar el documento",
                500
            )

    # ==========================================
    # CATEGORÍAS
    # ==========================================

    conexion.close()

    conexion = conectar_bd()

    categorias = conexion.execute("""
        SELECT *
        FROM categorias
        ORDER BY categoria ASC
    """).fetchall()

    conexion.close()

    return render_template(
        "editar_documento.html",
        documento=documento,
        categorias=categorias,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# ELIMINAR DOCUMENTO
# =========================

@app.route("/documentos/eliminar/<int:id>", methods=["POST"])
def eliminar_documento(id):

    
    if "usuario" not in session:
        return redirect(url_for("login"))

    # Solo Administrador
    if session.get("rol") != "Administrador":
        return redirect(url_for("documentos"))

    conexion = conectar_bd()

    documento = conexion.execute(
        "SELECT * FROM documentos WHERE id = ?",
        (id,)
    ).fetchone()

    if documento is None:
        conexion.close()
        return "Documento no encontrado", 404

    archivo_id = documento["archivo"]

    try:

        # =========================================
        # ELIMINAR ARCHIVO DE GOOGLE DRIVE
        # =========================================

        if archivo_id:

            try:

                servicio_drive = conectar_google_drive()

                eliminar_archivo(
                    servicio_drive,
                    archivo_id
                )

                print(
                    "ARCHIVO ELIMINADO DE GOOGLE DRIVE:",
                    archivo_id
                )

            except Exception as e:

                print(
                    "AVISO: NO SE PUDO ELIMINAR "
                    "EL ARCHIVO DE GOOGLE DRIVE:",
                    e
                )

        # =========================================
        # ELIMINAR REGISTRO DE SQLITE
        # =========================================

        conexion.execute(
            "DELETE FROM documentos WHERE id = ?",
            (id,)
        )

        conexion.commit()
        conexion.close()

        print(
            "DOCUMENTO ELIMINADO CORRECTAMENTE:",
            id
        )

        return redirect(
            url_for("documentos")
        )

    except Exception as e:

        conexion.close()

        print(
            "ERROR AL ELIMINAR DOCUMENTO:",
            e
        )

        return (
            "No se pudo eliminar el documento",
            500
        )
    

# =========================
# ARCHIVOS PERMITIDOS
# =========================

EXTENSIONES_PERMITIDAS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "jpg",
    "jpeg",
    "png",
    "txt"
}


def archivo_permitido(nombre_archivo):

    return (
        "." in nombre_archivo
        and nombre_archivo.rsplit(".", 1)[1].lower()
        in EXTENSIONES_PERMITIDAS
    )

# =========================
# NUEVO DOCUMENTO
# =========================

@app.route("/documentos/nuevo", methods=["GET", "POST"])
def nuevo_documento():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        print("========== POST EDITAR DOCUMENTO ==========")
        print("ID:", id)
        print("DATOS:", request.form)
        print("ARCHIVO:", request.files.get("archivo"))

        codigo = request.form["codigo"]
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        fecha = request.form["fecha"]
        descripcion = request.form["descripcion"]

        usuario = session["usuario"]

        archivo = request.files.get("archivo")

        archivo_drive_id = None
        enlace_drive = None
        nombre_original = None

        # =====================================================
        # SUBIR ARCHIVO A GOOGLE DRIVE
        # =====================================================

        if archivo and archivo.filename:

            if not archivo_permitido(archivo.filename):

                return "Tipo de archivo no permitido", 400

            nombre_original = archivo.filename

            # -------------------------------------------------
            # Guardar temporalmente el archivo
            # -------------------------------------------------

            extension = ""

            if "." in archivo.filename:

                extension = (
                    archivo.filename
                    .rsplit(".", 1)[1]
                    .lower()
                )

            nombre_temporal = f"{uuid.uuid4().hex}.{extension}"

            ruta_temporal = os.path.join(
                app.config["UPLOAD_FOLDER"],
                nombre_temporal
            )

            archivo.save(ruta_temporal)

            try:

                # -------------------------------------------------
                # Conectar con Google Drive
                # -------------------------------------------------

                servicio_drive = conectar_google_drive()

                # -------------------------------------------------
                # Obtener / crear carpeta de categoría
                # -------------------------------------------------

                carpeta_id = obtener_carpeta_categoria(
                    servicio_drive,
                    categoria
                )

                # -------------------------------------------------
                # Subir archivo
                # -------------------------------------------------

                archivo_subido = subir_archivo(

                    servicio_drive,

                    ruta_temporal,

                    nombre_original,

                    carpeta_id
                )

                archivo_drive_id = archivo_subido["id"]

                enlace_drive = archivo_subido.get(
                    "webViewLink"
                )

            finally:

                # -------------------------------------------------
                # Eliminar archivo temporal del servidor
                # -------------------------------------------------

                if os.path.exists(ruta_temporal):

                    os.remove(ruta_temporal)

        # =====================================================
        # GUARDAR INFORMACIÓN EN SQLITE
        # =====================================================

        conexion = conectar_bd()

        conexion.execute("""
            INSERT INTO documentos
            (
                codigo,
                nombre,
                categoria,
                fecha,
                descripcion,
                archivo,
                usuario,
                nombre_archivo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            codigo,
            nombre,
            categoria,
            fecha,
            descripcion,
            archivo_drive_id,
            usuario,
            nombre_original
        ))

        conexion.commit()
        conexion.close()

        return redirect(
            url_for("documentos")
        )

    # =====================================================
    # CARGAR CATEGORÍAS
    # =====================================================

    conexion = conectar_bd()

    categorias = conexion.execute("""
        SELECT *
        FROM categorias
        ORDER BY categoria ASC
    """).fetchall()

    conexion.close()

    return render_template(
        "nuevo_documento.html",
        categorias=categorias,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================
# DOCENTE INVESTIGADORES
# =========================

# =========================================================
# INVESTIGADORES
# =========================================================

@app.route("/investigadores")
def investigadores():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    buscar = request.args.get("buscar", "").strip()
    tipo = request.args.get("tipo", "").strip()
    estado = request.args.get("estado", "").strip()

    consulta = """
        SELECT *
        FROM investigadores
        WHERE 1 = 1
    """

    parametros = []

    # =====================================================
    # BUSCADOR
    # =====================================================

    if buscar:

        consulta += """
            AND (
                nombre LIKE ?
                OR apellido LIKE ?
                OR ci LIKE ?
                OR correo LIKE ?
            )
        """

        termino = f"%{buscar}%"

        parametros.extend([
            termino,
            termino,
            termino,
            termino
        ])

    # =====================================================
    # FILTRO POR TIPO
    # =====================================================

    if tipo:

        consulta += """
            AND tipo = ?
        """

        parametros.append(tipo)

    # =====================================================
    # FILTRO POR ESTADO
    # =====================================================

    if estado in ("0", "1"):

        consulta += """
            AND estado = ?
        """

        parametros.append(int(estado))

    # =====================================================
    # ORDEN
    # =====================================================

    consulta += """
        ORDER BY apellido ASC, nombre ASC
    """

    investigadores = conexion.execute(
        consulta,
        parametros
    ).fetchall()

    conexion.close()

    return render_template(
        "investigadores.html",
        investigadores=investigadores,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# VER INVESTIGADOR
# =========================================================

@app.route("/investigadores/ver/<int:id>")
def ver_investigador(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    investigador = conexion.execute("""
        SELECT *
        FROM investigadores
        WHERE id = ?
    """, (id,)).fetchone()

    conexion.close()

    if investigador is None:
        return redirect(url_for("investigadores"))

    return render_template(
        "ver_investigador.html",
        investigador=investigador,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# NUEVO INVESTIGADOR
# =========================================================

@app.route("/investigadores/nuevo", methods=["GET", "POST"])
def nuevo_investigador():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        # =====================================================
        # DATOS PERSONALES
        # =====================================================

        nombre = request.form["nombre"].strip()
        apellido = request.form["apellido"].strip()
        tipo = request.form["tipo"].strip()

        ci = request.form.get("ci", "").strip()
        correo = request.form.get("correo", "").strip()
        telefono = request.form.get("telefono", "").strip()


        # =====================================================
        # DATOS INSTITUCIONALES
        # =====================================================

        carrera_area = request.form.get(
            "carrera_area", ""
        ).strip()

        cargo = request.form.get(
            "cargo", ""
        ).strip()

        facultad = request.form.get(
            "facultad", ""
        ).strip()

        institucion = request.form.get(
            "institucion", ""
        ).strip()

        grado_academico = request.form.get(
            "grado_academico", ""
        ).strip()

        especialidad = request.form.get(
            "especialidad", ""
        ).strip()


        # =====================================================
        # DATOS PARA ESTUDIANTES
        # =====================================================

        semestre = request.form.get(
            "semestre", ""
        ).strip()

        matricula = request.form.get(
            "matricula", ""
        ).strip()

        tutor = request.form.get(
            "tutor", ""
        ).strip()

        linea_investigacion = request.form.get(
            "linea_investigacion", ""
        ).strip()


        # =====================================================
        # IDENTIFICADORES CIENTÍFICOS
        # =====================================================

        orcid = request.form.get(
            "orcid", ""
        ).strip()

        google_scholar = request.form.get(
            "google_scholar", ""
        ).strip()

        scopus = request.form.get(
            "scopus", ""
        ).strip()

        researcher_id = request.form.get(
            "researcher_id", ""
        ).strip()


        # =====================================================
        # ESTADO
        # =====================================================

        estado_texto = request.form.get(
            "estado",
            "Activo"
        ).strip()

        if estado_texto == "Inactivo":
            estado = 0
        else:
            estado = 1


        # =====================================================
        # OBSERVACIONES
        # =====================================================

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()


        # =====================================================
        # GENERAR CÓDIGO DEL INVESTIGADOR
        # =====================================================

        conexion = conectar_bd()

        ultimo = conexion.execute("""
            SELECT codigo
            FROM investigadores
            WHERE codigo LIKE 'INV-%'
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()


        if ultimo and ultimo["codigo"]:

            try:
                numero = int(
                    ultimo["codigo"].replace("INV-", "")
                ) + 1

            except ValueError:
                numero = 1

        else:
            numero = 1


        codigo = f"INV-{numero:04d}"


        # =====================================================
        # GUARDAR INVESTIGADOR
        # =====================================================

        conexion.execute("""
            INSERT INTO investigadores (

                codigo,
                nombre,
                apellido,
                tipo,
                ci,
                correo,
                telefono,

                carrera,
                carrera_area,
                cargo,
                facultad,
                institucion,

                grado_academico,
                especialidad,
                perfil,

                orcid,
                google_scholar,
                scopus_id,
                scopus,
                researcher_id,

                semestre,
                matricula,
                tutor,
                linea_investigacion,

                estado,
                fotografia,
                observaciones,
                usuario

            )

            VALUES (

                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?,
                ?,
                ?, ?
            )

        """, (

            codigo,
            nombre,
            apellido,
            tipo,
            ci,
            correo,
            telefono,

            carrera_area,
            carrera_area,
            cargo,
            facultad,
            institucion,

            grado_academico,
            especialidad,
            "",

            orcid,
            google_scholar,
            scopus,
            scopus,
            researcher_id,

            semestre,
            matricula,
            tutor,
            linea_investigacion,

            estado,
            "",
            observaciones,
            session.get("usuario")
        ))


        conexion.commit()
        conexion.close()


        return redirect(
            url_for("investigadores")
        )


    return render_template(
        "nuevo_investigador.html",
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# EDITAR INVESTIGADOR
# =========================================================

@app.route("/investigadores/editar/<int:id>", methods=["GET", "POST"])
def editar_investigador(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    investigador = conexion.execute("""
        SELECT *
        FROM investigadores
        WHERE id = ?
    """, (id,)).fetchone()

    if investigador is None:
        conexion.close()
        return redirect(url_for("investigadores"))

    # =====================================================
    # GUARDAR CAMBIOS
    # =====================================================

    if request.method == "POST":

        nombre = request.form["nombre"].strip()
        apellido = request.form["apellido"].strip()
        tipo = request.form["tipo"].strip()

        ci = request.form.get("ci", "").strip()
        correo = request.form.get("correo", "").strip()
        telefono = request.form.get("telefono", "").strip()

        carrera_area = request.form.get(
            "carrera_area", ""
        ).strip()

        cargo = request.form.get(
            "cargo", ""
        ).strip()

        facultad = request.form.get(
            "facultad", ""
        ).strip()

        institucion = request.form.get(
            "institucion", ""
        ).strip()

        grado_academico = request.form.get(
            "grado_academico", ""
        ).strip()

        especialidad = request.form.get(
            "especialidad", ""
        ).strip()

        orcid = request.form.get(
            "orcid", ""
        ).strip()

        google_scholar = request.form.get(
            "google_scholar", ""
        ).strip()

        scopus = request.form.get(
            "scopus", ""
        ).strip()

        researcher_id = request.form.get(
            "researcher_id", ""
        ).strip()

        estado = int(request.form.get("estado", 1))

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()

        semestre = request.form.get(
            "semestre",
            ""
        ).strip()

        matricula = request.form.get(
            "matricula",
            ""
        ).strip()

        tutor = request.form.get(
            "tutor",
            ""
        ).strip()

        linea_investigacion = request.form.get(
            "linea_investigacion",
            ""
        ).strip()

        # =================================================
        # ACTUALIZAR
        # =================================================

        conexion.execute("""
            UPDATE investigadores
            SET
                nombre = ?,
                apellido = ?,
                tipo = ?,
                ci = ?,
                correo = ?,
                telefono = ?,
                carrera_area = ?,
                cargo = ?,
                facultad = ?,
                institucion = ?,
                grado_academico = ?,
                especialidad = ?,
                orcid = ?,
                google_scholar = ?,
                scopus = ?,
                researcher_id = ?,
                estado = ?,
                observaciones = ?,
                semestre = ?,
                matricula = ?,
                tutor = ?,
                linea_investigacion = ?
            WHERE id = ?
        """, (
            nombre,
            apellido,
            tipo,
            ci,
            correo,
            telefono,
            carrera_area,
            cargo,
            facultad,
            institucion,
            grado_academico,
            especialidad,
            orcid,
            google_scholar,
            scopus,
            researcher_id,
            estado,
            observaciones,
            semestre,
            matricula,
            tutor,
            linea_investigacion,
            id
        ))

        conexion.commit()
        conexion.close()

        return redirect(
            url_for("investigadores")
        )

    # =====================================================
    # MOSTRAR FORMULARIO
    # =====================================================

    conexion.close()

    return render_template(
        "editar_investigador.html",
        investigador=investigador,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# ACTIVAR / DESACTIVAR INVESTIGADOR
# =========================================================

@app.route("/investigadores/eliminar/<int:id>")
def eliminar_investigador(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    investigador = conexion.execute("""
        SELECT estado
        FROM investigadores
        WHERE id = ?
    """, (id,)).fetchone()

    if investigador is None:
        conexion.close()
        return redirect(url_for("investigadores"))

    # =====================================================
    # CAMBIAR ESTADO
    # =====================================================

    if investigador["estado"] == 1:
        nuevo_estado = 0
    else:
        nuevo_estado = 1

    conexion.execute("""
        UPDATE investigadores
        SET estado = ?
        WHERE id = ?
    """, (nuevo_estado, id))

    conexion.commit()
    conexion.close()

    return redirect(url_for("investigadores"))

# =========================================================
# ELIMINAR DEFINITIVAMENTE INVESTIGADOR
# =========================================================

@app.route("/investigadores/eliminar-definitivo/<int:id>", methods=["POST"])
def eliminar_definitivo_investigador(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    investigador = conexion.execute("""
        SELECT id
        FROM investigadores
        WHERE id = ?
    """, (id,)).fetchone()

    if investigador is None:
        conexion.close()
        return redirect(url_for("investigadores"))

    conexion.execute("""
        DELETE FROM investigadores
        WHERE id = ?
    """, (id,))

    conexion.commit()
    conexion.close()

    return redirect(url_for("investigadores"))

# =========================================================
# ARTÍCULOS
# =========================================================

@app.route("/articulos")
def articulos():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    buscar = request.args.get("buscar", "").strip()
    anio = request.args.get("anio", "").strip()
    estado = request.args.get("estado", "").strip()

    consulta = """
        SELECT
            a.*,
            r.nombre AS revista_nombre
        FROM articulos a
        LEFT JOIN revistas r
            ON a.revista_id = r.id
        WHERE 1 = 1
    """

    parametros = []

    # =====================================================
    # BUSCADOR
    # =====================================================

    if buscar:

        consulta += """
            AND (
                a.codigo LIKE ?
                OR a.titulo LIKE ?
                OR a.doi LIKE ?
                OR a.issn LIKE ?
            )
        """

        termino = f"%{buscar}%"

        parametros.extend([
            termino,
            termino,
            termino,
            termino
        ])

    # =====================================================
    # FILTRO POR AÑO
    # =====================================================

    if anio:

        consulta += """
            AND a.anio = ?
        """

        parametros.append(anio)

    # =====================================================
    # FILTRO POR ESTADO
    # =====================================================

    if estado in ("0", "1"):

        consulta += """
            AND a.estado = ?
        """

        parametros.append(int(estado))

    # =====================================================
    # ORDEN
    # =====================================================

    consulta += """
        ORDER BY a.anio DESC, a.titulo ASC
    """

    articulos = conexion.execute(
        consulta,
        parametros
    ).fetchall()

    conexion.close()

    return render_template(
        "articulos.html",
        articulos=articulos,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )


# =========================================================
# VER ARTÍCULO
# =========================================================

@app.route("/articulos/ver/<int:id>")
def ver_articulo(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # OBTENER ARTÍCULO Y REVISTA
    # =====================================================

    articulo = conexion.execute("""
        SELECT
            articulos.*,
            revistas.nombre AS revista_nombre,
            revistas.codigo AS revista_codigo
        FROM articulos

        LEFT JOIN revistas
            ON articulos.revista_id = revistas.id

        WHERE articulos.id = ?
    """, (id,)).fetchone()

    if articulo is None:
        conexion.close()

        return redirect(
            url_for("articulos")
        )

    # =====================================================
    # OBTENER INFORMACIÓN DEL ARCHIVO DE GOOGLE DRIVE
    # =====================================================

    nombre_archivo = None
    enlace_archivo = None

    if articulo["archivo"]:

        try:

            servicio_drive = conectar_google_drive()

            informacion_archivo = servicio_drive.files().get(
                fileId=articulo["archivo"],
                fields="name,webViewLink"
            ).execute()

            nombre_archivo = informacion_archivo.get("name")
            enlace_archivo = informacion_archivo.get("webViewLink")

        except Exception as e:

            print("ERROR AL OBTENER ARCHIVO DE GOOGLE DRIVE:", e)

    # =====================================================
    # OBTENER INVESTIGADORES / AUTORES
    # =====================================================

    investigadores = conexion.execute("""
        SELECT
            investigadores.id,
            investigadores.codigo,
            investigadores.nombre,
            investigadores.apellido,
            articulo_investigadores.orden_autor

        FROM articulo_investigadores

        INNER JOIN investigadores
            ON articulo_investigadores.investigador_id =
               investigadores.id

        WHERE articulo_investigadores.articulo_id = ?

        ORDER BY articulo_investigadores.orden_autor ASC
    """, (id,)).fetchall()

    conexion.close()

    # =====================================================
    # MOSTRAR ARTÍCULO
    # =====================================================

    return render_template(
        "ver_articulo.html",

        articulo=articulo,

        investigadores=investigadores,

        nombre_archivo=nombre_archivo,

        enlace_archivo=enlace_archivo,

        usuario=session.get("usuario"),

        rol=session.get("rol")
    )


# =========================================================
# EDITAR ARTÍCULO
# =========================================================

@app.route("/articulos/editar/<int:id>", methods=["GET", "POST"])
def editar_articulo(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # OBTENER ARTÍCULO
    # =====================================================

    articulo = conexion.execute("""
        SELECT *
        FROM articulos
        WHERE id = ?
    """, (id,)).fetchone()

    if articulo is None:

        conexion.close()

        return redirect(
            url_for("articulos")
        )

    # =====================================================
    # GUARDAR CAMBIOS
    # =====================================================

    if request.method == "POST":

        titulo = request.form.get(
            "titulo", ""
        ).strip()

        resumen = request.form.get(
            "resumen", ""
        ).strip()

        palabras_clave = request.form.get(
            "palabras_clave", ""
        ).strip()

        fecha_publicacion = request.form.get(
            "fecha_publicacion", ""
        ).strip()

        anio = request.form.get(
            "anio", ""
        ).strip()

        revista_id = request.form.get(
            "revista_id", ""
        ).strip()

        volumen = request.form.get(
            "volumen", ""
        ).strip()

        numero = request.form.get(
            "numero", ""
        ).strip()

        paginas = request.form.get(
            "paginas", ""
        ).strip()

        doi = request.form.get(
            "doi", ""
        ).strip()

        issn = request.form.get(
            "issn", ""
        ).strip()

        url = request.form.get(
            "url", ""
        ).strip()

        observaciones = request.form.get(
            "observaciones", ""
        ).strip()

        # =================================================
        # ESTADO
        # =================================================

        estado = int(
            request.form.get(
                "estado",
                articulo["estado"]
            )
        )

        # =================================================
        # REVISTA
        # =================================================

        if revista_id:
            revista_id = int(revista_id)
        else:
            revista_id = None

        # =================================================
        # ARCHIVO
        # =================================================

        archivo_anterior = articulo["archivo"]
        archivo_nuevo_id = None
        ruta_temporal = None

        archivo = archivo_anterior

        archivo_subido = request.files.get(
            "archivo"
        )

        try:

            # =============================================
            # SI SE SELECCIONÓ UN NUEVO ARCHIVO
            # =============================================

            if archivo_subido and archivo_subido.filename:

                servicio_drive = conectar_google_drive()

                carpeta_articulos = obtener_carpeta_articulos(
                    servicio_drive
                )

                # -----------------------------------------
                # CARPETA TEMPORAL
                # -----------------------------------------

                carpeta_temporal = os.path.join(
                    os.getcwd(),
                    "temp"
                )

                os.makedirs(
                    carpeta_temporal,
                    exist_ok=True
                )

                archivo_nombre = archivo_subido.filename

                ruta_temporal = os.path.join(
                    carpeta_temporal,
                    archivo_nombre
                )

                archivo_subido.save(
                    ruta_temporal
                )

                # -----------------------------------------
                # SUBIR NUEVO ARCHIVO A GOOGLE DRIVE
                # -----------------------------------------

                archivo_drive = subir_archivo(
                    servicio_drive,
                    ruta_temporal,
                    archivo_nombre,
                    carpeta_articulos
                )

                archivo_nuevo_id = archivo_drive.get("id")

                if not archivo_nuevo_id:
                    raise Exception(
                        "Google Drive no devolvió el ID del archivo."
                    )

                # El campo archivo ahora guarda
                # el ID de Google Drive

                archivo = archivo_nuevo_id

                # -----------------------------------------
                # ELIMINAR ARCHIVO TEMPORAL
                # -----------------------------------------

                if os.path.exists(ruta_temporal):

                    os.remove(
                        ruta_temporal
                    )

                    ruta_temporal = None

            # =================================================
            # ACTUALIZAR ARTÍCULO
            # =================================================

            conexion.execute("""
                UPDATE articulos
                SET
                    titulo = ?,
                    resumen = ?,
                    palabras_clave = ?,
                    fecha_publicacion = ?,
                    anio = ?,
                    revista_id = ?,
                    volumen = ?,
                    numero = ?,
                    paginas = ?,
                    doi = ?,
                    issn = ?,
                    url = ?,
                    archivo = ?,
                    estado = ?,
                    observaciones = ?
                WHERE id = ?
            """, (
                titulo,
                resumen,
                palabras_clave,
                fecha_publicacion,
                int(anio),
                revista_id,
                volumen,
                numero,
                paginas,
                doi,
                issn,
                url,
                archivo,
                estado,
                observaciones,
                id
            ))

            # =================================================
            # ACTUALIZAR INVESTIGADORES / AUTORES
            # =================================================

            investigadores_ids = request.form.getlist(
                "investigadores"
            )

            # -----------------------------------------------
            # ELIMINAR AUTORES ANTERIORES
            # -----------------------------------------------

            conexion.execute("""
                DELETE FROM articulo_investigadores
                WHERE articulo_id = ?
            """, (id,))

            # -----------------------------------------------
            # REGISTRAR NUEVAMENTE LOS AUTORES
            # -----------------------------------------------

            for posicion, investigador_id in enumerate(
                investigadores_ids,
                start=1
            ):

                conexion.execute("""
                    INSERT INTO articulo_investigadores (
                        articulo_id,
                        investigador_id,
                        orden_autor
                    )
                    VALUES (?, ?, ?)
                """, (
                    id,
                    int(investigador_id),
                    posicion
                ))

            # =================================================
            # AUDITORÍA
            # =================================================

            conexion.execute("""
                INSERT INTO auditoria (
                    usuario,
                    accion,
                    modulo,
                    registro_id,
                    descripcion,
                    fecha
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                session.get("usuario"),
                "EDITAR",
                "ARTÍCULOS",
                id,
                f"Se modificó el artículo {articulo['codigo']} - {titulo}"
            ))

            # =================================================
            # CONFIRMAR CAMBIOS EN SQLITE
            # =================================================

            conexion.commit()

            # =================================================
            # ELIMINAR ARCHIVO ANTERIOR DE GOOGLE DRIVE
            # =================================================
            # Esto se hace SOLO después de que SQLite
            # confirmó correctamente los cambios.

            if archivo_nuevo_id and archivo_anterior:

                try:

                    eliminar_archivo(
                        servicio_drive,
                        archivo_anterior
                    )

                except Exception as e:

                    print(
                        "ADVERTENCIA: No se pudo eliminar "
                        "el archivo anterior de Google Drive:",
                        e
                    )

            conexion.close()

            return redirect(
                url_for("articulos")
            )

        except Exception as e:

            print(
                "ERROR AL EDITAR ARTÍCULO:",
                e
            )

            conexion.rollback()

            # =============================================
            # SI SE SUBIÓ UN ARCHIVO NUEVO PERO ALGO FALLÓ
            # =============================================

            if archivo_nuevo_id:

                try:

                    servicio_drive = conectar_google_drive()

                    eliminar_archivo(
                        servicio_drive,
                        archivo_nuevo_id
                    )

                    print(
                        "Archivo nuevo eliminado de Google Drive "
                        "porque la edición falló."
                    )

                except Exception as error_drive:

                    print(
                        "ERROR AL ELIMINAR ARCHIVO NUEVO:",
                        error_drive
                    )

            # =============================================
            # ELIMINAR ARCHIVO TEMPORAL SI QUEDÓ
            # =============================================

            if ruta_temporal and os.path.exists(
                ruta_temporal
            ):

                try:

                    os.remove(
                        ruta_temporal
                    )

                except Exception:
                    pass

            conexion.close()

            return redirect(
                url_for("editar_articulo", id=id)
            )

    # =====================================================
    # DATOS PARA EL FORMULARIO
    # =====================================================

    revistas = conexion.execute("""
        SELECT
            id,
            codigo,
            nombre
        FROM revistas
        WHERE estado = 1
        ORDER BY nombre ASC
    """).fetchall()

    investigadores = conexion.execute("""
        SELECT
            id,
            codigo,
            nombre,
            apellido,
            tipo
        FROM investigadores
        WHERE estado = 1
        ORDER BY
            apellido COLLATE NOCASE ASC,
            nombre COLLATE NOCASE ASC
    """).fetchall()

    # =====================================================
    # AUTORES ACTUALES
    # =====================================================

    autores_actuales = conexion.execute("""
        SELECT investigador_id
        FROM articulo_investigadores
        WHERE articulo_id = ?
        ORDER BY orden_autor ASC
    """, (id,)).fetchall()

    autores_ids = [
        autor["investigador_id"]
        for autor in autores_actuales
    ]

    # =====================================================
    # NOMBRE REAL DEL ARCHIVO EN GOOGLE DRIVE
    # =====================================================

    nombre_archivo = None
    enlace_archivo = None

    if articulo["archivo"]:

        try:

            servicio_drive = conectar_google_drive()

            informacion_archivo = servicio_drive.files().get(
                fileId=articulo["archivo"],
                fields="name,webViewLink"
            ).execute()

            nombre_archivo = informacion_archivo.get(
                "name"
            )

            enlace_archivo = informacion_archivo.get(
                "webViewLink"
            )

        except Exception as e:

            print(
                "ERROR AL OBTENER ARCHIVO DE GOOGLE DRIVE:",
                e
            )

    conexion.close()

    return render_template(
        "editar_articulo.html",
        articulo=articulo,
        revistas=revistas,
        investigadores=investigadores,
        autores_ids=autores_ids,
        nombre_archivo=nombre_archivo,
        enlace_archivo=enlace_archivo,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# ELIMINAR ARTÍCULO
# =========================================================

@app.route("/articulos/eliminar/<int:id>", methods=["POST"])
def eliminar_articulo(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # OBTENER ARTÍCULO
    # =====================================================

    articulo = conexion.execute("""
        SELECT
            id,
            codigo,
            titulo,
            archivo
        FROM articulos
        WHERE id = ?
    """, (id,)).fetchone()

    if articulo is None:

        conexion.close()

        return redirect(
            url_for("articulos")
        )

    archivo_drive_id = articulo["archivo"]

    try:

        # =================================================
        # ELIMINAR AUTORES RELACIONADOS
        # =================================================

        conexion.execute("""
            DELETE FROM articulo_investigadores
            WHERE articulo_id = ?
        """, (id,))

        # =================================================
        # ELIMINAR ARTÍCULO
        # =================================================

        conexion.execute("""
            DELETE FROM articulos
            WHERE id = ?
        """, (id,))

        # =================================================
        # AUDITORÍA
        # =================================================

        conexion.execute("""
            INSERT INTO auditoria (
                usuario,
                accion,
                modulo,
                registro_id,
                descripcion,
                fecha
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (
            session.get("usuario"),
            "ELIMINAR",
            "ARTÍCULOS",
            id,
            f"Se eliminó el artículo "
            f"{articulo['codigo']} - {articulo['titulo']}"
        ))

        # =================================================
        # CONFIRMAR ELIMINACIÓN EN SQLITE
        # =================================================

        conexion.commit()

        print(
            f"Artículo eliminado correctamente: "
            f"{articulo['codigo']} - {articulo['titulo']}"
        )

    except Exception as e:

        print(
            "ERROR AL ELIMINAR ARTÍCULO:",
            e
        )

        conexion.rollback()
        conexion.close()

        return redirect(
            url_for("articulos")
        )

    conexion.close()

    # =====================================================
    # ELIMINAR ARCHIVO DE GOOGLE DRIVE
    # =====================================================

    if archivo_drive_id:

        try:

            servicio_drive = conectar_google_drive()

            eliminar_archivo(
                servicio_drive,
                archivo_drive_id
            )

            print(
                "Archivo eliminado correctamente "
                "de Google Drive."
            )

        except Exception as e:

            print(
                "ADVERTENCIA: El artículo fue eliminado "
                "de la base de datos, pero no se pudo "
                "eliminar el archivo de Google Drive:",
                e
            )

    return redirect(
        url_for("articulos")
    )


# =========================================================

# NUEVO ARTÍCULO

# =========================================================

@app.route("/articulos/nuevo", methods=["GET", "POST"])
def nuevo_articulo():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # GUARDAR ARTÍCULO
    # =====================================================

    if request.method == "POST":

        titulo = request.form.get(
            "titulo",
            ""
        ).strip()

        resumen = request.form.get(
            "resumen",
            ""
        ).strip()

        palabras_clave = request.form.get(
            "palabras_clave",
            ""
        ).strip()

        fecha_publicacion = request.form.get(
            "fecha_publicacion",
            ""
        ).strip()

        anio = request.form.get(
            "anio",
            ""
        ).strip()

        revista_id = request.form.get(
            "revista_id",
            ""
        ).strip()

        volumen = request.form.get(
            "volumen",
            ""
        ).strip()

        numero = request.form.get(
            "numero",
            ""
        ).strip()

        paginas = request.form.get(
            "paginas",
            ""
        ).strip()

        doi = request.form.get(
            "doi",
            ""
        ).strip()

        issn = request.form.get(
            "issn",
            ""
        ).strip()

        url = request.form.get(
            "url",
            ""
        ).strip()

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()

        # =================================================
        # ESTADO
        # =================================================

        estado = int(
            request.form.get(
                "estado",
                1
            )
        )

        # =================================================
        # GENERAR CÓDIGO
        # =================================================

        ultimo = conexion.execute("""
            SELECT codigo
            FROM articulos
            WHERE codigo LIKE 'ART-%'
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if ultimo and ultimo["codigo"]:

            try:

                numero_codigo = int(
                    ultimo["codigo"].replace(
                        "ART-",
                        ""
                    )
                ) + 1

            except ValueError:

                numero_codigo = 1

        else:

            numero_codigo = 1

        codigo = f"ART-{numero_codigo:04d}"

        # =================================================
        # REVISTA
        # =================================================

        if revista_id:

            revista_id = int(
                revista_id
            )

        else:

            revista_id = None

        # =================================================
        # INVESTIGADORES / AUTORES
        # =================================================

        investigadores_seleccionados = request.form.getlist(
            "investigadores"
        )

        investigadores_ids = []

        for investigador_id in investigadores_seleccionados:

            try:

                investigador_id = int(
                    investigador_id
                )

                investigadores_ids.append(
                    investigador_id
                )

            except ValueError:

                pass

        # =================================================
        # ARCHIVO
        # =================================================

        archivo_subido = request.files.get(
            "archivo"
        )

        archivo_id = None

        archivo_nombre = None

        ruta_temporal = None

        # =================================================
        # PROCESO
        # =================================================

        try:

            # =================================================
            # SUBIR ARCHIVO A GOOGLE DRIVE
            # =================================================

            if archivo_subido and archivo_subido.filename:

                print(
                    "Subiendo archivo del artículo a Google Drive..."
                )

                # ---------------------------------------------
                # CONECTAR CON GOOGLE DRIVE
                # ---------------------------------------------

                servicio_drive = conectar_google_drive()

                # ---------------------------------------------
                # OBTENER CARPETA ARTÍCULOS
                # ---------------------------------------------

                carpeta_articulos = obtener_carpeta_articulos(
                    servicio_drive
                )

                print(
                    "Carpeta de artículos:",
                    carpeta_articulos
                )

                # ---------------------------------------------
                # CARPETA TEMPORAL
                # ---------------------------------------------

                carpeta_temporal = os.path.join(
                    os.getcwd(),
                    "temp"
                )

                os.makedirs(
                    carpeta_temporal,
                    exist_ok=True
                )

                # ---------------------------------------------
                # NOMBRE DEL ARCHIVO
                # ---------------------------------------------

                archivo_nombre = (
                    archivo_subido.filename
                )

                ruta_temporal = os.path.join(
                    carpeta_temporal,
                    archivo_nombre
                )

                # ---------------------------------------------
                # GUARDAR TEMPORALMENTE
                # ---------------------------------------------

                archivo_subido.save(
                    ruta_temporal
                )

                # ---------------------------------------------
                # SUBIR A GOOGLE DRIVE
                # ---------------------------------------------

                archivo_drive = subir_archivo(
                    servicio_drive,
                    ruta_temporal,
                    archivo_nombre,
                    carpeta_articulos
                )

                archivo_id = archivo_drive.get(
                    "id"
                )

                print(
                    "Archivo del artículo subido correctamente:",
                    archivo_id
                )

                print(
                    "Nombre guardado en Drive:",
                    archivo_nombre
                )

                # ---------------------------------------------
                # ELIMINAR TEMPORAL
                # ---------------------------------------------

                if os.path.exists(
                    ruta_temporal
                ):

                    os.remove(
                        ruta_temporal
                    )

                    ruta_temporal = None

            # =================================================
            # INSERTAR ARTÍCULO
            # =================================================

            cursor = conexion.execute("""
                INSERT INTO articulos (
                    codigo,
                    titulo,
                    resumen,
                    palabras_clave,
                    fecha_publicacion,
                    anio,
                    revista_id,
                    volumen,
                    numero,
                    paginas,
                    doi,
                    issn,
                    url,
                    archivo,
                    estado,
                    observaciones,
                    usuario
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
            """, (
                codigo,
                titulo,
                resumen,
                palabras_clave,
                fecha_publicacion,
                int(anio),
                revista_id,
                volumen,
                numero,
                paginas,
                doi,
                issn,
                url,
                archivo_id,
                estado,
                observaciones,
                session.get("usuario")
            ))

            articulo_id = cursor.lastrowid

            print(
                "Artículo registrado con ID:",
                articulo_id
            )

            # =================================================
            # GUARDAR INVESTIGADORES / AUTORES
            # =================================================

            for posicion, investigador_id in enumerate(
                investigadores_ids,
                start=1
            ):

                conexion.execute("""
                    INSERT INTO articulo_investigadores (
                        articulo_id,
                        investigador_id,
                        orden_autor
                    )
                    VALUES (?, ?, ?)
                """, (
                    articulo_id,
                    investigador_id,
                    posicion
                ))

                print(
                    f"Investigador {investigador_id} "
                    f"asociado al artículo {articulo_id} "
                    f"como autor {posicion}"
                )

            # =================================================
            # AUDITORÍA
            # =================================================

            conexion.execute("""
                INSERT INTO auditoria (
                    usuario,
                    accion,
                    modulo,
                    registro_id,
                    descripcion,
                    fecha
                )
                VALUES (
                    ?, ?, ?, ?, ?, datetime('now')
                )
            """, (
                session.get("usuario"),
                "CREAR",
                "ARTÍCULOS",
                articulo_id,
                f"Se registró el artículo {codigo} - {titulo}"
            ))

            # =================================================
            # CONFIRMAR CAMBIOS
            # =================================================

            conexion.commit()

            print(
                "Artículo registrado correctamente:",
                codigo
            )

            print(
                "Investigadores asociados:",
                len(investigadores_ids)
            )

        # =====================================================
        # ERROR DE INTEGRIDAD
        # =====================================================

        except sqlite3.IntegrityError as e:

            conexion.rollback()

            print(
                "ERROR DE INTEGRIDAD AL REGISTRAR ARTÍCULO:",
                e
            )

            # ---------------------------------------------
            # ELIMINAR ARCHIVO DE DRIVE
            # ---------------------------------------------

            if archivo_id:

                try:

                    servicio_drive = conectar_google_drive()

                    eliminar_archivo(
                        servicio_drive,
                        archivo_id
                    )

                    print(
                        "Archivo eliminado de Drive por error."
                    )

                except Exception as error_drive:

                    print(
                        "No se pudo eliminar el archivo de Drive:",
                        error_drive
                    )

            revistas = conexion.execute("""
                SELECT id, codigo, nombre
                FROM revistas
                WHERE estado = 1
                ORDER BY nombre ASC
            """).fetchall()

            investigadores = conexion.execute("""
                SELECT
                    id,
                    codigo,
                    nombre,
                    apellido,
                    tipo
                FROM investigadores
                WHERE estado = 1
                ORDER BY
                    apellido COLLATE NOCASE ASC,
                    nombre COLLATE NOCASE ASC
            """).fetchall()

            return render_template(
                "nuevo_articulo.html",
                revistas=revistas,
                investigadores=investigadores,
                error="No se pudo registrar el artículo. Verifique los datos ingresados.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # =====================================================
        # OTRO ERROR
        # =====================================================

        except Exception as e:

            conexion.rollback()

            print(
                "ERROR AL REGISTRAR ARTÍCULO:",
                e
            )

            # ---------------------------------------------
            # ELIMINAR ARCHIVO DE DRIVE
            # ---------------------------------------------

            if archivo_id:

                try:

                    servicio_drive = conectar_google_drive()

                    eliminar_archivo(
                        servicio_drive,
                        archivo_id
                    )

                    print(
                        "Archivo eliminado de Drive por error."
                    )

                except Exception as error_drive:

                    print(
                        "No se pudo eliminar el archivo de Drive:",
                        error_drive
                    )

            revistas = conexion.execute("""
                SELECT id, codigo, nombre
                FROM revistas
                WHERE estado = 1
                ORDER BY nombre ASC
            """).fetchall()

            investigadores = conexion.execute("""
                SELECT
                    id,
                    codigo,
                    nombre,
                    apellido,
                    tipo
                FROM investigadores
                WHERE estado = 1
                ORDER BY
                    apellido COLLATE NOCASE ASC,
                    nombre COLLATE NOCASE ASC
            """).fetchall()

            return render_template(
                "nuevo_articulo.html",
                revistas=revistas,
                investigadores=investigadores,
                error=f"No se pudo registrar el artículo: {e}",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        finally:

            # =================================================
            # ELIMINAR ARCHIVO TEMPORAL
            # =================================================

            if ruta_temporal:

                try:

                    if os.path.exists(
                        ruta_temporal
                    ):

                        os.remove(
                            ruta_temporal
                        )

                except:

                    pass

            # =================================================
            # CERRAR CONEXIÓN
            # =================================================

            try:

                conexion.close()

            except:

                pass

        # =================================================
        # VOLVER AL LISTADO
        # =================================================

        return redirect(
            url_for("articulos")
        )

    # =====================================================
    # DATOS PARA EL FORMULARIO
    # =====================================================

    revistas = conexion.execute("""
        SELECT
            id,
            codigo,
            nombre
        FROM revistas
        WHERE estado = 1
        ORDER BY nombre ASC
    """).fetchall()

    investigadores = conexion.execute("""
        SELECT
            id,
            codigo,
            nombre,
            apellido,
            tipo
        FROM investigadores
        WHERE estado = 1
        ORDER BY
            apellido COLLATE NOCASE ASC,
            nombre COLLATE NOCASE ASC
    """).fetchall()

    conexion.close()

    return render_template(
        "nuevo_articulo.html",
        revistas=revistas,
        investigadores=investigadores,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# REVISTAS - LISTADO
# =========================================================

@app.route("/revistas")
def revistas():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    buscar = request.args.get("buscar", "").strip()
    estado = request.args.get("estado", "").strip()

    consulta = """
        SELECT *
        FROM revistas
        WHERE 1=1
    """

    parametros = []

    # Buscar por código, nombre, ISSN, editorial o institución
    if buscar:
        consulta += """
            AND (
                codigo LIKE ?
                OR nombre LIKE ?
                OR issn LIKE ?
                OR issn_electronico LIKE ?
                OR editorial LIKE ?
                OR institucion LIKE ?
            )
        """

        termino = f"%{buscar}%"

        parametros.extend([
            termino,
            termino,
            termino,
            termino,
            termino,
            termino
        ])

    # Filtro por estado
    if estado in ("0", "1"):
        consulta += " AND estado = ?"
        parametros.append(int(estado))

    consulta += """
        ORDER BY nombre ASC
    """

    revistas = conexion.execute(
        consulta,
        parametros
    ).fetchall()

    conexion.close()

    return render_template(
        "revistas.html",
        revistas=revistas,
        buscar=buscar,
        estado=estado,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# NUEVA REVISTA
# =========================================================

@app.route("/revistas/nueva", methods=["GET", "POST"])
def nueva_revista():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        # -------------------------------------------------
        # DATOS DEL FORMULARIO
        # -------------------------------------------------

        codigo = request.form.get(
            "codigo",
            ""
        ).strip()

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        issn = request.form.get(
            "issn",
            ""
        ).strip()

        issn_electronico = request.form.get(
            "issn_electronico",
            ""
        ).strip()

        editorial = request.form.get(
            "editorial",
            ""
        ).strip()

        institucion = request.form.get(
            "institucion",
            ""
        ).strip()

        pais = request.form.get(
            "pais",
            ""
        ).strip()

        ciudad = request.form.get(
            "ciudad",
            ""
        ).strip()

        periodicidad = request.form.get(
            "periodicidad",
            ""
        ).strip()

        area_tematica = request.form.get(
            "area_tematica",
            ""
        ).strip()

        url = request.form.get(
            "url",
            ""
        ).strip()

        doi = request.form.get(
            "doi",
            ""
        ).strip()

        indexacion = request.form.get(
            "indexacion",
            ""
        ).strip()

        fecha_inicio = request.form.get(
            "fecha_inicio",
            ""
        ).strip()

        estado = request.form.get(
            "estado",
            "1"
        ).strip()

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()

        usuario = session["usuario"]

        # -------------------------------------------------
        # ARCHIVO
        # -------------------------------------------------

        archivo_subido = request.files.get("archivo")

        # -------------------------------------------------
        # VALIDACIONES
        # -------------------------------------------------

        if not codigo:

            flash(
                "El código de la revista es obligatorio.",
                "error"
            )

            return render_template(
                "nueva_revista.html",
                revista=request.form,
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        if not nombre:

            flash(
                "El nombre de la revista es obligatorio.",
                "error"
            )

            return render_template(
                "nueva_revista.html",
                revista=request.form,
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # -------------------------------------------------
        # CONEXIÓN BASE DE DATOS
        # -------------------------------------------------

        conexion = conectar_bd()

        # -------------------------------------------------
        # VERIFICAR CÓDIGO DUPLICADO
        # -------------------------------------------------

        existente = conexion.execute("""
            SELECT id
            FROM revistas
            WHERE codigo = ?
        """, (codigo,)).fetchone()

        if existente:

            conexion.close()

            flash(
                "Ya existe una revista registrada con ese código.",
                "error"
            )

            return render_template(
                "nueva_revista.html",
                revista=request.form,
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # -------------------------------------------------
        # DATOS DEL ARCHIVO EN GOOGLE DRIVE
        # -------------------------------------------------

        archivo_drive_id = None
        nombre_archivo = None

        # -------------------------------------------------
        # SUBIR ARCHIVO SI EXISTE
        # -------------------------------------------------

        if archivo_subido and archivo_subido.filename:

            ruta_temporal = None

            try:

                # -----------------------------------------
                # CREAR ARCHIVO TEMPORAL
                # -----------------------------------------

                extension = os.path.splitext(
                    archivo_subido.filename
                )[1]

                archivo_temporal = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=extension
                )

                ruta_temporal = archivo_temporal.name

                archivo_temporal.close()

                # -----------------------------------------
                # GUARDAR ARCHIVO TEMPORALMENTE
                # -----------------------------------------

                archivo_subido.save(
                    ruta_temporal
                )

                # -----------------------------------------
                # CONECTAR CON GOOGLE DRIVE
                # -----------------------------------------

                servicio = conectar_google_drive()

                # -----------------------------------------
                # OBTENER CARPETA REVISTAS
                # -----------------------------------------

                carpeta_revistas = obtener_carpeta_revistas(
                    servicio
                )

                # -----------------------------------------
                # SUBIR ARCHIVO
                # -----------------------------------------

                archivo_drive = subir_archivo(

                    servicio,

                    ruta_temporal,

                    archivo_subido.filename,

                    carpeta_revistas

                )

                archivo_drive_id = archivo_drive["id"]
                nombre_archivo = archivo_subido.filename

            except Exception as e:

                conexion.close()

                flash(
                    f"No se pudo subir el archivo a Google Drive: {e}",
                    "error"
                )

                return render_template(
                    "nueva_revista.html",
                    revista=request.form,
                    usuario=session.get("usuario"),
                    rol=session.get("rol")
                )

            finally:

                # -----------------------------------------
                # ELIMINAR ARCHIVO TEMPORAL
                # -----------------------------------------

                if ruta_temporal and os.path.exists(
                    ruta_temporal
                ):

                    os.remove(
                        ruta_temporal
                    )

        # -------------------------------------------------
        # GUARDAR REVISTA EN SQLITE
        # -------------------------------------------------

        try:

            conexion.execute("""
                INSERT INTO revistas (
                    codigo,
                    nombre,
                    issn,
                    issn_electronico,
                    editorial,
                    institucion,
                    pais,
                    ciudad,
                    periodicidad,
                    area_tematica,
                    url,
                    doi,
                    indexacion,
                    fecha_inicio,
                    estado,
                    archivo,
                    nombre_archivo,
                    observaciones,
                    usuario
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (

                codigo,
                nombre,
                issn,
                issn_electronico,
                editorial,
                institucion,
                pais,
                ciudad,
                periodicidad,
                area_tematica,
                url,
                doi,
                indexacion,
                fecha_inicio,
                int(estado),
                archivo_drive_id,
                nombre_archivo,
                observaciones,
                usuario

            ))

            conexion.commit()

            conexion.close()

        except Exception as e:

            conexion.close()

            # ---------------------------------------------
            # SI FALLA SQLITE, ELIMINAR ARCHIVO DE DRIVE
            # PARA NO DEJAR ARCHIVOS HUÉRFANOS
            # ---------------------------------------------

            if archivo_drive_id:

                try:

                    servicio = conectar_google_drive()

                    eliminar_archivo(
                        servicio,
                        archivo_drive_id
                    )

                except Exception:
                    pass

            flash(
                f"No se pudo guardar la revista: {e}",
                "error"
            )

            return render_template(
                "nueva_revista.html",
                revista=request.form,
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # -------------------------------------------------
        # ÉXITO
        # -------------------------------------------------

        flash(
            "Revista registrada correctamente.",
            "success"
        )

        return redirect(
            url_for("revistas")
        )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    return render_template(
        "nueva_revista.html",
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# VER REVISTA
# =========================================================

@app.route("/revistas/ver/<int:id>")
def ver_revista(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    revista = conexion.execute("""
        SELECT *
        FROM revistas
        WHERE id = ?
    """, (id,)).fetchone()

    if not revista:
        conexion.close()
        flash("La revista no existe.", "error")
        return redirect(url_for("revistas"))

    # -----------------------------------------------------
    # ARTÍCULOS PUBLICADOS EN ESTA REVISTA
    # -----------------------------------------------------

    articulos = conexion.execute("""
        SELECT *
        FROM articulos
        WHERE revista_id = ?
        ORDER BY anio DESC, titulo ASC
    """, (id,)).fetchall()

    conexion.close()

    return render_template(
        "ver_revista.html",
        revista=revista,
        articulos=articulos,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# ABRIR ARCHIVO DE LA REVISTA
# =========================================================

@app.route("/revistas/archivo/<int:id>")
def abrir_archivo_revista(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    revista = conexion.execute("""
        SELECT archivo
        FROM revistas
        WHERE id = ?
    """, (id,)).fetchone()

    conexion.close()

    if not revista:
        flash("La revista no existe.", "error")
        return redirect(url_for("revistas"))

    if not revista["archivo"]:
        flash("Esta revista no tiene un archivo asociado.", "error")
        return redirect(url_for("ver_revista", id=id))

    try:

        servicio = conectar_google_drive()

        archivo = servicio.files().get(
            fileId=revista["archivo"],
            fields="id,name,webViewLink"
        ).execute()

        enlace = archivo.get("webViewLink")

        if not enlace:
            enlace = f"https://drive.google.com/file/d/{revista['archivo']}/view"

        return redirect(enlace)

    except Exception as e:

        flash(
            f"No se pudo abrir el archivo: {e}",
            "error"
        )

        return redirect(
            url_for("ver_revista", id=id)
        )

# =========================================================
# EDITAR REVISTA
# =========================================================

@app.route("/revistas/editar/<int:id>", methods=["GET", "POST"])
def editar_revista(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    revista = conexion.execute("""
        SELECT *
        FROM revistas
        WHERE id = ?
    """, (id,)).fetchone()

    if not revista:
        conexion.close()

        flash(
            "La revista no existe.",
            "error"
        )

        return redirect(
            url_for("revistas")
        )

    # ---------------------------------------------
    # GUARDAR CAMBIOS
    # ---------------------------------------------

    if request.method == "POST":

        codigo = request.form.get(
            "codigo",
            ""
        ).strip()

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        issn = request.form.get(
            "issn",
            ""
        ).strip()

        issn_electronico = request.form.get(
            "issn_electronico",
            ""
        ).strip()

        editorial = request.form.get(
            "editorial",
            ""
        ).strip()

        institucion = request.form.get(
            "institucion",
            ""
        ).strip()

        pais = request.form.get(
            "pais",
            ""
        ).strip()

        ciudad = request.form.get(
            "ciudad",
            ""
        ).strip()

        periodicidad = request.form.get(
            "periodicidad",
            ""
        ).strip()

        area_tematica = request.form.get(
            "area_tematica",
            ""
        ).strip()

        url = request.form.get(
            "url",
            ""
        ).strip()

        doi = request.form.get(
            "doi",
            ""
        ).strip()

        indexacion = request.form.get(
            "indexacion",
            ""
        ).strip()

        fecha_inicio = request.form.get(
            "fecha_inicio",
            ""
        ).strip()

        estado = request.form.get(
            "estado",
            "1"
        ).strip()

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()

        archivo_subido = request.files.get(
            "archivo"
        )

        # -----------------------------------------
        # VALIDACIONES
        # -----------------------------------------

        if not codigo:

            conexion.close()

            flash(
                "El código de la revista es obligatorio.",
                "error"
            )

            return render_template(
                "editar_revista.html",
                revista=revista,
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        if not nombre:

            conexion.close()

            flash(
                "El nombre de la revista es obligatorio.",
                "error"
            )

            return render_template(
                "editar_revista.html",
                revista=revista,
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # -----------------------------------------
        # VERIFICAR CÓDIGO DUPLICADO
        # -----------------------------------------

        existente = conexion.execute("""
            SELECT id
            FROM revistas
            WHERE codigo = ?
              AND id != ?
        """, (
            codigo,
            id
        )).fetchone()

        if existente:

            conexion.close()

            flash(
                "Ya existe otra revista registrada con ese código.",
                "error"
            )

            return render_template(
                "editar_revista.html",
                revista=revista,
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # -----------------------------------------
        # ARCHIVO GOOGLE DRIVE
        # -----------------------------------------

        archivo_drive_id = revista["archivo"]
        nombre_archivo = revista["nombre_archivo"]
        archivo_nuevo_subido = False

        if archivo_subido and archivo_subido.filename:

            ruta_temporal = None

            try:

                extension = os.path.splitext(
                    archivo_subido.filename
                )[1]

                archivo_temporal = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=extension
                )

                ruta_temporal = archivo_temporal.name

                archivo_temporal.close()

                archivo_subido.save(
                    ruta_temporal
                )

                servicio = conectar_google_drive()

                carpeta_revistas = obtener_carpeta_revistas(
                    servicio
                )

                archivo_drive = subir_archivo(
                    servicio,
                    ruta_temporal,
                    archivo_subido.filename,
                    carpeta_revistas
                )

                archivo_drive_id = archivo_drive["id"]
                nombre_archivo = archivo_subido.filename
                archivo_nuevo_subido = True

            except Exception as e:

                conexion.close()

                flash(
                    f"No se pudo subir el nuevo archivo a Google Drive: {e}",
                    "error"
                )

                return render_template(
                    "editar_revista.html",
                    revista=revista,
                    usuario=session.get("usuario"),
                    rol=session.get("rol")
                )

            finally:

                if ruta_temporal and os.path.exists(
                    ruta_temporal
                ):
                    os.remove(
                        ruta_temporal
                    )

        # -----------------------------------------
        # ACTUALIZAR BASE DE DATOS
        # -----------------------------------------

        try:

            conexion.execute("""
                UPDATE revistas
                SET
                    codigo = ?,
                    nombre = ?,
                    issn = ?,
                    issn_electronico = ?,
                    editorial = ?,
                    institucion = ?,
                    pais = ?,
                    ciudad = ?,
                    periodicidad = ?,
                    area_tematica = ?,
                    url = ?,
                    doi = ?,
                    indexacion = ?,
                    fecha_inicio = ?,
                    estado = ?,
                    archivo = ?,
                    nombre_archivo = ?,
                    observaciones = ?
                WHERE id = ?
            """, (
                codigo,
                nombre,
                issn,
                issn_electronico,
                editorial,
                institucion,
                pais,
                ciudad,
                periodicidad,
                area_tematica,
                url,
                doi,
                indexacion,
                fecha_inicio,
                int(estado),
                archivo_drive_id,
                nombre_archivo,
                observaciones,
                id
            ))

            conexion.commit()
            conexion.close()

        except Exception as e:

            conexion.close()

            # Si subimos un archivo nuevo pero falló
            # la actualización de la BD, eliminamos
            # el archivo nuevo de Drive.

            if archivo_nuevo_subido and archivo_drive_id:

                try:

                    servicio = conectar_google_drive()

                    eliminar_archivo(
                        servicio,
                        archivo_drive_id
                    )

                except Exception:
                    pass

            flash(
                f"No se pudo actualizar la revista: {e}",
                "error"
            )

            return render_template(
                "editar_revista.html",
                revista=revista,
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # -----------------------------------------
        # ELIMINAR ARCHIVO ANTERIOR
        # -----------------------------------------

        # Solo después de actualizar correctamente
        # la BD eliminamos el archivo anterior.

        if (
            archivo_nuevo_subido
            and revista["archivo"]
            and revista["archivo"] != archivo_drive_id
        ):

            try:

                servicio = conectar_google_drive()

                eliminar_archivo(
                    servicio,
                    revista["archivo"]
                )

            except Exception:
                pass

        flash(
            "Revista actualizada correctamente.",
            "success"
        )

        return redirect(
            url_for(
                "revistas"
            )
        )

    # ---------------------------------------------
    # MOSTRAR FORMULARIO
    # ---------------------------------------------

    conexion.close()

    return render_template(
        "editar_revista.html",
        revista=revista,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# ELIMINAR REVISTA
# =========================================================

@app.route("/revistas/eliminar/<int:id>", methods=["POST"])
def eliminar_revista(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # -----------------------------------------------------
    # BUSCAR REVISTA
    # -----------------------------------------------------

    revista = conexion.execute("""
        SELECT *
        FROM revistas
        WHERE id = ?
    """, (id,)).fetchone()

    if not revista:

        conexion.close()

        flash(
            "La revista no existe.",
            "error"
        )

        return redirect(
            url_for("revistas")
        )

    # -----------------------------------------------------
    # GUARDAR ID DEL ARCHIVO DE GOOGLE DRIVE
    # -----------------------------------------------------

    archivo_drive_id = revista["archivo"]

    try:

        # -------------------------------------------------
        # DESVINCULAR ARTÍCULOS
        # -------------------------------------------------
        # Los artículos NO se eliminan.
        # Simplemente quedan sin revista asociada.

        conexion.execute("""
            UPDATE articulos
            SET revista_id = NULL
            WHERE revista_id = ?
        """, (id,))

        # -------------------------------------------------
        # ELIMINAR REVISTA
        # -------------------------------------------------

        conexion.execute("""
            DELETE FROM revistas
            WHERE id = ?
        """, (id,))

        conexion.commit()

        conexion.close()

    except Exception as e:

        conexion.rollback()
        conexion.close()

        flash(
            f"No se pudo eliminar la revista: {e}",
            "error"
        )

        return redirect(
            url_for("revistas")
        )

    # -----------------------------------------------------
    # ELIMINAR ARCHIVO DE GOOGLE DRIVE
    # -----------------------------------------------------

    if archivo_drive_id:

        try:

            servicio = conectar_google_drive()

            eliminar_archivo(
                servicio,
                archivo_drive_id
            )

        except Exception as e:

            flash(
                "La revista fue eliminada correctamente, "
                f"pero no se pudo eliminar su archivo de "
                f"Google Drive: {e}",
                "warning"
            )

            return redirect(
                url_for("revistas")
            )

    # -----------------------------------------------------
    # ÉXITO
    # -----------------------------------------------------

    flash(
        "Revista eliminada correctamente. "
        "Los artículos asociados fueron conservados.",
        "success"
    )

    return redirect(
        url_for("revistas")
    )

# =========================================================
# LISTADO DE LIBROS
# =========================================================

@app.route("/libros")
def libros():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # FILTROS
    # =====================================================

    buscar = request.args.get(
        "buscar",
        ""
    ).strip()

    anio = request.args.get(
        "anio",
        ""
    ).strip()

    estado = request.args.get(
        "estado",
        ""
    ).strip()

    # =====================================================
    # CONSULTA
    # =====================================================

    consulta = """
        SELECT *
        FROM libros
        WHERE 1 = 1
    """

    parametros = []

    # =====================================================
    # BUSCAR
    # =====================================================

    if buscar:

        consulta += """
            AND (
                codigo LIKE ?
                OR titulo LIKE ?
                OR subtitulo LIKE ?
                OR isbn LIKE ?
                OR editorial LIKE ?
                OR doi LIKE ?
            )
        """

        texto = f"%{buscar}%"

        parametros.extend([
            texto,
            texto,
            texto,
            texto,
            texto,
            texto
        ])

    # =====================================================
    # FILTRO POR AÑO
    # =====================================================

    if anio:

        consulta += """
            AND anio = ?
        """

        parametros.append(
            int(anio)
        )

    # =====================================================
    # FILTRO POR ESTADO
    # =====================================================

    if estado in ("0", "1"):

        consulta += """
            AND estado = ?
        """

        parametros.append(
            int(estado)
        )

    # =====================================================
    # ORDEN
    # =====================================================

    consulta += """
        ORDER BY anio DESC, titulo ASC
    """

    libros = conexion.execute(
        consulta,
        parametros
    ).fetchall()

    conexion.close()

    return render_template(
        "libros.html",
        libros=libros,
        buscar=buscar,
        anio=anio,
        estado=estado,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# NUEVO LIBRO
# =========================================================

@app.route("/libros/nuevo", methods=["GET", "POST"])
def nuevo_libro():

    if "usuario" not in session:
        return redirect(url_for("login"))

    # =====================================================
    # MOSTRAR FORMULARIO
    # =====================================================

    if request.method == "GET":

        conexion = conectar_bd()

        investigadores = conexion.execute("""
            SELECT id, nombre, apellido, tipo
            FROM investigadores
            WHERE estado = 1
            ORDER BY apellido, nombre
        """).fetchall()

        conexion.close()

        return render_template(
            "nuevo_libro.html",
            investigadores=investigadores,
            usuario=session.get("usuario"),
            rol=session.get("rol")
        )

    # =====================================================
    # DATOS DEL FORMULARIO
    # =====================================================

    codigo = request.form.get(
        "codigo",
        ""
    ).strip()

    titulo = request.form.get(
        "titulo",
        ""
    ).strip()

    subtitulo = request.form.get(
        "subtitulo",
        ""
    ).strip()

    isbn = request.form.get(
        "isbn",
        ""
    ).strip()

    editorial = request.form.get(
        "editorial",
        ""
    ).strip()

    edicion = request.form.get(
        "edicion",
        ""
    ).strip()

    lugar_publicacion = request.form.get(
        "lugar_publicacion",
        ""
    ).strip()

    fecha_publicacion = request.form.get(
        "fecha_publicacion",
        ""
    ).strip()

    anio = request.form.get(
        "anio",
        ""
    ).strip()

    paginas = request.form.get(
        "paginas",
        ""
    ).strip()

    doi = request.form.get(
        "doi",
        ""
    ).strip()

    url = request.form.get(
        "url",
        ""
    ).strip()

    tipo_libro = request.form.get(
        "tipo_libro",
        ""
    ).strip()

    observaciones = request.form.get(
        "observaciones",
        ""
    ).strip()

    # =====================================================
    # INVESTIGADORES SELECCIONADOS
    # =====================================================

    investigadores_seleccionados = request.form.getlist(
        "investigadores"
    )

    # Convertir los IDs a enteros
    investigadores_ids = []

    for investigador_id in investigadores_seleccionados:

        try:

            investigador_id = int(
                investigador_id
            )

            investigadores_ids.append(
                investigador_id
            )

        except ValueError:

            pass

    # =====================================================
    # VALIDACIONES
    # =====================================================

    if not codigo or not titulo or not anio:

        conexion = conectar_bd()

        investigadores = conexion.execute("""
            SELECT id, nombre, apellido, tipo
            FROM investigadores
            WHERE estado = 1
            ORDER BY apellido COLLATE NOCASE ASC, nombre COLLATE NOCASE ASC
        """).fetchall()

        conexion.close()

        return render_template(
            "nuevo_libro.html",
            investigadores=investigadores,
            error="Los campos Código, Título y Año son obligatorios.",
            usuario=session.get("usuario"),
            rol=session.get("rol")
        )

    try:

        anio = int(anio)

    except ValueError:

        conexion = conectar_bd()

        investigadores = conexion.execute("""
            SELECT id, nombre, apellido, tipo
            FROM investigadores
            WHERE estado = 1
            ORDER BY apellido, nombre
        """).fetchall()

        conexion.close()

        return render_template(
            "nuevo_libro.html",
            investigadores=investigadores,
            error="El año debe ser un número válido.",
            usuario=session.get("usuario"),
            rol=session.get("rol")
        )

    # =====================================================
    # VALIDAR PÁGINAS
    # =====================================================

    if paginas:

        try:

            paginas = int(paginas)

        except ValueError:

            conexion = conectar_bd()

            investigadores = conexion.execute("""
                SELECT id, nombre, apellido, tipo
                FROM investigadores
                WHERE estado = 1
                ORDER BY apellido, nombre
            """).fetchall()

            conexion.close()

            return render_template(
                "nuevo_libro.html",
                investigadores=investigadores,
                error="El número de páginas debe ser un número válido.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

    else:

        paginas = None

    # =====================================================
    # ARCHIVO
    # =====================================================

    archivo_subido = request.files.get(
        "archivo"
    )

    archivo_id = None

    archivo_nombre = None

    ruta_temporal = None

    # =====================================================
    # CONEXIÓN BASE DE DATOS
    # =====================================================

    conexion = conectar_bd()

    try:

        # =================================================
        # VERIFICAR CÓDIGO
        # =================================================

        existe = conexion.execute("""
            SELECT id
            FROM libros
            WHERE codigo = ?
        """, (
            codigo,
        )).fetchone()

        if existe:

            investigadores = conexion.execute("""
                SELECT id, nombre, apellido, tipo
                FROM investigadores
                WHERE estado = 1
                ORDER BY apellido, nombre
            """).fetchall()

            conexion.close()

            return render_template(
                "nuevo_libro.html",
                investigadores=investigadores,
                error="El código del libro ya existe. Ingrese otro código.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # =================================================
        # SUBIR ARCHIVO A GOOGLE DRIVE
        # =================================================

        if archivo_subido and archivo_subido.filename:

            print(
                "Subiendo archivo del libro a Google Drive..."
            )

            # ---------------------------------------------
            # CONECTAR CON GOOGLE DRIVE
            # ---------------------------------------------

            servicio_drive = conectar_google_drive()

            # ---------------------------------------------
            # OBTENER CARPETA LIBROS
            # ---------------------------------------------

            carpeta_libros = obtener_carpeta_libros(
                servicio_drive
            )

            print(
                "Carpeta de libros:",
                carpeta_libros
            )

            # ---------------------------------------------
            # CARPETA TEMPORAL
            # ---------------------------------------------

            carpeta_temporal = os.path.join(
                os.getcwd(),
                "temp"
            )

            os.makedirs(
                carpeta_temporal,
                exist_ok=True
            )

            # ---------------------------------------------
            # NOMBRE REAL DEL ARCHIVO
            # ---------------------------------------------

            archivo_nombre = archivo_subido.filename

            ruta_temporal = os.path.join(
                carpeta_temporal,
                archivo_nombre
            )

            # ---------------------------------------------
            # GUARDAR TEMPORALMENTE
            # ---------------------------------------------

            archivo_subido.save(
                ruta_temporal
            )

            # ---------------------------------------------
            # SUBIR A GOOGLE DRIVE
            # ---------------------------------------------

            archivo_drive = subir_archivo(
                servicio_drive,
                ruta_temporal,
                archivo_nombre,
                carpeta_libros
            )

            archivo_id = archivo_drive.get(
                "id"
            )

            print(
                "Archivo subido correctamente:",
                archivo_id
            )

            print(
                "Nombre guardado en Drive:",
                archivo_nombre
            )

            # ---------------------------------------------
            # ELIMINAR TEMPORAL
            # ---------------------------------------------

            if os.path.exists(
                ruta_temporal
            ):

                os.remove(
                    ruta_temporal
                )

                ruta_temporal = None

        # =================================================
        # INSERTAR LIBRO
        # =================================================

        cursor = conexion.execute("""
            INSERT INTO libros (
                codigo,
                titulo,
                subtitulo,
                isbn,
                editorial,
                edicion,
                lugar_publicacion,
                fecha_publicacion,
                anio,
                paginas,
                doi,
                url,
                tipo_libro,
                archivo,
                estado,
                observaciones,
                usuario
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            codigo,
            titulo,
            subtitulo,
            isbn,
            editorial,
            edicion,
            lugar_publicacion,
            fecha_publicacion,
            anio,
            paginas,
            doi,
            url,
            tipo_libro,
            archivo_id,
            1,
            observaciones,
            session.get("usuario")
        ))

        libro_id = cursor.lastrowid

        print(
            "Libro registrado con ID:",
            libro_id
        )

        # =================================================
        # GUARDAR INVESTIGADORES DEL LIBRO
        # =================================================

        for posicion, investigador_id in enumerate(
            investigadores_ids,
            start=1
        ):

            conexion.execute("""
                INSERT INTO libro_investigadores (
                    libro_id,
                    investigador_id,
                    orden_autor
                )
                VALUES (?, ?, ?)
            """, (
                libro_id,
                investigador_id,
                posicion
            ))

            print(
                f"Investigador {investigador_id} "
                f"asociado al libro {libro_id} "
                f"como autor {posicion}"
            )

        # =================================================
        # AUDITORÍA
        # =================================================

        conexion.execute("""
            INSERT INTO auditoria (
                usuario,
                accion,
                modulo,
                registro_id,
                descripcion,
                fecha
            )
            VALUES (
                ?, ?, ?, ?, ?, datetime('now')
            )
        """, (
            session.get("usuario"),
            "CREAR",
            "LIBROS",
            libro_id,
            f"Se registró el libro {codigo} - {titulo}"
        ))

        # =================================================
        # CONFIRMAR CAMBIOS
        # =================================================

        conexion.commit()

        print(
            "Libro registrado correctamente:",
            codigo
        )

        print(
            "Investigadores asociados:",
            len(investigadores_ids)
        )

    # =====================================================
    # ERROR DE INTEGRIDAD
    # =====================================================

    except sqlite3.IntegrityError as e:

        conexion.rollback()

        print(
            "ERROR DE INTEGRIDAD AL REGISTRAR LIBRO:",
            e
        )

        # ---------------------------------------------
        # ELIMINAR ARCHIVO DE DRIVE
        # ---------------------------------------------

        if archivo_id:

            try:

                servicio_drive = conectar_google_drive()

                eliminar_archivo(
                    servicio_drive,
                    archivo_id
                )

                print(
                    "Archivo eliminado de Drive por error."
                )

            except Exception as error_drive:

                print(
                    "No se pudo eliminar el archivo de Drive:",
                    error_drive
                )

        investigadores = conexion.execute("""
            SELECT id, nombre, apellido, tipo
            FROM investigadores
            WHERE estado = 1
            ORDER BY apellido, nombre
        """).fetchall()

        return render_template(
            "nuevo_libro.html",
            investigadores=investigadores,
            error="No se pudo registrar el libro. Verifique los datos ingresados.",
            usuario=session.get("usuario"),
            rol=session.get("rol")
        )

    # =====================================================
    # OTRO ERROR
    # =====================================================

    except Exception as e:

        conexion.rollback()

        print(
            "ERROR AL REGISTRAR LIBRO:",
            e
        )

        # ---------------------------------------------
        # ELIMINAR ARCHIVO DE DRIVE
        # ---------------------------------------------

        if archivo_id:

            try:

                servicio_drive = conectar_google_drive()

                eliminar_archivo(
                    servicio_drive,
                    archivo_id
                )

                print(
                    "Archivo eliminado de Drive por error."
                )

            except Exception as error_drive:

                print(
                    "No se pudo eliminar el archivo de Drive:",
                    error_drive
                )

        investigadores = conexion.execute("""
            SELECT id, nombre, apellido, tipo
            FROM investigadores
            WHERE estado = 1
            ORDER BY apellido, nombre
        """).fetchall()

        return render_template(
            "nuevo_libro.html",
            investigadores=investigadores,
            error=f"No se pudo registrar el libro: {e}",
            usuario=session.get("usuario"),
            rol=session.get("rol")
        )

    finally:

        # =================================================
        # CERRAR CONEXIÓN
        # =================================================

        try:

            conexion.close()

        except:

            pass

        # =================================================
        # ELIMINAR ARCHIVO TEMPORAL
        # =================================================

        if ruta_temporal:

            try:

                if os.path.exists(
                    ruta_temporal
                ):

                    os.remove(
                        ruta_temporal
                    )

            except:

                pass

    # =====================================================
    # VOLVER AL LISTADO
    # =====================================================

    return redirect(
        url_for("libros")
    )

# =========================================================
# VER LIBRO
# =========================================================

@app.route("/libros/ver/<int:id>")
def ver_libro(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    libro = conexion.execute("""
        SELECT *
        FROM libros
        WHERE id = ?
    """, (id,)).fetchone()

    if libro is None:
        conexion.close()
        return redirect(url_for("libros"))

    # =====================================================
    # INVESTIGADORES / AUTORES DEL LIBRO
    # =====================================================

    investigadores = conexion.execute("""
        SELECT
            i.id,
            i.nombre,
            i.apellido,
            i.tipo,
            li.orden_autor
        FROM libro_investigadores li
        INNER JOIN investigadores i
            ON i.id = li.investigador_id
        WHERE li.libro_id = ?
        ORDER BY li.orden_autor ASC
    """, (id,)).fetchall()

    conexion.close()

    # =====================================================
    # INFORMACIÓN DEL ARCHIVO
    # =====================================================

    archivo_drive = None

    if libro["archivo"]:

        try:

            servicio_drive = conectar_google_drive()

            archivo_drive = servicio_drive.files().get(
                fileId=libro["archivo"],
                fields="id,name,webViewLink,webContentLink,mimeType"
            ).execute()

        except Exception as e:

            print(
                "ERROR AL OBTENER ARCHIVO DEL LIBRO:",
                e
            )

            archivo_drive = None

    # =====================================================
    # MOSTRAR LIBRO
    # =====================================================

    return render_template(
        "ver_libro.html",
        libro=libro,
        investigadores=investigadores,
        archivo_drive=archivo_drive,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# EDITAR LIBRO
# =========================================================

@app.route("/libros/editar/<int:id>", methods=["GET", "POST"])
def editar_libro(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    libro = conexion.execute("""
        SELECT *
        FROM libros
        WHERE id = ?
    """, (id,)).fetchone()

    if libro is None:
        conexion.close()
        return redirect(url_for("libros"))

    # =====================================================
    # INVESTIGADORES
    # =====================================================

    investigadores = conexion.execute("""
        SELECT
            id,
            nombre,
            apellido,
            tipo
        FROM investigadores
        WHERE estado = 1
        ORDER BY
            apellido COLLATE NOCASE ASC,
            nombre COLLATE NOCASE ASC
    """).fetchall()

    investigadores_libro = conexion.execute("""
        SELECT investigador_id
        FROM libro_investigadores
        WHERE libro_id = ?
        ORDER BY orden_autor ASC
    """, (id,)).fetchall()

    investigadores_seleccionados = [
        fila["investigador_id"]
        for fila in investigadores_libro
    ]

    # =====================================================
    # GUARDAR CAMBIOS
    # =====================================================

    if request.method == "POST":

        codigo = request.form.get(
            "codigo", ""
        ).strip()

        titulo = request.form.get(
            "titulo", ""
        ).strip()

        subtitulo = request.form.get(
            "subtitulo", ""
        ).strip()

        isbn = request.form.get(
            "isbn", ""
        ).strip()

        editorial = request.form.get(
            "editorial", ""
        ).strip()

        edicion = request.form.get(
            "edicion", ""
        ).strip()

        lugar_publicacion = request.form.get(
            "lugar_publicacion", ""
        ).strip()

        fecha_publicacion = request.form.get(
            "fecha_publicacion", ""
        ).strip()

        anio = request.form.get(
            "anio", ""
        ).strip()

        paginas = request.form.get(
            "paginas", ""
        ).strip()

        doi = request.form.get(
            "doi", ""
        ).strip()

        url = request.form.get(
            "url", ""
        ).strip()

        tipo_libro = request.form.get(
            "tipo_libro", ""
        ).strip()

        observaciones = request.form.get(
            "observaciones", ""
        ).strip()

        estado = request.form.get(
            "estado",
            "1"
        ).strip()

        investigadores_seleccionados = request.form.getlist(
            "investigadores"
        )

        # =================================================
        # VALIDACIONES
        # =================================================

        if not codigo or not titulo or not anio:

            return render_template(
                "editar_libro.html",
                libro=libro,
                error="Los campos Código, Título y Año son obligatorios.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        try:

            anio = int(anio)

        except ValueError:

            return render_template(
                "editar_libro.html",
                libro=libro,
                error="El año debe ser un número válido.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        if paginas:

            try:

                paginas = int(paginas)

            except ValueError:

                return render_template(
                    "editar_libro.html",
                    libro=libro,
                    error="El número de páginas debe ser un número válido.",
                    usuario=session.get("usuario"),
                    rol=session.get("rol")
                )

        else:

            paginas = None

        # =================================================
        # ARCHIVO
        # =================================================

        archivo_actual = libro["archivo"]

        archivo_nuevo = request.files.get(
            "archivo"
        )

        # Por defecto se conserva el archivo actual
        nuevo_archivo_id = archivo_actual

        try:

            # =================================================
            # SI SE SELECCIONÓ UN NUEVO ARCHIVO
            # =================================================

            if archivo_nuevo and archivo_nuevo.filename:

                servicio_drive = conectar_google_drive()

                # ---------------------------------------------
                # CARPETA LIBROS
                # ---------------------------------------------

                carpeta_libros = obtener_carpeta_libros(
                    servicio_drive
                )

                # ---------------------------------------------
                # NOMBRE REAL DEL ARCHIVO
                # ---------------------------------------------

                nombre_archivo = archivo_nuevo.filename

                # IMPORTANTE:
                # Se conserva exactamente el nombre original
                # del archivo seleccionado por el usuario.

                nombre_drive = nombre_archivo

                # ---------------------------------------------
                # ARCHIVO TEMPORAL
                # ---------------------------------------------

                os.makedirs(
                    "temp",
                    exist_ok=True
                )

                ruta_temporal = os.path.join(
                    "temp",
                    nombre_archivo
                )

                archivo_nuevo.save(
                    ruta_temporal
                )

                # ---------------------------------------------
                # SUBIR A GOOGLE DRIVE
                # ---------------------------------------------

                archivo_subido = subir_archivo(

                    servicio_drive,

                    ruta_temporal,

                    nombre_drive,

                    carpeta_libros

                )

                # Guardar ID de Google Drive en la BD
                nuevo_archivo_id = archivo_subido["id"]

                # ---------------------------------------------
                # ELIMINAR ARCHIVO ANTERIOR
                # ---------------------------------------------

                if archivo_actual:

                    try:

                        eliminar_archivo(
                            servicio_drive,
                            archivo_actual
                        )

                    except Exception as e:

                        print(
                            "ADVERTENCIA: No se pudo eliminar el archivo anterior:",
                            e
                        )

                # ---------------------------------------------
                # ELIMINAR ARCHIVO TEMPORAL
                # ---------------------------------------------

                try:

                    os.remove(
                        ruta_temporal
                    )

                except:

                    pass

            # =================================================
            # ACTUALIZAR BASE DE DATOS
            # =================================================

            conexion.execute("""
                UPDATE libros

                SET
                    codigo = ?,
                    titulo = ?,
                    subtitulo = ?,
                    isbn = ?,
                    editorial = ?,
                    edicion = ?,
                    lugar_publicacion = ?,
                    fecha_publicacion = ?,
                    anio = ?,
                    paginas = ?,
                    doi = ?,
                    url = ?,
                    tipo_libro = ?,
                    archivo = ?,
                    estado = ?,
                    observaciones = ?

                WHERE id = ?

            """, (
                codigo,
                titulo,
                subtitulo,
                isbn,
                editorial,
                edicion,
                lugar_publicacion,
                fecha_publicacion,
                anio,
                paginas,
                doi,
                url,
                tipo_libro,
                nuevo_archivo_id,
                int(estado),
                observaciones,
                id
            ))

            # =====================================================
            # ACTUALIZAR INVESTIGADORES DEL LIBRO
            # =====================================================

            conexion.execute("""
                DELETE FROM libro_investigadores
                WHERE libro_id = ?
            """, (id,))

            for orden, investigador_id in enumerate(
                investigadores_seleccionados,
                start=1
            ):

                conexion.execute("""
                    INSERT INTO libro_investigadores (
                        libro_id,
                        investigador_id,
                        orden_autor
                    )
                    VALUES (?, ?, ?)
                """, (
                    id,
                    int(investigador_id),
                    orden
                ))

            conexion.commit()

        # =================================================
        # CÓDIGO DUPLICADO
        # =================================================

        except sqlite3.IntegrityError:

            conexion.close()

            return render_template(
                "editar_libro.html",
                libro=libro,
                error="El código ingresado ya pertenece a otro libro.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # =================================================
        # OTRO ERROR
        # =================================================

        except Exception as e:

            print(
                "ERROR AL EDITAR LIBRO:",
                e
            )

            conexion.rollback()
            conexion.close()

            return render_template(
                "editar_libro.html",
                libro=libro,
                error="Ocurrió un error al actualizar el libro.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # =================================================
        # CERRAR Y REGRESAR
        # =================================================

        conexion.close()

        return redirect(
            url_for("libros")
        )

    # =====================================================
    # MOSTRAR FORMULARIO
    # =====================================================

    conexion.close()

    return render_template(
        "editar_libro.html",
        libro=libro,
        investigadores=investigadores,
        investigadores_seleccionados=investigadores_seleccionados,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )


# =========================================================
# ELIMINAR ARCHIVO DEL LIBRO
# =========================================================

@app.route(
    "/libros/<int:id>/eliminar-archivo",
    methods=["POST"]
)
def eliminar_archivo_libro(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    libro = conexion.execute("""
        SELECT *
        FROM libros
        WHERE id = ?
    """, (id,)).fetchone()

    if libro is None:

        conexion.close()

        return redirect(
            url_for("libros")
        )

    archivo_id = libro["archivo"]

    try:

        # =================================================
        # ELIMINAR DE GOOGLE DRIVE
        # =================================================

        if archivo_id:

            servicio_drive = conectar_google_drive()

            eliminar_archivo(
                servicio_drive,
                archivo_id
            )

        # =================================================
        # ELIMINAR REFERENCIA DE LA BD
        # =================================================

        conexion.execute("""
            UPDATE libros
            SET archivo = NULL
            WHERE id = ?
        """, (id,))

        conexion.commit()

        print(
            f"ARCHIVO DEL LIBRO {id} ELIMINADO CORRECTAMENTE"
        )

    except Exception as e:

        print(
            "ERROR AL ELIMINAR ARCHIVO DEL LIBRO:",
            e
        )

        conexion.rollback()

    finally:

        conexion.close()

    return redirect(
        url_for(
            "editar_libro",
            id=id
        )
    )

# =========================================================
# ELIMINAR LIBRO
# =========================================================

@app.route("/libros/eliminar/<int:id>", methods=["POST"])
def eliminar_libro(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # BUSCAR LIBRO
    # =====================================================

    libro = conexion.execute("""
        SELECT *
        FROM libros
        WHERE id = ?
    """, (id,)).fetchone()

    if libro is None:

        conexion.close()

        return redirect(
            url_for("libros")
        )

    # =====================================================
    # DATOS DEL LIBRO
    # =====================================================

    archivo_id = libro["archivo"]

    codigo = libro["codigo"]
    titulo = libro["titulo"]

    try:

        # =================================================
        # ELIMINAR ARCHIVO DE GOOGLE DRIVE
        # =================================================

        if archivo_id:

            try:

                print(
                    f"Eliminando archivo de Google Drive: {archivo_id}"
                )

                servicio_drive = conectar_google_drive()

                eliminar_archivo(
                    servicio_drive,
                    archivo_id
                )

                print(
                    "Archivo de Google Drive eliminado correctamente."
                )

            except Exception as e:

                # -------------------------------------------------
                # SI EL ARCHIVO YA NO EXISTE EN DRIVE
                # NO IMPEDIMOS ELIMINAR EL LIBRO
                # -------------------------------------------------

                print(
                    "ADVERTENCIA: No se pudo eliminar el archivo de Drive:",
                    e
                )

        # =================================================
        # AUDITORÍA
        # =================================================

        conexion.execute("""
            INSERT INTO auditoria (
                usuario,
                accion,
                modulo,
                registro_id,
                descripcion,
                fecha
            )
            VALUES (
                ?, ?, ?, ?, ?, datetime('now')
            )
        """, (
            session.get("usuario"),
            "ELIMINAR",
            "LIBROS",
            id,
            f"Se eliminó el libro {codigo} - {titulo}"
        ))

        # =================================================
        # ELIMINAR INVESTIGADORES ASOCIADOS
        # =================================================

        conexion.execute("""
            DELETE FROM libro_investigadores
            WHERE libro_id = ?
        """, (id,))

        # =================================================
        # ELIMINAR REGISTRO DE LA BASE DE DATOS
        # =================================================

        conexion.execute("""
            DELETE FROM libros
            WHERE id = ?
        """, (id,))

        conexion.commit()

        print(
            f"Libro eliminado correctamente: {codigo} - {titulo}"
        )

    except Exception as e:

        print(
            "ERROR AL ELIMINAR LIBRO:",
            e
        )

        conexion.rollback()

    finally:

        conexion.close()

    # =====================================================
    # VOLVER AL LISTADO
    # =====================================================

    return redirect(
        url_for("libros")
    )

# =========================================================
# LISTADO DE TEXTOS EN ASIGNATURA
# =========================================================

@app.route("/textos-asignatura")
def textos_asignatura():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # FILTROS
    # =====================================================

    buscar = request.args.get(
        "buscar",
        ""
    ).strip()

    anio = request.args.get(
        "anio",
        ""
    ).strip()

    estado = request.args.get(
        "estado",
        ""
    ).strip()

    # =====================================================
    # CONSULTA
    # =====================================================

    consulta = """
        SELECT *
        FROM textos_asignatura
        WHERE 1 = 1
    """

    parametros = []

    # =====================================================
    # BUSCAR
    # =====================================================

    if buscar:

        consulta += """
            AND (
                codigo LIKE ?
                OR asignatura LIKE ?
                OR carrera LIKE ?
                OR facultad LIKE ?
                OR editorial LIKE ?
                OR institucion LIKE ?
                OR isbn LIKE ?
                OR doi LIKE ?
            )
        """

        texto = f"%{buscar}%"

        parametros.extend([
            texto,
            texto,
            texto,
            texto,
            texto,
            texto,
            texto,
            texto
        ])

    # =====================================================
    # FILTRO POR AÑO
    # =====================================================

    if anio:

        consulta += """
            AND anio = ?
        """

        parametros.append(
            int(anio)
        )

    # =====================================================
    # FILTRO POR ESTADO
    # =====================================================

    if estado in ("0", "1"):

        consulta += """
            AND estado = ?
        """

        parametros.append(
            int(estado)
        )

    # =====================================================
    # ORDEN
    # =====================================================

    consulta += """
        ORDER BY anio DESC, asignatura ASC
    """

    textos = conexion.execute(
        consulta,
        parametros
    ).fetchall()

    conexion.close()

    return render_template(
        "textos_asignatura.html",
        textos=textos,
        buscar=buscar,
        anio=anio,
        estado=estado,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# VER TEXTO EN ASIGNATURA
# =========================================================

@app.route("/textos-asignatura/ver/<int:id>")
def ver_texto_asignatura(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    texto = conexion.execute("""
        SELECT *
        FROM textos_asignatura
        WHERE id = ?
    """, (id,)).fetchone()

    if texto is None:
        conexion.close()
        return "Texto en asignatura no encontrado", 404

    # =====================================================
    # OBTENER INVESTIGADORES / AUTORES
    # =====================================================

    investigadores = conexion.execute("""
        SELECT
            i.id,
            i.nombre,
            i.apellido,
            i.tipo,
            tia.orden_autor
        FROM texto_asignatura_investigadores tia
        INNER JOIN investigadores i
            ON i.id = tia.investigador_id
        WHERE tia.texto_asignatura_id = ?
        ORDER BY tia.orden_autor ASC
    """, (id,)).fetchall()

    conexion.close()

   
    # =====================================================
    # OBTENER NOMBRE DEL ARCHIVO DESDE GOOGLE DRIVE
    # =====================================================

    nombre_archivo = None

    if texto["archivo"]:

        try:

            servicio_drive = conectar_google_drive()

            archivo_drive = servicio_drive.files().get(
                fileId=texto["archivo"],
                fields="name"
            ).execute()

            nombre_archivo = archivo_drive.get("name")

        except Exception as e:

            print(
                "No se pudo obtener el nombre del archivo:",
                e
            )


    return render_template(
        "ver_texto_asignatura.html",
        texto=texto,
        investigadores=investigadores,
        nombre_archivo=nombre_archivo,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# EDITAR TEXTO EN ASIGNATURA
# =========================================================

@app.route("/textos-asignatura/editar/<int:id>", methods=["GET", "POST"])
def editar_texto_asignatura(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # OBTENER TEXTO
    # =====================================================

    texto = conexion.execute("""
        SELECT *
        FROM textos_asignatura
        WHERE id = ?
    """, (id,)).fetchone()

    if texto is None:
        conexion.close()
        return "Texto en asignatura no encontrado", 404


    # =====================================================
    # POST - GUARDAR CAMBIOS
    # =====================================================

    if request.method == "POST":

        codigo = request.form.get(
            "codigo",
            ""
        ).strip()

        asignatura = request.form.get(
            "asignatura",
            ""
        ).strip()

        carrera = request.form.get(
            "carrera",
            ""
        ).strip()

        facultad = request.form.get(
            "facultad",
            ""
        ).strip()

        editorial = request.form.get(
            "editorial",
            ""
        ).strip()

        institucion = request.form.get(
            "institucion",
            ""
        ).strip()

        edicion = request.form.get(
            "edicion",
            ""
        ).strip()

        lugar_publicacion = request.form.get(
            "lugar_publicacion",
            ""
        ).strip()

        fecha_publicacion = request.form.get(
            "fecha_publicacion",
            ""
        ).strip()

        anio = request.form.get(
            "anio",
            ""
        ).strip()

        paginas = request.form.get(
            "paginas",
            ""
        ).strip()

        isbn = request.form.get(
            "isbn",
            ""
        ).strip()

        doi = request.form.get(
            "doi",
            ""
        ).strip()

        url = request.form.get(
            "url",
            ""
        ).strip()

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()

        # =================================================
        # ESTADO
        # =================================================

        estado = request.form.get(
            "estado",
            "1"
        ).strip()

        try:

            estado = int(estado)

            if estado not in (0, 1):
                estado = 1

        except ValueError:

            estado = 1


        # =================================================
        # INVESTIGADORES SELECCIONADOS
        # =================================================

        investigadores_seleccionados = request.form.getlist(
            "investigadores"
        )


        # =================================================
        # VALIDACIONES
        # =================================================

        if not codigo or not asignatura or not anio:

            conexion.close()

            return render_template(
                "editar_texto_asignatura.html",
                texto=texto,
                investigadores=[],
                seleccionados=[],
                nombre_archivo=None,
                error="Código, Asignatura y Año son campos obligatorios.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


        try:

            anio = int(anio)

            if paginas:
                paginas = int(paginas)
            else:
                paginas = None

        except ValueError:

            conexion.close()

            return render_template(
                "editar_texto_asignatura.html",
                texto=texto,
                investigadores=[],
                seleccionados=[],
                nombre_archivo=None,
                error="El año y las páginas deben contener valores numéricos.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


        # =================================================
        # VERIFICAR CÓDIGO DUPLICADO
        # =================================================

        existente = conexion.execute("""
            SELECT id
            FROM textos_asignatura
            WHERE codigo = ?
            AND id != ?
        """, (
            codigo,
            id
        )).fetchone()

        if existente:

            conexion.close()

            return render_template(
                "editar_texto_asignatura.html",
                texto=texto,
                investigadores=[],
                seleccionados=[],
                nombre_archivo=None,
                error="Ya existe otro texto en asignatura con ese código.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


        # =================================================
        # ARCHIVO
        # =================================================

        archivo_id = texto["archivo"]

        archivo_nuevo_id = None

        archivo_subido = request.files.get(
            "archivo"
        )

        ruta_temporal = None


        try:

            # =============================================
            # SI HAY ARCHIVO NUEVO
            # =============================================

            if archivo_subido and archivo_subido.filename:

                carpeta_temp = os.path.join(
                    os.getcwd(),
                    "temp"
                )

                os.makedirs(
                    carpeta_temp,
                    exist_ok=True
                )

                ruta_temporal = os.path.join(
                    carpeta_temp,
                    archivo_subido.filename
                )

                archivo_subido.save(
                    ruta_temporal
                )


                servicio_drive = conectar_google_drive()

                carpeta_textos = obtener_carpeta_textos_asignatura(
                    servicio_drive
                )


                archivo_drive = subir_archivo(
                    servicio_drive,
                    ruta_temporal,
                    archivo_subido.filename,
                    carpeta_textos
                )

                archivo_nuevo_id = archivo_drive.get(
                    "id"
                )


                # =========================================
                # ELIMINAR ARCHIVO TEMPORAL
                # =========================================

                if os.path.exists(
                    ruta_temporal
                ):

                    os.remove(
                        ruta_temporal
                    )

                    ruta_temporal = None


                # =========================================
                # ELIMINAR ARCHIVO ANTERIOR
                # =========================================

                if archivo_id:

                    try:

                        eliminar_archivo(
                            servicio_drive,
                            archivo_id
                        )

                    except Exception as e:

                        print(
                            "No se pudo eliminar el archivo anterior:",
                            e
                        )


                archivo_id = archivo_nuevo_id


            # =================================================
            # ACTUALIZAR TEXTO
            # =================================================

            conexion.execute("""
                UPDATE textos_asignatura
                SET
                    codigo = ?,
                    asignatura = ?,
                    carrera = ?,
                    facultad = ?,
                    editorial = ?,
                    institucion = ?,
                    edicion = ?,
                    lugar_publicacion = ?,
                    fecha_publicacion = ?,
                    anio = ?,
                    paginas = ?,
                    isbn = ?,
                    doi = ?,
                    url = ?,
                    archivo = ?,
                    observaciones = ?,
                    estado = ?
                WHERE id = ?
            """, (
                codigo,
                asignatura,
                carrera,
                facultad,
                editorial,
                institucion,
                edicion,
                lugar_publicacion,
                fecha_publicacion,
                anio,
                paginas,
                isbn,
                doi,
                url,
                archivo_id,
                observaciones,
                estado,
                id
            ))


            # =================================================
            # ACTUALIZAR INVESTIGADORES
            # =================================================

            conexion.execute("""
                DELETE FROM texto_asignatura_investigadores
                WHERE texto_asignatura_id = ?
            """, (
                id,
            ))


            for orden, investigador_id in enumerate(
                investigadores_seleccionados,
                start=1
            ):

                conexion.execute("""
                    INSERT INTO texto_asignatura_investigadores
                    (
                        texto_asignatura_id,
                        investigador_id,
                        orden_autor
                    )
                    VALUES (?, ?, ?)
                """, (
                    id,
                    investigador_id,
                    orden
                ))


            # =================================================
            # AUDITORÍA
            # =================================================

            conexion.execute("""
                INSERT INTO auditoria
                (
                    usuario,
                    accion,
                    modulo,
                    registro_id,
                    descripcion,
                    fecha
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                session.get("usuario"),
                "EDITAR",
                "TEXTOS EN ASIGNATURA",
                id,
                f"Se modificó el texto en asignatura: {codigo} - {asignatura}"
            ))


            # =================================================
            # CONFIRMAR CAMBIOS
            # =================================================

            conexion.commit()

            conexion.close()


            return redirect(
                
                url_for("textos_asignatura")
                    
                
            )


        except Exception as e:

            conexion.rollback()

            print(
                "Error al editar texto en asignatura:",
                e
            )


            # =============================================
            # SI SE SUBIÓ UN ARCHIVO NUEVO PERO OCURRIÓ
            # UN ERROR DESPUÉS, ELIMINARLO DE DRIVE
            # =============================================

            if archivo_nuevo_id:

                try:

                    servicio_drive = conectar_google_drive()

                    eliminar_archivo(
                        servicio_drive,
                        archivo_nuevo_id
                    )

                except Exception as error_drive:

                    print(
                        "No se pudo eliminar el archivo nuevo:",
                        error_drive
                    )


            conexion.close()

            return (
                f"Error al actualizar el texto en asignatura: {e}",
                500
            )


        finally:

            # =============================================
            # ELIMINAR ARCHIVO TEMPORAL SI EXISTE
            # =============================================

            if ruta_temporal:

                try:

                    if os.path.exists(
                        ruta_temporal
                    ):

                        os.remove(
                            ruta_temporal
                        )

                except Exception:

                    pass


    # =====================================================
    # GET - CARGAR FORMULARIO
    # =====================================================

    investigadores = conexion.execute("""
        SELECT
            id,
            nombre,
            apellido,
            tipo
        FROM investigadores
        WHERE estado = 1
        ORDER BY apellido, nombre
    """).fetchall()


    investigadores_seleccionados = conexion.execute("""
        SELECT investigador_id
        FROM texto_asignatura_investigadores
        WHERE texto_asignatura_id = ?
        ORDER BY orden_autor ASC
    """, (
        id,
    )).fetchall()


    seleccionados = [
        investigador["investigador_id"]
        for investigador in investigadores_seleccionados
    ]


    # =====================================================
    # OBTENER NOMBRE DEL ARCHIVO
    # =====================================================

    nombre_archivo = None

    if texto["archivo"]:

        try:

            servicio_drive = conectar_google_drive()

            archivo_drive = servicio_drive.files().get(
                fileId=texto["archivo"],
                fields="name"
            ).execute()

            nombre_archivo = archivo_drive.get(
                "name"
            )

        except Exception as e:

            print(
                "No se pudo obtener el nombre del archivo:",
                e
            )


    conexion.close()


    return render_template(
        "editar_texto_asignatura.html",
        texto=texto,
        investigadores=investigadores,
        seleccionados=seleccionados,
        nombre_archivo=nombre_archivo,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )


# =========================================================
# ELIMINAR TEXTO EN ASIGNATURA
# =========================================================

@app.route("/textos-asignatura/eliminar/<int:id>", methods=["POST", "GET"])
def eliminar_texto_asignatura(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("dicyt.db")
    conexion.row_factory = sqlite3.Row

    try:

        # =========================================================
        # BUSCAR EL TEXTO
        # =========================================================

        texto = conexion.execute("""
            SELECT *
            FROM textos_asignatura
            WHERE id = ?
        """, (id,)).fetchone()

        if texto is None:
            conexion.close()
            return redirect(url_for("textos_asignatura"))


        # =========================================================
        # ELIMINACIÓN LÓGICA
        # =========================================================

        conexion.execute("""
            UPDATE textos_asignatura
            SET estado = 0
            WHERE id = ?
        """, (id,))


        # =========================================================
        # AUDITORÍA
        # =========================================================

        conexion.execute("""
            INSERT INTO auditoria
            (
                usuario,
                accion,
                modulo,
                registro_id,
                descripcion,
                fecha
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (
            session.get("usuario"),
            "ELIMINAR",
            "TEXTOS EN ASIGNATURA",
            id,
            f"Se eliminó el texto en asignatura: {texto['codigo']} - {texto['asignatura']}"
        ))


        conexion.commit()

    except Exception as e:

        conexion.rollback()
        print("Error al eliminar texto en asignatura:", e)

    finally:

        conexion.close()


    return redirect(url_for("textos_asignatura"))

# =========================================================
# NUEVO TEXTO EN ASIGNATURA
# =========================================================

@app.route("/textos-asignatura/nuevo", methods=["GET", "POST"])
def nuevo_texto_asignatura():

    if "usuario" not in session:
        return redirect(url_for("login"))

    # =====================================================
    # MOSTRAR FORMULARIO
    # =====================================================

    if request.method == "GET":

        conexion = conectar_bd()

        investigadores = conexion.execute("""
            SELECT id, nombre, apellido, tipo
            FROM investigadores
            WHERE estado = 1
            ORDER BY apellido, nombre
        """).fetchall()

        conexion.close()

        return render_template(
            "nuevo_texto_asignatura.html",
            investigadores=investigadores,
            usuario=session.get("usuario"),
            rol=session.get("rol")
        )

    # =====================================================
    # DATOS DEL FORMULARIO
    # =====================================================

    codigo = request.form.get(
        "codigo",
        ""
    ).strip()

    asignatura = request.form.get(
        "asignatura",
        ""
    ).strip()

    carrera = request.form.get(
        "carrera",
        ""
    ).strip()

    facultad = request.form.get(
        "facultad",
        ""
    ).strip()

    editorial = request.form.get(
        "editorial",
        ""
    ).strip()

    institucion = request.form.get(
        "institucion",
        ""
    ).strip()

    edicion = request.form.get(
        "edicion",
        ""
    ).strip()

    lugar_publicacion = request.form.get(
        "lugar_publicacion",
        ""
    ).strip()

    fecha_publicacion = request.form.get(
        "fecha_publicacion",
        ""
    ).strip()

    anio = request.form.get(
        "anio",
        ""
    ).strip()

    paginas = request.form.get(
        "paginas",
        ""
    ).strip()

    isbn = request.form.get(
        "isbn",
        ""
    ).strip()

    doi = request.form.get(
        "doi",
        ""
    ).strip()

    url = request.form.get(
        "url",
        ""
    ).strip()

    observaciones = request.form.get(
        "observaciones",
        ""
    ).strip()

    # =====================================================
    # INVESTIGADORES / AUTORES SELECCIONADOS
    # =====================================================

    investigadores_seleccionados = request.form.getlist(
        "investigadores"
    )

    investigadores_ids = []

    for investigador_id in investigadores_seleccionados:

        try:

            investigador_id = int(
                investigador_id
            )

            investigadores_ids.append(
                investigador_id
            )

        except ValueError:

            pass

    # =====================================================
    # VALIDACIONES
    # =====================================================

    if not codigo or not asignatura or not anio:

        conexion = conectar_bd()

        investigadores = conexion.execute("""
            SELECT id, nombre, apellido, tipo
            FROM investigadores
            WHERE estado = 1
            ORDER BY apellido COLLATE NOCASE ASC,
                     nombre COLLATE NOCASE ASC
        """).fetchall()

        conexion.close()

        return render_template(
            "nuevo_texto_asignatura.html",
            investigadores=investigadores,
            error="Los campos Código, Asignatura y Año son obligatorios.",
            usuario=session.get("usuario"),
            rol=session.get("rol")
        )

    # =====================================================
    # VALIDAR AÑO
    # =====================================================

    try:

        anio = int(anio)

    except ValueError:

        conexion = conectar_bd()

        investigadores = conexion.execute("""
            SELECT id, nombre, apellido, tipo
            FROM investigadores
            WHERE estado = 1
            ORDER BY apellido, nombre
        """).fetchall()

        conexion.close()

        return render_template(
            "nuevo_texto_asignatura.html",
            investigadores=investigadores,
            error="El año debe ser un número válido.",
            usuario=session.get("usuario"),
            rol=session.get("rol")
        )

    # =====================================================
    # VALIDAR PÁGINAS
    # =====================================================

    if paginas:

        try:

            paginas = int(paginas)

        except ValueError:

            conexion = conectar_bd()

            investigadores = conexion.execute("""
                SELECT id, nombre, apellido, tipo
                FROM investigadores
                WHERE estado = 1
                ORDER BY apellido, nombre
            """).fetchall()

            conexion.close()

            return render_template(
                "nuevo_texto_asignatura.html",
                investigadores=investigadores,
                error="El número de páginas debe ser un número válido.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

    else:

        paginas = None

    # =====================================================
    # ARCHIVO
    # =====================================================

    archivo_subido = request.files.get(
        "archivo"
    )

    archivo_id = None

    archivo_nombre = None

    ruta_temporal = None

    # =====================================================
    # CONEXIÓN BASE DE DATOS
    # =====================================================

    conexion = conectar_bd()

    try:

        # =================================================
        # VERIFICAR CÓDIGO
        # =================================================

        existe = conexion.execute("""
            SELECT id
            FROM textos_asignatura
            WHERE codigo = ?
        """, (
            codigo,
        )).fetchone()

        if existe:

            investigadores = conexion.execute("""
                SELECT id, nombre, apellido, tipo
                FROM investigadores
                WHERE estado = 1
                ORDER BY apellido, nombre
            """).fetchall()

            conexion.close()

            return render_template(
                "nuevo_texto_asignatura.html",
                investigadores=investigadores,
                error="El código del texto en asignatura ya existe. Ingrese otro código.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )

        # =================================================
        # SUBIR ARCHIVO A GOOGLE DRIVE
        # =================================================

        if archivo_subido and archivo_subido.filename:

            print(
                "Subiendo archivo del texto en asignatura a Google Drive..."
            )

            # ---------------------------------------------
            # CONECTAR CON GOOGLE DRIVE
            # ---------------------------------------------

            servicio_drive = conectar_google_drive()

            # ---------------------------------------------
            # OBTENER CARPETA TEXTOS EN ASIGNATURA
            # ---------------------------------------------

            carpeta_textos = obtener_carpeta_textos_asignatura(
                servicio_drive
            )

            print(
                "Carpeta de textos en asignatura:",
                carpeta_textos
            )

            # ---------------------------------------------
            # CARPETA TEMPORAL
            # ---------------------------------------------

            carpeta_temporal = os.path.join(
                os.getcwd(),
                "temp"
            )

            os.makedirs(
                carpeta_temporal,
                exist_ok=True
            )

            # ---------------------------------------------
            # NOMBRE REAL DEL ARCHIVO
            # ---------------------------------------------

            archivo_nombre = archivo_subido.filename

            ruta_temporal = os.path.join(
                carpeta_temporal,
                archivo_nombre
            )

            # ---------------------------------------------
            # GUARDAR TEMPORALMENTE
            # ---------------------------------------------

            archivo_subido.save(
                ruta_temporal
            )

            # ---------------------------------------------
            # SUBIR A GOOGLE DRIVE
            # ---------------------------------------------

            archivo_drive = subir_archivo(
                servicio_drive,
                ruta_temporal,
                archivo_nombre,
                carpeta_textos
            )

            archivo_id = archivo_drive.get(
                "id"
            )

            print(
                "Archivo subido correctamente:",
                archivo_id
            )

            print(
                "Nombre guardado en Drive:",
                archivo_nombre
            )

            # ---------------------------------------------
            # ELIMINAR TEMPORAL
            # ---------------------------------------------

            if os.path.exists(
                ruta_temporal
            ):

                os.remove(
                    ruta_temporal
                )

                ruta_temporal = None

        # =================================================
        # INSERTAR TEXTO EN ASIGNATURA
        # =================================================

        cursor = conexion.execute("""
            INSERT INTO textos_asignatura (
                codigo,
                asignatura,
                carrera,
                facultad,
                editorial,
                institucion,
                edicion,
                lugar_publicacion,
                fecha_publicacion,
                anio,
                paginas,
                isbn,
                doi,
                url,
                archivo,
                estado,
                observaciones,
                usuario
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            codigo,
            asignatura,
            carrera,
            facultad,
            editorial,
            institucion,
            edicion,
            lugar_publicacion,
            fecha_publicacion,
            anio,
            paginas,
            isbn,
            doi,
            url,
            archivo_id,
            1,
            observaciones,
            session.get("usuario")
        ))

        texto_id = cursor.lastrowid

        print(
            "Texto en asignatura registrado con ID:",
            texto_id
        )

        # =================================================
        # GUARDAR INVESTIGADORES / AUTORES
        # =================================================

        for posicion, investigador_id in enumerate(
            investigadores_ids,
            start=1
        ):

            conexion.execute("""
                INSERT INTO texto_asignatura_investigadores (
                    texto_asignatura_id,
                    investigador_id,
                    orden_autor
                )
                VALUES (?, ?, ?)
            """, (
                texto_id,
                investigador_id,
                posicion
            ))

            print(
                f"Investigador {investigador_id} "
                f"asociado al texto {texto_id} "
                f"como autor {posicion}"
            )

        # =================================================
        # AUDITORÍA
        # =================================================

        conexion.execute("""
            INSERT INTO auditoria
            (
                usuario,
                accion,
                modulo,
                registro_id,
                descripcion,
                fecha
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (
            session.get("usuario"),
            "EDITAR",
            "TEXTOS EN ASIGNATURA",
            id,
            f"Se modificó el texto en asignatura: {codigo} - {asignatura}"
        ))

        # =================================================
        # CONFIRMAR CAMBIOS
        # =================================================

        conexion.commit()

        print(
            "Texto en asignatura registrado correctamente:",
            codigo
        )

        print(
            "Investigadores asociados:",
            len(investigadores_ids)
        )

    # =====================================================
    # ERROR DE INTEGRIDAD
    # =====================================================

    except sqlite3.IntegrityError as e:

        conexion.rollback()

        print(
            "ERROR DE INTEGRIDAD AL REGISTRAR TEXTO EN ASIGNATURA:",
            e
        )

        # ---------------------------------------------
        # ELIMINAR ARCHIVO DE DRIVE
        # ---------------------------------------------

        if archivo_id:

            try:

                servicio_drive = conectar_google_drive()

                eliminar_archivo(
                    servicio_drive,
                    archivo_id
                )

                print(
                    "Archivo eliminado de Drive por error."
                )

            except Exception as error_drive:

                print(
                    "No se pudo eliminar el archivo de Drive:",
                    error_drive
                )

        investigadores = conexion.execute("""
            SELECT id, nombre, apellido, tipo
            FROM investigadores
            WHERE estado = 1
            ORDER BY apellido, nombre
        """).fetchall()

        return render_template(
            "nuevo_texto_asignatura.html",
            investigadores=investigadores,
            error="No se pudo registrar el texto en asignatura. Verifique los datos ingresados.",
            usuario=session.get("usuario"),
            rol=session.get("rol")
        )

    # =====================================================
    # OTRO ERROR
    # =====================================================

    except Exception as e:

        conexion.rollback()

        print(
            "ERROR AL REGISTRAR TEXTO EN ASIGNATURA:",
            e
        )

        # ---------------------------------------------
        # ELIMINAR ARCHIVO DE DRIVE
        # ---------------------------------------------

        if archivo_id:

            try:

                servicio_drive = conectar_google_drive()

                eliminar_archivo(
                    servicio_drive,
                    archivo_id
                )

                print(
                    "Archivo eliminado de Drive por error."
                )

            except Exception as error_drive:

                print(
                    "No se pudo eliminar el archivo de Drive:",
                    error_drive
                )

        investigadores = conexion.execute("""
            SELECT id, nombre, apellido, tipo
            FROM investigadores
            WHERE estado = 1
            ORDER BY apellido, nombre
        """).fetchall()

        return render_template(
            "nuevo_texto_asignatura.html",
            investigadores=investigadores,
            error=f"No se pudo registrar el texto en asignatura: {e}",
            usuario=session.get("usuario"),
            rol=session.get("rol")
        )

    finally:

        # =================================================
        # CERRAR CONEXIÓN
        # =================================================

        try:

            conexion.close()

        except:

            pass

        # =================================================
        # ELIMINAR ARCHIVO TEMPORAL
        # =================================================

        if ruta_temporal:

            try:

                if os.path.exists(
                    ruta_temporal
                ):

                    os.remove(
                        ruta_temporal
                    )

            except:

                pass

    # =====================================================
    # VOLVER AL LISTADO
    # =====================================================

    return redirect(
        url_for("textos_asignatura")
    )

# =========================================================
# LISTADO DE SOCIEDADES CIENTÍFICAS
# =========================================================

@app.route("/sociedades-cientificas")
def sociedades_cientificas():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    buscar = request.args.get(
        "buscar",
        ""
    ).strip()

    gestion = request.args.get(
        "gestion",
        ""
    ).strip()

    carrera = request.args.get(
        "carrera",
        ""
    ).strip()

    facultad = request.args.get(
        "facultad",
        ""
    ).strip()

    estado = request.args.get(
        "estado",
        ""
    ).strip()

    # -----------------------------------------------------
    # CONSULTA BASE
    # -----------------------------------------------------

    consulta = """
        SELECT *
        FROM sociedades_cientificas
        WHERE 1 = 1
    """

    parametros = []

    # -----------------------------------------------------
    # BUSCAR
    # -----------------------------------------------------

    if buscar:

        consulta += """
            AND (
                codigo LIKE ?
                OR nombre LIKE ?
                OR sigla LIKE ?
            )
        """

        texto_busqueda = f"%{buscar}%"

        parametros.extend([
            texto_busqueda,
            texto_busqueda,
            texto_busqueda
        ])

    # -----------------------------------------------------
    # FILTRO GESTIÓN
    # -----------------------------------------------------

    if gestion:

        consulta += """
            AND gestion = ?
        """

        parametros.append(
            gestion
        )

    # -----------------------------------------------------
    # FILTRO CARRERA
    # -----------------------------------------------------

    if carrera:

        consulta += """
            AND carrera = ?
        """

        parametros.append(
            carrera
        )

    # -----------------------------------------------------
    # FILTRO FACULTAD
    # -----------------------------------------------------

    if facultad:

        consulta += """
            AND facultad = ?
        """

        parametros.append(
            facultad
        )

    # -----------------------------------------------------
    # FILTRO ESTADO
    # -----------------------------------------------------

    if estado in ("0", "1"):

        consulta += """
            AND estado = ?
        """

        parametros.append(
            int(estado)
        )

    # -----------------------------------------------------
    # ORDEN
    # -----------------------------------------------------

    consulta += """
        ORDER BY gestion DESC, nombre ASC
    """

    sociedades = conexion.execute(
        consulta,
        parametros
    ).fetchall()

    # -----------------------------------------------------
    # DATOS PARA FILTROS
    # -----------------------------------------------------

    gestiones = conexion.execute("""
        SELECT DISTINCT gestion
        FROM sociedades_cientificas
        WHERE gestion IS NOT NULL
        ORDER BY gestion DESC
    """).fetchall()

    carreras = conexion.execute("""
        SELECT DISTINCT carrera
        FROM sociedades_cientificas
        WHERE carrera IS NOT NULL
          AND carrera != ''
        ORDER BY carrera ASC
    """).fetchall()

    facultades = conexion.execute("""
        SELECT DISTINCT facultad
        FROM sociedades_cientificas
        WHERE facultad IS NOT NULL
          AND facultad != ''
        ORDER BY facultad ASC
    """).fetchall()

    conexion.close()

    return render_template(
        "sociedades_cientificas.html",
        sociedades=sociedades,
        buscar=buscar,
        gestion=gestion,
        carrera=carrera,
        facultad=facultad,
        estado=estado,
        gestiones=gestiones,
        carreras=carreras,
        facultades=facultades,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# NUEVA SOCIEDAD CIENTÍFICA
# =========================================================

@app.route("/sociedades-cientificas/nuevo", methods=["GET", "POST"])
def nueva_sociedad_cientifica():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # CARGAR ESTUDIANTES INVESTIGADORES ACTIVOS
    # =====================================================

    estudiantes = conexion.execute("""
        SELECT
            id,
            codigo,
            nombre,
            apellido,
            matricula,
            carrera,
            facultad,
            semestre
        FROM investigadores
        WHERE tipo = 'Estudiante Investigador'
          AND estado = 1
        ORDER BY apellido ASC, nombre ASC
    """).fetchall()


    # =====================================================
    # GUARDAR
    # =====================================================

    if request.method == "POST":

        codigo = request.form.get(
            "codigo",
            ""
        ).strip()

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        sigla = request.form.get(
            "sigla",
            ""
        ).strip()

        carrera = request.form.get(
            "carrera",
            ""
        ).strip()

        facultad = request.form.get(
            "facultad",
            ""
        ).strip()

        gestion = request.form.get(
            "gestion",
            ""
        ).strip()

        fecha_constitucion = request.form.get(
            "fecha_constitucion",
            ""
        ).strip()

        correo = request.form.get(
            "correo",
            ""
        ).strip()

        telefono = request.form.get(
            "telefono",
            ""
        ).strip()

        url = request.form.get(
            "url",
            ""
        ).strip()

        descripcion = request.form.get(
            "descripcion",
            ""
        ).strip()

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()


        # =================================================
        # VALIDACIONES
        # =================================================

        if not codigo:

            conexion.close()

            return render_template(
                "nueva_sociedad_cientifica.html",
                estudiantes=estudiantes,
                sociedad=request.form,
                error="El código de la sociedad es obligatorio.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


        if not nombre:

            conexion.close()

            return render_template(
                "nueva_sociedad_cientifica.html",
                estudiantes=estudiantes,
                sociedad=request.form,
                error="El nombre de la sociedad es obligatorio.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


        if not gestion:

            conexion.close()

            return render_template(
                "nueva_sociedad_cientifica.html",
                estudiantes=estudiantes,
                sociedad=request.form,
                error="La gestión es obligatoria.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


        try:

            gestion = int(gestion)

        except ValueError:

            conexion.close()

            return render_template(
                "nueva_sociedad_cientifica.html",
                estudiantes=estudiantes,
                sociedad=request.form,
                error="La gestión debe ser un año válido.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


        # =================================================
        # VERIFICAR CÓDIGO DUPLICADO
        # =================================================

        existe = conexion.execute("""
            SELECT id
            FROM sociedades_cientificas
            WHERE codigo = ?
        """, (
            codigo,
        )).fetchone()


        if existe:

            conexion.close()

            return render_template(
                "nueva_sociedad_cientifica.html",
                estudiantes=estudiantes,
                sociedad=request.form,
                error="Ya existe una sociedad científica con ese código.",
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


        # =================================================
        # ESTUDIANTES SELECCIONADOS
        # =================================================

        estudiantes_seleccionados = request.form.getlist(
            "estudiantes"
        )


        # =================================================
        # ARCHIVO
        # =================================================

        archivo_drive_id = None

        archivo_subido_drive = False

        archivo = request.files.get(
            "archivo"
        )


        try:

            # =================================================
            # SUBIR ARCHIVO A GOOGLE DRIVE
            # =================================================

            if archivo and archivo.filename:

                import os
                import tempfile


                nombre_archivo = archivo.filename


                extension = os.path.splitext(
                    nombre_archivo
                )[1]


                archivo_temporal = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=extension
                )


                ruta_temporal = archivo_temporal.name


                archivo_temporal.close()


                archivo.save(
                    ruta_temporal
                )


                try:

                    servicio = conectar_google_drive()


                    carpeta_sociedades = (
                        obtener_carpeta_sociedades_cientificas(
                            servicio
                        )
                    )


                    archivo_drive = subir_archivo(
                        servicio,
                        ruta_temporal,
                        nombre_archivo,
                        carpeta_sociedades
                    )


                    archivo_drive_id = archivo_drive["id"]


                    archivo_subido_drive = True


                finally:

                    if os.path.exists(
                        ruta_temporal
                    ):

                        os.remove(
                            ruta_temporal
                        )


            # =================================================
            # INSERTAR SOCIEDAD
            # =================================================

            cursor = conexion.execute("""
                INSERT INTO sociedades_cientificas (
                    codigo,
                    nombre,
                    sigla,
                    carrera,
                    facultad,
                    gestion,
                    fecha_constitucion,
                    correo,
                    telefono,
                    url,
                    descripcion,
                    archivo,
                    estado,
                    observaciones,
                    usuario
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
            """, (
                codigo,
                nombre,
                sigla,
                carrera,
                facultad,
                gestion,
                fecha_constitucion,
                correo,
                telefono,
                url,
                descripcion,
                archivo_drive_id,
                1,
                observaciones,
                session.get("usuario")
            ))


            sociedad_id = cursor.lastrowid


            # =================================================
            # GUARDAR ESTUDIANTES
            # =================================================

            for estudiante_id in estudiantes_seleccionados:

                cargo = request.form.get(
                    f"cargo_{estudiante_id}",
                    "Miembro"
                ).strip()


                fecha_inicio = request.form.get(
                    f"fecha_inicio_{estudiante_id}",
                    ""
                ).strip()


                fecha_fin = request.form.get(
                    f"fecha_fin_{estudiante_id}",
                    ""
                ).strip()


                conexion.execute("""
                    INSERT INTO sociedad_estudiantes (
                        sociedad_id,
                        investigador_id,
                        cargo,
                        fecha_inicio,
                        fecha_fin
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    sociedad_id,
                    int(estudiante_id),
                    cargo if cargo else "Miembro",
                    fecha_inicio,
                    fecha_fin
                ))


            # =================================================
            # AUDITORÍA
            # =================================================

            conexion.execute("""
                INSERT INTO auditoria (
                    usuario,
                    accion,
                    modulo,
                    registro_id,
                    descripcion,
                    fecha
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                session.get("usuario"),
                "CREAR",
                "SOCIEDADES CIENTÍFICAS",
                sociedad_id,
                f"Se creó la sociedad científica "
                f"{codigo} - {nombre}"
            ))


            # =================================================
            # CONFIRMAR
            # =================================================

            conexion.commit()

            conexion.close()


            # =================================================
            # VOLVER A TABLA PRINCIPAL
            # =================================================

            flash(
                "Sociedad científica registrada correctamente.",
                "success"
            )


            return redirect(
                url_for(
                    "sociedades_cientificas"
                )
            )


        except Exception as e:

            conexion.rollback()


            # =================================================
            # ELIMINAR ARCHIVO DE DRIVE SI HUBO ERROR
            # =================================================

            if archivo_subido_drive and archivo_drive_id:

                try:

                    servicio = conectar_google_drive()


                    eliminar_archivo(
                        servicio,
                        archivo_drive_id
                    )


                except Exception as error_drive:

                    print(
                        "No se pudo eliminar el archivo "
                        "de Google Drive:",
                        error_drive
                    )


            conexion.close()


            print(
                "Error al guardar sociedad científica:",
                e
            )


            return render_template(
                "nueva_sociedad_cientifica.html",
                estudiantes=estudiantes,
                sociedad=request.form,
                error=(
                    "Error al guardar la sociedad científica: "
                    f"{e}"
                ),
                usuario=session.get("usuario"),
                rol=session.get("rol")
            )


    # =====================================================
    # MOSTRAR FORMULARIO
    # =====================================================

    conexion.close()


    return render_template(
        "nueva_sociedad_cientifica.html",
        estudiantes=estudiantes,
        sociedad={},
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# VER SOCIEDAD CIENTÍFICA
# =========================================================

@app.route("/sociedades-cientificas/ver/<int:id>")
def ver_sociedad_cientifica(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # OBTENER SOCIEDAD
    # =====================================================

    sociedad = conexion.execute("""
        SELECT *
        FROM sociedades_cientificas
        WHERE id = ?
    """, (id,)).fetchone()

    if sociedad is None:

        conexion.close()

        flash(
            "La sociedad científica no existe.",
            "error"
        )

        return redirect(
            url_for("sociedades_cientificas")
        )

    # =====================================================
    # OBTENER ESTUDIANTES DE LA SOCIEDAD
    # =====================================================

    estudiantes = conexion.execute("""
        SELECT
            se.id,
            se.cargo,
            se.fecha_inicio,
            se.fecha_fin,

            i.id AS investigador_id,
            i.codigo,
            i.nombre,
            i.apellido,
            i.matricula,
            i.carrera,
            i.facultad,
            i.semestre,
            i.estado

        FROM sociedad_estudiantes se

        INNER JOIN investigadores i
            ON i.id = se.investigador_id

        WHERE se.sociedad_id = ?

        ORDER BY
            i.apellido ASC,
            i.nombre ASC

    """, (id,)).fetchall()

    conexion.close()

    # =====================================================
    # MOSTRAR INFORMACIÓN
    # =====================================================

    return render_template(
        "ver_sociedad_cientifica.html",
        sociedad=sociedad,
        estudiantes=estudiantes,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# EDITAR SOCIEDAD CIENTÍFICA
# =========================================================

@app.route("/sociedades-cientificas/editar/<int:id>", methods=["GET", "POST"])
def editar_sociedad_cientifica(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # OBTENER SOCIEDAD
    # =====================================================

    sociedad = conexion.execute("""
        SELECT *
        FROM sociedades_cientificas
        WHERE id = ?
    """, (id,)).fetchone()

    if sociedad is None:

        conexion.close()

        flash(
            "La sociedad científica no existe.",
            "error"
        )

        return redirect(
            url_for("sociedades_cientificas")
        )

    # =====================================================
    # POST - GUARDAR CAMBIOS
    # =====================================================

    if request.method == "POST":

        codigo = request.form.get(
            "codigo",
            ""
        ).strip()

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        sigla = request.form.get(
            "sigla",
            ""
        ).strip()

        carrera = request.form.get(
            "carrera",
            ""
        ).strip()

        facultad = request.form.get(
            "facultad",
            ""
        ).strip()

        gestion = request.form.get(
            "gestion",
            ""
        ).strip()

        fecha_constitucion = request.form.get(
            "fecha_constitucion",
            ""
        ).strip()

        correo = request.form.get(
            "correo",
            ""
        ).strip()

        telefono = request.form.get(
            "telefono",
            ""
        ).strip()

        url = request.form.get(
            "url",
            ""
        ).strip()

        descripcion = request.form.get(
            "descripcion",
            ""
        ).strip()

        estado = request.form.get(
            "estado",
            "1"
        ).strip()

        observaciones = request.form.get(
            "observaciones",
            ""
        ).strip()

        archivo_subido = request.files.get("archivo")

        # =================================================
        # VALIDACIONES
        # =================================================

        if not codigo:

            conexion.close()

            flash(
                "El código de la sociedad es obligatorio.",
                "error"
            )

            return redirect(
                url_for(
                    "editar_sociedad_cientifica",
                    id=id
                )
            )

        if not nombre:

            conexion.close()

            flash(
                "El nombre de la sociedad es obligatorio.",
                "error"
            )

            return redirect(
                url_for(
                    "editar_sociedad_cientifica",
                    id=id
                )
            )

        if not gestion:

            conexion.close()

            flash(
                "La gestión es obligatoria.",
                "error"
            )

            return redirect(
                url_for(
                    "editar_sociedad_cientifica",
                    id=id
                )
            )

        try:

            gestion = int(gestion)

        except ValueError:

            conexion.close()

            flash(
                "La gestión debe ser un año válido.",
                "error"
            )

            return redirect(
                url_for(
                    "editar_sociedad_cientifica",
                    id=id
                )
            )

        # =================================================
        # VERIFICAR CÓDIGO DUPLICADO
        # =================================================

        existente = conexion.execute("""
            SELECT id
            FROM sociedades_cientificas
            WHERE codigo = ?
              AND id != ?
        """, (
            codigo,
            id
        )).fetchone()

        if existente:

            conexion.close()

            flash(
                "Ya existe otra sociedad científica con ese código.",
                "error"
            )

            return redirect(
                url_for(
                    "editar_sociedad_cientifica",
                    id=id
                )
            )

        # =================================================
        # ESTADO
        # =================================================

        try:

            estado = int(estado)

            if estado not in (0, 1):
                estado = 1

        except ValueError:

            estado = 1

        # =================================================
        # ARCHIVO GOOGLE DRIVE
        # =================================================

        archivo_drive_id = sociedad["archivo"]

        archivo_nuevo_id = None

        archivo_nuevo_subido = False

        nombre_archivo = None

        if archivo_subido and archivo_subido.filename:

            ruta_temporal = None

            try:

                import os
                import tempfile

                nombre_archivo = archivo_subido.filename

                extension = os.path.splitext(
                    nombre_archivo
                )[1]

                archivo_temporal = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=extension
                )

                ruta_temporal = archivo_temporal.name

                archivo_temporal.close()

                archivo_subido.save(
                    ruta_temporal
                )

                servicio = conectar_google_drive()

                carpeta_sociedades = (
                    obtener_carpeta_sociedades_cientificas(
                        servicio
                    )
                )

                archivo_drive = subir_archivo(
                    servicio,
                    ruta_temporal,
                    nombre_archivo,
                    carpeta_sociedades
                )

                archivo_nuevo_id = archivo_drive["id"]

                archivo_drive_id = archivo_nuevo_id

                archivo_nuevo_subido = True

            except Exception as e:

                if ruta_temporal and os.path.exists(
                    ruta_temporal
                ):
                    os.remove(ruta_temporal)

                conexion.close()

                flash(
                    f"No se pudo subir el nuevo archivo a Google Drive: {e}",
                    "error"
                )

                return redirect(
                    url_for(
                        "editar_sociedad_cientifica",
                        id=id
                    )
                )

            finally:

                if ruta_temporal and os.path.exists(
                    ruta_temporal
                ):

                    os.remove(
                        ruta_temporal
                    )

        # =================================================
        # ESTUDIANTES SELECCIONADOS
        # =================================================

        estudiantes_seleccionados = request.form.getlist(
            "estudiantes"
        )

        # =================================================
        # ACTUALIZAR
        # =================================================

        try:

            conexion.execute("""
                UPDATE sociedades_cientificas
                SET
                    codigo = ?,
                    nombre = ?,
                    sigla = ?,
                    carrera = ?,
                    facultad = ?,
                    gestion = ?,
                    fecha_constitucion = ?,
                    correo = ?,
                    telefono = ?,
                    url = ?,
                    descripcion = ?,
                    archivo = ?,
                    estado = ?,
                    observaciones = ?
                WHERE id = ?
            """, (
                codigo,
                nombre,
                sigla,
                carrera,
                facultad,
                gestion,
                fecha_constitucion,
                correo,
                telefono,
                url,
                descripcion,
                archivo_drive_id,
                estado,
                observaciones,
                id
            ))

            # =================================================
            # ELIMINAR RELACIONES ANTERIORES
            # =================================================

            conexion.execute("""
                DELETE FROM sociedad_estudiantes
                WHERE sociedad_id = ?
            """, (id,))

            # =================================================
            # GUARDAR NUEVOS ESTUDIANTES
            # =================================================

            for estudiante_id in estudiantes_seleccionados:

                cargo = request.form.get(
                    f"cargo_{estudiante_id}",
                    "Miembro"
                ).strip()

                fecha_inicio = request.form.get(
                    f"fecha_inicio_{estudiante_id}",
                    ""
                ).strip()

                fecha_fin = request.form.get(
                    f"fecha_fin_{estudiante_id}",
                    ""
                ).strip()

                conexion.execute("""
                    INSERT INTO sociedad_estudiantes (
                        sociedad_id,
                        investigador_id,
                        cargo,
                        fecha_inicio,
                        fecha_fin
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    id,
                    int(estudiante_id),
                    cargo if cargo else "Miembro",
                    fecha_inicio,
                    fecha_fin
                ))

            # =================================================
            # AUDITORÍA
            # =================================================

            conexion.execute("""
                INSERT INTO auditoria (
                    usuario,
                    accion,
                    modulo,
                    registro_id,
                    descripcion,
                    fecha
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                session.get("usuario"),
                "EDITAR",
                "SOCIEDADES CIENTÍFICAS",
                id,
                f"Se modificó la sociedad científica "
                f"{codigo} - {nombre}"
            ))

            conexion.commit()

        except Exception as e:

            conexion.rollback()

            # =================================================
            # ELIMINAR ARCHIVO NUEVO SI HUBO ERROR
            # =================================================

            if archivo_nuevo_subido and archivo_nuevo_id:

                try:

                    servicio = conectar_google_drive()

                    eliminar_archivo(
                        servicio,
                        archivo_nuevo_id
                    )

                except Exception:
                    pass

            conexion.close()

            flash(
                f"No se pudo actualizar la sociedad científica: {e}",
                "error"
            )

            return redirect(
                url_for(
                    "editar_sociedad_cientifica",
                    id=id
                )
            )

        conexion.close()

        # =================================================
        # ELIMINAR ARCHIVO ANTERIOR
        # =================================================

        if (
            archivo_nuevo_subido
            and sociedad["archivo"]
            and sociedad["archivo"] != archivo_nuevo_id
        ):

            try:

                servicio = conectar_google_drive()

                eliminar_archivo(
                    servicio,
                    sociedad["archivo"]
                )

            except Exception as e:

                print(
                    "No se pudo eliminar el archivo anterior:",
                    e
                )

        flash(
            "Sociedad científica actualizada correctamente.",
            "success"
        )

        return redirect(
            url_for("sociedades_cientificas")
        )

    # =====================================================
    # GET - CARGAR ESTUDIANTES
    # =====================================================

    estudiantes = conexion.execute("""
        SELECT
            id,
            codigo,
            nombre,
            apellido,
            matricula,
            carrera,
            facultad,
            semestre
        FROM investigadores
        WHERE tipo = 'Estudiante Investigador'
          AND estado = 1
        ORDER BY apellido ASC, nombre ASC
    """).fetchall()

    # =====================================================
    # ESTUDIANTES YA REGISTRADOS
    # =====================================================

    estudiantes_sociedad = conexion.execute("""
        SELECT
            investigador_id,
            cargo,
            fecha_inicio,
            fecha_fin
        FROM sociedad_estudiantes
        WHERE sociedad_id = ?
    """, (id,)).fetchall()

    seleccionados = {}

    for estudiante in estudiantes_sociedad:

        seleccionados[estudiante["investigador_id"]] = {
            "cargo": estudiante["cargo"],
            "fecha_inicio": estudiante["fecha_inicio"],
            "fecha_fin": estudiante["fecha_fin"]
        }

    # =====================================================
    # NOMBRE DEL ARCHIVO
    # =====================================================

    nombre_archivo = None

    if sociedad["archivo"]:

        try:

            servicio = conectar_google_drive()

            archivo_drive = servicio.files().get(
                fileId=sociedad["archivo"],
                fields="name"
            ).execute()

            nombre_archivo = archivo_drive.get("name")

        except Exception as e:

            print(
                "No se pudo obtener el nombre del archivo:",
                e
            )

    conexion.close()

    return render_template(
        "editar_sociedad_cientifica.html",
        sociedad=sociedad,
        estudiantes=estudiantes,
        seleccionados=seleccionados,
        nombre_archivo=nombre_archivo,
        usuario=session.get("usuario"),
        rol=session.get("rol")
    )

# =========================================================
# ELIMINAR SOCIEDAD CIENTÍFICA
# =========================================================

@app.route("/sociedades-cientificas/eliminar/<int:id>")
def eliminar_sociedad_cientifica(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =====================================================
    # OBTENER SOCIEDAD
    # =====================================================

    sociedad = conexion.execute("""
        SELECT
            id,
            codigo,
            nombre,
            estado
        FROM sociedades_cientificas
        WHERE id = ?
    """, (id,)).fetchone()

    if sociedad is None:

        conexion.close()

        flash(
            "La sociedad científica no existe.",
            "error"
        )

        return redirect(
            url_for("sociedades_cientificas")
        )

    # =====================================================
    # VERIFICAR SI YA ESTÁ INACTIVA
    # =====================================================

    if sociedad["estado"] == 0:

        conexion.close()

        flash(
            "La sociedad científica ya se encuentra inactiva.",
            "error"
        )

        return redirect(
            url_for("sociedades_cientificas")
        )

    try:

        # =================================================
        # CAMBIAR ESTADO A INACTIVO
        # =================================================

        conexion.execute("""
            UPDATE sociedades_cientificas
            SET estado = 0
            WHERE id = ?
        """, (id,))

        # =================================================
        # AUDITORÍA
        # =================================================

        conexion.execute("""
            INSERT INTO auditoria (
                usuario,
                accion,
                modulo,
                registro_id,
                descripcion,
                fecha
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (
            session.get("usuario"),
            "ELIMINAR",
            "SOCIEDADES CIENTÍFICAS",
            id,
            f"Se desactivó la sociedad científica: "
            f"{sociedad['codigo']} - {sociedad['nombre']}"
        ))

        conexion.commit()
        conexion.close()

        flash(
            "Sociedad científica eliminada correctamente.",
            "success"
        )

        return redirect(
            url_for("sociedades_cientificas")
        )

    except Exception as e:

        conexion.rollback()
        conexion.close()

        print(
            "Error al eliminar sociedad científica:",
            e
        )

        flash(
            f"No se pudo eliminar la sociedad científica: {e}",
            "error"
        )

        return redirect(
            url_for("sociedades_cientificas")
        )

# =========================
# REPORTE DE DOCUMENTOS
# =========================

@app.route("/reportes/documentos")
def reporte_documentos():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    # =========================
    # FILTROS
    # =========================

    buscar = request.args.get("buscar", "").strip()
    categoria = request.args.get("categoria", "").strip()
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    usuario_filtro = request.args.get("usuario", "").strip()

    # =========================
    # CONSULTA PRINCIPAL
    # =========================

    consulta = """
        SELECT
            id,
            codigo,
            nombre,
            categoria,
            fecha,
            descripcion,
            archivo,
            usuario,
            nombre_archivo
        FROM documentos
        WHERE 1 = 1
    """

    parametros = []

    # Búsqueda general
    if buscar:

        consulta += """
            AND (
                codigo LIKE ?
                OR nombre LIKE ?
                OR categoria LIKE ?
                OR descripcion LIKE ?
            )
        """

        texto = f"%{buscar}%"

        parametros.extend([
            texto,
            texto,
            texto,
            texto
        ])

    # Filtro por categoría
    if categoria:

        consulta += """
            AND categoria = ?
        """

        parametros.append(categoria)

    # Filtro desde
    if fecha_desde:

        consulta += """
            AND date(fecha) >= date(?)
        """

        parametros.append(fecha_desde)

    # Filtro hasta
    if fecha_hasta:

        consulta += """
            AND date(fecha) <= date(?)
        """

        parametros.append(fecha_hasta)

    # Filtro por usuario
    if usuario_filtro:

        consulta += """
            AND usuario = ?
        """

        parametros.append(usuario_filtro)

    consulta += """
        ORDER BY date(fecha) DESC, id DESC
    """

    documentos = conexion.execute(
        consulta,
        parametros
    ).fetchall()

    # =========================
    # CATEGORÍAS
    # =========================

    categorias = conexion.execute("""
        SELECT DISTINCT categoria
        FROM documentos
        WHERE categoria IS NOT NULL
          AND categoria != ''
        ORDER BY categoria ASC
    """).fetchall()

    # =========================
    # USUARIOS
    # =========================

    usuarios = conexion.execute("""
        SELECT DISTINCT usuario
        FROM documentos
        WHERE usuario IS NOT NULL
          AND usuario != ''
        ORDER BY usuario ASC
    """).fetchall()

    # =========================
    # TOTAL DE DOCUMENTOS
    # =========================

    total_documentos = conexion.execute("""
        SELECT COUNT(*)
        FROM documentos
    """).fetchone()[0]

    # =========================
    # TOTAL DE CATEGORÍAS
    # =========================

    total_categorias = conexion.execute("""
        SELECT COUNT(DISTINCT categoria)
        FROM documentos
        WHERE categoria IS NOT NULL
          AND categoria != ''
    """).fetchone()[0]

    # =========================
    # DOCUMENTOS DEL AÑO ACTUAL
    # =========================

    documentos_anio_actual = conexion.execute("""
        SELECT COUNT(*)
        FROM documentos
        WHERE strftime('%Y', fecha) = strftime('%Y', 'now')
    """).fetchone()[0]

    # =========================
    # USUARIOS REGISTRADORES
    # =========================

    total_usuarios = conexion.execute("""
        SELECT COUNT(DISTINCT usuario)
        FROM documentos
        WHERE usuario IS NOT NULL
          AND usuario != ''
    """).fetchone()[0]

    # =========================
    # GRÁFICO:
    # DOCUMENTOS POR CATEGORÍA
    # =========================

    documentos_categoria = conexion.execute("""
        SELECT
            categoria,
            COUNT(*) AS total
        FROM documentos
        WHERE categoria IS NOT NULL
          AND categoria != ''
        GROUP BY categoria
        ORDER BY total DESC
    """).fetchall()

    # =========================
    # GRÁFICO:
    # DOCUMENTOS POR AÑO
    # =========================

    documentos_anio = conexion.execute("""
        SELECT
            strftime('%Y', fecha) AS anio,
            COUNT(*) AS total
        FROM documentos
        WHERE fecha IS NOT NULL
          AND fecha != ''
        GROUP BY strftime('%Y', fecha)
        ORDER BY anio ASC
    """).fetchall()

    # =========================
    # GRÁFICO:
    # DISTRIBUCIÓN POR CATEGORÍA
    # =========================

    distribucion_categoria = conexion.execute("""
        SELECT
            categoria,
            COUNT(*) AS total
        FROM documentos
        WHERE categoria IS NOT NULL
          AND categoria != ''
        GROUP BY categoria
        ORDER BY total DESC
    """).fetchall()

    conexion.close()

    ahora = datetime.now()

    fecha_generacion = ahora.strftime("%d/%m/%Y")
    hora_generacion = ahora.strftime("%H:%M")

    return render_template(
        "reporte_documentos.html",

        documentos=documentos,

        categorias=categorias,
        usuarios=usuarios,

        buscar=buscar,
        categoria=categoria,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        usuario_filtro=usuario_filtro,

        total_documentos=total_documentos,
        total_categorias=total_categorias,
        documentos_anio_actual=documentos_anio_actual,
        total_usuarios=total_usuarios,

        documentos_categoria=documentos_categoria,
        documentos_anio=documentos_anio,
        distribucion_categoria=distribucion_categoria,

        usuario=session.get("usuario"),
        rol=session.get("rol"),

        fecha_generacion=fecha_generacion,
        hora_generacion=hora_generacion
    )

# =========================
# REPORTE DE GESTIONES
# =========================

@app.route("/reportes/gestiones")
def reporte_gestiones():

    if "usuario" not in session:
        return redirect(url_for("login"))

    import sqlite3
    from datetime import datetime

    conn = sqlite3.connect("dicyt.db")
    conn.row_factory = sqlite3.Row

    # =========================================================
    # FILTROS
    # =========================================================

    buscar = request.args.get("buscar", "").strip()
    tipo_filtro = request.args.get("tipo", "").strip()
    estado_filtro = request.args.get("estado", "").strip()
    prioridad_filtro = request.args.get("prioridad", "").strip()
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()


    # =========================================================
    # CONSULTA UNIFICADA
    # ACTIVIDADES + SOLICITUDES
    # =========================================================

    sql = """
        SELECT *
        FROM (

            -- =============================================
            -- ACTIVIDADES
            -- =============================================

            SELECT
                id,
                codigo,
                tipo,
                asunto,
                responsable,
                fecha_inicio,
                fecha_limite,
                estado,
                prioridad,
                usuario,
                'Actividad' AS origen
            FROM gestiones


            UNION ALL


            -- =============================================
            -- SOLICITUDES
            -- =============================================

            SELECT
                id,
                codigo,
                tipo,
                asunto,
                solicitante AS responsable,
                fecha AS fecha_inicio,
                NULL AS fecha_limite,
                estado,
                NULL AS prioridad,
                usuario,
                'Solicitud' AS origen
            FROM solicitudes

        ) AS registros

        WHERE 1=1
    """

    parametros = []


    # =========================================================
    # BUSCADOR
    # =========================================================

    if buscar:

        sql += """
            AND (
                codigo LIKE ?
                OR tipo LIKE ?
                OR asunto LIKE ?
                OR responsable LIKE ?
            )
        """

        texto = f"%{buscar}%"

        parametros.extend([
            texto,
            texto,
            texto,
            texto
        ])


    # =========================================================
    # FILTRO POR TIPO
    # =========================================================

    if tipo_filtro:

        sql += """
            AND tipo = ?
        """

        parametros.append(tipo_filtro)


    # =========================================================
    # FILTRO POR ESTADO
    # =========================================================

    if estado_filtro:

        sql += """
            AND estado = ?
        """

        parametros.append(estado_filtro)


    # =========================================================
    # FILTRO POR PRIORIDAD
    # =========================================================

    if prioridad_filtro:

        sql += """
            AND prioridad = ?
        """

        parametros.append(prioridad_filtro)


    # =========================================================
    # FILTRO FECHA DESDE
    # =========================================================

    if fecha_desde:

        sql += """
            AND date(fecha_inicio) >= date(?)
        """

        parametros.append(fecha_desde)


    # =========================================================
    # FILTRO FECHA HASTA
    # =========================================================

    if fecha_hasta:

        sql += """
            AND date(fecha_inicio) <= date(?)
        """

        parametros.append(fecha_hasta)


    # =========================================================
    # ORDEN
    # =========================================================

    sql += """
        ORDER BY date(fecha_inicio) DESC, id DESC
    """


    gestiones = conn.execute(
        sql,
        parametros
    ).fetchall()


    # =========================================================
    # TOTAL DE GESTIONES
    # ACTIVIDADES + SOLICITUDES
    # =========================================================

    total_gestiones = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM gestiones)
            +
            (SELECT COUNT(*) FROM solicitudes)
        """
    ).fetchone()[0]


    # =========================================================
    # TIPOS DISTINTOS
    # =========================================================

    total_tipos = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT tipo
            FROM gestiones
            WHERE tipo IS NOT NULL
            AND TRIM(tipo) <> ''

            UNION

            SELECT tipo
            FROM solicitudes
            WHERE tipo IS NOT NULL
            AND TRIM(tipo) <> ''
        )
        """
    ).fetchone()[0]


    # =========================================================
    # GESTIONES DEL AÑO ACTUAL
    # =========================================================

    anio_actual = datetime.now().strftime("%Y")

    gestiones_anio_actual = conn.execute(
        """
        SELECT
            (
                SELECT COUNT(*)
                FROM gestiones
                WHERE fecha_inicio IS NOT NULL
                AND strftime('%Y', fecha_inicio) = ?
            )
            +
            (
                SELECT COUNT(*)
                FROM solicitudes
                WHERE fecha IS NOT NULL
                AND strftime('%Y', fecha) = ?
            )
        """,
        (
            anio_actual,
            anio_actual
        )
    ).fetchone()[0]


    # =========================================================
    # RESPONSABLES / SOLICITANTES
    # =========================================================

    total_responsables = conn.execute(
        """
        SELECT COUNT(*)
        FROM (

            SELECT DISTINCT responsable
            FROM gestiones
            WHERE responsable IS NOT NULL
            AND TRIM(responsable) <> ''

            UNION

            SELECT DISTINCT solicitante
            FROM solicitudes
            WHERE solicitante IS NOT NULL
            AND TRIM(solicitante) <> ''

        )
        """
    ).fetchone()[0]


    # =========================================================
    # TIPOS
    # ACTIVIDADES + SOLICITUDES
    # =========================================================

    tipos = conn.execute(
        """
        SELECT tipo
        FROM (

            SELECT tipo
            FROM gestiones
            WHERE tipo IS NOT NULL
            AND TRIM(tipo) <> ''

            UNION

            SELECT tipo
            FROM solicitudes
            WHERE tipo IS NOT NULL
            AND TRIM(tipo) <> ''

        )
        ORDER BY tipo
        """
    ).fetchall()


    # =========================================================
    # ESTADOS
    # ACTIVIDADES + SOLICITUDES
    # =========================================================

    estados = conn.execute(
        """
        SELECT estado
        FROM (

            SELECT estado
            FROM gestiones
            WHERE estado IS NOT NULL
            AND TRIM(estado) <> ''

            UNION

            SELECT estado
            FROM solicitudes
            WHERE estado IS NOT NULL
            AND TRIM(estado) <> ''

        )
        ORDER BY estado
        """
    ).fetchall()


    # =========================================================
    # PRIORIDADES
    # SOLO ACTIVIDADES
    # =========================================================

    prioridades = conn.execute(
        """
        SELECT DISTINCT prioridad
        FROM gestiones
        WHERE prioridad IS NOT NULL
        AND TRIM(prioridad) <> ''
        ORDER BY prioridad
        """
    ).fetchall()


    # =========================================================
    # GRÁFICO: GESTIONES POR TIPO
    # ACTIVIDADES + SOLICITUDES
    # =========================================================

    gestiones_tipo = conn.execute(
        """
        SELECT
            tipo,
            COUNT(*) AS total
        FROM (

            SELECT tipo
            FROM gestiones
            WHERE tipo IS NOT NULL
            AND TRIM(tipo) <> ''

            UNION ALL

            SELECT tipo
            FROM solicitudes
            WHERE tipo IS NOT NULL
            AND TRIM(tipo) <> ''

        )
        GROUP BY tipo
        ORDER BY total DESC
        """
    ).fetchall()


    # =========================================================
    # GRÁFICO: DISTRIBUCIÓN POR ESTADO
    # ACTIVIDADES + SOLICITUDES
    # =========================================================

    gestiones_estado = conn.execute(
        """
        SELECT
            estado,
            COUNT(*) AS total
        FROM (

            SELECT estado
            FROM gestiones
            WHERE estado IS NOT NULL
            AND TRIM(estado) <> ''

            UNION ALL

            SELECT estado
            FROM solicitudes
            WHERE estado IS NOT NULL
            AND TRIM(estado) <> ''

        )
        GROUP BY estado
        ORDER BY total DESC
        """
    ).fetchall()


    # =========================================================
    # GRÁFICO: GESTIONES POR AÑO
    # ACTIVIDADES + SOLICITUDES
    # =========================================================

    gestiones_anio = conn.execute(
        """
        SELECT
            anio,
            COUNT(*) AS total
        FROM (

            SELECT
                strftime('%Y', fecha_inicio) AS anio
            FROM gestiones
            WHERE fecha_inicio IS NOT NULL
            AND TRIM(fecha_inicio) <> ''

            UNION ALL

            SELECT
                strftime('%Y', fecha) AS anio
            FROM solicitudes
            WHERE fecha IS NOT NULL
            AND TRIM(fecha) <> ''

        )
        WHERE anio IS NOT NULL
        AND TRIM(anio) <> ''
        GROUP BY anio
        ORDER BY anio
        """
    ).fetchall()


    # =========================================================
    # USUARIOS
    # ACTIVIDADES + SOLICITUDES
    # =========================================================

    usuarios = conn.execute(
        """
        SELECT usuario
        FROM (

            SELECT DISTINCT usuario
            FROM gestiones
            WHERE usuario IS NOT NULL
            AND TRIM(usuario) <> ''

            UNION

            SELECT DISTINCT usuario
            FROM solicitudes
            WHERE usuario IS NOT NULL
            AND TRIM(usuario) <> ''

        )
        ORDER BY usuario
        """
    ).fetchall()


    conn.close()


    # =========================================================
    # FECHA Y HORA DE GENERACIÓN
    # =========================================================

    ahora = datetime.now()

    fecha_generacion = ahora.strftime("%d/%m/%Y")
    hora_generacion = ahora.strftime("%H:%M")


    # =========================================================
    # ENVIAR DATOS AL REPORTE
    # =========================================================

    return render_template(
        "reporte_gestiones.html",

        gestiones=gestiones,

        total_gestiones=total_gestiones,
        total_tipos=total_tipos,
        gestiones_anio_actual=gestiones_anio_actual,
        total_responsables=total_responsables,

        tipos=tipos,
        estados=estados,
        prioridades=prioridades,
        usuarios=usuarios,

        gestiones_tipo=gestiones_tipo,
        gestiones_estado=gestiones_estado,
        gestiones_anio=gestiones_anio,

        buscar=buscar,
        tipo_filtro=tipo_filtro,
        estado_filtro=estado_filtro,
        prioridad_filtro=prioridad_filtro,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,

        fecha_generacion=fecha_generacion,
        hora_generacion=hora_generacion
    )

# =========================
# REPORTE INVESTIGACIÓN
# =========================

@app.route("/reportes/investigacion")
def reporte_investigacion():

    if "usuario" not in session:
        return redirect(url_for("login"))

    # =========================================================
    # FECHA Y HORA DE GENERACIÓN
    # =========================================================

    ahora = datetime.now()

    fecha_generacion = ahora.strftime("%d/%m/%Y")
    hora_generacion = ahora.strftime("%H:%M:%S")

    conn = sqlite3.connect("dicyt.db")
    conn.row_factory = sqlite3.Row

    # =========================================================
    # INVESTIGADORES
    # =========================================================

    investigadores = conn.execute("""
        SELECT
            id,
            codigo,
            nombre,
            apellido,
            tipo,
            grado_academico,
            orcid,
            estado
        FROM investigadores
        ORDER BY apellido, nombre
    """).fetchall()

    total_investigadores = conn.execute("""
        SELECT COUNT(*)
        FROM investigadores
    """).fetchone()[0]

    docentes = conn.execute("""
        SELECT COUNT(*)
        FROM investigadores
        WHERE tipo = 'Docente Investigador'
    """).fetchone()[0]

    estudiantes = conn.execute("""
        SELECT COUNT(*)
        FROM investigadores
        WHERE tipo = 'Estudiante Investigador'
    """).fetchone()[0]

    investigadores_activos = conn.execute("""
        SELECT COUNT(*)
        FROM investigadores
        WHERE estado = 1
    """).fetchone()[0]

    # =========================================================
    # PRODUCCIÓN CIENTÍFICA
    # =========================================================

    total_articulos = conn.execute("""
        SELECT COUNT(*)
        FROM articulos
    """).fetchone()[0]

    total_libros = conn.execute("""
        SELECT COUNT(*)
        FROM libros
    """).fetchone()[0]

    total_revistas = conn.execute("""
        SELECT COUNT(*)
        FROM revistas
    """).fetchone()[0]

    total_textos = conn.execute("""
        SELECT COUNT(*)
        FROM textos_asignatura
    """).fetchone()[0]

    total_sociedades = conn.execute("""
        SELECT COUNT(*)
        FROM sociedades_cientificas
    """).fetchone()[0]

    total_publicaciones = (
        total_articulos
        + total_libros
        + total_revistas
        + total_textos
        + total_sociedades
    )

    # =========================================================
    # PRODUCCIÓN UNIFICADA
    # =========================================================

    produccion = []

    # ---------------------------------------------------------
    # ARTÍCULOS
    # ---------------------------------------------------------

    articulos = conn.execute("""
        SELECT
            a.id,
            a.codigo,
            'Artículo' AS tipo,
            a.titulo,
            a.anio,
            a.estado
        FROM articulos a
        ORDER BY a.anio DESC, a.titulo
    """).fetchall()

    for articulo in articulos:

        autores = conn.execute("""
            SELECT
                i.nombre,
                i.apellido
            FROM articulo_investigadores ai
            INNER JOIN investigadores i
                ON i.id = ai.investigador_id
            WHERE ai.articulo_id = ?
            ORDER BY ai.orden_autor
        """, (articulo["id"],)).fetchall()

        nombres_autores = ", ".join(
            f"{a['nombre']} {a['apellido']}".strip()
            for a in autores
        )

        produccion.append({
            "codigo": articulo["codigo"],
            "tipo": articulo["tipo"],
            "titulo": articulo["titulo"],
            "autores": nombres_autores or "—",
            "anio": articulo["anio"],
            "estado": articulo["estado"]
        })

    # ---------------------------------------------------------
    # LIBROS
    # ---------------------------------------------------------

    libros = conn.execute("""
        SELECT
            l.id,
            l.codigo,
            'Libro' AS tipo,
            l.titulo,
            l.anio,
            l.estado
        FROM libros l
        ORDER BY l.anio DESC, l.titulo
    """).fetchall()

    for libro in libros:

        autores = conn.execute("""
            SELECT
                i.nombre,
                i.apellido
            FROM libro_investigadores li
            INNER JOIN investigadores i
                ON i.id = li.investigador_id
            WHERE li.libro_id = ?
            ORDER BY li.orden_autor
        """, (libro["id"],)).fetchall()

        nombres_autores = ", ".join(
            f"{a['nombre']} {a['apellido']}".strip()
            for a in autores
        )

        produccion.append({
            "codigo": libro["codigo"],
            "tipo": libro["tipo"],
            "titulo": libro["titulo"],
            "autores": nombres_autores or "—",
            "anio": libro["anio"],
            "estado": libro["estado"]
        })

    # ---------------------------------------------------------
    # REVISTAS
    # ---------------------------------------------------------

    revistas = conn.execute("""
        SELECT
            codigo,
            'Revista' AS tipo,
            nombre AS titulo,
            fecha_inicio,
            estado
        FROM revistas
        ORDER BY fecha_inicio DESC, nombre
    """).fetchall()

    for revista in revistas:

        anio = ""

        if revista["fecha_inicio"]:
            anio = str(revista["fecha_inicio"])[:4]

        produccion.append({
            "codigo": revista["codigo"],
            "tipo": revista["tipo"],
            "titulo": revista["titulo"],
            "autores": "—",
            "anio": anio,
            "estado": revista["estado"]
        })

    # ---------------------------------------------------------
    # TEXTOS EN ASIGNATURA
    # ---------------------------------------------------------

    textos = conn.execute("""
        SELECT
            t.id,
            t.codigo,
            'Texto en Asignatura' AS tipo,
            t.asignatura AS titulo,
            t.anio,
            t.estado
        FROM textos_asignatura t
        ORDER BY t.anio DESC, t.asignatura
    """).fetchall()

    for texto in textos:

        autores = conn.execute("""
            SELECT
                i.nombre,
                i.apellido
            FROM texto_asignatura_investigadores tai
            INNER JOIN investigadores i
                ON i.id = tai.investigador_id
            WHERE tai.texto_asignatura_id = ?
            ORDER BY tai.orden_autor
        """, (texto["id"],)).fetchall()

        nombres_autores = ", ".join(
            f"{a['nombre']} {a['apellido']}".strip()
            for a in autores
        )

        produccion.append({
            "codigo": texto["codigo"],
            "tipo": texto["tipo"],
            "titulo": texto["titulo"],
            "autores": nombres_autores or "—",
            "anio": texto["anio"],
            "estado": texto["estado"]
        })

    # ---------------------------------------------------------
    # SOCIEDADES CIENTÍFICAS
    # ---------------------------------------------------------

    sociedades = conn.execute("""
        SELECT
            s.id,
            s.codigo,
            'Sociedad Científica' AS tipo,
            s.nombre AS titulo,
            s.gestion AS anio,
            s.estado
        FROM sociedades_cientificas s
        ORDER BY s.gestion DESC, s.nombre
    """).fetchall()

    for sociedad in sociedades:

        integrantes = conn.execute("""
            SELECT
                i.nombre,
                i.apellido
            FROM sociedad_estudiantes se
            INNER JOIN investigadores i
                ON i.id = se.investigador_id
            WHERE se.sociedad_id = ?
            ORDER BY se.fecha_inicio
        """, (sociedad["id"],)).fetchall()

        nombres_integrantes = ", ".join(
            f"{i['nombre']} {i['apellido']}".strip()
            for i in integrantes
        )

        produccion.append({
            "codigo": sociedad["codigo"],
            "tipo": sociedad["tipo"],
            "titulo": sociedad["titulo"],
            "autores": nombres_integrantes or "—",
            "anio": sociedad["anio"],
            "estado": sociedad["estado"]
        })

    conn.close()


    return render_template(
        "reporte_investigacion.html",
        investigadores=investigadores,
        produccion=produccion,

        total_investigadores=total_investigadores,
        docentes=docentes,
        estudiantes=estudiantes,
        investigadores_activos=investigadores_activos,

        total_publicaciones=total_publicaciones,
        total_articulos=total_articulos,
        total_libros=total_libros,
        total_revistas=total_revistas,
        total_textos=total_textos,
        total_sociedades=total_sociedades,

        fecha_generacion=fecha_generacion,
        hora_generacion=hora_generacion
    )

# =========================
# PERFIL DEL USUARIO
# =========================

@app.route("/perfil")
def perfil():

    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conexion = conectar_bd()

    usuario = conexion.execute(
        """
        SELECT id, nombre, usuario, rol, estado
        FROM usuarios
        WHERE id = ?
        """,
        (session["usuario_id"],)
    ).fetchone()

    conexion.close()

    if usuario is None:
        session.clear()
        return redirect(url_for("login"))

    return render_template(
        "perfil.html",
        usuario=usuario
    )

# =========================
# EJECUTAR
# =========================

if __name__ == "__main__":
    crear_bd()
    app.run(host="0.0.0.0", port=5000, debug=True)