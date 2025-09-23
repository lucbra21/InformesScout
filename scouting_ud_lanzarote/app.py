import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from fpdf import FPDF
import matplotlib.pyplot as plt
import numpy as np

# === LOGIN CON ROLES ===
USERS = {
    "admin": {"password": "admin", "role": "admin"},
    "scout": {"password": "scout123", "role": "scout"}
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

if not st.session_state.logged_in:
    # Centrar contenido
    col1, col2, col3 = st.columns([1,6,1])
    with col2:
        # Mostrar logo si existe
        logo_path = "ud_lanzarote_logo3.png"
        if os.path.exists(logo_path):
            st.image(logo_path, width=200)
        st.title("Scouting UD Lanzarote")
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")
        if st.button("Iniciar sesión"):
            if usuario in USERS and contraseña == USERS[usuario]["password"]:
                st.session_state.logged_in = True
                st.session_state.role = USERS[usuario]["role"]
                st.success(f"✅ Bienvenido, {usuario} ({st.session_state.role})")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
        st.stop()


# === CONFIGURACIÓN ===
DATA_DIR = "."  # Carpeta donde están los .json
TABLES = ["Posiciones", "Scouts", "Jugadores", "Informes"]

# Lista de atributos valorables
ATRIBUTOS_VALORABLES = [
    "Juego con los pies", "Juego aéreo", "Reflejos (Bajo palos)", "Blocajes",
    "Salidas (mano a mano)", "Despejes", "Velocidad de reacción", "Colocación",
    "Salida de balón (corto)", "Salida de balón (largo)", "Duelos", "Duelos aéreos",
    "Resistencia", "Velocidad", "Precisión en el pase corto", "Precisión en el pase largo",
    "Llegada al área rival", "Presión", "Desmarques", "Desborde", "Gol", "Descargas",
    "Remate de cabeza", "Disparos", "Presión mental", "Liderazgo"
]

# Lista de atributos estadísticos (porcentajes)
ATRIBUTOS_PORCENTAJE = [
    "% Duelos ganados",
    "% Duelos aéreos ganados",
    "% Pases cortos acertados",
    "% Pases largos acertados",
    "% Disparos a puerta"
]

# FUNCIONES AUXILIARES #
def load_table(table_name):
    path = os.path.join(DATA_DIR, f"{table_name}.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []
    if data:
        fields_list = [record.get("fields", {}) for record in data]
        df = pd.DataFrame(fields_list)
    else:
        df = pd.DataFrame()
    return df, path

def save_table(df, path):
    # Asegurarse de guardar strings (no NaN) y registros limpios
    records = [{"fields": row.dropna().to_dict()} for _, row in df.iterrows()]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)

def add_new_record(table_name, new_record):
    df, path = load_table(table_name)
    df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
    save_table(df, path)

# INICIALIZAR session_state para formularios persistentes #
if "show_create_player_form" not in st.session_state:
    st.session_state.show_create_player_form = False
if "show_create_report_form" not in st.session_state:
    st.session_state.show_create_report_form = False

#  FUNCIÓN DE GENERACIÓN DE PDF (FPDF2) #
def generar_pdf(informe, logo_path="ud_lanzarote_logo.png"):
    """
    Genera un PDF con encabezado diferenciado, escudo, línea divisoria,
    tabla de atributos, tabla de estadísticas y bloque de observaciones.
    Devuelve la ruta del fichero generado.
    """
    # Nombre de fichero (reemplazamos espacios por guiones)
    jugador_safe = str(informe.get("Jugador", "desconocido")).replace(" ", "_")
    fecha_safe = str(informe.get("Fecha informe", datetime.today().strftime("%Y-%m-%d")))
    file_name = f"Informe_{jugador_safe}_{fecha_safe}.pdf"
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Página y dimensiones
    page_w = pdf.w - 2 * pdf.l_margin  # ancho
    left_x = pdf.l_margin

    # Encabezado con fondo claro
    header_h = 30
    pdf.set_fill_color(245, 245, 245)  # color fondo encabezado
    pdf.rect(left_x - 1, 10, page_w + 2, header_h, style="F")  # rectángulo de fondo

    # Logo (si existe)
    if os.path.exists(logo_path):
        try:
            logo_w = 36
            logo_h = 36
            pdf.image(logo_path, left_x + 2, 2.5, logo_w, logo_h)
        except Exception:
            # si hay problema con imagen, ignoramos
            pass

    # Título centralizado dentro del encabezado
    pdf.set_xy(left_x, 12)
    pdf.set_font("Arial", "B", 16)
    title = f"Informe de Jugador"
    pdf.cell(page_w, 7, title, ln=1, align="C")

    # Nombre del jugador (debajo del título)
    pdf.set_font("Arial", "B", 14)
    jugador_text = informe.get("Jugador", "")
    pdf.cell(page_w, 8, jugador_text, ln=1, align="C")

    # Subtítulo con fecha y scout
    pdf.set_font("Arial", "", 11)
    subt = f"Fecha: {informe.get('Fecha informe','')}    -    Scout: {informe.get('Scout','')}"
    pdf.cell(page_w, 6, subt, ln=1, align="C")

    pdf.ln(6)

    # Línea divisoria de color (roja)
    pdf.set_draw_color(200, 0, 0)
    pdf.set_line_width(0.8)
    y_line = pdf.get_y()
    pdf.line(left_x, y_line, left_x + page_w, y_line)
    pdf.ln(6)

    # Atributos valorables: cabecera de tabla (En futuro igual meter estrellas? + visual)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, " Atributos valorables", ln=1)
    pdf.ln(2)

    # Table layout
    name_col = int(page_w * 0.75)  # columna nombre atributo
    val_col = int(page_w * 0.25)   # columna valor
    row_h = 8

    # Cabecera de la tabla
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(name_col, row_h, "Atributo", border=1, fill=True)
    pdf.cell(val_col, row_h, "Valor (0-5)", border=1, fill=True, ln=1)

    # Filas: usamos multi_cell para el nombre por si se parte
    pdf.set_font("Arial", "", 10)
    for attr in ATRIBUTOS_VALORABLES:
        val = informe.get(attr, "")
        if str(val).strip() != "" and str(val) not in ["0", "0.0"]:
            x_before = pdf.get_x()
            y_before = pdf.get_y()
            pdf.multi_cell(name_col, row_h, str(attr), border=1)
            y_after_name = pdf.get_y()
            pdf.set_xy(left_x + name_col, y_before)
            pdf.multi_cell(val_col, row_h, str(val), border=1, align="C")
            pdf.set_xy(left_x, max(y_after_name, pdf.get_y()))
    pdf.ln(6)
           
    # Estadísticas / porcentajes 
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, " Estadísticas", ln=1)
    pdf.ln(2)

    # Cabecera tabla estadísticas
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(name_col, row_h, "Indicador", border=1, fill=True)
    pdf.cell(val_col, row_h, "Valor", border=1, fill=True, ln=1)

    pdf.set_font("Arial", "", 10)
    for stat in ATRIBUTOS_PORCENTAJE:
        val = informe.get(stat, "")
        if str(val).strip() != "" and str(val) not in ["0", "0.0"]:   # 👈 filtro
            x_before = pdf.get_x()
            y_before = pdf.get_y()
            pdf.multi_cell(name_col, row_h, str(stat), border=1)
            y_after_name = pdf.get_y()
            pdf.set_xy(left_x + name_col, y_before)
            pdf.multi_cell(val_col, row_h, f"{val}%", border=1, align="C")
            pdf.set_xy(left_x, max(y_after_name, pdf.get_y()))
    pdf.ln(8)
        
    # Observaciones
    obs = informe.get("Observaciones", "")
    if obs:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, " Observaciones", ln=1)
        pdf.ln(2)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, obs)

    # Guardar fichero
    pdf.output(file_name)
    return file_name

# === INTERFAZ STREAMLIT ===
st.set_page_config(page_title="Scouting UD Lanzarote", layout="wide")
st.title("📊 Scouting   UD Lanzarote")

# Sidebar - SOLO las 4 tablas principales
# === LOGO EN LA SIDEBAR ===
logo_path = "ud_lanzarote_logo3.png"  # Asegúrate de que este archivo está en la misma carpeta que el app.py
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width=160)
st.sidebar.title("Menú")
# Menú lateral según rol
if st.session_state.role == "admin":
    menu = st.sidebar.radio("", TABLES + ["Formulario", "Radar"])
elif st.session_state.role == "scout":
    menu = st.sidebar.radio("", ["Formulario"])
# --- Botón de Cerrar sesión ---
if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()
# Cargar la tabla seleccionada
df, path = load_table(menu)

# ---------------------------
# CREAR SCOUT (form persistente con session_state)
# ---------------------------
if menu == "Scouts":
    # Inicializar flag en session_state
    if "show_create_scout_form" not in st.session_state:
        st.session_state.show_create_scout_form = False

    # Botón para abrir formulario
    if st.button("➕ Nuevo Scout"):
        st.session_state.show_create_scout_form = True

    # Mostrar formulario si el flag está activo
    if st.session_state.show_create_scout_form:
        with st.form("form_crear_scout"):
            st.write("### ✏️ Nuevo Scout")

            nuevo_scout = {}
            scouts_df, _ = load_table("Scouts")

            # Si la tabla está vacía, ponemos un campo por defecto
            columnas = scouts_df.columns.tolist() if not scouts_df.empty else ["Nombre scout"]

            # Generamos dinámicamente inputs según las columnas
            for col_name in columnas:
                # Si la columna parece de fecha, usar date_input
                if "fecha" in col_name.lower():
                    valor = st.date_input(col_name, value=date.today(), key=f"ns_{col_name}")
                    nuevo_scout[col_name] = valor.strftime("%Y-%m-%d")
                else:
                    # texto por defecto
                    valor = st.text_input(col_name, key=f"ns_{col_name}")
                    nuevo_scout[col_name] = valor

            # Botones Guardar / Cancelar
            col_guardar, col_cancelar = st.columns(2)
            guardar = col_guardar.form_submit_button("✅ Guardar scout")
            cancelar = col_cancelar.form_submit_button("❌ Cancelar")

            if guardar:
                # Validación mínima: nombre obligatorio
                if not str(nuevo_scout.get("Nombre scout", "")).strip():
                    st.error("El nombre del scout es obligatorio.")
                else:
                    add_new_record("Scouts", nuevo_scout)
                    st.success(f"Scout '{nuevo_scout['Nombre scout']}' añadido correctamente ✅")
                    st.session_state.show_create_scout_form = False
                    st.rerun()

            if cancelar:
                st.session_state.show_create_scout_form = False
                st.rerun()

# ---------------------------
# CREAR JUGADOR (form persistente con session_state)
# ---------------------------
if menu == "Jugadores":
    # botón para abrir el formulario
    if st.button("➕ Crear jugador"):
        st.session_state.show_create_player_form = True

    # mostrar el formulario si el flag está activo
    if st.session_state.show_create_player_form:
        with st.form("form_crear_jugador"):
            st.write("### ✏️ Nuevo jugador")

            nuevo_jugador = {}
            nuevo_jugador["Nombre jugador"] = st.text_input("Nombre jugador", key="nj_nombre")
            # Guardamos fecha en formato YYYY-MM-DD
            fecha_nac = st.date_input(
                "Fecha de nacimiento",
                min_value=date(1900, 1, 1),
                value=date.today(),
                max_value=date.today(),
                key="nj_fecha"
            )
            nuevo_jugador["Fecha de nacimiento"] = fecha_nac.strftime("%Y-%m-%d")
            nuevo_jugador["Club"] = st.text_input("Club", key="nj_club")
            nuevo_jugador["Sub 23"] = st.selectbox("Sub 23", ["Sí", "No"], key="nj_sub23")

            col_guardar, col_cancelar = st.columns(2)
            guardar = col_guardar.form_submit_button("✅ Guardar jugador")
            cancelar = col_cancelar.form_submit_button("❌ Cancelar")

            if guardar:
                if not str(nuevo_jugador["Nombre jugador"]).strip():
                    st.error("El nombre del jugador es obligatorio.")
                else:
                    add_new_record("Jugadores", nuevo_jugador)
                    st.success(f"Jugador '{nuevo_jugador['Nombre jugador']}' añadido correctamente ✅")
                    st.session_state.show_create_player_form = False
                    # forzar recarga para que la tabla se actualice
                    st.rerun()

            if cancelar:
                st.session_state.show_create_player_form = False
                st.rerun()

# ---------------------------
# CREAR FORMULARIO (form persistente)
# ---------------------------
if menu == "Formulario":
    st.subheader("📝 Crear informes")
    col_nuevo, col_nuevo_unreg = st.columns(2)

    if col_nuevo.button("📝 Nuevo informe de jugador registrado"):
        st.session_state.show_create_report_form = True
        st.session_state.show_create_unreg_report_form = False

    if col_nuevo_unreg.button("📝 Nuevo informe de jugador no registrado"):
        st.session_state.show_create_unreg_report_form = True
        st.session_state.show_create_report_form = False
    # ---------------------------
    # Formulario normal (jugador registrado)
    # ---------------------------
    if st.session_state.get("show_create_report_form", False):
        with st.form("form_crear_informe"):
            st.write("### 📋 Nuevo informe de jugador (registrado)")

            if df.empty:
                columnas = ["Fecha informe", "Scout","Temporada", "Competición", "Equipo local", "Equipo visitante", "Jugador", "Posición", "Lateralidad", "Acción", "Observaciones"] + ATRIBUTOS_VALORABLES + ATRIBUTOS_PORCENTAJE

            else:
                columnas = df.columns.tolist()
            scouts_df, _ = load_table("Scouts")
            jugadores_df, _ = load_table("Jugadores")
            posiciones_df, _ = load_table("Posiciones")

            nuevo_informe = {}

            # Fecha del informe (siempre arriba)
            fecha_informe = st.date_input("Fecha del informe", value=date.today(), key="ni_fecha")
            nuevo_informe["Fecha informe"] = fecha_informe.strftime("%Y-%m-%d")

            # Campos descriptivos (en una sola columna)
            campos_descriptivos = [
                col for col in columnas
                if col not in ["Sub 23", "Fecha de nacimiento", "Club", "Acción", "Observaciones", "Fecha informe"]
                + ATRIBUTOS_VALORABLES + ATRIBUTOS_PORCENTAJE
            ]
            for idx, col_name in enumerate(campos_descriptivos):
                low = col_name.lower()
                if low == "scout" and not scouts_df.empty:
                    nuevo_informe[col_name] = st.selectbox(f"{col_name}:", scouts_df["Nombre scout"].dropna().unique(), key=f"ni_scout_{idx}")
                elif low == "jugador" and not jugadores_df.empty:
                    jugador_sel = st.selectbox(f"{col_name}:", jugadores_df["Nombre jugador"].dropna().unique(), key=f"ni_jugador_{idx}")
                    nuevo_informe[col_name] = jugador_sel
                    # auto-completar
                    fila = jugadores_df.loc[jugadores_df["Nombre jugador"] == jugador_sel]
                    if not fila.empty:
                        if "Sub 23" in jugadores_df.columns:
                            nuevo_informe["Sub 23"] = fila["Sub 23"].values[0]
                        if "Fecha de nacimiento" in jugadores_df.columns:
                            nuevo_informe["Fecha de nacimiento"] = fila["Fecha de nacimiento"].values[0]
                        if "Club" in jugadores_df.columns:
                            nuevo_informe["Club"] = fila["Club"].values[0]
                elif low == "posición" and not posiciones_df.empty:
                    nuevo_informe[col_name] = st.selectbox(f"{col_name}:", posiciones_df.iloc[:, 0].dropna().unique(), key=f"ni_pos_{idx}")
                elif low == "lateralidad":
                    nuevo_informe[col_name] = st.selectbox(f"{col_name}:", ["Diestro", "Zurdo", "Ambas"], key=f"ni_lat_{idx}")
                else:
                    nuevo_informe[col_name] = st.text_input(f"{col_name}:", key=f"ni_txt_{idx}")

            # Atributos (sliders) en 3 columnas
            atributos = [a for a in columnas if a in ATRIBUTOS_VALORABLES]
            if atributos:
                st.markdown("#### ⚡ Atributos valorables")
                num_cols = 3
                cols_sl = st.columns(num_cols)
                for idx, attr in enumerate(atributos):
                    c = cols_sl[idx % num_cols]
                    nuevo_informe[attr] = c.slider(attr, 0, 5, 0, 1, key=f"ni_attr_{idx}")

            # Porcentajes (2 columnas)
            porcentajes = [a for a in columnas if a in ATRIBUTOS_PORCENTAJE]
            if porcentajes:
                st.markdown("#### 📊 Estadísticas")
                c1, c2 = st.columns(2)
                for idx, stat in enumerate(porcentajes):
                    target = c1 if idx % 2 == 0 else c2
                    nuevo_informe[stat] = target.number_input(stat, min_value=0, max_value=100, step=1, key=f"ni_pct_{idx}")

            # Acción y Observaciones
            if "Acción" in columnas:
                nuevo_informe["Acción"] = st.selectbox("Acción:", ["Fichar", "Descartar", "Seguir ojeando"], key="ni_accion")
            if "Observaciones" in columnas:
                nuevo_informe["Observaciones"] = st.text_area("Observaciones:", height=120, key="ni_obs")

            col_save, col_cancel = st.columns(2)
            guardar = col_save.form_submit_button("✅ Guardar informe")
            cancelar = col_cancel.form_submit_button("❌ Cancelar")

            if guardar and nuevo_informe:
                add_new_record("Informes", nuevo_informe)
                st.success("Nuevo informe añadido correctamente ✅")
                st.session_state.show_create_report_form = False
                st.rerun()

            if cancelar:
                st.session_state.show_create_report_form = False
                st.rerun()


    # ---------------------------
    # Formulario alternativo (jugador no registrado)
    # ---------------------------
    if st.session_state.get("show_create_unreg_report_form", False):
        with st.form("form_crear_informe_unreg"):
            st.write("### 📋 Nuevo informe de jugador **no registrado**")

            nuevo_informe = {}

            # Fecha del informe
            fecha_informe = st.date_input("Fecha del informe", value=date.today(), key="niu_fecha")
            nuevo_informe["Fecha informe"] = fecha_informe.strftime("%Y-%m-%d")

                # Scout
            scouts_df, _ = load_table("Scouts")
            if not scouts_df.empty:
                nuevo_informe["Scout"] = st.selectbox("Scout:", scouts_df["Nombre scout"].dropna().unique(), key="niu_scout")

            # Datos manuales del jugador
            nuevo_informe["Temporada"] = st.text_input("Temporada", key="niu_temporada")
            nuevo_informe["Competición"] = st.text_input("Competición", key="niu_competicion")
            nuevo_informe["Equipo local"] = st.text_input("Equipo local", key="niu_local")
            nuevo_informe["Equipo visitante"] = st.text_input("Equipo visitante", key="niu_visitante")
            nuevo_informe["Jugador"] = st.text_input("Nombre jugador", key="niu_jugador")
            fecha_nac = st.date_input("Fecha de nacimiento", min_value=date(1900,1,1), max_value=date.today(), value=date.today(), key="niu_fnac")
            nuevo_informe["Fecha de nacimiento"] = fecha_nac.strftime("%Y-%m-%d")
            nuevo_informe["Club"] = st.text_input("Club", key="niu_club")
            nuevo_informe["Sub 23"] = st.selectbox("Sub 23", ["Sí", "No"], key="niu_sub23")

            # Posición
            posiciones_df, _ = load_table("Posiciones")
            if not posiciones_df.empty:
                nuevo_informe["Posición"] = st.selectbox("Posición:", posiciones_df.iloc[:, 0].dropna().unique(), key="niu_pos")

            # Lateralidad
            nuevo_informe["Lateralidad"] = st.selectbox("Lateralidad:", ["Diestro", "Zurdo", "Ambas"], key="niu_lat")

            # Atributos (sliders)
            st.markdown("#### ⚡ Atributos valorables")
            num_cols = 3
            cols_sl = st.columns(num_cols)
            for idx, attr in enumerate(ATRIBUTOS_VALORABLES):
                nuevo_informe[attr] = cols_sl[idx % num_cols].slider(attr, 0, 5, 0, 1, key=f"nr_attr_{idx}")

            # Porcentajes
            porcentajes = [a for a in df.columns if a in ATRIBUTOS_PORCENTAJE]
            if porcentajes:
                st.markdown("#### 📊 Estadísticas")
                c1, c2 = st.columns(2)
                for idx, stat in enumerate(porcentajes):
                    target = c1 if idx % 2 == 0 else c2
                    nuevo_informe[stat] = target.number_input(stat, min_value=0, max_value=100, step=1, key=f"niu_pct_{idx}")

            # Acción y Observaciones
            nuevo_informe["Acción"] = st.selectbox("Acción:", ["Fichar", "Descartar", "Seguir ojeando"], key="niu_accion")
            nuevo_informe["Observaciones"] = st.text_area("Observaciones:", height=120, key="niu_obs")

            col_save, col_cancel = st.columns(2)
            guardar = col_save.form_submit_button("✅ Guardar informe")
            cancelar = col_cancel.form_submit_button("❌ Cancelar")

            if guardar and nuevo_informe.get("Jugador", "").strip():
                # Guardar informe en Informes
                add_new_record("Informes", nuevo_informe)

                # Guardar también el jugador en la tabla Jugadores si no existe
                jugadores_df, jugadores_path = load_table("Jugadores")
                nombre_jugador = nuevo_informe["Jugador"]

                if "Nombre jugador" in jugadores_df.columns:
                    ya_existe = nombre_jugador in jugadores_df["Nombre jugador"].values
                else:
                    ya_existe = False

                if not ya_existe:
                    nuevo_jugador = {
                        "Nombre jugador": nombre_jugador,
                        "Fecha de nacimiento": nuevo_informe.get("Fecha de nacimiento", ""),
                        "Club": nuevo_informe.get("Club", ""),
                        "Sub 23": nuevo_informe.get("Sub 23", "")
                    }
                    add_new_record("Jugadores", nuevo_jugador)

                st.success("Nuevo informe (jugador no registrado) añadido correctamente ✅")
                st.session_state.show_create_unreg_report_form = False
                st.rerun()
            if cancelar:
                st.session_state.show_create_unreg_report_form = False
                st.rerun()

# ---------------------------
# MOSTRAR / EDITAR TABLAS SEGÚN PESTAÑA
# ---------------------------
df, path = load_table(menu)
if menu in ["Posiciones", "Jugadores", "Scouts"]:
    # Subtítulo y tabla normales
    st.subheader(f"Datos de {menu}")
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_{menu}"
    )
    if st.button("💾 Guardar cambios", key=f"save_{menu}"):
        save_table(edited_df, path)
        st.success(f"{menu} actualizado correctamente ✅")
        st.rerun()
elif menu == "Informes":
    # Botón "Nuevo informe" ya está definido antes
    if not df.empty:
        st.markdown("---")
        st.markdown("### 📋 Lista de Informes")
        # ---------------------------
        # FILTROS
        # ---------------------------
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            scout_filter = st.multiselect(
                "Scout",
                sorted(df["Scout"].dropna().unique()) if "Scout" in df.columns else [],
                key="filter_scout"
            )
        with col2:
            jugador_filter = st.multiselect(
                "Jugador",
                sorted(df["Jugador"].dropna().unique()) if "Jugador" in df.columns else [],
                key="filter_jugador"
            )
        with col3:
            sub23_filter = st.multiselect(
                "Sub 23",
                sorted(df["Sub 23"].dropna().unique()) if "Sub 23" in df.columns else [],
                key="filter_sub23"
            )
        with col4:
            posicion_filter = st.multiselect(
                "Posición",
                sorted(df["Posición"].dropna().unique()) if "Posición" in df.columns else [],
                key="filter_posicion"
            )
        with col5:
            accion_filter = st.multiselect(
                "Acción",
                sorted(df["Acción"].dropna().unique()) if "Acción" in df.columns else [],
                key="filter_accion"
            )
        # ---------------------------
        # FILTRADO DE DATOS
        # ---------------------------
        df_filtrado = df.copy()
        if scout_filter and "Scout" in df.columns:
            df_filtrado = df_filtrado[df_filtrado["Scout"].isin(scout_filter)]
        if jugador_filter and "Jugador" in df.columns:
            df_filtrado = df_filtrado[df_filtrado["Jugador"].isin(jugador_filter)]
        if sub23_filter and "Sub 23" in df.columns:
            df_filtrado = df_filtrado[df_filtrado["Sub 23"].isin(sub23_filter)]
        if posicion_filter and "Posición" in df.columns:
            df_filtrado = df_filtrado[df_filtrado["Posición"].isin(posicion_filter)]
        if accion_filter and "Acción" in df.columns:
            df_filtrado = df_filtrado[df_filtrado["Acción"].isin(accion_filter)]
        # ---------------------------
        # DATA EDITOR CON KEY ÚNICO
        # ---------------------------
        edited_df = st.data_editor(
            df_filtrado,
            num_rows="dynamic",
            use_container_width=True,
            key="data_editor_Informes"
        )
        # ---------------------------
        # BOTÓN GUARDAR
        # ---------------------------
        if st.button("💾 Guardar cambios", key="save_Informes"):
            save_table(edited_df, path)
            st.success("Informes actualizado correctamente ✅")
            st.rerun()
    else:
        st.info("No hay informes disponibles.")
else:  # Radar
    # No mostramos tabla ni subtítulo
    edited_df = df  # para que el resto del código no falle
# ---------------------------
# EXPORTAR A PDF (solo en Informes)
# ---------------------------
if menu == "Informes" and not df.empty:
    st.markdown("---")
    st.markdown("### 📤 Exportar informe a PDF")
    # Elegir informe por índice (evita ambigüedades si hay varios informes para el mismo jugador)
    index_options = df.index.tolist()
    sel_index = st.selectbox(
        "Selecciona el informe:",
        index_options,
        format_func=lambda i: f"{i} — {df.loc[i].get('Jugador','')} — {df.loc[i].get('Fecha informe','')}"
    )
    if st.button("📄 Generar PDF"):
        informe_dict = df.loc[sel_index].to_dict()
        try:
            pdf_path = generar_pdf(informe_dict)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=f,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Error generando PDF: {e}")
# === NUEVA PESTAÑA RADAR ===
if menu == "Radar":
    st.subheader("📊 Radar de atributos")
    # Cargar jugadores e informes
    jugadores, _ = load_table("Jugadores")
    informes, _ = load_table("Informes")
    if jugadores.empty or informes.empty:
        st.warning("No hay jugadores o informes disponibles todavía.")
    else:
        # Selector de jugador
        jugador_seleccionado = st.selectbox(
            "Selecciona un jugador:",
            jugadores["Nombre jugador"].dropna().unique()
        )
        # Fila de informe más reciente para el jugador
        informe_jugador = informes[informes["Jugador"] == jugador_seleccionado]
        if informe_jugador.empty:
            st.warning(f"No hay informes para {jugador_seleccionado}")
        else:
            datos_jugador = informe_jugador.iloc[-1]  # último informe
            # === Dividir atributos ===
            atributos_portero = [
            "Juego con los pies",
            "Juego aéreo","Reflejos (Bajo palos)",
            "Blocajes",
            "Salidas (mano a mano)",
            "Despejes",
            "Velocidad de reacción",
            "Colocación"
            ]
            atributos_defensa = [
            "Salida de balón (corto)",
            "Salida de balón (largo)",
            "Duelos",
            "Duelos aéreos",
            "Resistencia",
            "Velocidad",
            "Precisión en el pase corto",
            "Precisión en el pase largo",
            "Presión mental",
            "Liderazgo"     
            ]
            atributos_medios = [
            "Colocación",
            "Salida de balón (corto)",
            "Salida de balón (largo)",
            "Duelos",
            "Duelos aéreos",
            "Resistencia",
            "Velocidad",
            "Precisión en el pase corto",
            "Precisión en el pase largo",
            "Llegada al área rival",
            "Presión mental",
            "Liderazgo"                
            ]
            atributos_ataque = [
            "Resistencia",
            "Velocidad",
            "Presión",
            "Desmarques",
            "Desborde",
            "Gol",
            "Descargas",
            "Remate de cabeza",
            "Disparos",
            "Presión mental",
            "Liderazgo",   
            ]
            grupo = st.radio("Selecciona grupo de atributos:",["Porteros", "Defensas", "Mediocampistas", "Atacantes"])
            if grupo == "Porteros":
                atributos = atributos_portero
            elif grupo == "Defensas":
                atributos = atributos_defensa
            elif grupo == "Mediocampistas":
                atributos = atributos_medios
            else:
                atributos = atributos_ataque
            if st.button("🎯 Generar radar"):
                # Filtrar valores
                valores = [float(datos_jugador.get(attr, 0)) for attr in atributos]
                # Crear gráfico radar
                N = len(atributos)
                valores += valores[:1]  # cerrar el polígono
                angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
                angles += angles[:1]

                fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

                ax.plot(angles, valores, linewidth=2, linestyle='solid')
                ax.fill(angles, valores, alpha=0.25)

                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(atributos, fontsize=9)
                ax.set_yticks(range(0, 6))  # porque tus sliders son de 0 a 5
                ax.set_title(f"Radar de {jugador_seleccionado}", size=14, weight="bold")
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.pyplot(fig)

