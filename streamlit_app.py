import streamlit as st
import math
import pandas as pd
import time
import random

st.set_page_config(page_title="Simulador Biomecánico", page_icon="🦖", layout="wide")

# --- Título ---
st.title("🦖 Simulador Biomecánico de Dinosaurios y Animales Modernos")
st.write("""
Explora cómo distintos animales reaccionarían a cambios extremos en el ambiente.
Ajusta los parámetros y observa qué pasaría biomecánicamente.
""")

# --- Parámetros del ecosistema ---
st.sidebar.header("🌍 Ecosistema")
ecosistema = st.sidebar.selectbox(
    "Selecciona un ambiente",
    ["Selva", "Desierto", "Tundra", "Montaña", "Fondo marino"]
)

presion = st.sidebar.slider("Presión atmosférica (atm)", 0.1, 10.0, 1.0, 0.1)
temperatura = st.sidebar.slider("Temperatura (°C)", -50, 60, 25)
oxigeno = st.sidebar.slider("Concentración de oxígeno (%)", 1, 40, 21)
altitud = st.sidebar.slider("Altitud (m)", -10000, 8000, 0)

# --- Base de datos de animales ---
animales = {
    "Tyrannosaurus rex": {"masa": 7000, "femur": 1.2, "tipo": "dinosaurio"},
    "Velociraptor mongoliensis": {"masa": 15, "femur": 0.3, "tipo": "dinosaurio"},
    "Brachiosaurus altithorax": {"masa": 35000, "femur": 2.5, "tipo": "dinosaurio"},
    "Spinosaurus aegyptiacus": {"masa": 6000, "femur": 1.5, "tipo": "dinosaurio"},
    "Elephas maximus (Elefante)": {"masa": 5400, "femur": 1.2, "tipo": "actual"},
    "Panthera leo (León)": {"masa": 190, "femur": 0.6, "tipo": "actual"},
}

nombre = st.selectbox("Selecciona un animal", list(animales.keys()))
animal = animales[nombre]

# --- Funciones biomecánicas ---
def fuerza_muscular(masa, longitud):
    return 0.3 * masa * math.sqrt(longitud)

def velocidad_maxima(masa, longitud):
    return 8 * (longitud / math.pow(masa, 1/3))

def evaluar_adaptacion(presion, temp, oxigeno, altitud, ecosistema, tipo):
    # Factores ambientales
    score = 100
    descripciones = []

    if ecosistema == "Fondo marino" and tipo != "dinosaurio":
        descripciones.append("❌ No puede respirar bajo el agua.")
        score -= 80
    elif ecosistema == "Fondo marino" and tipo == "dinosaurio":
        descripciones.append("🐊 Si tiene adaptaciones acuáticas, puede sobrevivir parcialmente.")
        score -= 40

    if oxigeno < 10:
        descripciones.append("🫁 Bajo nivel de oxígeno reduce su energía y velocidad.")
        score -= 25

    if temperatura < 0:
        descripciones.append("❄️ El frío extremo afecta sus músculos y movilidad.")
        score -= 20
    elif temperatura > 45:
        descripciones.append("🔥 El calor extremo puede causar colapso térmico.")
        score -= 30

    if presion > 5:
        descripciones.append("⚙️ Alta presión afecta el sistema respiratorio y circulación.")
        score -= 25

    if altitud > 3000:
        descripciones.append("⛰️ La altura reduce el oxígeno disponible.")
        score -= 15

    if score < 40:
        estado = "💀 Muere durante la simulación."
    elif score < 70:
        estado = "⚠️ Sobrevive con dificultades."
    else:
        estado = "✅ Se adapta exitosamente."

    return score, estado, descripciones

# --- Cálculos biomecánicos ---
masa = animal["masa"]
femur = animal["femur"]
tipo = animal["tipo"]

fuerza = fuerza_muscular(masa, femur)
velocidad = velocidad_maxima(masa, femur)

# --- Mostrar info inicial ---
col1, col2 = st.columns([1, 2])
with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Tyrannosaurus_rex_NT.jpg/220px-Tyrannosaurus_rex_NT.jpg", width=200)
    st.markdown(f"**Masa:** {masa} kg")
    st.markdown(f"**Longitud del fémur:** {femur} m")
    st.markdown(f"**Tipo:** {tipo}")
with col2:
    st.subheader("Datos biomecánicos base")
    st.write(f"**Fuerza muscular estimada:** {fuerza:.2f} N")
    st.write(f"**Velocidad máxima teórica:** {velocidad:.2f} m/s")

# --- Simulación ---
if st.button("▶️ Iniciar simulación"):
    st.subheader("Simulando condiciones ambientales...")
    with st.empty():
        for i in range(10):
            st.write(f"🦖 {nombre} adaptándose... ({i+1}/10)")
            time.sleep(0.5)
        score, estado, desc = evaluar_adaptacion(presion, temperatura, oxigeno, altitud, ecosistema, tipo)
        st.success(f"**Resultado final: {estado}**")
        st.progress(score / 100)
        st.write("**Efectos observados:**")
        for d in desc:
            st.write("-", d)

# --- Reset ---
if st.button("🔄 Reiniciar simulación"):
    st.experimental_rerun()


