from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave_sencilla_123"



def crear_base_datos():
    bd = sqlite3.connect("cinepedia.db")

    
    bd.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre VARCHAR(45) NOT NULL,
            apellido VARCHAR(45) NOT NULL,
            email VARCHAR(80) NOT NULL UNIQUE,
            password_hash VARCHAR(2) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    bd.execute("""
        CREATE TABLE IF NOT EXISTS peliculas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_pelicula VARCHAR(45) NOT NULL UNIQUE,
            director VARCHAR(45) NOT NULL,
            fecha_estreno VARCHAR(45) NOT NULL,
            sinopsis TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    bd.execute("""
        CREATE TABLE IF NOT EXISTS comentarios (
            usuarios_id INTEGER NOT NULL,
            peliculas_id INTEGER NOT NULL,
            comentario TEXT NOT NULL,
            PRIMARY KEY (usuarios_id, peliculas_id)
        )
    """)

    bd.commit()
    bd.close()


def conectar():
    """Abre la base de datos"""
    conn = sqlite3.connect("cinepedia.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def inicio():
    if "usuario_id" in session:
        return redirect(url_for("lista_peliculas"))
    return render_template("registro.html")


@app.route("/registrarse", methods=["POST"])
def registrarse():
    nombre = request.form["nombre"].strip()
    apellido = request.form["apellido"].strip()
    email = request.form["email"].strip()
    clave = request.form["contraseña"]
    confirmar = request.form["confirmar"]

    
    if len(nombre) < 2 or len(apellido) < 2:
        flash("Nombre y apellido: mínimo 2 caracteres", "error")
    elif "@" not in email:
        flash("Escribe un correo válido", "error")
    elif clave != confirmar:
        flash("Las contraseñas no coinciden", "error")
    else:
        bd = conectar()
        try:
            bd.execute(
                "INSERT INTO usuarios (nombre, apellido, email, password_hash) VALUES (?, ?, ?, ?)",
                (nombre, apellido, email, clave)
            )
            bd.commit()
            flash("¡Registrado con éxito! Inicia sesión", "ok")
        except:
            flash("Ese correo ya está registrado", "error")
        bd.close()

    return redirect(url_for("inicio"))


@app.route("/entrar", methods=["POST"])
def entrar():
    email = request.form["email_login"].strip()
    clave = request.form["contraseña_login"]

    bd = conectar()
    usuario = bd.execute(
        "SELECT * FROM usuarios WHERE email = ?", (email,)
    ).fetchone()
    bd.close()

    if usuario and usuario["password_hash"] == clave:
        session["usuario_id"] = usuario["id"]
        session["nombre"] = usuario["nombre"]
        return redirect(url_for("lista_peliculas"))

    flash("Correo o contraseña incorrectos", "error")
    return redirect(url_for("inicio"))


@app.route("/peliculas")
def lista_peliculas():
    if "usuario_id" not in session:
        return redirect(url_for("inicio"))

    bd = conectar()
    todas = bd.execute("SELECT * FROM peliculas ORDER BY id DESC").fetchall()
    bd.close()
    return render_template("inicio.html", peliculas=todas)


@app.route("/cerrar")
def cerrar():
    session.clear()
    return redirect(url_for("inicio"))



@app.route("/nueva", methods=["GET", "POST"])
def nueva_peli():
    if "usuario_id" not in session:
        return redirect(url_for("inicio"))

    if request.method == "POST":
        nombre = request.form["nombre_pelicula"].strip()
        director = request.form["director"].strip()
        fecha = request.form["fecha_estreno"].strip()
        sinopsis = request.form["sinopsis"].strip()

        if len(nombre) < 3 or len(director) < 3:
            flash("Nombre y director: mínimo 3 caracteres", "error")
        elif fecha == "" or sinopsis == "":
            flash("Ningún campo puede quedar vacío", "error")
        else:
            bd = conectar()
            try:
                bd.execute(
                    "INSERT INTO peliculas (nombre_pelicula, director, fecha_estreno, sinopsis) VALUES (?, ?, ?, ?)",
                    (nombre, director, fecha, sinopsis)
                )
                bd.commit()
                flash("Película guardada", "ok")
                return redirect(url_for("lista_peliculas"))
            except:
                flash("Ese nombre de película ya existe", "error")
            bd.close()

    return render_template("nueva.html")



@app.route("/ver/<int:id_peli>", methods=["GET", "POST"])
def ver_peli(id_peli):
    bd = conectar()
    peli = bd.execute("SELECT * FROM peliculas WHERE id = ?", (id_peli,)).fetchone()

    if not peli:
        bd.close()
        return redirect(url_for("lista_peliculas"))

   
    dueño = bd.execute("""
        SELECT u.id, u.nombre FROM usuarios u
        JOIN comentarios c ON u.id = c.usuarios_id
        WHERE c.peliculas_id = ? LIMIT 1
    """, (id_peli,)).fetchone()

    
    if not dueño:
       
        dueño_id = None
    else:
        dueño_id = dueño["id"]

    
    if request.method == "POST" and "usuario_id" in session:
        if dueño_id and session["usuario_id"] == dueño_id:
            flash("No puedes comentar tu propia película", "error")
        else:
            texto = request.form["comentario"].strip()
            if texto:
                bd.execute(
                    "INSERT INTO comentarios VALUES (?, ?, ?)",
                    (session["usuario_id"], id_peli, texto)
                )
                bd.commit()
        return redirect(url_for("ver_peli", id_peli=id_peli))

    
    comentarios = bd.execute("""
        SELECT c.*, u.nombre FROM comentarios c
        JOIN usuarios u ON c.usuarios_id = u.id
        WHERE c.peliculas_id = ?
    """, (id_peli,)).fetchall()

    bd.close()
    return render_template("ver.html", peli=peli, comentarios=comentarios, dueño_id=dueño_id)


@app.route("/editar/<int:id_peli>", methods=["GET", "POST"])
def editar_peli(id_peli):
    if "usuario_id" not in session:
        return redirect(url_for("inicio"))

    bd = conectar()
    peli = bd.execute("SELECT * FROM peliculas WHERE id = ?", (id_peli,)).fetchone()

    dueño = bd.execute("""
        SELECT DISTINCT c.usuarios_id FROM comentarios c
        WHERE c.peliculas_id = ?
    """, (id_peli,)).fetchone()

    if not dueño or dueño["usuarios_id"] != session["usuario_id"]:
        flash("Solo puedes editar tus películas", "error")
        bd.close()
        return redirect(url_for("lista_peliculas"))

    if request.method == "POST":
        nombre = request.form["nombre_pelicula"].strip()
        director = request.form["director"].strip()
        fecha = request.form["fecha_estreno"].strip()
        sinopsis = request.form["sinopsis"].strip()

        if len(nombre) < 3 or len(director) < 3:
            flash("Nombre y director: mínimo 3 caracteres", "error")
        elif fecha == "":
            flash("La fecha no puede estar vacía", "error")
        else:
            try:
                bd.execute("""
                    UPDATE peliculas
                    SET nombre_pelicula=?, director=?, fecha_estreno=?, sinopsis=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """, (nombre, director, fecha, sinopsis, id_peli))
                bd.commit()
                flash("Película actualizada", "ok")
                return redirect(url_for("ver_peli", id_peli=id_peli))
            except:
                flash("Ese nombre ya existe", "error")

    bd.close()
    return render_template("editar.html", peli=peli)



@app.route("/borrar/<int:id_peli>")
def borrar_peli(id_peli):
    if "usuario_id" not in session:
        return redirect(url_for("inicio"))

    bd = conectar()
    dueño = bd.execute("""
        SELECT DISTINCT c.usuarios_id FROM comentarios c
        WHERE c.peliculas_id = ?
    """, (id_peli,)).fetchone()

    if dueño and dueño["usuarios_id"] == session["usuario_id"]:
        bd.execute("DELETE FROM peliculas WHERE id = ?", (id_peli,))
        bd.execute("DELETE FROM comentarios WHERE peliculas_id = ?", (id_peli,))
        bd.commit()
        flash("Película eliminada", "ok")

    bd.close()
    return redirect(url_for("lista_peliculas"))



if __name__ == "__main__":
    with app.app_context():
        crear_base_datos()
    app.run(debug=True, port=5000)