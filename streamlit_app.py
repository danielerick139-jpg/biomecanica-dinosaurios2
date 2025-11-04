import streamlit as st
import pandas as pd
import time
from PIL import Image

# ==============================
# 🔬 SIMULADOR BIOMECÁNICO VISUAL
# ==============================

st.set_page_config(page_title="Simulador Biomecánico Visual", layout="wide")

# ---- Datos base ----
animales = {
    "Tyrannosaurus rex": {"masa": 7000, "velocidad": 8, "temp": 38, "respiracion": "pulmones tipo ave"},
    "Velociraptor mongoliensis": {"masa": 15, "velocidad": 18, "temp": 39, "respiracion": "pulmones tipo ave"},
    "Brachiosaurus altithorax": {"masa": 56000, "velocidad": 4, "temp": 36, "respiracion": "pulmones tipo ave"},
    "Panthera tigris": {"masa": 220, "velocidad": 17, "temp": 38, "respiracion": "pulmones mamífero"},
    "Loxodonta africana": {"masa": 6000, "velocidad": 6, "temp": 36, "respiracion": "pulmones mamífero"},
    "Aquila chrysaetos": {"masa": 6, "velocidad": 30, "temp": 40, "respiracion": "pulmones tipo ave"}
}

# ---- Variables de sesión ----
if "simulando" not in st.session_state:
    st.session_state.simulando = False
if "resultados" not in st.session_state:
    st.session_state.resultados = None

# ---- Sidebar ----
st.sidebar.title("⚙️ Configuración del entorno")
animal_sel = st.sidebar.selectbox("Selecciona el animal", list(animales.keys()))

presion = st.sidebar.slider("Presión (kPa)", 50, 150, 101)
temperatura = st.sidebar.slider("Temperatura (°C)", -30, 50, 25)
altitud = st.sidebar.slider("Altitud (m)", 0, 8000, 0)
gravedad = st.sidebar.slider("Gravedad (m/s²)", 5.0, 25.0, 9.8)
humedad = st.sidebar.slider("Humedad (%)", 0, 100, 50)

fondo = st.sidebar.file_uploader("Fondo del ecosistema (PNG)", type=["png"])
sprite = st.sidebar.file_uploader("Sprite del animal (PNG)", type=["png"])

col1, col2 = st.sidebar.columns(2)
start_btn = col1.button("▶️ Iniciar simulación")
reset_btn = col2.button("🔄 Reiniciar")

# ---- Reset ----
if reset_btn:
    st.session_state.simulando = False
    st.session_state.resultados = None
    st.rerun()

# ---- Mostrar fondo ----
if fondo:
    st.image(fondo, use_column_width=True)
else:
    st.info("Sube un fondo PNG para el ecosistema.")

# ---- Simulación ----
if start_btn:
    st.session_state.simulando = True
    st.session_state.resultados = None

if st.session_state.simulando:
    datos = animales[animal_sel]
    masa = datos["masa"]
    vel_base = datos["velocidad"]

    st.subheader(f"🦖 Simulando {animal_sel} en ambiente extremo...")

    placeholder = st.empty()
    descripcion = st.empty()

    eventos = []
    for segundo in range(1, 11):
        time.sleep(0.5)
        cambio_vel = 1.0
        estado = "Normal"

        if presion < 80:
            cambio_vel -= 0.1
            estado = "Hipoxia leve"
        elif presion < 60:
            cambio_vel -= 0.3
            estado = "Hipoxia severa"
        elif presion > 130:
            cambio_vel -= 0.2
            estado = "Daño pulmonar por presión"

        if temperatura < 0:
            cambio_vel -= 0.15
            estado = "Congelación muscular"
        elif temperatura > 40:
            cambio_vel -= 0.2
            estado = "Estrés térmico"

        if gravedad > 15:
            cambio_vel -= 0.25
            estado = "Sobrecarga muscular"
        elif gravedad < 7:
            cambio_vel -= 0.1
            estado = "Desorientación por baja gravedad"

        vel_actual = max(vel_base * cambio_vel, 0)

        eventos.append({
            "segundo": segundo,
            "estado": estado,
            "velocidad": vel_actual
        })

        descripcion.write(f"**Segundo {segundo}:** {estado}. Velocidad: {vel_actual:.2f} m/s")
        placeholder.progress(segundo / 10)

    # ---- Evaluar resultado final ----
    estado_final = eventos[-1]["estado"]
    vel_final = eventos[-1]["velocidad"]
    sobrevivio = vel_final > 0.5 * vel_base

    if sobrevivio:
        st.success(f"✅ {animal_sel} logró adaptarse parcialmente al ambiente.")
        conclusion = "El animal sobrevivió, aunque con adaptaciones necesarias para mantener la homeostasis."
    else:
        st.error(f"💀 {animal_sel} no logró sobrevivir al entorno.")
        conclusion = "Las condiciones ambientales superaron su fisiología; sufriría fallo sistémico o muerte."

    st.subheader("📋 Informe final")
    st.write(f"**Condición final:** {estado_final}")
    st.write(f"**Velocidad final:** {vel_final:.2f} m/s")
    st.write(f"**Conclusión:** {conclusion}")

    st.session_state.resultados = pd.DataFrame(eventos)
    st.line_chart(st.session_state.resultados.set_index("segundo")["velocidad"], use_container_width=True)

    st.session_state.simulando = False

