# main.py
import streamlit as st
import base64, json, math, time
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Simulador Biomecánico — Visual (20 s)", layout="wide")
st.title("🦖 Simulador Biomecánico Visual — Movimiento por hábitat")

# -------------------------
# Especies y valores base
# -------------------------
SPECIES = {
    "Tyrannosaurus rex": {"masa": 7000, "femur": 1.2, "habitat": "terrestre", "temp_opt": 30.0, "ox_opt": 21.0},
    "Velociraptor mongoliensis": {"masa": 15, "femur": 0.8, "habitat": "terrestre", "temp_opt": 32.0, "ox_opt": 21.0},
    "Brachiosaurus altithorax": {"masa": 35000, "femur": 2.5, "habitat": "terrestre", "temp_opt": 28.0, "ox_opt": 21.0},
    "Spinosaurus aegyptiacus": {"masa": 6000, "femur": 1.5, "habitat": "marino", "temp_opt": 28.0, "ox_opt": 20.0},
    "Crocodylus (Cocodrilo)": {"masa": 1000, "femur": 0.9, "habitat": "marino", "temp_opt": 29.0, "ox_opt": 20.0},
    "Aquila chrysaetos (Águila)": {"masa": 6, "femur": 0.25, "habitat": "volador", "temp_opt": 40.0, "ox_opt": 21.0},
}

# Default UI values (used to reset)
DEFAULTS = {
    "species_name": list(SPECIES.keys())[0],
    "environment": "Llanura",
    "presion_init": 101.3,
    "temp_init": 25,
    "ox_init": 21,
    "altitud_init": 0,
    "dyn_intensity": 0.45,
    "seed": 12345,
}

# -------------------------
# Helper: set session defaults for widget keys
# -------------------------
def ensure_session_defaults():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

ensure_session_defaults()

# -------------------------
# Sidebar (widgets have explicit keys so we can reset them)
# -------------------------
st.sidebar.header("Configuración de la simulación (20 s)")

species_name = st.sidebar.selectbox("Selecciona especie", list(SPECIES.keys()),
                                    index=list(SPECIES.keys()).index(st.session_state.get("species_name", DEFAULTS["species_name"])),
                                    key="species_name")

environment = st.sidebar.selectbox("Selecciona bioma/ambiente (donde se coloca el animal)",
                                   ["Llanura", "Selva", "Desierto", "Montaña", "Fondo marino"],
                                   index=["Llanura", "Selva", "Desierto", "Montaña", "Fondo marino"].index(st.session_state.get("environment", DEFAULTS["environment"])),

                                   key="environment")

bg_file = st.sidebar.file_uploader("Sube fondo (PNG/JPG)", type=["png","jpg","jpeg"], key="bg_file")
sprite_file = st.sidebar.file_uploader("Sube sprite (PNG con transparencia preferible)", type=["png"], key="sprite_file")
st.sidebar.markdown("---")
st.sidebar.subheader("Condiciones físicas iniciales (valores base)")

presion_init = st.sidebar.slider("Presión (kPa)", 20.0, 200.0, float(st.session_state.get("presion_init", DEFAULTS["presion_init"])), step=0.1, key="presion_init")
temp_init = st.sidebar.slider("Temperatura (°C)", -30, 60, int(st.session_state.get("temp_init", DEFAULTS["temp_init"])), key="temp_init")
ox_init = st.sidebar.slider("Oxígeno (%)", 1, 40, int(st.session_state.get("ox_init", DEFAULTS["ox_init"])), key="ox_init")
altitud_init = st.sidebar.slider("Altitud (m)", -10000, 8000, int(st.session_state.get("altitud_init", DEFAULTS["altitud_init"])), key="altitud_init")
st.sidebar.markdown("---")
st.sidebar.subheader("Dinámica")

dyn_intensity = st.sidebar.slider("Intensidad de variación dinámica (0=estable → 1=muy dinámica)", 0.0, 1.0, float(st.session_state.get("dyn_intensity", DEFAULTS["dyn_intensity"])), step=0.05, key="dyn_intensity")
seed = st.sidebar.number_input("Semilla aleatoria (opcional)", value=int(st.session_state.get("seed", DEFAULTS["seed"])), step=1, key="seed")
st.sidebar.markdown("---")

start_btn = st.sidebar.button("▶️ Iniciar simulación (20 s)", key="start_btn")
reset_btn = st.sidebar.button("🔄 Reiniciar todo y valores base", key="reset_btn")

# Reset handler: restore session_state defaults and clear caches
if reset_btn:
    # restore widget keys to defaults
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    # clear uploaded files (can't programmatically clear file_uploader UI, but we remove their session_state entries)
    for key in ("bg_file", "sprite_file"):
        if key in st.session_state:
            try:
                del st.session_state[key]
            except Exception:
                pass
    # clear other derived keys
    for key in list(st.session_state.keys()):
        if key not in DEFAULTS and key not in ("species_name","environment","presion_init","temp_init","ox_init","altitud_init","dyn_intensity","seed","bg_file","sprite_file","start_btn","reset_btn"):
            try:
                del st.session_state[key]
            except Exception:
                pass
    # rerun to update widgets
    st.experimental_rerun()

# Validate images
if (not bg_file) or (not sprite_file):
    st.info("Sube fondo y sprite en la barra lateral para activar la simulación. (Puedes volver a Reiniciar para restaurar valores base.)")
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

# Movement region fractions depending on habitat (fractions of container height)
REGION = {
    "terrestre": {"y_min_frac": 0.65, "y_max_frac": 0.85},
    "marino": {"y_min_frac": 0.10, "y_max_frac": 0.85},
    "volador": {"y_min_frac": 0.05, "y_max_frac": 0.5},
}

# -------------------------
# Physics/biomech model (precompute arrays)
# -------------------------
def compute_stepwise_evolution(presion0, temp0, ox0, alt0, dyn_intensity, steps, step_interval):
    pres = presion0
    temp = temp0
    ox = ox0
    alt = alt0

    pres_arr = []; temp_arr = []; ox_arr = []; alt_arr = []
    energy_arr = []; speed_ratio_arr = []; ox_factor_arr = []; narrative_arr = []

    energy = 100.0

    for i in range(steps):
        # small deterministic time increment
        t = i * step_interval

        # dynamic drift: random walk scaled by intensity
        pres += (np.random.randn() * 0.7) * dyn_intensity
        temp += (np.random.randn() * 0.6) * dyn_intensity
        ox += (np.random.randn() * 0.4) * dyn_intensity
        alt += (np.random.randn() * 5.0) * dyn_intensity

        # clamp realistic ranges
        pres = float(max(20.0, min(200.0, pres)))
        temp = float(max(-50.0, min(60.0, temp)))
        ox = float(max(1.0, min(40.0, ox)))
        alt = float(max(-10000.0, min(8000.0, alt)))

        # oxygen partial approx: pressure * O2 fraction adjusted by altitude
        ox_partial = (pres / 101.3) * (ox / 21.0) * math.exp(-alt / 7000.0)

        temp_diff = temp - temp_opt
        temp_penalty = max(0.0, abs(temp_diff) * 0.02)  # linear penalty
        pres_penalty = 0.0
        if pres > 140: pres_penalty += 0.25
        if pres < 60: pres_penalty += 0.18

        ox_factor = max(0.01, min(2.0, ox_partial))

        # energy decrement: combine penalties
        delta_energy = - (temp_penalty * 6 + pres_penalty * 5 + (1 - min(1.0, ox_factor)) * 12) * (step_interval / 2.0)
        energy = max(0.0, energy + delta_energy)

        speed_ratio = max(0.02, math.sqrt(energy / 100.0))

        # narrative
        msg_parts = []
        if abs(temp_diff) > 6:
            if temp_diff < 0:
                msg_parts.append(f"Frío pronunciado (Δ {temp_diff:.1f} °C): contracción muscular y reducción en velocidad.")
            else:
                msg_parts.append(f"Calor pronunciado (Δ +{temp_diff:.1f} °C): riesgo de hipertermia y deshidratación.")
        if ox_factor < 0.85:
            msg_parts.append(f"Hipoxia funcional (factor O₂ {ox_factor:.2f}): fatiga y pérdida de coordinación.")
        if pres > 140:
            msg_parts.append("Presión elevada: compresión de estructuras y menor capacidad de ventilación.")
        if pres < 60:
            msg_parts.append("Presión baja: expansión de gases internos y mareo.")
        if alt > 3000:
            msg_parts.append("Altitud alta: disminución de presión parcial de O₂.")
        if alt < -200:
            msg_parts.append("Presión hidrostática alta (subacuática): riesgo de daño por compresión.")

        # habitat mismatch messages
        if environment == "Fondo marino" and habitat != "marino":
            msg_parts.append("Ambiente marino detectado: organismo no adaptado muestra signos de inmersión y estrés respiratorio.")
        if environment != "Fondo marino" and habitat == "marino":
            msg_parts.append("Organismo marino fuera del agua: desecación y fallo respiratorio progresivo.")

        narrative = " ".join(msg_parts) if msg_parts else "Condiciones dentro de parámetros operativos."

        pres_arr.append(pres); temp_arr.append(temp); ox_arr.append(ox); alt_arr.append(alt)
        energy_arr.append(energy); speed_ratio_arr.append(speed_ratio); ox_factor_arr.append(ox_factor); narrative_arr.append(narrative)

    return {
        "pres": pres_arr, "temp": temp_arr, "ox": ox_arr, "alt": alt_arr,
        "energy": energy_arr, "speed_ratio": speed_ratio_arr, "ox_factor": ox_factor_arr, "narrative": narrative_arr
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
    "width": 940,
    "height": 520,
    "region": REGION[habitat],
    "habitat": habitat,
    "environment": environment,
    "speed_array": [float(x) for x in timeline["speed_ratio"]],
    "energy_array": [float(x) for x in timeline["energy"]],
    "narrative_array": timeline["narrative"],
}

# -------------------------
# Render: ANIMACIÓN arriba, métricas debajo
# -------------------------
st.subheader("Visualización (animación en tiempo real)")
payload_json = json.dumps(payload)
html = f"""
<div id="sim_container" style="width:{payload['width']}px; height:{payload['height']}px; border-radius:12px; overflow:hidden; position:relative;
    background-image:url('data:image/png;base64,{payload['bg_b64']}'); background-size:cover; background-position:center;">
    <img id="animal_sprite" src="data:image/png;base64,{payload['sprite_b64']}" style="position:absolute; left:0px; top:0px; width:120px; transition: left 0.35s linear, top 0.35s linear, opacity 0.35s linear, transform 0.35s linear;"/>
    <div id="hud" style="position:absolute; left:10px; top:10px; background:rgba(0,0,0,0.45); color:white; padding:8px; border-radius:6px; font-family:Arial, sans-serif;">
        <div id="timer">Tiempo: 0s</div>
        <div id="energy">Energía: 100</div>
        <div id="narr">Estado: -</div>
    </div>
    <div id="end_overlay" style="position:absolute; left:0; top:0; width:100%; height:100%; display:none;
         align-items:center; justify-content:center; background:rgba(0,0,0,0.6); color:white; font-size:22px;">
        <div id="end_text" style="text-align:center;"></div>
    </div>
</div>
<script>
(function(){{
    const payload = {payload_json};
    const steps = payload.steps;
    const stepInterval = payload.step_interval * 1000;
    const totalMs = payload.sim_duration * 1000;
    const sprite = document.getElementById('animal_sprite');
    const container = document.getElementById('sim_container');
    const timerEl = document.getElementById('timer');
    const energyEl = document.getElementById('energy');
    const narrEl = document.getElementById('narr');
    const endOverlay = document.getElementById('end_overlay');
    const endText = document.getElementById('end_text');

    let width = payload.width;
    let height = payload.height;
    let region = payload.region;
    let habitat = payload.habitat;
    let environment = payload.environment;

    const speedArr = payload.speed_array;
    const energyArr = payload.energy_array;
    const narrativeArr = payload.narrative_array;

    // region fractions to px
    const yMin = Math.floor(region.y_min_frac * height);
    const yMax = Math.floor(region.y_max_frac * height);
    const xMin = Math.floor(0.05 * width);
    const xMax = Math.floor(0.92 * width);

    // initial position depends on habitat & environment
    let x = Math.floor((xMin + xMax) / 8); // start left-ish
    let y;
    if (habitat === 'volador') {{
        y = Math.floor(height * 0.08); // start near top
    }} else if (habitat === 'marino') {{
        y = Math.floor(height * 0.12); // start near surface/top
    }} else {{
        // terrestrial start lower within band
        y = Math.floor(yMin + (yMax - yMin) * 0.05);
    }}
    sprite.style.left = x + 'px';
    sprite.style.top = y + 'px';

    // For terrestrial: move horizontally, bounce at edges; minimal vertical bob
    // For volador: maintain altitude unless energy low -> descend
    // For marino: if environment is marine and species marine => swim 2D; else sink

    let step = 0;
    let elapsedMs = 0;
    let died = false;
    let deathReason = "";
    let dir = 1; // horizontal direction for terrestrial/volador

    let intervalId = setInterval(() => {{
        const idx = Math.min(step, steps-1);
        const speedRatio = speedArr[idx]; // 0..1 roughly
        const energy = Math.round(energyArr[idx]);
        const narrative = narrativeArr[idx];

        timerEl.innerText = 'Tiempo: ' + Math.round(elapsedMs/1000) + ' s';
        energyEl.innerText = 'Energía: ' + energy;
        narrEl.innerText = narrative ? ('Estado: ' + narrative) : 'Estado: sin eventos';

        // Movement logic by habitat
        if (habitat === 'terrestre') {{
            // move horizontally in straight line within bottom band
            const step_px = Math.round((4 + 18 * speedRatio) * dir); // speed depends on energy
            x = x + step_px;
            // small bob
            const bob = Math.round(Math.sin(step * 0.6) * 4);
            y = Math.floor(yMin + (yMax - yMin) * 0.06) + bob;

            // bounce on edges
            if (x >= xMax) {{ x = xMax; dir = -1; }}
            if (x <= xMin) {{ x = xMin; dir = 1; }}

            // If placed in marine environment and not marine species -> sink
            if (environment === 'Fondo marino' && habitat !== 'marino') {{
                y += Math.round((1.0 - speedRatio) * 8);
                sprite.style.opacity = Math.max(0.12, energy/100);
                if (y > height - 80) {{ died = true; deathReason = 'Hundimiento/Asfixia en ambiente marino.'; }}
            }}
        }} else if (habitat === 'volador') {{
            // horizontal motion with altitude maintenance; descent if low energy
            const step_px = Math.round((6 + 24 * speedRatio) * dir);
            x = x + step_px;
            if (x >= xMax) {{ x = xMax; dir = -1; }}
            if (x <= xMin) {{ x = xMin; dir = 1; }}

            if (energy < 60) {{
                // descend proportionally to energy deficit
                y += Math.round((60 - energy) / 10.0);
            }} else {{
                // small variations
                y = Math.max(5, Math.min(Math.floor(yMax*0.6), y + Math.round(Math.sin(step*0.7)*3)));
            }}

            if (environment === 'Fondo marino' && energy < 30) {{
                y += 6 + Math.round((30 - energy)/6.0);
            }}
            sprite.style.opacity = Math.max(0.2, energy / 100);
            if (y > height - 80) {{ died = true; deathReason = 'Caída/impacto fatal o inmersión (volador).'; }}
        }} else if (habitat === 'marino') {{
            // if environment is marine and species marine => swim 2D random walk biased by speed
            if (environment === 'Fondo marino') {{
                // target towards random points; movement scaled by speedRatio
                let tx = Math.floor(Math.random() * (xMax - xMin) + xMin);
                let ty = Math.floor(Math.random() * (yMax - yMin) + yMin);
                x = Math.round(x + (tx - x) * (0.18 + 0.7 * speedRatio));
                y = Math.round(y + (ty - y) * (0.18 + 0.7 * speedRatio));
                sprite.style.opacity = Math.max(0.25, energy / 100);
            }} else {{
                // marine species out of water -> slide/fall and fade
                y += Math.round((1.0 - speedRatio) * 8);
                sprite.style.opacity = Math.max(0.05, energy / 100);
                if (y > height - 80) {{ died = true; deathReason = 'Exposición fuera del agua: fallo respiratorio.'; }}
            }}
        }}

        // Visual filters by energy
        if (energy < 30) {{
            sprite.style.filter = 'grayscale(80%) brightness(65%)';
            sprite.style.transform = 'rotate(' + (Math.sin(step*0.3)*6) + 'deg)';
        }} else if (energy < 60) {{
            sprite.style.filter = 'grayscale(35%) brightness(85%)';
            sprite.style.transform = 'rotate(' + (Math.sin(step*0.2)*3) + 'deg)';
        }} else {{
            sprite.style.filter = 'none';
            sprite.style.transform = 'rotate(0deg)';
        }}

        // clamp positions so sprite never leaves container
        x = Math.max(0, Math.min(width - 60, x));
        y = Math.max(0, Math.min(height - 60, y));
        sprite.style.left = x + 'px';
        sprite.style.top = y + 'px';

        // kill by extreme low energy
        if (energy <= 2 && !died) {{
            died = true;
            deathReason = 'Fallo sistémico por energía crítica baja.';
        }}

        step += 1;
        elapsedMs += stepInterval;
        if (elapsedMs >= totalMs || step >= steps || died) {{
            clearInterval(intervalId);
            const finalEnergy = energyArr[Math.min(steps-1, step-1)];
            let verdict = 'VIVO / ADAPTADO';
            if (died) verdict = 'MUERTO: ' + deathReason;
            else if (finalEnergy < 40) verdict = 'DEBIL / Sobrevive con dificultades';
            else if (finalEnergy < 65) verdict = 'PARCIALMENTE adaptado (fatigado)';
            endText.innerHTML = '<div style="padding:20px; text-align:center;"><strong>Simulación finalizada</strong><br><br>Veredicto: <em>'+verdict+'</em><br><br>Observación final: '+(deathReason || 'Ninguna')+'</div>';
            endOverlay.style.display = 'flex';
        }}
    }}, stepInterval);

}})();
</script>
"""
st.components.v1.html(html, height=payload["height"]+20, scrolling=False)

# -------------------------
# Estado y métricas (ahora VA DEBAJO de la animación)
# -------------------------
st.subheader("Estado y métricas (precalculos)")
st.markdown(f"- **Especie:** {species_name}  \n- **Hábitat base especie:** {habitat}  \n- **Bioma seleccionado (ambiente):** {environment}")
st.markdown(f"- **Condiciones iniciales:** Presión {presion_init:.1f} kPa · Temp {temp_init:.1f} °C · O₂ {ox_init:.1f}% · Altitud {altitud_init:.0f} m")
st.markdown("---")
preview_df = pd.DataFrame({
    "t (s)": [round(i*STEP_INTERVAL,1) for i in range(min(6, STEPS))],
    "Energía (preview)": [round(x,2) for x in timeline["energy"][:min(6,STEPS)]],
    "Vel ratio (preview)": [round(x,2) for x in timeline["speed_ratio"][:min(6,STEPS)]],
})
st.dataframe(preview_df, use_container_width=True)

# -------------------------
# Results and detailed explanation (available immediately below)
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

final_energy = timeline["energy"][-1]
if final_energy > 70:
    final_state = "VIVO — funcionamiento relativamente normal"
elif final_energy > 45:
    final_state = "DEBIL — sobrevive con signos claros de fatiga y estrés"
else:
    final_state = "MUERTO / COLAPSADO — fallo por condiciones hostiles"

st.markdown(f"**Veredicto (modelo simplificado):** **{final_state}**  \n**Energía final:** {final_energy:.2f}/100")

# Long explanation tailored
explanacion = []
explanacion.append(f"### Resumen científico extendido para {species_name}")
explanacion.append(f"Hábitat base especie: **{habitat}**. Bioma seleccionado: **{environment}**.")
explanacion.append(f"Condiciones iniciales: presión {presion_init:.1f} kPa, temperatura {temp_init:.1f} °C, O₂ {ox_init:.1f}%, altitud {altitud_init:.0f} m.")
explanacion.append("")
explanacion.append("Durante los 20 segundos la simulación varió condiciones (drift aleatorio calibrado por intensidad). Se calculó una métrica energética (0–100) que resume la capacidad del organismo para sostener metabolismo y locomoción. El comportamiento observacional en la animación depende de tres procesos biomecánicos principales:")
explanacion.append("1. **Intercambio gaseoso:** la eficiencia ventilatoria depende de la presión parcial de O₂ y la estructura pulmonar. En baja presión o baja fracción de O₂ la entrega de oxígeno a músculo disminuye (hipoxia) y la potencia muscular cae.")
explanacion.append("2. **Cinemática muscular y térmica:** la temperatura altera la cinética enzimática y la velocidad de contracción. Temperaturas muy bajas ralentizan, y temperaturas altas pueden causar fallo térmico.")
explanacion.append("3. **Carga mecánica por presión/densidad del medio:** en medios densos (agua) o con presiones altas, la ventilación y la perfusión se ven afectadas; la flotabilidad y resistencia cambian la potencia locomotora requerida.")
explanacion.append("")
# drivers identification
drivers = []
avg_temp_dev = abs(np.mean(timeline["temp"]) - temp_opt)
avg_ox_dev = abs(np.mean(timeline["ox"]) - ox_opt)
avg_pres = np.mean(timeline["pres"])
if avg_temp_dev > 5:
    drivers.append(f"La temperatura media se desvió ~{avg_temp_dev:.1f}°C respecto al óptimo ({temp_opt}°C), afectando rendimiento enzimático y fuerza.")
if avg_ox_dev > 3:
    drivers.append(f"El oxígeno funcional se desvió ~{avg_ox_dev:.1f}% respecto al óptimo ({ox_opt}%), exponiendo al animal a hipoxia parcial.")
if avg_pres > 140:
    drivers.append("La presión media fue elevada, con riesgo de compresión y problemas ventilatorios.")
if environment == "Fondo marino" and habitat != "marino":
    drivers.append("El bioma marino impone flotabilidad y asfixia a organismos terrestres/voladores: hundimiento y falla respiratoria rápida.")
if drivers:
    for d in drivers:
        explanacion.append("- " + d)
else:
    explanacion.append("- Las condiciones permanecieron cercanas a los óptimos durante la simulación.")

explanacion.append("")
explanacion.append("**Recomendaciones adaptativas hipotéticas (educativas):**")
if final_energy < 50:
    explanacion.append("- Aumentar capacidad pulmonar (sacos aéreos, mayor superficie de intercambio) y mejorar transporte sanguíneo.")
    explanacion.append("- Comportamientos: buscar microhábitats con mayor O₂ o sombra, reducir actividad motora hasta recuperar energía.")
    explanacion.append("- Morfológicas: reducir masa efectiva; patas/alas adaptadas para la nueva densidad o presión.")
else:
    explanacion.append("- El organismo no requiere cambios inmediatos. Mantener acceso a recursos y refugios es suficiente.")
explanacion.append("")
explanacion.append("**Limitaciones:** Este es un modelo didáctico y simplificado. Para uso científico requiere calibración con datos empíricos y modelos fisiológicos más profundos.")

st.markdown("\n".join(explanacion))

st.markdown("### Tabla de evolución (muestras)")
st.dataframe(pd.concat([results_df.head(4), results_df.tail(4)]).reset_index(drop=True))

csv = results_df.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Descargar datos de la simulación (CSV)", csv, file_name=f"sim_{species_name.replace(' ','_')}.csv", mime="text/csv")
