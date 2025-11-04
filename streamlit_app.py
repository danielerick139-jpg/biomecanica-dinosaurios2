import streamlit as st
import math
import time
import base64
from PIL import Image
import io

st.set_page_config(page_title="Simulador Biomecánico", page_icon="🦖", layout="wide")

st.title("🦖 Simulador Biomecánico Avanzado")
st.markdown("""
Esta simulación muestra cómo los animales —prehistóricos y modernos— reaccionan biomecánica y fisiológicamente a cambios extremos en el ambiente.
Podrás visualizar su comportamiento dentro del ecosistema y entender los efectos reales de la presión, temperatura, oxígeno y altitud sobre su organismo.
""")

# --- Parámetros del ecosistema ---
st.sidebar.header("🌍 Parámetros Ambientales")
ecosistema = st.sidebar.selectbox(
    "Tipo de ecosistema",
    ["Selva", "Desierto", "Tundra", "Montaña", "Fondo marino"]
)

presion = st.sidebar.slider("Presión (atm)", 0.1, 10.0, 1.0, 0.1)
temperatura = st.sidebar.slider("Temperatura (°C)", -50, 60, 25)
oxigeno = st.sidebar.slider("Oxígeno (%)", 1, 40, 21)
altitud = st.sidebar.slider("Altitud (m)", -10000, 8000, 0)

# --- Cargar imágenes ---
st.sidebar.header("🖼️ Imágenes de simulación")
bg_file = st.sidebar.file_uploader("Fondo del ecosistema", type=["png", "jpg", "jpeg"])
sprite_file = st.sidebar.file_uploader("Sprite del animal (PNG con fondo transparente)", type=["png"])

if not bg_file or not sprite_file:
    st.warning("⬆️ Sube ambas imágenes para iniciar la simulación.")
    st.stop()

def image_to_base64(file):
    return base64.b64encode(file.read()).decode()

bg_base64 = image_to_base64(bg_file)
sprite_base64 = image_to_base64(sprite_file)

# --- Evaluación biomecánica detallada ---
def evaluar_adaptacion(presion, temp, oxigeno, altitud, ecosistema):
    energia = 100
    desc = []
    datos = {}

    # Presión
    if presion > 5:
        energia -= 25
        desc.append("**Presión extrema:** el sistema respiratorio se colapsa parcialmente. Los vasos sanguíneos se comprimen y la oxigenación muscular cae drásticamente.")
        datos["Compresión tisular"] = "Alta"
    elif presion < 0.5:
        energia -= 15
        desc.append("**Presión baja:** los gases internos se expanden, provocando mareo y desorientación. Los movimientos se vuelven erráticos.")
        datos["Equilibrio barométrico"] = "Inestable"

    # Temperatura
    if temp < 0:
        energia -= 25
        desc.append("**Frío extremo:** las enzimas metabólicas reducen su eficiencia. El flujo sanguíneo periférico disminuye y los músculos se congelan gradualmente.")
        datos["Actividad enzimática"] = "Muy baja"
    elif temp > 40:
        energia -= 30
        desc.append("**Calor extremo:** se produce sobrecalentamiento interno, colapso térmico y alteración neurológica. La velocidad de movimiento cae un 60%.")
        datos["Tasa de sudoración o jadeo"] = "Elevada"

    # Oxígeno
    if oxigeno < 10:
        energia -= 35
        desc.append("**Déficit de oxígeno:** la sangre no puede transportar suficiente O₂. Se observa hipoxia muscular y pérdida de coordinación.")
        datos["Nivel de oxigenación sanguínea"] = "Críticamente bajo"
    elif oxigeno > 30:
        energia -= 10
        desc.append("**Exceso de oxígeno:** acelera la oxidación celular, aumentando el riesgo de daño tisular a largo plazo.")
        datos["Estrés oxidativo"] = "Moderado"

    # Altitud
    if altitud > 3000:
        energia -= 20
        desc.append("**Altitud elevada:** menor presión parcial de oxígeno. El animal se mueve más lento y su respiración se acelera.")
        datos["Adaptación pulmonar"] = "Baja"
    elif altitud < -500:
        energia -= 20
        desc.append("**Altitud negativa (subacuática):** la presión hidrostática incrementa, afectando el flujo interno y provocando daños internos.")
        datos["Presión interna corporal"] = "Excesiva"

    # Ecosistema
    if ecosistema == "Fondo marino":
        energia -= 40
        desc.append("**Entorno marino:** si no es acuático, sus pulmones colapsan en segundos. Solo reptiles semiacuáticos podrían resistir brevemente.")
        datos["Adaptación acuática"] = "Muy baja"

    # Evaluar estado
    if energia > 70:
        estado = "✅ El animal mantiene sus funciones vitales y se adapta temporalmente."
    elif energia > 40:
        estado = "⚠️ El animal sobrevive, pero muestra debilidad muscular y respiración forzada."
    else:
        estado = "💀 El animal colapsa y muere bajo las condiciones actuales."

    return energia, estado, desc, datos

# --- Calcular resultados ---
energia, estado, desc, datos = evaluar_adaptacion(presion, temperatura, oxigeno, altitud, ecosistema)
speed = max(0.6, energia / 40)
opacity = max(0.3, energia / 100)

# --- Simulación visual HTML ---
animation_html = f"""
<div style='position: relative; width: 900px; height: 450px;
             background-image: url("data:image/png;base64,{bg_base64}");
             background-size: cover; border-radius: 20px; overflow: hidden;'>
    <img src="data:image/png;base64,{sprite_base64}" id="sprite"
         style="position: absolute; bottom: 40px; left: 0px;
         width: 140px; opacity: {opacity}; transition: left {speed}s linear;">
</div>
<script>
let sprite = document.getElementById("sprite");
let pos = 0;
let direction = 1;
let interval = setInterval(() => {{
    pos += direction * 30;
    sprite.style.left = pos + 'px';
    if (pos > 750 || pos < 0) direction *= -1;
}}, 600);
setTimeout(() => clearInterval(interval), 12000);
</script>
"""

st.markdown(animation_html, unsafe_allow_html=True)

# --- Información científica extendida ---
st.subheader("📊 Resultados de la simulación biomecánica")
st.write(f"**Estado final:** {estado}")
st.progress(energia / 100)
st.markdown("### 🔬 Explicaciones fisiológicas y biomecánicas detalladas:")
for d in desc:
    st.markdown(f"- {d}")

st.markdown("### 📈 Parámetros fisiológicos afectados:")
for k, v in datos.items():
    st.write(f"**{k}:** {v}")

# --- Botón de reinicio ---
if st.button("🔄 Reiniciar simulación"):
    st.experimental_rerun()
