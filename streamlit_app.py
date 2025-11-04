# main.py
import streamlit as st
import math, json, base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Simulador Biomecánico — Supervivencia", layout="wide")
st.title("🦖 Simulador Biomecánico — Probabilidad de supervivencia (20 s)")

# -------------------------
# Especies base (6)
# -------------------------
SPECIES = {
    "Tyrannosaurus rex": {"masa": 7000, "habitat": "terrestre", "temp_opt": 30.0, "ox_opt": 21.0, "color": (150, 30, 30)},
    "Spinosaurus aegyptiacus": {"masa": 6000, "habitat": "marino", "temp_opt": 28.0, "ox_opt": 20.0, "color": (50, 120, 180)},
    "Pteranodon longiceps": {"masa": 25, "habitat": "volador", "temp_opt": 34.0, "ox_opt": 21.0, "color": (200, 180, 80)},
    "Triceratops horridus": {"masa": 6000, "habitat": "terrestre", "temp_opt": 28.0, "ox_opt": 21.0, "color": (80, 140, 60)},
    "Mosasaurus hoffmanni": {"masa": 15000, "habitat": "marino", "temp_opt": 18.0, "ox_opt": 20.0, "color": (30, 100, 120)},
    "Crocodylus niloticus": {"masa": 500, "habitat": "marino", "temp_opt": 29.0, "ox_opt": 20.0, "color": (40, 80, 40)},
}

# -------------------------
# Predeterminados UI
# -------------------------
DEFAULT_DURATION = 20.0
STEP_INTERVAL = 0.5
STEPS = int(DEFAULT_DURATION / STEP_INTERVAL)

# Sidebar: controls
st.sidebar.header("Configuración")
species_name = st.sidebar.selectbox("Especie", list(SPECIES.keys()))
environment = st.sidebar.selectbox("Bioma / ambiente", ["Llanura", "Selva", "Desierto", "Montaña", "Fondo marino"])
presion_init = st.sidebar.slider("Presión (kPa)", 20.0, 200.0, 101.3, step=0.1)
temp_init = st.sidebar.slider("Temperatura (°C)", -30, 60, 25)
ox_init = st.sidebar.slider("Oxígeno (%)", 1, 40, 21)
altitud_init = st.sidebar.slider("Altitud (m)", -10000, 8000, 0)
dyn_intensity = st.sidebar.slider("Intensidad dinámica (0–1)", 0.0, 1.0, 0.4, step=0.05)

start = st.sidebar.button("▶️ Iniciar simulación")
reset = st.sidebar.button("🔄 Reiniciar valores")

# Reset handler
if reset:
    st.experimental_rerun()

# -------------------------
# Generar imágenes predeterminadas (fondos y sprite)
# -------------------------
def pil_to_b64(img, fmt="PNG"):
    buf = BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# background generators
def bg_land(w=940, h=520):
    img = Image.new("RGB", (w,h), (120, 200, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, int(h*0.7), w, h], fill=(70,50,30))  # ground
    # simple distant hills
    draw.ellipse([-100, h*0.45, 300, h*0.85], fill=(90,120,60))
    draw.ellipse([200, h*0.4, 600, h*0.9], fill=(80,110,50))
    return img

def bg_sea(w=940, h=520):
    img = Image.new("RGB", (w,h), (10,60,110))
    draw = ImageDraw.Draw(img)
    # water gradient: lighten towards surface
    for i in range(h):
        r = int(10 + (60*(h-i)/h))
        g = int(60 + (60*(h-i)/h))
        b = int(110 + (40*(h-i)/h))
        draw.line([(0,i),(w,i)], fill=(r,g,b))
    # surface line
    draw.rectangle([0, int(h*0.12)-2, w, int(h*0.12)+2], fill=(200,240,255))
    return img

def bg_air(w=940,h=520):
    img = Image.new("RGB", (w,h), (170,220,255))
    draw = ImageDraw.Draw(img)
    # simple clouds
    for cx in (120, 300, 600, 760):
        draw.ellipse([cx-80,80,cx+80,140], fill=(255,255,255))
    return img

# sprite generator: colored circle with species initial
def make_sprite(color=(200,50,50), size=140, label="D"):
    img = Image.new("RGBA", (size,size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    # circle
    draw.ellipse([4,4,size-4,size-4], fill=color+(255,), outline=(0,0,0,180))
    # letter
    try:
        f = ImageFont.truetype("arial.ttf", size//3)
    except Exception:
        f = ImageFont.load_default()
    w,h = draw.textsize(label, font=f)
    draw.text(((size-w)/2,(size-h)/2), label, fill=(255,255,255,255), font=f)
    return img

# choose backgrounds based on environment
bg_img = {
    "Llanura": bg_land(),
    "Selva": bg_land(),
    "Desierto": bg_land(),
    "Montaña": bg_land(),
    "Fondo marino": bg_sea(),
}

# species sprite
spec = SPECIES[species_name]
sprite_img = make_sprite(color=spec["color"], size=120, label=species_name.split()[0][0])

# b64
bg_b64 = pil_to_b64(bg_img[environment])
sprite_b64 = pil_to_b64(sprite_img)

# -------------------------
# Biomechanics & survival model
# -------------------------
def compute_timeline(pres0, temp0, ox0, alt0, dyn_int, steps, step_interval, species):
    pres = pres0
    temp = temp0
    ox = ox0
    alt = alt0
    mass = species["masa"]
    temp_opt = species["temp_opt"]
    ox_opt = species["ox_opt"]
    habitat = species["habitat"]

    energy = 100.0
    damage = 0.0
    resp_issue = 0.0

    pres_arr=[]; temp_arr=[]; ox_arr=[]; alt_arr=[]
    energy_arr=[]; survival_arr=[]; damage_arr=[]; resp_arr=[]; narrative=[]

    for i in range(steps):
        # dynamics
        pres += (np.random.randn() * 0.6) * dyn_int
        temp += (np.random.randn() * 0.5) * dyn_int
        ox += (np.random.randn() * 0.35) * dyn_int
        alt += (np.random.randn() * 3.0) * dyn_int

        pres = float(max(20.0, min(200.0, pres)))
        temp = float(max(-50.0, min(60.0, temp)))
        ox = float(max(1.0, min(40.0, ox)))
        alt = float(max(-10000.0, min(8000.0, alt)))

        # oxygen partial effect
        ox_partial = (pres/101.3) * (ox/21.0) * math.exp(-alt/7000.0)
        # temperature penalty
        temp_diff = temp - temp_opt
        temp_penalty = max(0.0, abs(temp_diff) * 0.025)
        pres_penalty = 0.0
        if pres > 140: pres_penalty += 0.28
        if pres < 60: pres_penalty += 0.18

        ox_factor = max(0.01, min(2.0, ox_partial))

        # energy change (simple aggregate)
        delta = - (temp_penalty*7 + pres_penalty*5 + (1 - min(1.0, ox_factor))*14) * (step_interval/2.0)
        # habitat mismatch penalty (if not marine but environment marine etc. -> heavy)
        # this will be applied outside based on chosen environment; return arrays and JS can decide visuals
        energy = max(0.0, energy + delta)

        # damage accumulates if extremes
        if temp_penalty > 0.5:
            damage += temp_penalty * 0.5
        if ox_factor < 0.7:
            resp_issue += (0.7 - ox_factor) * 20.0

        # survival heuristic: combine energy, damage, resp_issue, mass (big mass less tolerant)
        # normalize components to 0..1 then combine
        e_comp = energy / 100.0
        dmg_comp = max(0.0, 1.0 - min(1.0, damage/50.0))  # more damage reduces survival
        resp_comp = max(0.0, 1.0 - min(1.0, resp_issue/80.0))
        mass_comp = 1.0 - math.tanh(max(0,mass/10000.0)) * 0.5  # large mass slightly reduces adaptability

        # habitat mismatch big penalty if species terrestrial/volador in Fondo marino or marine species in non-marine
        # We'll calculate a simple habitat_flag outside (we will return needed data); for now compute base survival
        base_survival = 0.5*e_comp + 0.25*dmg_comp + 0.2*resp_comp + 0.05*mass_comp
        survival_pct = max(0.0, min(1.0, base_survival))

        pres_arr.append(pres); temp_arr.append(temp); ox_arr.append(ox); alt_arr.append(alt)
        energy_arr.append(energy); damage_arr.append(damage); resp_arr.append(resp_issue)
        survival_arr.append(survival_pct*100.0)
        # narrative
        msgs=[]
        if abs(temp_diff) > 6:
            msgs.append(f"Temp Δ{temp_diff:+.1f}°C")
        if ox_factor < 0.85:
            msgs.append(f"O₂ funcional {ox_factor:.2f}")
        if pres>140:
            msgs.append("Presión alta")
        if pres<60:
            msgs.append("Presión baja")
        narrative.append("; ".join(msgs) if msgs else "Condiciones operativas")
    return {
        "pres": pres_arr, "temp": temp_arr, "ox": ox_arr, "alt": alt_arr,
        "energy": energy_arr, "damage": damage_arr, "resp": resp_arr,
        "survival": survival_arr, "narrative": narrative
    }

# -------------------------
# On start compute timeline & render animation + graphs
# -------------------------
if start:
    # compute
    timeline = compute_timeline(presion_init, temp_init, ox_init, altitud_init, dyn_intensity, STEPS, STEP_INTERVAL, spec)

    # apply habitat mismatch penalties to survival curve depending on selected environment vs species habitat
    survival = np.array(timeline["survival"])
    habitat = spec["habitat"]
    # heavy penalty if species not in its habitat: terrestrial/volador in Fondo marino; marine not in Fondo marino
    if environment == "Fondo marino" and habitat != "marino":
        # progressive additional penalty representing drowning/stress
        penalty = np.linspace(0, 0.7, STEPS) * 100.0  # up to -70%
        survival = survival - penalty
    if environment != "Fondo marino" and habitat == "marino":
        penalty = np.linspace(0, 0.6, STEPS) * 100.0
        survival = survival - penalty

    survival = np.clip(survival, 0.0, 100.0)
    timeline["survival_adjusted"] = survival.tolist()

    # Build payload to animate
    payload = {
        "bg_b64": bg_b64,
        "sprite_b64": sprite_b64,
        "steps": STEPS,
        "step_interval": STEP_INTERVAL,
        "sim_duration": DEFAULT_DURATION,
        "width": 880,
        "height": 480,
        "habitat": spec["habitat"],
        "environment": environment,
        "energy": timeline["energy"],
        "survival": timeline["survival_adjusted"],
        "narrative": timeline["narrative"],
    }

    payload_json = json.dumps(payload)

    # Left: animation (HTML+JS). Right: graphs and text
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader("Animación de la simulación (20 s)")
        html = f"""
        <div id="sim_container" style="width:{payload['width']}px; height:{payload['height']}px; position:relative; border-radius:10px; overflow:hidden;
             background-image:url('data:image/png;base64,{payload['bg_b64']}'); background-size:cover; background-position:center;">
          <img id="sprite" src="data:image/png;base64,{payload['sprite_b64']}" style="position:absolute; left:0px; top:0px; width:120px; transition:left 0.35s linear, top 0.35s linear, opacity 0.35s linear;"/>
          <div id="hud" style="position:absolute; left:8px; top:8px; background:rgba(0,0,0,0.45); color:white; padding:8px; border-radius:6px;">
            <div id="time">Tiempo: 0 s</div>
            <div id="surv">Supervivencia: 100%</div>
            <div id="note" style="max-width:300px; font-size:12px; margin-top:4px;">Estado: -</div>
          </div>
        </div>

        <script>
        (function(){{
            const payload = {payload_json};
            const steps = payload.steps;
            const stepMs = payload.step_interval * 1000;
            const totalMs = payload.sim_duration * 1000;
            const sprite = document.getElementById('sprite');
            const container = document.getElementById('sim_container');
            const timeEl = document.getElementById('time');
            const survEl = document.getElementById('surv');
            const noteEl = document.getElementById('note');

            const width = payload.width;
            const height = payload.height;
            const habitat = payload.habitat;
            const environment = payload.environment;

            const survival = payload.survival;
            const energy = payload.energy;
            const narrative = payload.narrative;

            // Movement region
            let xMin = Math.floor(width*0.05), xMax = Math.floor(width*0.9);
            let yMin = Math.floor((habitat === 'volador') ? height*0.05 : (habitat==='marino' ? height*0.12 : height*0.65));
            let yMax = Math.floor((habitat === 'volador') ? height*0.45 : (habitat==='marino' ? height*0.9 : height*0.85));

            // initial pos
            let x = Math.floor(xMin + (xMax - xMin)*0.02);
            let y = Math.floor(yMin + (yMax - yMin)*0.02);
            sprite.style.left = x + 'px';
            sprite.style.top = y + 'px';

            let step = 0;
            let elapsed = 0;
            let dir = 1;

            const interval = setInterval(() => {{
                const idx = Math.min(step, steps-1);
                const surv = Math.round(survival[idx]);
                const en = Math.round(energy[idx]);
                const note = narrative[idx] || '';

                timeEl.innerText = 'Tiempo: ' + Math.round(elapsed/1000) + ' s';
                survEl.innerText = 'Supervivencia: ' + surv + '%';
                noteEl.innerText = 'Estado: ' + (note.length?note:'Operativo');

                // movement rules by habitat and survival/energy
                let speedFactor = Math.max(0.05, en/100);
                if (habitat === 'terrestre') {{
                    // move in straight line near bottom; if in marine environment and survival low => sink (visual)
                    x += Math.round(8 * speedFactor * dir);
                    if (x >= xMax) {{ x = xMax; dir = -1; }}
                    if (x <= xMin) {{ x = xMin; dir = 1; }}
                    y = Math.floor(yMax - (10 * (1 - speedFactor)));
                    if (environment === 'Fondo marino' && habitat !== 'marino') {{
                        // sink effect
                        y += Math.round((1 - speedFactor)*10);
                        sprite.style.opacity = Math.max(0.12, speedFactor);
                    }} else {{
                        sprite.style.opacity = 1.0;
                    }}
                }} else if (habitat === 'marino') {{
                    // swim in 2D; if not marine environment -> slide down
                    if (environment === 'Fondo marino') {{
                        let tx = Math.floor(Math.random()*(xMax-xMin)+xMin);
                        let ty = Math.floor(Math.random()*(yMax-yMin)+yMin);
                        x = Math.round(x + (tx - x) * (0.15 + 0.6 * speedFactor));
                        y = Math.round(y + (ty - y) * (0.15 + 0.6 * speedFactor));
                        sprite.style.opacity = Math.max(0.25, speedFactor);
                    }} else {{
                        y += Math.round((1 - speedFactor)*8);
                        sprite.style.opacity = Math.max(0.05, speedFactor);
                    }}
                }} else if (habitat === 'volador') {{
                    // keep altitude when energy good; descend if low
                    x += Math.round(10 * speedFactor * dir);
                    if (x >= xMax) {{ x = xMax; dir = -1; }}
                    if (x <= xMin) {{ x = xMin; dir = 1; }}
                    if (en < 60) {{
                        y += Math.round((60 - en)/8);
                    }} else {{
                        y = Math.max(yMin, Math.min(yMax*0.6, y + Math.round(Math.sin(step*0.8)*3)));
                    }}
                    if (environment === 'Fondo marino' && en < 35) {{
                        y += Math.round((35 - en)/4);
                    }}
                    sprite.style.opacity = Math.max(0.2, speedFactor);
                }}

                // clamp
                x = Math.max(0, Math.min(width-80, x));
                y = Math.max(0, Math.min(height-80, y));
                sprite.style.left = x + 'px';
                sprite.style.top = y + 'px';

                step += 1;
                elapsed += stepMs;

                if (elapsed >= totalMs || step >= steps) {{
                    clearInterval(interval);
                    // leave final HUD visible; the Python side also shows graph/explanation
                }}
            }}, stepMs);
        }})();
        </script>
        """
        st.components.v1.html(html, height=payload['height']+20, scrolling=False)

    with col2:
        st.subheader("Gráfica: Probabilidad de supervivencia")
        # Plot survival curve with colored bands
        times = [i*STEP_INTERVAL for i in range(STEPS)]
        surv = timeline["survival_adjusted"]
        fig, ax = plt.subplots(figsize=(5,3))
        ax.plot(times, surv, linewidth=2, label="Probabilidad de supervivencia (%)", color="#22a884")
        ax.fill_between(times, surv, color="#22a884", alpha=0.12)
        ax.set_ylim(0,100)
        ax.set_xlabel("Tiempo (s)")
        ax.set_ylabel("Supervivencia (%)")
        ax.grid(alpha=0.25)
        ax.axhline(66, color="gold", linestyle="--", linewidth=0.8, label="Umbral: estrés moderado")
        ax.axhline(33, color="red", linestyle="--", linewidth=0.8, label="Umbral: riesgo crítico")
        ax.legend(loc="upper right", fontsize=8)
        st.pyplot(fig)

        # Short interpretative summary
        final = float(surv[-1])
        if final >= 66:
            verdict = "SOBREVIVE — condiciones compatibles"
            colorv = "🟢"
        elif final >= 33:
            verdict = "EN PELIGRO — fatiga y daños acumulados"
            colorv = "🟡"
        else:
            verdict = "MUERTE PROBABLE — daño o hipoxia crítica"
            colorv = "🔴"

        st.markdown(f"### Resultado: {colorv} {verdict}")
        st.markdown(f"**Probabilidad final de supervivencia:** {final:.1f}%")

        # Detailed automated explanation (scientific)
        expl = []
        expl.append(f"**Especie:** {species_name} (hábitat base: {spec['habitat']}; masa {spec['masa']} kg).")
        expl.append(f"**Bioma seleccionado:** {environment}.")
        expl.append("")
        # Find main drivers
        avg_temp = sum(timeline["temp"])/len(timeline["temp"])
        avg_ox = sum(timeline["ox"])/len(timeline["ox"])
        avg_pres = sum(timeline["pres"])/len(timeline["pres"])
        drivers = []
        if abs(avg_temp - spec["temp_opt"]) > 4:
            drivers.append(f"La temperatura media (≈{avg_temp:.1f}°C) difiere del óptimo ({spec['temp_opt']}°C): afecta enzimas y potencia muscular.")
        if abs(avg_ox - spec["ox_opt"]) > 2:
            drivers.append(f"El oxígeno medio (≈{avg_ox:.1f}%) difiere del óptimo ({spec['ox_opt']}%): reducción en intercambio gaseoso.")
        if avg_pres > 140:
            drivers.append("Presión media elevada: compresión de tejidos y dificultad ventilatoria.")
        if environment == "Fondo marino" and spec["habitat"] != "marino":
            drivers.append("El animal está en ambiente marino sin adaptaciones: hundimiento y asfixia progresiva.")
        if drivers:
            expl.append("**Factores que redujeron la supervivencia:**")
            for d in drivers:
                expl.append("- " + d)
        else:
            expl.append("No se detectaron desviaciones severas de las condiciones óptimas en promedio.")

        expl.append("")
        # Mechanistic explanation
        expl.append("**Interpretación biomecánica:**")
        expl.append("- Energía metabólica (modelo simplificado) cae cuando la temperatura está lejos del óptimo o cuando la presión/abundancia de O₂ disminuye; la contracción muscular pierde potencia y la locomoción empeora.")
        expl.append("- El daño acumulado y los problemas respiratorios (estimados aquí como 'resp_issue') reducen la capacidad de recuperación y aumentan la probabilidad de colapso.")
        expl.append("")
        # Recommendations
        expl.append("**Recomendaciones adaptativas hipotéticas (educativas):**")
        if final < 50:
            expl.append("- Buscar microhábitats con mayor O₂ (valles, corrientes superficiales), reducir actividad y conservar energía.")
            expl.append("- Adaptaciones fisiológicas: mayor superficie de intercambio gaseoso (sacos aéreos), hemoglobinas más eficientes, reducción de masa activa.")
        else:
            expl.append("- Mantener comportamiento normal; monitorizar variaciones extremas de temperatura o presión.")
        st.markdown("\n\n".join(expl))

        # show a small table sample
        df_sample = pd.DataFrame({
            "t (s)": [round(i*STEP_INTERVAL,2) for i in range(0,STEPS, max(1,STEPS//8))],
            "Survival (%)": [round(float(s),2) for s in survival[::max(1,STEPS//8)]]
        })
        st.dataframe(df_sample)

    # allow download of full timeline
    results_df = pd.DataFrame({
        "t (s)": [round(i*STEP_INTERVAL,2) for i in range(STEPS)],
        "Presion (kPa)": timeline["pres"],
        "Temp (°C)": timeline["temp"],
        "Ox (%)": timeline["ox"],
        "Energia": timeline["energy"],
        "Damage": timeline["damage"],
        "Resp_issue": timeline["resp"],
        "Survival (%)": timeline["survival_adjusted"]
    })
    csv = results_df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Descargar datos completos (CSV)", csv, file_name=f"sim_{species_name.replace(' ','_')}.csv", mime="text/csv")

else:
    st.info("Configura los parámetros en la barra lateral y pulsa ▶️ Iniciar simulación para ejecutar 20 s.")

# Footer note
st.markdown("---")
st.markdown("_Modelo simplificado y educativo — no sustituye análisis empírico o modelos fisiológicos detallados._")
