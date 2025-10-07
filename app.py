import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from fpdf import FPDF
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import math
from PIL import Image

# === LOGIN CON ROLES ===
USERS = {
    "Iván Manrique Márquez": {"password": "admin", "role": "admin"},
    "Sergio David Hernández Viñoly": {"password": "admin1", "role": "admin"},
    "José Manuel Sánchez Padrón": {"password": "scoutjms", "role": "scout"},
    "Víctor Manuel Páez Romero": {"password": "scoutvmp", "role": "scout"},
    "Enrique Guillén Peñate": {"password": "scoutegp", "role": "scout"},
    "César Saavedra Reyes": {"password": "scoutcsr", "role": "scout"},
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
                st.session_state.scout_name = usuario # guardar nombre del scout
                st.success(f"✅ Bienvenido, {usuario} ({st.session_state.role})")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
        st.stop()

# === CONFIGURACIÓN ===
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")  # Carpeta "data"
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

def _insert_image_safely(pdf, img_path, w_mm=90, x=None, pad_bottom=6, title=None):
    """
    Inserta una imagen respetando saltos de página:
      - Mantiene proporción calculando h a partir de w.
      - Si no cabe en la página actual, añade página.
      - Coloca un título (opcional) encima.
      - Ajusta el cursor al final de la imagen + padding.
    """
    
    # Medidas y márgenes
    page_h = getattr(pdf, "h", 297)  # A4 por defecto en mm
    left_margin  = getattr(pdf, "l_margin", 10)
    bottom_margin = getattr(pdf, "b_margin", 10)
    
    # Posición X por defecto
    if x is None:
        x = left_margin

    # Altura de la imagen en mm (preservando aspecto)
    with Image.open(img_path) as im:
        w_px, h_px = im.size
    aspect = (h_px / float(w_px)) if w_px else 1.0
    h_mm = w_mm * aspect

    # Altura extra si hay título
    title_h = 0
    if title:
        title_h = 6
        if pdf.get_y() + title_h > page_h - bottom_margin:
            pdf.add_page()
    
    # Comprobar si la imagen cabe; si no, saltar de página
    if pdf.get_y() + title_h + h_mm > page_h - bottom_margin:
        pdf.add_page()

    # Título (opcional)
    if title:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_x(x)
        pdf.cell(0, 6, title, ln=1)
    
    # Dibujo de imagen
    y = pdf.get_y()
    pdf.image(img_path, x=x, y=y, w=w_mm)
    pdf.set_y(y + h_mm + pad_bottom)

#Gráfico Radar Informe vs media
def _build_radar_image_union(current_vals: dict, mean_vals: dict, out_path: str, title: str = ""):
    """
    Variante: incluye categorías si al menos una serie tiene valor > 0.
    - En el eje donde una de las dos series no tenga valor > 0, esa serie se grafica con 0.
    """

    all_keys = set(current_vals.keys()) | set(mean_vals.keys())

    def _clean(v):
        try:
            x = float(v)
            return 0.0 if math.isnan(x) else x
        except Exception:
            return 0.0

    raw_curr = {k: _clean(current_vals.get(k, 0)) for k in all_keys}
    raw_mean = {k: _clean(mean_vals.get(k, 0)) for k in all_keys}
    attrs = [k for k in sorted(all_keys) if (raw_curr[k] > 0 or raw_mean[k] > 0)]

    # Placeholder si no hay suficientes ejes
    if len(attrs) < 3:
        fig = plt.figure(figsize=(3.35, 3.35), dpi=300)
        plt.text(0.5, 0.5, "Sin suficientes\natributos válidos", ha='center', va='center')
        plt.axis('off')
        fig.savefig(out_path, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        return

    values_curr = [raw_curr.get(a, 0.0) for a in attrs]
    values_mean = [raw_mean.get(a, 0.0) for a in attrs]
    values_curr += values_curr[:1]
    values_mean += values_mean[:1]

    N = len(attrs)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig = plt.figure(figsize=(3.35, 3.35), dpi=300)  # ≈ 85 x 85 mm
    ax = plt.subplot(111, polar=True)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(attrs, fontsize=7)
    ax.set_rlabel_position(0)
    ax.set_ylim(0, 5)
    ax.set_yticks([1, 2, 3, 4, 5])

    ax.plot(angles, values_curr, linewidth=2)
    ax.fill(angles, values_curr, alpha=0.15)
    ax.plot(angles, values_mean, linewidth=2)
    ax.fill(angles, values_mean, alpha=0.15)

    if title:
        ax.set_title(title, va='bottom', fontsize=9)

    fig.tight_layout(pad=0.6)
    fig.savefig(out_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)

def _insert_two_images_row(pdf, left_img_path, right_img_path, w_mm=90, gap_mm=8, pad_bottom=8):
    """
    Inserta dos imágenes alineadas horizontalmente en la misma fila:
      - Ajusta Y para que ambas queden a la misma altura (sin 'diagonal').
      - Calcula la altura mayor y mueve el cursor por debajo de la fila.
      - Si no cabe la fila completa, salta de página antes de dibujar.

    Si 2*w_mm + gap + márgenes > ancho de página, reduce w_mm automáticamente.
    """
    from PIL import Image

    page_w = getattr(pdf, "w", 210)   # A4 ancho mm
    page_h = getattr(pdf, "h", 297)   # A4 alto  mm
    lmar   = getattr(pdf, "l_margin", 10)
    rmar   = getattr(pdf, "r_margin", 10)
    bmar   = getattr(pdf, "b_margin", 10)

    # Asegurar que caben dos imágenes; si no, recalcular w_mm
    total_needed = 2 * w_mm + gap_mm + lmar + rmar
    if total_needed > page_w:
        w_mm = (page_w - lmar - rmar - gap_mm) / 2.0

    # Alturas preservando aspecto
    def _img_h_mm(p, w_target):
        with Image.open(p) as im:
            w_px, h_px = im.size
        aspect = (h_px / float(w_px)) if w_px else 1.0
        return w_target * aspect

    h_left  = _img_h_mm(left_img_path,  w_mm)
    h_right = _img_h_mm(right_img_path, w_mm)
    row_h   = max(h_left, h_right)

    # ¿Cabe la fila completa? si no, salto de página
    y0 = pdf.get_y()
    if y0 + row_h > page_h - bmar:
        pdf.add_page()
        y0 = pdf.get_y()

    # Coordenadas
    x_left  = lmar
    x_right = lmar + w_mm + gap_mm

    # Insertar ambas a la MISMA y
    pdf.image(left_img_path,  x=x_left,  y=y0, w=w_mm)
    pdf.image(right_img_path, x=x_right, y=y0, w=w_mm)

    # Avanzar cursor bajo la fila
    pdf.set_y(y0 + row_h + pad_bottom)


#  FUNCIÓN DE GENERACIÓN DE PDF (FPDF2) #
def generar_pdf(informe, logo_path="ud_lanzarote_logo3.png", logo_path_wm="ud_lanzarote_logo3bn.png", ttf_path="DejaVuSans.ttf"):
    """
    Genera un PDF con encabezado diferenciado, escudo, línea divisoria,
    tabla de atributos, tabla de estadísticas y bloque de observaciones.
    Devuelve la ruta del fichero generado.
    """
    # Nombre de fichero (reemplazamos espacios por guiones)
    jugador_safe = str(informe.get("Jugador", "desconocido")).replace(" ", "_")
    fecha_safe = str(informe.get("Fecha informe", datetime.today().strftime("%d-%m-%Y")))
    file_name = f"Informe_{jugador_safe}_{fecha_safe}.pdf"
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Página y dimensiones
    page_w = pdf.w - 2 * pdf.l_margin  # ancho
    left_x = pdf.l_margin

    # Registrar fuente Unicode
    if os.path.exists(ttf_path):
        pdf.add_font("DejaVu", "", ttf_path, uni=True)
        pdf.set_font("DejaVu", "", 14)
    else:
        pdf.set_font("Arial", "", 12)  # fallback

    # --- Marca de agua ---
    if os.path.exists(logo_path_wm):
        try:
            watermark_w = 160
            watermark_h = 240
            x = (pdf.w - watermark_w) / 2
            y = (pdf.h - watermark_h) / 1.3
            pdf.image(logo_path_wm, x, y, watermark_w, watermark_h)
        except:
            pass

    # Logo (si existe)
    if os.path.exists(logo_path):
        try:
            logo_w = 25 
            logo_h = 35
            pdf.image(logo_path, left_x , 2.5, logo_w, logo_h)
        except Exception:
            pass

    # Título centralizado dentro del encabezado
    pdf.set_xy(left_x, 5)
    pdf.set_font("DejaVu", "", 20)
    title = f"Sistema de Scouting UD Lanzarote"
    pdf.cell(page_w, 10, title, ln=1, align="C")

    # Subtítulo con fecha y scout
    pdf.set_y(pdf.get_y() + 5)  # añadimos 10 mm de espacio
    pdf.set_font("DejaVu", "", 12+1)
    subt = f"Fecha: {informe.get('Fecha informe','')}    -    Scout: {informe.get('Scout','')}"
    pdf.cell(page_w, 7, subt, ln=1, align="C")

    pdf.ln(12)

    # Línea divisoria de color (roja)
    pdf.set_draw_color(200, 0, 0)
    pdf.set_line_width(0.8)
    y_line = pdf.get_y()
    pdf.line(left_x, y_line, left_x + page_w, y_line)
    pdf.ln(6)

    # --- Bloque: Información del jugador ---
    pdf.set_font("DejaVu", "", 12)  # fuente normal para los datos
    # Lista de campos
    campos = [
        ("Nombre del jugador", informe.get("Jugador", "")),
        ("Fecha de nacimiento", informe.get("Fecha de nacimiento", "")),
        ("Club", informe.get("Club", "")),
        ("Posición", informe.get("Posición", "")),
        ("Lateralidad", informe.get("Lateralidad", ""))
    ]

    for etiqueta, valor in campos:
        pdf.cell(page_w, 6, f"{etiqueta}: {valor}", ln=1, align="L")
    pdf.ln(6)

    # Tablas
    name_col = int(page_w * 0.75)  # columna nombre atributo
    val_col = int(page_w * 0.25)   # columna valor
    row_h = 8

    # Tabla Atributos
    pdf.set_font("DejaVu", "", 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(name_col, row_h, "Atributos valorables", border=0, fill=True)
    pdf.cell(val_col, row_h, "Valor (0-5)", border=0, fill=True, align="C", ln=1)

    # Filas: usamos multi_cell para el nombre por si se parte
    pdf.set_font("DejaVu", "", 12)
    for attr in ATRIBUTOS_VALORABLES:
        val = informe.get(attr, "")
        if str(val).strip() != "" and str(val) not in ["0", "0.0"]:
            try:
                val_num = max(0, min(5, int(round(float(val)))))
                estrellas = "★" * val_num + "☆" * (5 - val_num)
            except Exception:
                estrellas = "N/A"  # fallback en caso de error
            x_before = pdf.get_x()
            y_before = pdf.get_y()
            pdf.multi_cell(name_col, row_h, str(attr), border=0)
            y_after_name = pdf.get_y()
            pdf.set_xy(left_x + name_col, y_before)
            pdf.multi_cell(val_col, row_h, estrellas, border=0, align="C")
            pdf.set_xy(left_x, max(y_after_name, pdf.get_y()))
    pdf.ln(6)
           
    # Tabla estadísticas
    pdf.set_font("DejaVu", "", 12)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(name_col, row_h, "Datos estadísticos", border=0, fill=True)
    pdf.cell(val_col, row_h, "Valor", border=0, fill=True,align="C", ln=1)

    pdf.set_font("DejaVu", "", 12)
    for stat in ATRIBUTOS_PORCENTAJE:
        val = informe.get(stat, "")
        if str(val).strip() != "" and str(val) not in ["0", "0.0"]:   # 👈 filtro
            x_before = pdf.get_x()
            y_before = pdf.get_y()
            pdf.multi_cell(name_col, row_h, str(stat), border=0)
            y_after_name = pdf.get_y()
            pdf.set_xy(left_x + name_col, y_before)
            pdf.multi_cell(val_col, row_h, f"{val}%", border=0, align="C")
            pdf.set_xy(left_x, max(y_after_name, pdf.get_y()))
    pdf.ln(8)

        # === SECCIÓN DE GRÁFICOS RADAR ===
    try:
        # --- Radar 1: Informe actual vs Media del jugador ---
        informes_df, _ = load_table("Informes")

        jugador = informe.get("Jugador", "")
        # Serie actual
        curr_vals = {}
        for attr in ATRIBUTOS_VALORABLES:
            v = pd.to_numeric(informe.get(attr, None), errors="coerce")
            if pd.notna(v):
                curr_vals[attr] = float(v)

        # Media del jugador (ignorando ceros y NaN)
        mean_vals = {}
        if jugador and not informes_df.empty and "Jugador" in informes_df.columns:
            df_j = informes_df[informes_df["Jugador"] == jugador].copy()
            if not df_j.empty:
                for attr in ATRIBUTOS_VALORABLES:
                    if attr in df_j.columns:
                        col = pd.to_numeric(df_j[attr], errors="coerce").replace(0, np.nan)
                        m = col.mean(skipna=True)
                        if pd.notna(m) and m > 0:
                            mean_vals[attr] = float(m)

        # --- Radar 2: Media del jugador vs Media de su posición ---
        informes_all, _ = load_table("Informes")

        # Detectar columna de posición
        pos_col = None
        for cand in ["Posición", "Posicion", "position", "Position"]:
            if cand in informes_all.columns:
                pos_col = cand
                break

        jugador_pos = None
        if pos_col:
            df_j_all = informes_all[informes_all["Jugador"] == jugador]
            if not df_j_all.empty:
                jugador_pos = df_j_all.iloc[0][pos_col]

        # Medias de jugador (>0)
        player_mean = {}
        for a in ATRIBUTOS_VALORABLES:
            v = mean_vals.get(a, None)
            if v is not None and float(v) > 0:
                player_mean[a] = float(v)

        # Media de su posición (ignorando 0 -> NaN)
        pos_mean = {}
        if jugador_pos and pos_col:
            df_pos = informes_all[informes_all[pos_col] == jugador_pos].copy()
            if not df_pos.empty:
                for a in ATRIBUTOS_VALORABLES:
                    if a in df_pos.columns:
                        s = pd.to_numeric(df_pos[a], errors="coerce").replace(0, np.nan)
                        m = s.mean(skipna=True)
                        if pd.notna(m) and m > 0:
                            pos_mean[a] = float(m)

        # === GENERAR Y COLOCAR LOS DOS RADARES LADO A LADO ===
        if len(curr_vals) >= 1 and len(mean_vals) >= 1 and len(pos_mean) >= 1:
            img_left = f"_radar1_{jugador_safe}_{fecha_safe}.png"
            _build_radar_image_union(
                curr_vals, mean_vals, img_left,
                title=f"{jugador} — Informe vs Media"
            )

            img_right = f"_radar2_{jugador_safe}_{fecha_safe}.png"
            _build_radar_image_union(
                player_mean, pos_mean, img_right,
                title=f"{jugador} — Media vs {jugador_pos or 'Posición'}"
            )

            # Colocar ambos perfectamente alineados
            _insert_two_images_row(pdf, img_left, img_right, w_mm=90, gap_mm=8, pad_bottom=10)

            # Limpiar archivos temporales
            for p in [img_left, img_right]:
                try:
                    os.remove(p)
                except:
                    pass

    except Exception as e:
        # Evita que errores gráficos rompan la exportación
        pass


    # Observaciones
    obs = informe.get("Observaciones", "")
    if obs:
        # Encabezado "Observaciones"
        pdf.set_font("DejaVu", "", 12)
        pdf.set_fill_color(230, 230, 230)  # mismo fondo que cabeceras anteriores
        pdf.cell(name_col, row_h, "Observaciones", border=0, fill=True)
        pdf.cell(val_col, row_h, "", border=0, fill=True, ln=1)  # segunda columna vacía
        pdf.ln(2)
        pdf.set_font("DejaVu", "", 12)

        # Cuadro de texto blanco para observaciones
        y_start = pdf.get_y()
        pdf.set_fill_color(255, 255, 255)  # fondo blanco
        pdf.rect(left_x, y_start, page_w, 40, style="F")
        pdf.set_xy(left_x, y_start)
        pdf.multi_cell(0, 6, obs, border=0, fill=True)  # border=1 usa el color y grosor activos
        pdf.ln(10)
    
    # Guardar fichero
    pdf.output(file_name)
    return file_name

# === Función para estadísticas generales ===
def get_statistics(df):
    """Obtener estadísticas generales del sistema y mostrarlas en Streamlit"""
    if df.empty:
        st.info("No hay reportes para analizar")
        return
    
    stats = {
        'total_reportes': len(df),
        'scouts_activos': df['Scout'].nunique() if 'Scout' in df else 0,
        'jugadores_evaluados': df['Jugador'].nunique() if 'Jugador' in df else 0,
    }

    # Mostrar estadísticas generales
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📑 Total de reportes", stats['total_reportes'])
    col2.metric("🕵️ Scouts activos", stats['scouts_activos'])
    col3.metric("👟 Jugadores evaluados", stats['jugadores_evaluados'])

# === INTERFAZ STREAMLIT ===
st.set_page_config(page_title="Scouting UD Lanzarote", layout="wide")
st.title("📊 Scouting   UD Lanzarote")

# Sidebar - SOLO las 4 tablas principales
# === LOGO EN LA SIDEBAR ===
logo_path = "ud_lanzarote_logo3.png"  # Asegúrate de que este archivo está en la misma carpeta que el app.py
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width=160)
st.sidebar.title("UD Lanzarote")
# Menú lateral según rol
if st.session_state.role == "admin":
    menu = st.sidebar.radio("", ["Dashboard"] + TABLES + ["Formulario", "Buscar jugador", "Comparativa"])
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
# CREAR UN DASHBOARD
# ---------------------------

if menu == "Dashboard":

    informes, _ = load_table("Informes")

    if informes.empty:
        st.info("No hay informes disponibles todavía.")
    else:
        get_statistics(informes)
        # === Gráfico 1: Informes por scout (tarta) ===
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("🕵️ Scouts")
            informes_por_scout = informes["Scout"].value_counts().reset_index()
            informes_por_scout.columns = ["Scout", "Total"]
            fig1 = px.pie(informes_por_scout, names="Scout", values="Total", hole=0.3, color_discrete_sequence=["#2600ff", "#00b7ff", "#ff9633", "#ff0000"]) 
            #fig1.update_layout(legend=dict(x=-0.8))  # mueve horizontal (izquierda)
            fig1.update_layout(showlegend=False)  # ← oculta la leyenda
            
            st.plotly_chart(fig1, use_container_width=True)

        # === Gráfico 2: Informes por posición (barras) ===
        with col2:
            st.markdown("⚽ Posiciones")
            if "Posición" in informes.columns:
                informes_por_pos = informes["Posición"].value_counts().reset_index()
                informes_por_pos.columns = ["Posición", "Total"]
                informes_por_pos = informes_por_pos.sort_values("Total", ascending=False)
                fig2 = px.bar(
                    informes_por_pos,
                    x="Total",
                    y="Posición",
                    orientation="h",
                    text="Total",
                    color_discrete_sequence=["#ff0000"]
                )
                # Quitar títulos, números y líneas de cuadrícula
                fig2.update_yaxes(title=None, showgrid=False, autorange="reversed")
                fig2.update_xaxes(showticklabels=False, title=None, showgrid=False)
                st.plotly_chart(fig2, use_container_width=True)

        # === Panel de jugadores destacados ===
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("🌟 Jugadores destacados")

            atributos_cols = [c for c in informes.columns if c in ATRIBUTOS_VALORABLES]
            if atributos_cols:
                informes_num = informes.copy()
                for col in atributos_cols:
                    informes_num[col] = pd.to_numeric(informes_num[col], errors="coerce")

                informes_num[atributos_cols] = informes_num[atributos_cols].replace(0, np.nan) # ignorar ceros
                media_global = informes_num[atributos_cols].mean().mean()
                medias_jugador = informes_num.groupby("Jugador")[atributos_cols].mean().mean(axis=1)

                destacados = medias_jugador[medias_jugador > media_global].sort_values(ascending=False)

                if destacados.empty:
                    st.info("No hay jugadores por encima de la media global.")
                else:
                    # Mostrar solo top 5
                    top5 = destacados.head(5)

                    # Crear grid de 2 columnas
                    cols = st.columns(2)
                    for i, (jugador, media) in enumerate(top5.items()):
                        estrellas_llenas = int(round(media))
                        estrellas = "⭐" * estrellas_llenas + "☆" * (5 - estrellas_llenas)

                        # Elegir columna alternando
                        with cols[i % 2]:
                            st.markdown(
                                f"""
                                <div style="width:150px; height:150px;
                                            padding:15px; border-radius:12px;
                                            margin-bottom:15px; 
                                            background-color:#2c2c2c;
                                            border:2px solid #e74c3c;
                                            box-shadow:0px 4px 8px rgba(0,0,0,0.1);">
                                    <h4 style="margin:0; font-size:18px; color:#ecf0f1;">{jugador}</h4>
                                    <p style="margin:5px 0; font-size:16px; color:#f1c40f;">{estrellas}</p>
                                    <p style="margin:0; font-size:14px; color:#bdc3c7;">{media:.2f} / 5</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
        # === Gráfico 3: Acciones (columnas) ===
        with col4:
            st.markdown("🎯 Acción")
            if "Acción" in informes.columns:
                informes_por_accion = informes["Acción"].value_counts().reset_index()
                informes_por_accion.columns = ["Acción", "Total"]

                colores_accion = {
                    "Fichar": "#2ecc71",
                    "Seguir ojeando": "#e67e22",
                    "Descartar": "#e74c3c"
                }

                fig3 = px.bar(
                    informes_por_accion,
                    x="Acción",
                    y="Total",
                    text="Total",
                    color="Acción",
                    color_discrete_map=colores_accion,
                    category_orders={"Acción": ["Fichar", "Seguir ojeando", "Descartar"]}
                )
                # Quitar títulos, números y líneas de cuadrícula
                fig3.update_xaxes(title=None, showgrid=False)
                fig3.update_yaxes(showticklabels=False, title=None, showgrid=False)
                fig3.update_layout(showlegend=False)
                fig3.update_traces(textfont_color="black")
                st.plotly_chart(fig3, use_container_width=True)

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
                    nuevo_scout[col_name] = valor.strftime("%d-%m-%Y")
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
            nuevo_jugador["Fecha de nacimiento"] = fecha_nac.strftime("%d-%m-%Y")
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

            # Fecha del informe
            fecha_informe = st.date_input("Fecha del informe", value=date.today(), key="ni_fecha")
            # Guardamos en formato DD-MM-AAAA
            nuevo_informe["Fecha informe"] = fecha_informe.strftime("%d-%m-%Y")


            # Campos descriptivos (en una sola columna)
            campos_descriptivos = [col for col in columnas
                if col not in ["Sub 23", "Fecha de nacimiento", "Club", "Acción", "Observaciones", "Fecha informe"]
                + ATRIBUTOS_VALORABLES + ATRIBUTOS_PORCENTAJE]
            for idx, col_name in enumerate(campos_descriptivos):
                low = col_name.lower()
                if low == "scout":
                    if st.session_state.role == "admin":
                        # ✅ Admin puede elegir el scout al que asignar el informe
                        nuevo_informe[col_name] = st.selectbox(
                            f"{col_name}:",
                            scouts_df["Nombre scout"].dropna().unique(),
                            key=f"ni_scout_{idx}"
                        )
                    else:
                        # ✅ Si es scout, se asigna automáticamente al que ha iniciado sesión
                        nuevo_informe[col_name] = st.session_state.scout_name
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
            nuevo_informe["Fecha informe"] = fecha_informe.strftime("%d-%m-%Y")

            # Scout
            scouts_df, _ = load_table("Scouts")
            if st.session_state.role == "admin":
                # ✅ Admin puede elegir el scout al que asignar el informe
                if not scouts_df.empty:
                    nuevo_informe["Scout"] = st.selectbox(
                        "Scout:",
                        scouts_df["Nombre scout"].dropna().unique(),
                        key="niu_scout"
                    )
            else:
                # ✅ Si es scout, se asigna automáticamente al que ha iniciado sesión
                nuevo_informe["Scout"] = st.session_state.scout_name

            # Datos manuales del jugador
            nuevo_informe["Temporada"] = st.text_input("Temporada", key="niu_temporada")
            nuevo_informe["Competición"] = st.text_input("Competición", key="niu_competicion")
            nuevo_informe["Equipo local"] = st.text_input("Equipo local", key="niu_local")
            nuevo_informe["Equipo visitante"] = st.text_input("Equipo visitante", key="niu_visitante")
            nuevo_informe["Jugador"] = st.text_input("Nombre jugador", key="niu_jugador")
            fecha_nac = st.date_input("Fecha de nacimiento", min_value=date(1900,1,1), max_value=date.today(), value=date.today(), key="niu_fnac")
            nuevo_informe["Fecha de nacimiento"] = fecha_nac.strftime("%d-%m-%Y")
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
            if ATRIBUTOS_PORCENTAJE:
                st.markdown("#### 📊 Estadísticas")
                c1, c2 = st.columns(2)
                for idx, stat in enumerate(ATRIBUTOS_PORCENTAJE):
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

# === Pestaña Comparativa ===
if menu == "Comparativa":
    st.subheader("🆚 Comparativa de Jugadores")

    jugadores_df, _ = load_table("Jugadores")
    informes_df, _ = load_table("Informes")

    if jugadores_df.empty or informes_df.empty:
        st.info("No hay jugadores o informes para comparar todavía.")
    else:
        # Filtro opcional de posición
        posiciones = informes_df["Posición"].dropna().unique().tolist()
        pos_sel = st.selectbox("Filtrar por posición (opcional)", ["Todas"] + posiciones)

        # Filtrar dataframe según posición si se ha elegido una específica
        if pos_sel != "Todas":
            informes_filtrados = informes_df[informes_df["Posición"] == pos_sel]
        else:
            informes_filtrados = informes_df.copy()
        # Selección múltiple de jugadores
        seleccionados = st.multiselect(
            "Selecciona jugadores a comparar",
            informes_filtrados["Jugador"].tolist()
        )

        if len(seleccionados) >= 2:
            # Filtrar los jugadores seleccionados
            jugadores_sel = informes_df[informes_df["Jugador"].isin(seleccionados)]

            # Mostrar datos básicos
            st.markdown("#### 📋 Datos del jugador")
            st.dataframe(
                jugadores_sel[["Jugador", "Club", "Fecha de nacimiento", "Posición", "Lateralidad"]],
                use_container_width=True
            )

            # Calcular promedios de atributos (ignorando NaN y 0)
            promedios = []
            for jugador in seleccionados:
                informes_jugador = informes_df[informes_df["Jugador"] == jugador]
                if not informes_jugador.empty:
                    # Convertir a numérico
                    datos = informes_jugador[ATRIBUTOS_VALORABLES].apply(pd.to_numeric, errors="coerce")
                    # Reemplazar 0 por NaN para que no cuente
                    datos = datos.replace(0, np.nan)
                    medias = datos.mean(skipna=True)
                    medias["Nombre"] = jugador
                    promedios.append(medias)

            if promedios:
                df_promedios = pd.DataFrame(promedios).set_index("Nombre")

                # === Tarjetas de medias de jugadores seleccionados ===
                st.markdown("#### 🌟 Valoración media")

                # Crear fila de columnas, una por jugador
                cols = st.columns(len(df_promedios))

                for col, (jugador, fila) in zip(cols, df_promedios.iterrows()):
                    media_jugador = fila.dropna().mean()  # promedio real ignorando NaN/ceros
                    estrellas_llenas = int(round(media_jugador))
                    estrellas = "⭐" * estrellas_llenas + "☆" * (5 - estrellas_llenas)

                    with col:
                        st.markdown(
                            f"""
                            <div style="width:150px; height:150px; 
                                        padding:10px; border-radius:12px; 
                                        display:flex; flex-direction:column; justify-content:center; align-items:center;
                                        background-color:#2c2c2c;
                                        border:2px solid #e74c3c;
                                        box-shadow:0px 2px 6px rgba(0,0,0,0.1); 
                                        margin:auto;">
                                <h4 style="margin:0; font-size:18px; color:#ecf0f1; text-align:center;">{jugador}</h4>
                                <p style="margin:5px 0; font-size:16px; color:#f1c40f; text-align:center;">{estrellas}</p>
                                <p style="margin:0; font-size:14px; color:#bdc3c7; text-align:center;">{media_jugador:.2f} / 5</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                # Radar dinámico:
                # 1. Eliminar solo columnas donde todos los jugadores tienen NaN
                df_radar = df_promedios.dropna(axis=1, how="all").reset_index().melt(
                    id_vars="Nombre",
                    var_name="Atributo",
                    value_name="Valor"
                )
                # 2. Quitar NaN, pero mantener atributos que tengan valor aunque sea en un solo jugador
                df_radar = df_radar.dropna()

                st.markdown("#### 🕸️ Radar comparativo")
                fig = px.line_polar(
                    df_radar,
                    r="Valor",
                    theta="Atributo",
                    color="Nombre",
                    line_close=True,
                    range_r=[0, 5]
                )

                # Líneas más gruesas y rellenar con transparencia
                fig.update_traces(line=dict(width=3), fill='toself')

                # Configuración de ejes y fondo oscuro
                fig.update_layout(
                    polar=dict(
                        bgcolor="#2c2c2c",  # Fondo del radar oscuro
                        radialaxis=dict(
                            tick0=0,
                            dtick=1,
                            tickfont=dict(color="#ecf0f1"),  # Números en blanco grisáceo
                            showline=True,
                            linewidth=1,
                            linecolor="#bdc3c7",             # Ejes en gris claro
                            gridcolor="#444"                 # Grilla tenue
                        ),
                        angularaxis=dict(
                            tickfont=dict(color="#ecf0f1"),  # Atributos en blanco grisáceo
                            linecolor="#bdc3c7",
                            gridcolor="#444"
                        )
                    ),
                    legend=dict(title_text="", font=dict(color="#ecf0f1")),  # Leyenda en blanco
                    paper_bgcolor="#1e1e1e",   # Fondo de todo el gráfico oscuro
                    plot_bgcolor="#1e1e1e",
                    width=600,
                    height=600
                )

                st.plotly_chart(fig, use_container_width=True)

            else:
                st.warning("Los jugadores seleccionados no tienen informes registrados.")
        else:
            st.info("Selecciona al menos 2 jugadores para la comparativa.")
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
# === NUEVA PESTAÑA BUSCAR JUGADOR ===
if menu == "Buscar jugador":
    st.subheader("🔎 Buscar jugador")

    # Cargar tablas
    jugadores, _ = load_table("Jugadores")
    informes, _ = load_table("Informes")

    if jugadores.empty or informes.empty:
        st.warning("No hay jugadores o informes disponibles todavía.")
    else:
        # === Filtro por posición (opcional) ===
        posiciones = informes["Posición"].dropna().unique().tolist()
        posiciones.insert(0, "-- Todas --")  # opción por defecto
        posicion_sel = st.selectbox("Selecciona posición:", posiciones, index=0)

        if posicion_sel != "-- Todas --":
            jugadores_filtrados = informes[informes["Posición"] == posicion_sel]
        else:
            jugadores_filtrados = informes.copy()  # no filtra por posición

        # === Filtro por jugador ===
        jugadores_lista = jugadores_filtrados["Jugador"].dropna().unique().tolist()
        jugadores_lista.insert(0, "")  # opción vacía
        jugador_sel = st.selectbox("Selecciona jugador:", jugadores_lista, index=0)

        if jugador_sel:  # solo continuar si hay jugador elegido
            # Último informe del jugador seleccionado
            informe_jugador = informes[informes["Jugador"] == jugador_sel]
            if informe_jugador.empty:
                st.warning(f"No hay informes para {jugador_sel}")
            else:
                datos_jugador = informe_jugador.iloc[-1]  # último informe

                # === INFO DEL JUGADOR ===
                jugador_info = informes[informes["Jugador"] == jugador_sel].iloc[0]
                nombre = jugador_info.get("Jugador", "Desconocido")
                fecha_nacimiento = jugador_info.get("Fecha de nacimiento", "Desconocida")
                posicion = jugador_info.get("Posición", "Desconocida")
                club = jugador_info.get("Club", "Desconocido")
                lateralidad = jugador_info.get("Lateralidad", "Desconocida")
                num_informes = len(informe_jugador)

                # Filtrar atributos con valores > 0
                atributos_valorados = {
                    attr: float(datos_jugador[attr])
                    for attr in ATRIBUTOS_VALORABLES
                    if attr in datos_jugador and pd.to_numeric(datos_jugador[attr], errors="coerce") > 0
                }

                if len(atributos_valorados) == 0:
                    st.warning("Este jugador no tiene atributos valorados todavía.")
                else:
                    media = np.mean(list(atributos_valorados.values()))

                    # === Mostrar información del jugador en tarjeta oscura ===
                    st.markdown(
                        f"""
                        <div style="
                            padding:20px; 
                            border-radius:12px; 
                            margin-bottom:15px;
                            background-color:#2c2c2c; 
                            border:2px solid #e74c3c;
                            color:#ecf0f1;
                            box-shadow:0px 4px 8px rgba(0,0,0,0.2);
                        ">
                            <h3 style="margin:0 0 10px 0; color:#ecf0f1;">{nombre}</h3>
                            <p style="margin:5px 0;"><strong>Fecha nacimiento🗓️:</strong> {fecha_nacimiento}</p>
                            <p style="margin:5px 0;"><strong>Posición📍: </strong> {posicion}</p>
                            <p style="margin:5px 0;"><strong>Club🏠:</strong> {club}</p>
                            <p style="margin:5px 0;"><strong>Lateralidad🦵:</strong> {lateralidad}</p>
                            <p style="margin:5px 0;"><strong>Número de informes📝:</strong> {num_informes}</p>
                            <p style="margin:5px 0;"><strong>Promedio de atributos valorados⭐:</strong> {media:.2f} / 5</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # === RADAR PLOTLY ===
                    df_radar = pd.DataFrame({
                        "Atributo": list(atributos_valorados.keys()),
                        "Valor": list(atributos_valorados.values()),
                        "Jugador": [jugador_sel] * len(atributos_valorados)
                    })

                    fig = px.line_polar(
                        df_radar,
                        r="Valor",
                        theta="Atributo",
                        color="Jugador",
                        line_close=True,
                        range_r=[0, 5]
                    )

                    # Estilo oscuro
                    fig.update_traces(line=dict(width=3), fill="toself")
                    fig.update_layout(
                        polar=dict(
                            bgcolor="#2c2c2c",
                            radialaxis=dict(
                                tick0=0, dtick=1,
                                tickfont=dict(color="#ecf0f1"),
                                showline=True, linecolor="#bdc3c7", gridcolor="#444"
                            ),
                            angularaxis=dict(
                                tickfont=dict(color="#ecf0f1"),
                                linecolor="#bdc3c7", gridcolor="#444"
                            )
                        ),
                        legend=dict(title_text="", font=dict(color="#ecf0f1")),
                        paper_bgcolor="#1e1e1e",
                        plot_bgcolor="#1e1e1e",
                        width=600, height=600
                    )

                    st.plotly_chart(fig, use_container_width=True)


