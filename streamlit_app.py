import streamlit as st
import random
import time
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import io

# Configuración de la aplicación
st.set_page_config(page_title="Simulación Biomecánica Animal", layout="wide")

st.title("🌎 Simulación Biomecánica Animal")
st.write("Observa cómo distintos tipos de animales reaccionan ante condiciones ambientales dinámicas según su tipo (terrestre, marino o volador).")

# --- Definición de animales ---
species = {
    "Tigre terrestre": {"type": "terrestre", "color": "orange"},
    "Delfín marino": {"type": "marino", "color": "blue"},
    "Águila voladora": {"type": "volador", "color": "gray"},
}

# --- Variables globales ---
if "running" not in st.session_state:
    st.session_state.running = False
if "results" not in st.session_state:
    st.session_state.results = []
if "positions" not in st.session_state:
    st.session_state.positions = {name: (0, 0) for name in species.keys()}
if "time_start" not in st.session_state:
    st.session_state.time_start = 0

# --- Función para crear sprite temporal ---
def make_sprite(color="blue", size=100, label="A"):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((10, 10, size - 10, size - 10), fill=color)
    try:
        f = ImageFont.truetype("arial.ttf", 40)
    except:
        f = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=f)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - w) / 2, (size - h) / 2), label, font=f, fill="white")
    return img

# --- Simulación principal ---
def run_simulation():
    duration = 20
    interval = 0.5
    steps = int(duration / interval)

    st.session_state.results = []
    st.session_state.time_start = time.time()

    # Condiciones iniciales
    temp = random.uniform(5, 35)
    viento = random.uniform(0, 30)
    profundidad = random.uniform(0, 50)

    progress = st.progress(0, text="Simulación en curso...")
    status = st.empty()

    for step in range(steps):
        elapsed = step * interval
        temp += random.uniform(-1, 1)
        viento += random.uniform(-1, 1)
        profundidad += random.uniform(-1, 2)

        new_positions = {}
        step_results = {}

        for name, spec in species.items():
            x, y = st.session_state.positions[name]
            tipo = spec["type"]

            # --- Movimiento según tipo ---
            if tipo == "terrestre":
                y = 480
                x += random.randint(10, 25)
                if profundidad > 10:
                    y += 5
            elif tipo == "marino":
                if profundidad < 10:
                    y += 5
                elif profundidad > 20:
                    y -= 2
                x += random.randint(5, 15)
            elif tipo == "volador":
                y -= random.randint(5, 15)
                if viento > 20:
                    y += 10

            # Limitar bordes
            x = max(0, min(800, x))
            y = max(0, min(500, y))
            new_positions[name] = (x, y)

            # --- Efectos biomecánicos ---
            speed_factor = 1.0
            damage = 0

            if tipo == "terrestre":
                if profundidad > 5:
                    damage += (profundidad - 5) * 2
                if temp < 10:
                    speed_factor *= 0.7
            elif tipo == "marino":
                if temp > 30:
                    damage += (temp - 30) * 1.5
                if profundidad < 5:
                    damage += 10
            elif tipo == "volador":
                if viento > 20:
                    damage += (viento - 20) * 1.5
                if temp < 5:
                    speed_factor *= 0.5

            survival = max(0, 100 - damage)
            step_results[name] = {
                "pos": (x, y),
                "damage": damage,
                "survival": survival,
                "temp": temp,
                "viento": viento,
                "profundidad": profundidad,
            }

        st.session_state.positions = new_positions
        st.session_state.results.append(step_results)

        progress.progress((step + 1) / steps, text=f"Simulación {int((step + 1) / steps * 100)}% completada")
        status.text(f"🌡️ Temp: {temp:.1f}°C | 🌬️ Viento: {viento:.1f} km/h | 🌊 Profundidad: {profundidad:.1f} m")
        time.sleep(interval)

    progress.empty()
    status.empty()

# --- Botones de control ---
col1, col2 = st.columns(2)

with col1:
    if st.button("▶️ Iniciar simulación", use_container_width=True):
        st.session_state.running = True
        run_simulation()
        st.session_state.running = False

with col2:
    if st.button("🔄 Reiniciar todo", use_container_width=True):
        st.session_state.results = []
        st.session_state.positions = {name: (0, 0) for name in species.keys()}
        st.session_state.running = False
        st.session_state.time_start = 0
        st.rerun()

# --- Mostrar resultados ---
if st.session_state.results:
    last_step = st.session_state.results[-1]

    st.subheader("📊 Resultados Biomecánicos Finales")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(0, 800)
    ax.set_ylim(0, 500)
    ax.set_facecolor("#8EE4AF")
    ax.set_title("Posiciones finales y supervivencia")

    for name, data in last_step.items():
        x, y = data["pos"]
        ax.scatter(x, y, label=f"{name} ({data['survival']:.1f}% supervivencia)")
        ax.text(x + 10, y, name, fontsize=9)

    ax.legend()
    st.pyplot(fig)

    st.subheader("📈 Evolución de daño y supervivencia")
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    for name in species.keys():
        surv_vals = [step[name]["survival"] for step in st.session_state.results]
        ax2.plot(surv_vals, label=name)
    ax2.set_xlabel("Tiempo (s)")
    ax2.set_ylabel("Supervivencia (%)")
    ax2.set_title("Evolución de la supervivencia durante la simulación")
    ax2.legend()
    st.pyplot(fig2)

    st.write("✅ *Esta gráfica muestra cómo las condiciones ambientales afectan biomecánicamente a cada animal: los terrestres sufren con el agua, los marinos con el calor, y los voladores con el viento.*")
