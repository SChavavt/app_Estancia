# app.py
import re
import base64
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st
from github import Github

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="Smart Core – Estancia", page_icon="🧠", layout="wide")
st.title("🧠 Smart Core – Cuestionario y Ranking por Categoría")
st.caption("App unificada: cuestionario → pesos → SmartScore → ranking → guardado automático en GitHub")

DATA_FILES = {
    "Instant Noodles": "data/Productos_Instant_Noodles_SmartScore.xlsx",
    "Mac & Cheese": "data/Productos_Mac_and_Cheese_SmartScore.xlsx",
    "Ready to Eat": "data/Productos_ReadyToEat_SmartScore.xlsx",
}

RESULTS_FILENAME = "Resultados_SmartScore.xlsx"  # Se guarda en la raíz del repo

# =========================================================
# HELPERS
# =========================================================
def _read_all_products(files_dict: dict) -> pd.DataFrame:
    frames = []
    for category, path in files_dict.items():
        df = pd.read_excel(path)
        df["Categoría__App"] = category
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

def _extract_minutes(s: str) -> float:
    if not isinstance(s, str):
        return 0.0
    s_low = s.lower().strip()
    if "listo" in s_low:
        return 0.0
    m = re.search(r"(\d+)", s_low)
    return float(m.group(1)) if m else 0.0

def _to_bool_natural(x) -> int:
    try:
        s = str(x).lower()
    except Exception:
        return 0
    if any(k in s for k in ["sí", "si", "orgánico", "organico", "organic"]):
        return 1
    return 0

def normalize_minmax(series: pd.Series) -> pd.Series:
    smin, smax = series.min(), series.max()
    denom = (smax - smin) if (smax - smin) != 0 else 1.0
    return (series - smin) / denom

# =========================================================
# 1️⃣ CUESTIONARIO → PESOS
# =========================================================
st.header("1️⃣ Cuestionario de preferencias → cálculo de PESOS")

col1, col2 = st.columns(2)
with col1:
    w_portion = st.slider("🔹 ¿Qué tan importante es el tamaño de la porción?", 0, 5, 3)
    w_diet = st.slider("🔹 ¿Qué tan importante es llevar una dieta sana?", 1, 7, 5)
    w_salt = st.slider("🔹 ¿Qué tan importante es bajo en sal?", 0, 5, 3)
    w_fat = st.slider("🔹 ¿Qué tan importante es bajo en grasa saturada?", 0, 5, 3)
with col2:
    w_natural = st.slider("🔹 ¿Qué tan importante es que use ingredientes naturales/orgánicos?", 0, 5, 3)
    w_convenience = st.slider("🔹 ¿Qué tan importante es que sea rápido y fácil de preparar?", 0, 5, 3)
    w_price = st.slider("🔹 ¿Qué tan importante es precio bajo / buena relación calidad-precio?", 0, 5, 3)

weights = {
    "portion": w_portion / 5.0,
    "diet": w_diet / 7.0,
    "salt": w_salt / 5.0,
    "fat": w_fat / 5.0,
    "natural": w_natural / 5.0,
    "convenience": w_convenience / 5.0,
    "price": w_price / 5.0,
}
with st.expander("Ver pesos normalizados"):
    st.json(weights)

# =========================================================
# 2️⃣ CARGA Y NORMALIZACIÓN DE ATRIBUTOS
# =========================================================
st.header("2️⃣ Carga y normalización de atributos")

try:
    df_all = _read_all_products(DATA_FILES)
except Exception as e:
    st.error(f"No pude leer los Excel en /data: {e}")
    st.stop()

df_calc = df_all.copy()

try:
    df_calc["Sodio_norm"] = 1 - normalize_minmax(df_calc["Sodio_mg"])
    df_calc["Grasa_norm"] = 1 - normalize_minmax(df_calc["Grasa Saturada_g"])
    df_calc["Precio_norm"] = 1 - normalize_minmax(df_calc["Precio_USD"])
    minutos = df_calc["Tiempo_Preparación"].apply(_extract_minutes)
    df_calc["Conveniencia_norm"] = 1 - normalize_minmax(minutos)
    df_calc["Dieta_norm"] = normalize_minmax(df_calc["Proteína_g"])
    df_calc["Porción_norm"] = normalize_minmax(df_calc["Calorías"])
    df_calc["Natural_norm"] = df_calc["Naturales"].apply(_to_bool_natural).astype(float)
except KeyError as e:
    st.error(f"Falta una columna esperada en tus Excel: {e}")
    st.stop()

with st.expander("Ver muestra de atributos normalizados"):
    st.dataframe(
        df_calc[
            ["Producto", "Categoría", "Sodio_norm", "Grasa_norm", "Precio_norm",
             "Conveniencia_norm", "Dieta_norm", "Porción_norm", "Natural_norm"]
        ].head(10)
    )

# =========================================================
# 3️⃣ SMART SCORE Y RANKING
# =========================================================
st.header("3️⃣ Cálculo del Smart Score y Ranking por categoría")

if st.button("🧮 Calcular SmartScore y Rankear"):
    sum_w = sum(weights.values()) if sum(weights.values()) != 0 else 1.0
    df_calc["SmartScore"] = (
        weights["salt"] * df_calc["Sodio_norm"] +
        weights["fat"] * df_calc["Grasa_norm"] +
        weights["natural"] * df_calc["Natural_norm"] +
        weights["convenience"] * df_calc["Conveniencia_norm"] +
        weights["price"] * df_calc["Precio_norm"] +
        weights["portion"] * df_calc["Porción_norm"] +
        weights["diet"] * df_calc["Dieta_norm"]
    ) / sum_w

    df_resultado = df_calc[["Producto", "Categoría", "Categoría__App", "SmartScore", "Comentarios Clave"]].copy()
    df_resultado = df_resultado.sort_values("SmartScore", ascending=False).reset_index(drop=True)

    st.success("✅ SmartScore personalizado calculado para cada producto.")
    st.dataframe(df_resultado.head(20))

    st.subheader("🏆 Top por categoría (3 mejores)")
    topk = (
        df_resultado.sort_values("SmartScore", ascending=False)
        .groupby("Categoría__App")
        .head(3)
        .reset_index(drop=True)
    )
    st.dataframe(topk)

    st.subheader("📊 Resumen por categoría")
    stats = df_resultado.groupby("Categoría__App")["SmartScore"].agg(["mean", "std", "min", "max"]).reset_index()
    stats.columns = ["Categoría", "Promedio", "Desviación Std", "Mínimo", "Máximo"]
    st.dataframe(stats)

    # =====================================================
    # 4️⃣ GUARDADO EN GITHUB (en raíz del repo)
    # =====================================================
    st.header("4️⃣ Guardado en GitHub (opcional)")
    st.caption("Asegúrate de tener configurado el secret `GITHUB_TOKEN` con permiso `repo` y usar el repo `app_Estancia`.")

    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        user = g.get_user()
        repo = g.get_user().get_repo("app_Estancia")
        st.success(f"✅ Conectado como {user.login} y repositorio '{repo.name}' disponible.")
    except Exception as e:
        st.error(f"❌ No se pudo conectar con GitHub: {e}")
        st.stop()

    usuario = st.text_input("Tu nombre o identificador (para registro):")

    if usuario:
        if st.button("💾 Guardar resultados"):
            try:
                # Preparar registro
                pesos_str = str(weights)
                top_lines = [f"{r['Categoría__App']}: {r['Producto']} ({r['SmartScore']:.3f})" for _, r in topk.iterrows()]
                top_str = " | ".join(top_lines)
                nuevo_registro = pd.DataFrame([{
                    "Usuario": usuario,
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Pesos": pesos_str,
                    "TopPorCategoria": top_str,
                }])

                # Intentar leer el archivo existente
                try:
                    contents = repo.get_contents(RESULTS_FILENAME)
                    excel_data = base64.b64decode(contents.content)
                    df_existente = pd.read_excel(BytesIO(excel_data))
                    df_nuevo = pd.concat([df_existente, nuevo_registro], ignore_index=True)

                    buffer = BytesIO()
                    df_nuevo.to_excel(buffer, index=False)
                    repo.update_file(
                        path=RESULTS_FILENAME,
                        message=f"Actualización SmartScore ({usuario})",
                        content=buffer.getvalue(),
                        sha=contents.sha
                    )
                    st.success(f"✅ Resultados de {usuario} actualizados correctamente en el repositorio.")

                except Exception:
                    # Si el archivo no existe, lo crea
                    buffer = BytesIO()
                    nuevo_registro.to_excel(buffer, index=False)
                    repo.create_file(
                        path=RESULTS_FILENAME,
                        message=f"Creación inicial de Resultados_SmartScore.xlsx ({usuario})",
                        content=buffer.getvalue()
                    )
                    st.success(f"✅ Archivo creado y resultados de {usuario} guardados correctamente en GitHub.")

            except Exception as e:
                st.error(f"❌ Error al guardar los resultados en GitHub: {e}")

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption("Estancia Profesional · Smart Core · 2025")
