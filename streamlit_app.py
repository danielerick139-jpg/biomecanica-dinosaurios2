# simulador_biomecanico_visual.py
# Simulador biomecánico visual (Streamlit)
# - Muestra un fondo PNG y un sprite PNG del animal que "camina" horizontalmente
# - Simulación de 10 segundos (ajustable) donde se aplican factores ambientales
# - A la derecha aparece una narración que se va actualizando cada segundo
# - Dependencias: streamlit, pillow, pandas, math
# Ejecutar: pip install streamlit pillow pandas
# streamlit run simulador_biomecanico_visual.py

import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
import math
import time
import io
import pandas as pd

st.set_page_config(page_title="Simulador Biomecánico Visual", page_icon="🦖", layout="wide")
st.title("🦖 Simulador biomecánico visual — dinosaurios & animales actuales")

# -------------------------
# Datos precargados (6 especies)
# -------------------------
SPECIES = {
    "Tyrannosaurus rex": {"masa": 7000, "long_pierna": 1.2, "velocidad": 8, "tipo": "dinosaurio", "temp_corp": 38},
    "Velociraptor mongoliensis": {"masa": 15, "long_pierna": 0.8, "velocidad": 18, "tipo": "dinosaurio", "temp_corp": 39},
    "Brachiosaurus altithorax": {"masa": 56000, "long_pierna": 2.5, "velocidad": 4, "tipo": "dinosaurio", "temp_corp": 36},
    "Panthera tigris (tigre)": {"masa": 220, "long_pierna": 0.6, "velocidad": 17, "tipo": "actual", "temp_corp": 38},
    "Loxodonta africana (elefante)": {"masa": 6000, "long_pierna": 1.2, "velocidad": 6, "tipo": "actual", "temp_corp": 36},
    "Aquila chrysaetos (águila)": {"masa": 6, "long_pierna": 0.25, "velocidad": 30, "tipo": "actual", "temp_corp": 40},
}

# -------------------------
# Sidebar: configuración
# -------------------------
st.sidebar.header("Configuración de simulación")
modo = st.sidebar.selectbox("Tipo de organismo", ["Dinosaurio", "Animal actual", "Cualquiera"], index=2)

species_list = [k for k, v in SPECIES.items() if modo == "Cualquiera" or (modo == "Dinosaurio" and v['tipo'] == 'dinosaurio') or (modo == "Animal actual" and v['tipo'] == 'actual')]
selected_name = st.sidebar.selectbox("Selecciona especie precargada", ["-- Ninguno --"] + species_list)
use_manual = st.sidebar.checkbox("Ingresar datos manuales (en vez de precargado)")

# Environmental presets
st.sidebar.header("Ecosistema / Condiciones ambientales")
preset = st.sidebar.selectbox("Preset ambiental", ["Plano (estándar)", "Montañas altas", "Pantano/tropical", "Desierto caliente", "Alta presión (denso)", "Personalizado"]) 

PRESETS = {
    "Plano (estándar)": {"presion": 101.3, "temp": 25, "altitud": 200, "gravedad": 9.81, "humedad": 50, "tipo_terreno": "Plana"},
    "Montañas altas": {"presion": 80.0, "temp": 5, "altitud": 3500, "gravedad": 9.81, "humedad": 30, "tipo_terreno": "Rocosa"},
    "Pantano/tropical": {"presion": 101.0, "temp": 30, "altitud": 50, "gravedad": 9.81, "humedad": 85, "tipo_terreno": "Blanda"},
    "Desierto caliente": {"presion": 100.0, "temp": 45, "altitud": 400, "gravedad": 9.81, "humedad": 10, "tipo_terreno": "Suelta"},
    "Alta presión (denso)": {"presion": 150.0, "temp": 20, "altitud": 50, "gravedad": 9.81, "humedad": 60, "tipo_terreno": "Plana"},
}

if preset != "Personalizado":
    env_defaults = PRESETS[preset]
else:
    env_defaults = {"presion": 101.3, "temp": 25, "altitud": 200, "gravedad": 9.81, "humedad": 50, "tipo_terreno": "Plana"}

presion = st.sidebar.slider("Presión ambiental (kPa)", 20.0, 200.0, float(env_defaults["presion"]), step=0.1)
temp = st.sidebar.slider("Temperatura (°C)", -50, 80, int(env_defaults["temp"]))
altitud = st.sidebar.slider("Altitud (m)", 0, 10000, int(env_defaults["altitud"]))
gravedad = st.sidebar.slider("Gravedad local (m/s²)", 1.0, 20.0, float(env_defaults["gravedad"]), step=0.01)
humedad = st.sidebar.slider("Humedad (%)", 0, 100, int(env_defaults["humedad"]))
tipo_terreno = st.sidebar.selectbox("Tipo de terreno", ["Plana", "Rocosa", "Blanda", "Suelta", "Acuática"]) 

# Simulation params
st.sidebar.header("Parámetros de animación")
duracion = st.sidebar.slider("Duración simulación (s)", 5, 30, 10)
fps = st.sidebar.slider("FPS (frames por segundo)", 2, 15, 6)

# Images
st.sidebar.header("Imágenes (PNG)")
bg_file = st.sidebar.file_uploader("Fondo (png preferible)", type=["png", "jpg", "jpeg"], help="Si no subes, se usará un fondo gris neutro")
animal_file = st.sidebar.file_uploader("Sprite PNG del animal (transparente recomendado)", type=["png", "jpg", "jpeg"])

# -------------------------
# Manual inputs (override)
# -------------------------
manual = {}
if use_manual:
    st.sidebar.header("Datos manuales")
    manual['name'] = st.sidebar.text_input("Nombre (manual)", "Mi criatura")
    manual['masa'] = st.sidebar.number_input("Masa (kg)", 1.0, 1e6, 100.0)
    manual['long_pierna'] = st.sidebar.number_input("Long. pierna (m)", 0.01, 10.0, 0.5)
    manual['velocidad'] = st.sidebar.number_input("Velocidad base (m/s)", 0.0, 200.0, 5.0)
    manual['temp_corp'] = st.sidebar.number_input("Temp corporal (°C)", 20, 45, 37)

# -------------------------
# Biomechanical functions
# -------------------------

def factor_oxigeno(presion_kpa, alt_m):
    ajuste_alt = math.exp(-alt_m / 7000)
    return (presion_kpa / 101.3) * ajuste_alt

def factor_temperatura(temp_c):
    return max(0.05, 1 - abs(temp_c - 25) * 0.01)

def factor_gravedad(grav_m_s2):
    return 9.81 / grav_m_s2

def factor_terreno(tipo):
    mapping = {"Plana": 1.0, "Rocosa": 0.9, "Blanda": 0.75, "Suelta": 0.8, "Acuática": 0.5}
    return mapping.get(tipo, 1.0)

def fuerza_muscular(masa, long_pierna):
    return 0.3 * masa * math.sqrt(max(0.01, long_pierna))

def velocidad_teorica(masa, long_pierna, vel_base=None):
    if vel_base and vel_base > 0:
        return vel_base
    return 8 * (long_pierna / math.pow(max(0.1, masa), 1/3))

# Apply environmental modifiers
def aplicar_factores(f_base, v_base, presion_kpa, temp_c, alt_m, grav, terreno):
    f_ox = factor_oxigeno(presion_kpa, alt_m)
    f_temp = factor_temperatura(temp_c)
    f_grav = factor_gravedad(grav)
    f_ter = factor_terreno(terreno)

    fuerza_mod = f_base * f_ox * f_temp * f_grav
    drag_presion = 1 / (1 + (presion_kpa - 101.3) * 0.005) if presion_kpa >= 101.3 else 1 + (101.3 - presion_kpa) * 0.002
    velocidad_mod = v_base * f_temp * f_grav * drag_presion * f_ter

    gasto = 0.1 * (1 / max(0.01, f_ox)) * (1 / max(0.01, f_temp)) * (9.81 / max(0.01, f_grav)) * (1 / max(0.01, f_ter))
    return fuerza_mod, velocidad_mod, gasto, {"f_ox": f_ox, "f_temp": f_temp, "f_grav": f_grav, "f_ter": f_ter}

# Survival evaluation
def evaluar_supervivencia(f_ratio, v_ratio, ox_ratio):
    score = 0.5 * min(1, f_ratio) + 0.3 * min(1, v_ratio) + 0.2 * min(1, ox_ratio)
    if score >= 0.75:
        return "ALTA", score
    elif score >= 0.45:
        return "MEDIA", score
    else:
        return "BAJA", score

# Recommendations (text)
def generar_recomendaciones(factores, f_ratio, v_ratio):
    recs = []
    if factores['f_ox'] < 0.9 or f_ratio < 0.9:
        recs.append("Incrementar eficiencia pulmonar: sacos aéreos, mayor hematocrito o hemoglobinas eficientes.")
    if factores['f_temp'] < 0.9:
        recs.append("Aislamiento térmico o comportamientos de termorregulación (buscar microhábitats).")
    if factores['f_grav'] < 0.95:
        recs.append("Robustez ósea y muscular; patas más cortas y fuertes.")
    if factores['f_ter'] < 0.85:
        recs.append("Adaptaciones para terreno blando: patas con mayor superficie de apoyo.")
    if not recs:
        recs.append("Organismo razonablemente adaptado a estas condiciones.")
    return recs

# -------------------------
# Prepare organism data
# -------------------------
if use_manual:
    name = manual['name']
    masa = manual['masa']
    long_pierna = manual['long_pierna']
    vel_base = manual['velocidad']
    temp_corp = manual['temp_corp']
elif selected_name and selected_name != "-- Ninguno --":
    name = selected_name
    d = SPECIES[selected_name]
    masa = d['masa']
    long_pierna = d['long_pierna']
    vel_base = d['velocidad']
    temp_corp = d['temp_corp']
else:
    st.info("Selecciona una especie precargada o activa 'Ingresar datos manuales' en la barra lateral.")
    st.stop()

# Base metrics
f_base = fuerza_muscular(masa, long_pierna)
v_base = velocidad_teorica(masa, long_pierna, vel_base)

# -------------------------
# UI principal: área visual + narración lateral
# -------------------------
col_vis, col_info = st.columns([2, 1])
with col_vis:
    st.subheader(f"Simulación visual: {name}")
    canvas = st.empty()

with col_info:
    st.subheader("Narrativa y métricas en tiempo real")
    metric_f = st.empty()
    metric_v = st.empty()
    metric_o = st.empty()
    progress_container = st.empty()
    narrative = st.empty()
    recs_box = st.empty()

# Load images
if bg_file:
    bg = Image.open(bg_file).convert("RGBA")
else:
    # neutral background
    bg = Image.new("RGBA", (800, 450), (200, 220, 255, 255))

if animal_file:
    sprite = Image.open(animal_file).convert("RGBA")
else:
    # placeholder: a simple colored rectangle representing the animal
    sprite = Image.new("RGBA", (120, 80), (120, 70, 20, 255))

# Resize background to canvas size
canvas_w, canvas_h = bg.size
# ensure reasonable size
if canvas_w < 400:
    canvas_w = 800
    canvas_h = int(canvas_w * 0.56)
    bg = bg.resize((canvas_w, canvas_h))

# Scale sprite relative to canvas height
sprite_scale = max(20, int(canvas_h * 0.18))
sprite_ratio = sprite.width / sprite.height
sprite_h = sprite_scale
sprite_w = int(sprite_h * sprite_ratio)
sprite = sprite.resize((sprite_w, sprite_h), Image.LANCZOS)

# Simulation timeline
frames = int(duracion * fps)
interval = 1.0 / fps
x_start = int(canvas_w * 0.05)
x_end = int(canvas_w * 0.85)

# Initial status
alive = True
current_x = x_start

# Precompute environmental effects that change during simulation (we'll keep them constant now but narrative will describe progression)
f_mod, v_mod, gasto, factores = aplicar_factores(f_base, v_base, presion, temp, altitud, gravedad, tipo_terreno)

f_ratio = f_mod / max(1e-6, f_base)
v_ratio = v_mod / max(1e-6, v_base)
ox_ratio = factores['f_ox']

surv_label, surv_score = evaluar_supervivencia(f_ratio, v_ratio, ox_ratio)
recs = generar_recomendaciones(factores, f_ratio, v_ratio)

# Determine baseline movement speed in pixels/frame from v_mod (we map m/s to px/frame)
# mapping: assume animal would cross 50% canvas width in t_cross seconds at its speed; set t_cross = max(1, 10/v_mod) clamps
if v_mod <= 0:
    px_per_frame = 0
else:
    t_cross = max(1.0, 10.0 / v_mod)  # seconds to cross
    total_px = x_end - x_start
    px_per_frame = total_px / (t_cross * fps)

# We'll also model progressive stress: if gasto is very high or ox low, the animal slows down over time
stress_factor = max(0.0, 1.0 - (gasto - 1) * 0.05 - (1 - ox_ratio) * 0.5)
# clamp
stress_factor = max(0.0, min(1.5, stress_factor))

# Animation loop
with st.spinner("Simulando..."):
    for frame in range(frames):
        # progressive degradation: if environment is hostile, worsen a bit each second
        elapsed = frame / fps
        # small progressive penalty if survival baja
        progressive_penalty = 1.0
        if surv_label == 'BAJA':
            progressive_penalty -= 0.02 * (elapsed / max(1.0, duracion/5))
        elif surv_label == 'MEDIA':
            progressive_penalty -= 0.01 * (elapsed / max(1.0, duracion/8))

        # compute current px movement
        current_px_speed = px_per_frame * stress_factor * progressive_penalty
        current_x += current_px_speed

        # if too slow or ox very low, chance to collapse
        if ox_ratio < 0.6 or gasto > 5:
            # increase chance of death over time
            death_prob = min(0.9, 0.02 + 0.05 * (elapsed / duracion) + (5 if gasto > 10 else 0))
            # deterministic trigger for extreme cases
            if ox_ratio < 0.35 or gasto > 20:
                alive = False
        # if reached end, stop
        if current_x >= x_end:
            current_x = x_end

        # Compose frame
        frame_img = bg.copy()
        # Optionally tint background slightly based on survival label
        if surv_label == 'BAJA':
            # add red translucent overlay increasing with elapsed
            overlay = Image.new('RGBA', frame_img.size, (255, 60, 60, int(40 + 120 * (elapsed / duracion))))
            frame_img = Image.alpha_composite(frame_img.convert('RGBA'), overlay)
        elif surv_label == 'MEDIA':
            overlay = Image.new('RGBA', frame_img.size, (255, 180, 60, int(20 + 80 * (elapsed / duracion))))
            frame_img = Image.alpha_composite(frame_img.convert('RGBA'), overlay)

        # If dead, render sprite dimmed and add "colapsado"
        sprite_to_draw = sprite.copy()
        if not alive:
            sprite_to_draw = ImageOps.grayscale(sprite_to_draw).convert('RGBA')
            sprite_to_draw = ImageEnhance.Brightness(sprite_to_draw).enhance(0.4)
        else:
            # small bobbing to simulate paso
            bob = int(math.sin(frame * 0.6) * 6)
            sprite_to_draw = sprite_to_draw

        # Paste sprite
        y_pos = int(canvas_h * 0.65) - sprite_h + bob if 'bob' in locals() else int(canvas_h * 0.65) - sprite_h
        frame_img.paste(sprite_to_draw, (int(current_x), max(0, y_pos)), sprite_to_draw)

        # Draw simple HUD text on image (nombre y estado)
        # Convert to RGB for display
        display_img = frame_img.convert('RGB')

        # Show image in canvas
        canvas.image(display_img, use_column_width=True)

        # Update metrics and narrative
        metric_f.metric("Fuerza (modific.)", f"{f_mod:.1f} N", delta=f"{(f_ratio-1)*100:.1f}%")
        metric_v.metric("Velocidad (modific.)", f"{v_mod:.2f} m/s", delta=f"{(v_ratio-1)*100:.1f}%")
        metric_o.metric("Oxigenación relativa", f"{factores['f_ox']:.3f}")

        # Narrative update: a short sentence per second (we update even if fps>1)
        sec = int(elapsed)
        narrative_text = []
        narrative_text.append(f"Segundo {sec+1}/{duracion} — Estado: {surv_label} (score={surv_score:.2f})")
        if factores['f_ox'] < 0.9:
            narrative_text.append("Oxigenación reducida: la capacidad de esfuerzo se ve comprometida.")
        if factores['f_temp'] < 0.9:
            narrative_text.append("Temperatura subóptima: metabolismo más lento.")
        if factores['f_grav'] < 0.95:
            narrative_text.append("Gravedad elevada: carga sobre huesos y músculos.")
        if factores['f_ter'] < 0.9:
            narrative_text.append("Terreno penaliza la locomoción (mayor gasto energético).")
        # Add dynamic effects due to elapsed time
        if elapsed > duracion*0.6 and surv_label == 'BAJA':
            narrative_text.append("Signos de fatiga: respiración agitada y tambaleo.")
        if not alive:
            narrative_text = ["El animal ha colapsado y no puede moverse. Muerte por condiciones adversas."]

        narrative.markdown("\n".join(["- **"+s+"**" if i==0 else s for i,s in enumerate(narrative_text)]))

        # Recommendations box
        recs_box.markdown("**Recomendaciones adaptativas:**\n" + "\n".join(["- "+r for r in recs]))

        # Progress
        progress = (frame+1)/frames
        progress_container.progress(progress)

        # Early stop if dead
        if not alive:
            canvas.image(display_img, use_column_width=True)
            break

        time.sleep(interval)

# Final summary
st.success("Simulación terminada")
res_df = pd.DataFrame([{
    'Organismo': name,
    'Masa (kg)': masa,
    'Fuerza base (N)': f_base,
    'Fuerza mod (N)': f_mod,
    'Velocidad base (m/s)': v_base,
    'Velocidad mod (m/s)': v_mod,
    'Oxigeno_factor': factores['f_ox'],
    'Temp_factor': factores['f_temp'],
    'Grav_factor': factores['f_grav'],
    'Terreno_factor': factores['f_ter'],
    'Supervivencia': surv_label,
    'Recomendaciones': "; ".join(recs)
}])

st.subheader("Reporte final (resumen)")
st.dataframe(res_df.set_index('Organismo'))

# Descargar imagen final
buf = io.BytesIO()
final_img = display_img
final_img.save(buf, format='PNG')
buf.seek(0)
st.download_button("Descargar imagen final PNG", buf, file_name=f"sim_{name.replace(' ', '_')}.png", mime='image/png')

# Guardar CSV
csv = res_df.to_csv(index=False).encode('utf-8')
st.download_button("Descargar reporte (CSV)", csv, file_name='reporte_simulacion.csv', mime='text/csv')

# Nota
st.markdown("\n---\n**Notas:**\n- Las fórmulas son simplificaciones con fines exploratorios y educativos.\n- Para trabajar con modelos científicos publicables hay que calibrar parámetros con bibliografía y datos experimentales.\n- Si quieres que la animación use sprites con varias poses (pisadas), puedo añadir soporte para spritesheets y animación por frames.")
