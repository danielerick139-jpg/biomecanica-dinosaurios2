# app.py
import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Simulador Biomecánico de Ecosistemas", page_icon="🦖", layout="wide")
st.title("🌎 Simulador Biomecánico de Ecosistemas — Dinosaurios & Animales actuales")

# --------------------------
# Datos precargados (puedes ampliar)
# --------------------------
# Valores son estimados; puedes editar o ampliar la tabla.
DINOSAURIOS = {
    "Tyrannosaurus rex": {"masa": 8000, "long_pierna": 1.2, "velocidad": 8},
    "Velociraptor": {"masa": 15, "long_pierna": 0.8, "velocidad": 18},
    "Triceratops": {"masa": 6000, "long_pierna": 1.0, "velocidad": 7},
    "Brachiosaurus": {"masa": 40000, "long_pierna": 2.5, "velocidad": 5},
}

ANIMALES_ACTUALES = {
    "León": {"masa": 190, "long_pierna": 0.6, "velocidad": 20},
    "Elefante africano": {"masa": 6000, "long_pierna": 1.2, "velocidad": 7},
    "Águila real": {"masa": 6, "long_pierna": 0.25, "velocidad": 25},
    "Caballo": {"masa": 500, "long_pierna": 1.0, "velocidad": 15},
}

# --------------------------
# Sidebar: opciones generales
# --------------------------
st.sidebar.header("Configuración general")
modo = st.sidebar.radio("¿Qué tipo de organismo quieres simular?", ["Dinosaurio", "Animal actual", "Comparar ambos"])
usar_precargado = st.sidebar.radio("¿Usar datos precargados o ingresar manualmente?", ["Precargado", "Manual"], index=0)

st.sidebar.header("Ecosistema / Condiciones ambientales")
preset = st.sidebar.selectbox("Preset de ecosistema",
                              ["Plano (estándar)", "Montañas altas", "Pantano/tropical", "Desierto caliente", "Alta presión (denso)", "Personalizado"])

# Valores por defecto para presets (presión en kPa, temperatura C, altitud m, gravedad g (m/s^2), humedad %)
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

# --------------------------
# Selección de organismo(s)
# --------------------------
st.sidebar.header("Seleccionar organismo")

if modo in ["Dinosaurio", "Comparar ambos"]:
    if usar_precargado == "Precargado":
        dino_elegido = st.sidebar.selectbox("Dinosaurio (precargado)", ["-- Ninguno --"] + list(DINOSAURIOS.keys()))
    else:
        dino_elegido = "-- Manual --"
else:
    dino_elegido = "-- Ninguno --"

if modo in ["Animal actual", "Comparar ambos"]:
    if usar_precargado == "Precargado":
        animal_elegido = st.sidebar.selectbox("Animal actual (precargado)", ["-- Ninguno --"] + list(ANIMALES_ACTUALES.keys()))
    else:
        animal_elegido = "-- Manual --"
else:
    animal_elegido = "-- Ninguno --"

st.sidebar.divider()
st.sidebar.header("Opciones de imagen")
imagen_dino = st.sidebar.file_uploader("Imagen dinosaurio (opcional)", type=["png", "jpg", "jpeg"])
imagen_animal = st.sidebar.file_uploader("Imagen animal actual (opcional)", type=["png", "jpg", "jpeg"])

# --------------------------
# Funciones biomecánicas y ambientales
# --------------------------
def factor_oxigeno(presion_kpa, alt_m):
    # Aproximación: la presión parcial de O2 escala con la presión atmosférica y disminuye con altura.
    # Normalizamos con 101.3 kPa como referencia.
    ajuste_alt = math.exp(-alt_m / 7000)  # caída exponencial aproximada
    return (presion_kpa / 101.3) * ajuste_alt

def factor_temperatura(temp_c):
    # Factor que afecta metabolismo: óptimo ~25°C
    return max(0.1, 1 - abs(temp_c - 25) * 0.01)

def factor_gravedad(grav_m_s2):
    # Si la gravedad sube, carga muscular/ósea aumenta -> rendimiento disminuye aproximadamente inversamente
    return 9.81 / grav_m_s2

def factor_terreno(tipo):
    # Multiplicador de gasto energético/penalización a velocidad
    mapping = {"Plana": 1.0, "Rocosa": 0.85, "Blanda": 0.7, "Suelta": 0.75, "Acuática": 0.5}
    return mapping.get(tipo, 1.0)

def fuerza_muscular(masa, long_pierna):
    # Base simple: proporcional a masa y a sqrt(longitud de palanca)
    return 0.3 * masa * math.sqrt(max(0.01, long_pierna))

def velocidad_teorica(masa, long_pierna):
    # Relación empírica: inversamente proporcional a la raíz cúbica de la masa y proporcional a longitud de pierna
    return 8 * (long_pierna / math.pow(max(0.1, masa), 1/3))

def aplicar_factores(fuerza_base, velocidad_base, presion_kpa, temp_c, alt_m, grav, terreno):
    f_ox = factor_oxigeno(presion_kpa, alt_m)
    f_temp = factor_temperatura(temp_c)
    f_grav = factor_gravedad(grav)
    f_ter = factor_terreno(terreno)

    # Fuerza se ve afectada por oxigenación, temperatura y gravedad:
    fuerza_mod = fuerza_base * f_ox * f_temp * f_grav
    # Velocidad por densidad/drag (proporcional a presion), temperatura y terreno
    # a mayor presión -> mayor resistencia -> velocidad baja
    drag_presion = 1 / (1 + (presion_kpa - 101.3) * 0.005) if presion_kpa >= 101.3 else 1 + (101.3 - presion_kpa) * 0.002
    velocidad_mod = velocidad_base * f_temp * f_grav * drag_presion * f_ter

    # Gasto energético (simplificado): aumenta si terreno blando o gravedad alta o temp fuera de óptimo
    gasto = (masa_energy_factor := 0.1) * (1 / f_ox) * (1 / f_temp) * (9.81 / f_grav) * (1 / f_ter)

    return fuerza_mod, velocidad_mod, gasto, {"f_ox": f_ox, "f_temp": f_temp, "f_grav": f_grav, "f_ter": f_ter}

def evaluar_supervivencia(fuerza_ratio, velocidad_ratio, ox_ratio):
    # Un índice simple combinando ratios normalizados (1 = igual que ambiente base de referencia)
    score = 0.5 * min(1, fuerza_ratio) + 0.3 * min(1, velocidad_ratio) + 0.2 * min(1, ox_ratio)
    # score en 0..1
    if score >= 0.75:
        return "ALTA", 0.75
    elif score >= 0.45:
        return "MEDIA", 0.45
    else:
        return "BAJA", 0.2

def generar_recomendaciones(specie_name, masa, long_pierna, fuerza_ratio, velocidad_ratio, ox_ratio, factores):
    recs = []
    # Si oxigenación baja
    if factores["f_ox"] < 0.9 or ox_ratio < 0.9:
        recs.append("Incrementar eficiencia pulmonar: pulmones más grandes, sacos aéreos o mayor flujo sanguíneo.")
        recs.append("Aumentar tasa hematocrito o mecanismos de transporte de O₂ (hemoglobinas más eficientes).")
    # Si temperatura fuera de óptimo
    if factores["f_temp"] < 0.9:
        recs.append("Aislamiento térmico (plumas/grasas) o comportamientos de termorregulación.")
    # Si gravedad penaliza
    if factores["f_grav"] < 0.95:
        recs.append("Aumentar robustez ósea y masa muscular relativa; patas más cortas y robustas.")
    # Si velocidad baja
    if velocidad_ratio < 0.85:
        recs.append("Modificar palancas locomotoras (piernas más largas o diferentes proporciones) o reducir masa corporal.")
    # Si terreno blando
    if factores["f_ter"] < 0.9:
        recs.append("Adaptaciones para terreno blando: extremidades con mayor superficie (pies más anchos) o uñas/pezuñas.")
    if not recs:
        recs.append("No se requieren adaptaciones mayores; organismo razonablemente adaptado.")
    return recs

# --------------------------
# Componer la(s) simulación(es)
# --------------------------
st.header("Parámetros seleccionados")
with st.expander("Ver condiciones ambientales actuales"):
    st.write({
        "Presión (kPa)": presion,
        "Temperatura (°C)": temp,
        "Altitud (m)": altitud,
        "Gravedad (m/s²)": gravedad,
        "Humedad (%)": humedad,
        "Tipo de terreno": tipo_terreno
    })

# Contenedores para resultados
cols = st.columns(2)

results = []

def procesar_organismo(label, massa, long_p, vel_base, imagen_file=None):
    # cálculos base
    f_base = fuerza_muscular(massa, long_p)
    v_base = velocidad_teorica(massa, long_p) if vel_base is None else vel_base
    f_mod, v_mod, gasto, factores = aplicar_factores(f_base, v_base, presion, temp, altitud, gravedad, tipo_terreno)

    # ratios respecto a valores base (normalizados)
    fuerza_ratio = f_mod / max(1e-6, f_base)
    velocidad_ratio = v_mod / max(1e-6, v_base)
    ox_ratio = factores["f_ox"]

    surv_label, surv_thresh = evaluar_supervivencia(fuerza_ratio, velocidad_ratio, ox_ratio)
    recomendaciones = generar_recomendaciones(label, massa, long_p, fuerza_ratio, velocidad_ratio, ox_ratio, factores)

    resultado = {
        "Organismo": label,
        "Masa (kg)": massa,
        "Long pierna (m)": long_p,
        "Fuerza base (N)": f_base,
        "Velocidad base (m/s)": v_base,
        "Fuerza mod (N)": f_mod,
        "Velocidad mod (m/s)": v_mod,
        "Gasto relativo": gasto,
        "Oxigeno_factor": factores["f_ox"],
        "Temp_factor": factores["f_temp"],
        "Grav_factor": factores["f_grav"],
        "Terreno_factor": factores["f_ter"],
        "Supervivencia": surv_label,
        "Recomendaciones": recomendaciones,
        "Imagen": imagen_file
    }
    return resultado

# Recoger datos manuales si corresponde
manual_input = {}
if usar_precargado == "Manual":
    st.sidebar.header("Datos manuales (si aplica)")
    manual_name = st.sidebar.text_input("Nombre (manual)", "")
    manual_masa = st.sidebar.number_input("Masa (kg) manual", 1, 100000, 100)
    manual_long = st.sidebar.number_input("Long. pierna (m) manual", 0.01, 10.0, 0.5)
    manual_vel = st.sidebar.number_input("Velocidad base (m/s) manual (opcional, 0 para calcular)", 0.0, 200.0, 0.0)
    manual_img = st.sidebar.file_uploader("Imagen manual (opcional)", type=["png", "jpg", "jpeg"], key="manual_img")

# Procesar dinosaurio (si aplica)
if modo in ["Dinosaurio", "Comparar ambos"]:
    if usar_precargado == "Precargado" and dino_elegido and dino_elegido != "-- Ninguno --":
        data = DINOSAURIOS[dino_elegido]
        res_dino = procesar_organismo(dino_elegido, data["masa"], data["long_pierna"], data["velocidad"], imagen_dino)
        results.append(res_dino)
    elif usar_precargado == "Manual" and manual_name:
        res_dino = procesar_organismo(manual_name, manual_masa, manual_long, manual_vel if manual_vel > 0 else None, manual_img)
        results.append(res_dino)

# Procesar animal actual (si aplica)
if modo in ["Animal actual", "Comparar ambos"]:
    if usar_precargado == "Precargado" and animal_elegido and animal_elegido != "-- Ninguno --":
        data = ANIMALES_ACTUALES[animal_elegido]
        res_animal = procesar_organismo(animal_elegido, data["masa"], data["long_pierna"], data["velocidad"], imagen_animal)
        results.append(res_animal)
    elif usar_precargado == "Manual" and manual_name and (modo != "Dinosaurio"):
        # si se usa manual y el usuario no puso dino, usamos los datos manuales como "animal actual"
        res_animal = procesar_organismo(manual_name, manual_masa, manual_long, manual_vel if manual_vel > 0 else None, manual_img)
        results.append(res_animal)

# --------------------------
# Mostrar resultados en la UI
# --------------------------
if not results:
    st.info("Selecciona uno o más organismos en la barra lateral (precargado o manual) para ver la simulación.")
else:
    st.header("📊 Resultados de la simulación")
    # Mostrar cards/columnas para cada resultado
    for r in results:
        with st.container():
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader(r["Organismo"])
                if r["Imagen"]:
                    st.image(r["Imagen"], use_container_width=True)
                st.metric("Supervivencia estimada", r["Supervivencia"])
                # Semáforo visual
                if r["Supervivencia"] == "ALTA":
                    st.success("🟩 Probabilidad alta de mantener funciones (sin adaptaciones severas).")
                elif r["Supervivencia"] == "MEDIA":
                    st.warning("🟧 Probabilidad moderada — se requieren adaptaciones o comportamientos.")
                else:
                    st.error("🟥 Probabilidad baja — organismo mal adaptado al ambiente.")
            with c2:
                st.markdown("**Indicadores principales (modificado por ambiente)**")
                st.write(f"- Fuerza: **{r['Fuerza mod (N)']:.2f} N**  (base: {r['Fuerza base (N)']:.2f} N)")
                st.write(f"- Velocidad: **{r['Velocidad mod (m/s)']:.2f} m/s**  (base: {r['Velocidad base (m/s)']:.2f} m/s)")
                st.write(f"- Gasto relativo estimado: **{r['Gasto relativo']:.2f}**")
                st.write("**Factores ambientales aplicados:**")
                st.write(f"- Oxigenación relativa: {r['Oxigeno_factor']:.3f}")
                st.write(f"- Temperatura (efecto): {r['Temp_factor']:.3f}")
                st.write(f"- Gravedad (efecto): {r['Grav_factor']:.3f}")
                st.write(f"- Terreno (efecto): {r['Terreno_factor']:.3f}")
                st.divider()
                st.markdown("**Recomendaciones adaptativas (breves)**")
                for rec in r["Recomendaciones"]:
                    st.write("• " + rec)
            st.markdown("---")

    # Tabla comparativa
    st.subheader("Tabla comparativa")
    df = pd.DataFrame(results).drop(columns=["Recomendaciones", "Imagen"])
    st.dataframe(df.set_index("Organismo"))

    # Gráficos: Fuerza y Velocidad
    st.subheader("Gráficos comparativos")
    chart_df = pd.DataFrame([{
        "Organismo": r["Organismo"],
        "Fuerza base": r["Fuerza base (N)"],
        "Fuerza modificada": r["Fuerza mod (N)"],
        "Velocidad base": r["Velocidad base (m/s)"],
        "Velocidad modificada": r["Velocidad mod (m/s)"]
    } for r in results]).set_index("Organismo")

    st.bar_chart(chart_df[["Fuerza base", "Fuerza modificada"]])
    st.bar_chart(chart_df[["Velocidad base", "Velocidad modificada"]])

    # Descargar resultados como CSV
    csv = pd.DataFrame(results).drop(columns=["Recomendaciones", "Imagen"]).to_csv(index=False)
    st.download_button("⬇️ Descargar resultados (CSV)", csv, file_name="simulacion_resultados.csv", mime="text/csv")
