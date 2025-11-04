# main.py
import streamlit as st
import base64, json, math, time
import pandas as pd
from io import BytesIO
from PIL import Image
import numpy as np

st.set_page_config(page_title="Simulador Biomecánico — Visual", layout="wide")
st.title("🦖 Simulador Biomecánico Visual (20 s)")

# -------------------------
# Presets de especies (hábitat: 'terrestre','marino','volador')
# Cada especie tiene condiciones base (temp ideal, oxígeno ideal, tolerancia)
# -------------------------
SPECIES = {
    "Tyrannosaurus rex": {"masa": 7000, "femur": 1.2, "habitat": "terrestre", "temp_opt": 30, "ox_opt": 21},
    "Velociraptor mongoliensis": {"masa": 15, "femur": 0.8, "habitat": "terrestre", "temp_opt": 32, "ox_opt": 21},
    "Brachiosaurus altithorax": {"masa": 35000, "femur": 2.5, "habitat": "terrestre", "temp_opt": 28, "ox_opt": 21},
    "Spinosaurus aegyptiacus": {"masa": 6000, "femur": 1.5, "habitat": "marino", "temp_opt": 28, "ox_opt": 20},
    "Crocodylus (Cocodrilo)": {"masa": 1000, "femur": 0.9, "habitat": "marino", "temp_opt": 29, "ox_opt": 20},
    "Aquila chrysaetos (Águila)": {"masa": 6, "femur": 0.25, "habitat": "volador", "temp_opt": 40, "ox_opt": 21},
}

# -------------------------
# Sidebar inputs
# -------------------------
st.sidebar.header("Configuración de la simulación (20 s)")
species_name = st.sidebar.selectbox("Selecciona especie", list(SPECIES.keys()))
bg_file = st.sidebar.file_uploader("Sube fondo (PNG/JPG)", type=["png","jpg","jpeg"])
sprite_file = st.sidebar.file_uploader("Sube sprite (PNG con transparencia preferible)", type=["png"])
st.sidebar.markdown("---")
st.sidebar.subheader("Condiciones iniciales (valores base)")
presion_init = st.sidebar.slider("Presión (kPa)", 20.0, 200.0, 101.3, step=0.1)
temp_init = st.sidebar.slider("Temperatura (°C)", -30, 60, 25)
ox_init = st.sidebar.slider("Oxígeno (%)", 1, 40, 21)
altitud_init = st.sidebar.slider("Altitud (m)", -10000, 8000, 0)
st.sidebar.markdown("---")
st.sidebar.subheader("Dinámica")
dyn_intensity = st.sidebar.slider("Intensidad de variación dinámica (0=estable → 1=muy dinámica)", 0.0, 1.0, 0.4, step=0.05)
seed = st.sidebar.number_input("Semilla aleatoria (opcional)", value=12345, step=1)
st.sidebar.markdown("---")
start_btn = st.sidebar.button("▶️ Iniciar simulación (20 s)")
reset_btn = st.sidebar.button("🔄 Reiniciar todo")

# Reset handler
if reset_btn:
    for k in st.session_state.keys():
        try:
            del st.session_state[k]
        except Exception:
            pass
    st.experimental_rerun()

# Validate images
if not bg_file or not sprite_file:
    st.info("Sube fondo y sprite en la barra lateral para activar la simulación.")
    st.stop()

# Utility: convert uploaded file to base64 string for embedding
def file_to_base64_u(file):
    file_bytes = file.read()
    return base64.b64encode(file_bytes).decode("utf-8"), file_bytes

bg_b64, bg_bytes = file_to_base64_u(bg_file)
sprite_b64, sprite_bytes = file_to_base64_u(sprite_file)

# Simulation parameters
SIM_DURATION = 20.0  # seconds total
STEP_INTERVAL = 0.5  # seconds per simulation step
STEPS = int(SIM_DURATION / STEP_INTERVAL)
np.random.seed(int(seed))

# Species base
spec = SPECIES[species_name]
habitat = spec["habitat"]
temp_opt = spec["temp_opt"]
ox_opt = spec["ox_opt"]
mass = spec["masa"]

# Movement region fractions depending on habitat
# terrestrial: near ground band; marino: full vertical band; volador: full 2D area
REGION = {
    "terrestre": {"y_min_frac": 0.55, "y_max_frac": 0.85},
    "marino": {"y_min_frac": 0.15, "y_max_frac": 0.85},
    "volador": {"y_min_frac": 0.05, "y_max_frac": 0.85},
}

# Base physiology model (very simplified, educational)
def compute_stepwise_evolution(presion0, temp0, ox0, alt0, dyn_intensity, steps, step_interval):
    """
    Precompute arrays of environmental variables and animal state across time steps.
    Returns dict with arrays length=steps.
    """
    pres = presion0
    temp = temp0
    ox = ox0
    alt = alt0

    pres_arr = []
    temp_arr = []
    ox_arr = []
    alt_arr = []
    energy_arr = []
    speed_ratio_arr = []
    ox_factor_arr = []
    narrative_arr = []

    # initial energy baseline (100 healthy)
    energy = 100.0

    for i in range(steps):
        t = i * step_interval

        # dynamic drift: small random walk proportional to dyn_intensity
        pres += (np.random.randn() * 0.5) * dyn_intensity
        temp += (np.random.randn() * 0.4) * dyn_intensity
        ox += (np.random.randn() * 0.3) * dyn_intensity
        alt += (np.random.randn() * 3.0) * dyn_intensity

        # clamp realistic ranges
        pres = max(20.0, min(200.0, pres))
        temp = max(-50.0, min(60.0, temp))
        ox = max(1.0, min(40.0, ox))
        alt = max(-10000.0, min(8000.0, alt))

        # compute factors: oxygen availability (approx scaling by pressure and ox fraction, and altitude)
        ox_partial = (pres / 101.3) * (ox / 21.0) * math.exp(-alt / 7000.0)

        # temperature factor: optimum near temp_opt; penalize away from optimum
        temp_diff = abs(temp - temp_opt)
        temp_factor = max(0.05, 1.0 - 0.02 * temp_diff)

        # pressure factor: extremely high or low pressures penalize
        pres_factor = 1.0
        if pres > 140:
            pres_factor -= 0.3
        if pres < 60:
            pres_factor -= 0.2

        # ox factor simple
        ox_factor = max(0.01, min(2.0, ox_partial))

        # compute instantaneous energy change: penalize by deviations
        delta_energy = - ( (1 - temp_factor)*8 + (1 - pres_factor)*5 + (1 - min(1.0,ox_factor))*10 ) * (step_interval/2.0)
        energy = max(0.0, energy + delta_energy)

        # speed ratio: assume base speed proportional to sqrt(energy)
        speed_ratio = max(0.05, math.sqrt(energy / 100.0))

        # Narrative message (more elaborate)
        msgs = []
        if temp_diff > 8:
            if temp < temp_opt:
                msgs.append(f"Frío significativo: enzimas y contracciones musculares se enlentecen (Δ {temp - temp_opt:+.1f}°C).")
            else:
                msgs.append(f"Calor significativo: riesgo de fallo térmico e hipertermia (Δ {temp - temp_opt:+.1f}°C).")
        if ox_factor < 0.85:
            msgs.append(f"Niveles de oxígeno funcional reducidos (factor {ox_factor:.2f}): hipoxia muscular y fatiga progresiva.")
        if pres > 140:
            msgs.append("Presión elevada detectada: compresión de tejidos y dificultades respiratorias.")
        if pres < 60:
            msgs.append("Presión baja detectada: riesgo de embolias por expansión de gases y mareo.")
        if alt > 3000:
            msgs.append("Altitud alta: disminución de presión parcial de O₂ y respiración acelerada.")
        if alt < -200:
            msgs.append("Condiciones subacuáticas profundas: presión hidrostática alta, daño por compresión si no está adaptado.")
        # Habitat mismatch effects (if in water but terrestrial)
        habitat_msg = ""
        # We'll handle sinking/struggling in narrative too
        narrative = " ".join(msgs) if msgs else "Condiciones dentro de parámetros operativos."
        if habitat == "terrestre" and pres > 110 and ox < 15 and dyn_intensity>0.4:
            narrative += " Señales de estrés: respiración acelerada y pérdida de coordinación."
        # record
        pres_arr.append(pres)
        temp_arr.append(temp)
        ox_arr.append(ox)
        alt_arr.append(alt)
        energy_arr.append(energy)
        speed_ratio_arr.append(speed_ratio)
        ox_factor_arr.append(ox_factor)
        narrative_arr.append(narrative)

    return {
        "pres": pres_arr,
        "temp": temp_arr,
        "ox": ox_arr,
        "alt": alt_arr,
        "energy": energy_arr,
        "speed_ratio": speed_ratio_arr,
        "ox_factor": ox_factor_arr,
        "narrative": narrative_arr
    }

# Precompute timeline
timeline = compute_stepwise_evolution(presion_init, temp_init, ox_init, altitud_init, dyn_intensity, STEPS, STEP_INTERVAL)

# Build payload for JS
payload = {
    "bg_b64": bg_b64,
    "sprite_b64": sprite_b64,
    "steps": STEPS,
    "step_interval": STEP_INTERVAL,
    "sim_duration": SIM_DURATION,
    "width": 900,
    "height": 480,
    "region": REGION[habitat],
    "habitat": habitat,
    "speed_array": [float(x) for x in timeline["speed_ratio"]],
    "energy_array": [float(x) for x in timeline["energy"]],
    "narrative_array": timeline["narrative"],
}

# Render UI: left = animation, right = live metrics & final results
col_anim, col_info = st.columns([2,1])

with col_anim:
    st.subheader("Visualización (animación en tiempo real)")
    # HTML + JS that animates sprite using arrays from payload
    payload_json = json.dumps(payload)
    html = f"""
    <div id="sim_container" style="width:{payload['width']}px; height:{payload['height']}px; border-radius:12px; overflow:hidden; position:relative;
        background-image:url('data:image/png;base64,{payload['bg_b64']}'); background-size:cover; background-position:center;">
        <img id="animal_sprite" src="data:image/png;base64,{payload['sprite_b64']}" style="position:absolute; left:0px; bottom:0px; width:120px; transition: left 0.3s linear, top 0.3s linear, opacity 0.3s linear;"/>
        <div id="overlay" style="position:absolute; left:10px; top:10px; background:rgba(0,0,0,0.35); color:white; padding:8px; border-radius:6px; font-family:Arial, sans-serif;">
            <div id="timer">Tiempo: 0s</div>
            <div id="energy">Energía: 100</div>
        </div>
        <div id="end_overlay" style="position:absolute; left:0; top:0; width:100%; height:100%; display:none;
             align-items:center; justify-content:center; background:rgba(0,0,0,0.6); color:white; font-size:22px;">
            <div id="end_text"></div>
        </div>
    </div>
    <script>
    (function(){{
        const payload = {payload_json};
        const steps = payload.steps;
        const stepInterval = payload.step_interval * 1000; // ms
        const totalMs = payload.sim_duration * 1000;
        const sprite = document.getElementById('animal_sprite');
        const container = document.getElementById('sim_container');
        const timerEl = document.getElementById('timer');
        const energyEl = document.getElementById('energy');
        const endOverlay = document.getElementById('end_overlay');
        const endText = document.getElementById('end_text');

        let width = payload.width;
        let height = payload.height;
        let region = payload.region;
        let habitat = payload.habitat;
        // randomness seed using Math.random; movement targets will be per-step
        const speedArr = payload.speed_array;
        const energyArr = payload.energy_array;
        const narrativeArr = payload.narrative_array;

        // Convert region fractions to px
        const yMin = Math.floor(region.y_min_frac * height);
        const yMax = Math.floor(region.y_max_frac * height);
        const xMin = Math.floor(0.05 * width);
        const xMax = Math.floor(0.90 * width);

        // initial position random in region
        let x = Math.floor(Math.random() * (xMax - xMin) + xMin);
        let y = Math.floor(Math.random() * (yMax - yMin) + yMin);
        sprite.style.left = x + 'px';
        sprite.style.top = y + 'px';

        // For volador allow larger y range
        function chooseTarget(step) {{
            let tx = Math.floor(Math.random() * (xMax - xMin) + xMin);
            let ty = Math.floor(Math.random() * (yMax - yMin) + yMin);
            // if marine habitat and sprite terrestrial mismatch handling can be done externally
            return {{x:tx, y:ty}};
        }}

        let step = 0;
        const stepCount = steps;
        let elapsedMs = 0;
        let intervalId = setInterval(() => {{
            // update UI and visual effects based on arrays
            const speedRatio = speedArr[Math.min(step, stepCount-1)];
            const energy = Math.round(energyArr[Math.min(step, stepCount-1)]);
            const narrative = narrativeArr[Math.min(step, stepCount-1)];
            timerEl.innerText = 'Tiempo: ' + Math.round(elapsedMs/1000) + ' s';
            energyEl.innerText = 'Energía: ' + energy;

            // compute new target and move proportionally to speedRatio
            const target = chooseTarget(step);
            // distance to move scaled by speedRatio
            const dx = (target.x - x) * (0.2 + 0.8 * speedRatio); // more energy => longer steps
            const dy = (target.y - y) * (0.2 + 0.8 * speedRatio);
            x = Math.round(x + dx);
            y = Math.round(y + dy);

            // habitat mismatch visual rules:
            // If habitat is 'terrestre' but background implies marine (handled by server), we handle by checking payload.habitat mismatch externally.
            // We'll apply sinking effect if needed based on energy and pre-known mismatch: (rendered visually by adjusting top)
            // For simplicity, if energy < 25, dim sprite and reduce movement
            if (energy < 25) {{
                sprite.style.opacity = 0.35;
            }} else if (energy < 50) {{
                sprite.style.opacity = 0.6;
            }} else {{
                sprite.style.opacity = 1.0;
            }}

            // Place sprite, clamp to container
            x = Math.max(0, Math.min(width - 60, x));
            y = Math.max(0, Math.min(height - 60, y));
            sprite.style.left = x + 'px';
            sprite.style.top = y + 'px';

            // Visual tint if energy very low (apply CSS filter)
            if (energy < 30) {{
                sprite.style.filter = 'grayscale(60%) brightness(70%)';
            }} else if (energy < 60) {{
                sprite.style.filter = 'brightness(90%)';
            }} else {{
                sprite.style.filter = 'none';
            }}

            // show a little "narrative" as tooltip overlay (update overlay element)
            // We'll reuse energyEl for brevity; in the app we also render narratives on Python side.
            // Advance
            step += 1;
            elapsedMs += stepInterval;
            if (elapsedMs >= totalMs || step >= stepCount) {{
                clearInterval(intervalId);
                // finalize: compute final verdict from last energy
                const finalEnergy = energyArr[Math.max(0, stepCount-1)];
                let verdict = 'VIVO / ADAPTADO';
                if (finalEnergy < 40) verdict = 'MUERTO / COLAPSADO';
                else if (finalEnergy < 65) verdict = 'Débil / Sobrevive con dificultades';
                endText.innerHTML = '<div style="padding:20px; text-align:center;"><strong>Simulación finalizada</strong><br><br>Veredicto: <em>'+verdict+'</em></div>';
                endOverlay.style.display = 'flex';
                // hide overlay after 3s (but keep endOverlay)
            }}
        }}, stepInterval);

    }})();
    </script>
    """
    # show html
    st.components.v1.html(html, height=payload["height"]+20, scrolling=False)

with col_info:
    st.subheader("Estado y métricas en tiempo real (precalculus)")
    st.markdown("**Nota:** las curvas y la narrativa detallada se calculan en Python y se muestran abajo al terminar la simulación automáticamente.")
    # show initial summary
    st.markdown(f"- **Especie:** {species_name}  \n- **Hábitat base:** {habitat}  \n- **Condiciones iniciales:** Presión {presion_init:.1f} kPa · Temp {temp_init:.1f} °C · O₂ {ox_init:.1f}% · Altitud {altitud_init:.0f} m")
    st.markdown("---")
    # Live-ish preview (first few seconds)
    preview_df = pd.DataFrame({
        "t (s)": [round(i*STEP_INTERVAL,1) for i in range(min(6, STEPS))],
        "Energía (preview)": [round(x,2) for x in timeline["energy"][:min(6,STEPS)]],
        "Vel ratio (preview)": [round(x,2) for x in timeline["speed_ratio"][:min(6,STEPS)]],
    })
    st.dataframe(preview_df, use_container_width=True)

# -------------------------
# When simulation ends, show full graphs and detailed text
# Since animation runs client-side, we'll display full results immediately below (user can inspect)
# -------------------------
st.markdown("---")
st.subheader("Resultados completos y explicación científica")

results_df = pd.DataFrame({
    "t (s)": [round(i*STEP_INTERVAL,2) for i in range(STEPS)],
    "Presión (kPa)": timeline["pres"],
    "Temp (°C)": timeline["temp"],
    "Ox (%)": timeline["ox"],
    "Altitud (m)": timeline["alt"],
    "Energía": timeline["energy"],
    "Vel_ratio": timeline["speed_ratio"],
    "Narrativa (breve)": timeline["narrative"],
})
st.line_chart(results_df.set_index("t (s)")[["Energía", "Vel_ratio"]])

# Detailed textual final explanation (long form)
final_energy = timeline["energy"][-1]
if final_energy > 70:
    final_state = "VIVO — funcionamiento normal o con mínima fatiga"
elif final_energy > 45:
    final_state = "DEBIL — sobrevive con signos claros de fatiga y estrés fisiológico"
else:
    final_state = "MUERTO / COLAPSADO — fallo sistémico por condiciones hostiles"

st.markdown(f"**Veredicto final (modelo simplificado):** **{final_state}**  \n**Energía final:** {final_energy:.2f}/100")

# Long explanation (multi-paragraph)
explanacion = []
explanacion.append(f"### Resumen científico extendido para {species_name}")
explanacion.append(f"Hábitat base: **{habitat}**. Condiciones iniciales: presión {presion_init:.1f} kPa, temperatura {temp_init:.1f} °C, O₂ {ox_init:.1f}%, altitud {altitud_init:.0f} m.")
explanacion.append("")
explanacion.append("Durante la simulación, las condiciones ambientales variaron dinámicamente con intensidad configurada por el usuario. El modelo calcula una métrica energética (0-100) que resume la capacidad del organismo para mantener funciones metabólicas y locomotrices. Esta métrica depende de:")
explanacion.append("- Eficiencia de intercambio gaseoso (función de presión, fracción de O₂ y altitud).")
explanacion.append("- Temperatura corporal y efecto sobre la cinética enzimática y contracción muscular.")
explanacion.append("- Carga mecánica por presión externa y diferencias de densidad (especialmente relevante en entornos subacuáticos).")
explanacion.append("")
explanacion.append("**Interpretación de resultados:**")
# add some tailored paragraphs depending on final state and main drivers
drivers = []
# find main drivers by analysing average deviations
avg_temp_dev = abs(np.mean(timeline["temp"]) - temp_opt)
avg_ox_dev = abs(np.mean(timeline["ox"]) - ox_opt)
avg_pres = np.mean(timeline["pres"])
if avg_temp_dev > 5:
    drivers.append(f"La temperatura estuvo en promedio desviada ~{avg_temp_dev:.1f}°C respecto al óptimo del organismo ({temp_opt}°C), lo que afecta enzimas y contractilidad.")
if avg_ox_dev > 3:
    drivers.append(f"El oxígeno funcional varió en promedio ~{avg_ox_dev:.1f}% respecto al óptimo ({ox_opt}%), provocando hipoxia parcial.")
if avg_pres > 140:
    drivers.append("La presión media fue alta, con riesgo de compresión tisular y problemas respiratorios.")
if altitud_init > 3000 or np.mean(timeline["alt"]) > 3000:
    drivers.append("La altitud o sus variaciones redujeron notablemente la presión parcial de O₂.")
if habitat == "marino":
    drivers.append("Al ser un organismo adaptado al agua (o no), la presión hidrostática y la densidad del medio cambiaron los patrones de flotabilidad y respiración.")
if drivers:
    for d in drivers:
        explanacion.append("- " + d)
else:
    explanacion.append("- Las condiciones no mostraron desviaciones relevantes respecto a los óptimos.")

explanacion.append("")
explanacion.append("**Recomendaciones adaptativas hipotéticas:**")
# basic suggestions
recs = []
if final_energy < 50:
    recs.append("Aumentar capacidad pulmonar o sacos aéreos (si es aplicable) para incrementar el intercambio gaseoso.")
    recs.append("Mejorar el transporte sanguíneo (mayor hematocrito o hemoglobinas más eficientes).")
    recs.append("Modificaciones morfológicas: reducción de masa corporal o patas más robustas si la gravedad/presión penaliza la locomoción.")
else:
    recs.append("No se requieren adaptaciones inmediatas; el organismo mantiene funciones.")
for r in recs:
    explanacion.append("- " + r)

# Show explanation
st.markdown("\n".join(explanacion))

# Show table (first + last few rows)
st.markdown("### Tabla de evolución (muestras)")
st.dataframe(pd.concat([results_df.head(5), results_df.tail(5)]).reset_index(drop=True))

# Allow download of CSV
csv = results_df.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Descargar datos de la simulación (CSV)", csv, file_name=f"sim_{species_name.replace(' ','_')}.csv", mime="text/csv")

