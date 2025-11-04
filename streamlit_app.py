import streamlit as st
import math
import time
import random
from PIL import Image
import io
import base64

st.set_page_config(page_title="Simulador Biomecánico", page_icon="🦖", layout="wide")

st.title("🦖 Simulador Biomecánico Interactivo")
st.markdown("""
Explora cómo distintos animales reaccionan biomecánicamente a cambios extremos en su ambiente.
Sube un fondo y un sprite, ajusta las condiciones y observa cómo el animal lucha por adaptarse.
""")

# --- Parámetros del ecosistema ---
st.sidebar.header("🌍 Ecosistema y condiciones")
ecosistema = st.sidebar.selectbox(
    "Selecciona el tipo de ambiente",
    ["Selva", "Desierto", "Tundra", "Montaña", "Fondo marino"]
)

presion = st.sidebar.slider("Presión atmosférica (atm)", 0.1, 10.0, 1.0, 0.1)
temperatura = st.sidebar.slider("Temperatura (°C)", -50, 60, 25)
oxigeno = st.sidebar.slider("Concentración de oxígeno (%)", 1, 40, 21)
altitud = st.sidebar.slider("Altitud (m)", -10000, 8000, 0)

# --- Cargar imágenes ---
st.sidebar.header("🖼️ Imágenes de simulación")
bg_file = st.sidebar.file_uploader("Sube una imagen de fondo (ecosistema)", type=["png", "jpg", "jpeg"])
sprite_file = st.sidebar.file_uploader("Sube el sprite del animal (PNG con fondo transparente)", type=["png"])

if not bg_file or not sprite_file:
    st.warning("⬆️ Sube ambas imágenes para iniciar la simulación.")
    st.stop()

# Convertir imágenes a base64 para animarlas en HTML
def image_to_base64(img_file):
    return base64.b64encode(img_file.read()).decode()

bg_base64 = image_to_base64(bg_file)
sprite_base64 = image_to_base64(sprite_file)

# --- Funciones biomecánicas ---
def evaluar_adaptacion(presion, temp, oxigeno, altitud, ecosistema):
    descripcion = []
    energia = 100

    # Presión
    if presion > 5:
        energia -= 30
        descripcion.append("La presión extrema aplasta los tejidos blandos y dificulta la respiración, reduciendo la movilidad.")
    elif presion < 0.5:
        energia -= 20
        descripcion.append("La presión muy baja genera problemas circulatorios y expansión de gases internos, el animal se desorienta.")

    # Temperatura
    if temp < 0:
        energia -= 25
        descripcion.append("El frío congela los fluidos corporales, disminuye la velocidad de reacción y causa rigidez muscular.")
    elif temp > 40:
        energia -= 35
        descripcion.append("El calor extremo provoca deshidratación, sobrecalentamiento cerebral y colapso térmico.")

    # Oxígeno
    if oxigeno < 10:
        energia -= 30
        descripcion.append("Con poco oxígeno, el metabolismo se desacelera y los músculos pierden fuerza, el animal jadea y se tambalea.")
    elif oxigeno > 30:
        energia -= 10
        descripcion.append("El exceso de oxígeno acelera la oxidación celular, lo que podría causar estrés oxidativo.")

    # Altitud
    if altitud > 3000:
        energia -= 20
        descripcion.append("La altitud reduce la densidad del aire y el oxígeno disponible, dificultando la respiración y el movimiento.")
    elif altitud < -100:
        energia -= 15
        descripcion.append("La presión subacuática es enorme, el animal sufre daños internos y colapsa si no está adaptado al agua.")

    # Ecosistema
    if ecosistema == "Fondo marino":
        energia -= 40
        descripcion.append("Bajo el agua, la mayoría de dinosaurios y mamíferos terrestres no pueden respirar, se agitan antes de hundirse lentamente.")

    if energia > 70:
        estado = "✅ Se adapta bien al entorno, manteniendo su movilidad."
    elif energia > 40:
        estado = "⚠️ Sobrevive, pero muestra fatiga y desorientación."
    else:
        estado = "💀 No logra adaptarse y muere tras unos segundos."

    return energia, estado, descripcion

# --- Simulación visual ---
energia, estado, desc = evaluar_adaptacion(presion, temperatura, oxigeno, altitud, ecosistema)

# Velocidad de movimiento del sprite según la energía
speed = max(0.5, energia / 50)

# HTML para animar sprite en el fondo
animation_html = f"""
<div style='position: relative; width: 800px; height: 400px; background-image: url("data:image/png;base64,{bg_base64}");
background-size: cover; border-radius: 15px; overflow: hidden;'>
    <img src="data:image/png;base64,{sprite_base64}" id="sprite" 
         style="position: absolute; bottom: 30px; left: 0px; width: 120px; transition: left {speed}s linear;">
</div>
<script>
let sprite = document.getElementById("sprite");
let pos = 0;
let direction = 1;
let interval = setInterval(() => {{
    pos += direction * 20;
    sprite.style.left = pos + 'px';
    if (pos > 650 || pos < 0) direction *= -1;
}}, 500);
setTimeout(() => clearInterval(interval), 10000);
</script>
"""

st.markdown(animation_html, unsafe_allow_html=True)
st.subheader("📖 Análisis Biomecánico del Entorno")
st.write(f"**Resultado:** {estado}")
st.progress(energia / 100)
for d in desc:
    st.markdown(f"• {d}")

if st.button("🔄 Reiniciar simulación"):
    st.experimental_rerun()



