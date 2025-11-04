import streamlit as st
import math
import pandas as pd

st.title("🦖 Comparador biomecánico de dinosaurios")

st.sidebar.header("Dinosaurio 1")
nombre1 = st.sidebar.text_input("Nombre", "Tyrannosaurus rex")
masa1 = st.sidebar.number_input("Masa (kg)", 100, 80000, 7000)
femur1 = st.sidebar.number_input("Longitud del fémur (m)", 0.1, 5.0, 1.2)

st.sidebar.header("Dinosaurio 2")
nombre2 = st.sidebar.text_input("Nombre ", "Allosaurus fragilis")
masa2 = st.sidebar.number_input("Masa (kg) ", 100, 80000, 2000)
femur2 = st.sidebar.number_input("Longitud del fémur (m) ", 0.1, 5.0, 0.9)

def fuerza_muscular(masa, longitud):
    return 0.3 * masa * math.sqrt(longitud)

def velocidad_maxima(masa, longitud):
    return 8 * (longitud / math.pow(masa, 1/3))

data = {
    "Dinosaurio": [nombre1, nombre2],
    "Masa (kg)": [masa1, masa2],
    "Longitud fémur (m)": [femur1, femur2],
    "Fuerza muscular estimada (N)": [fuerza_muscular(masa1, femur1), fuerza_muscular(masa2, femur2)],
    "Velocidad máx. teórica (m/s)": [velocidad_maxima(masa1, femur1), velocidad_maxima(masa2, femur2)]
}

df = pd.DataFrame(data)
st.subheader("📊 Resultados comparativos")
st.dataframe(df)

st.bar_chart(df.set_index("Dinosaurio")[["Fuerza muscular estimada (N)", "Velocidad máx. teórica (m/s)"]])
