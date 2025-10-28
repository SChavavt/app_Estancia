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
st.caption("App unificada: cuestionario → pesos → SmartScore → ranking → (opcional) guardado en GitHub")

DATA_FILES = {
    "Instant Noodles": "data/Productos_Instant_Noodles_SmartScore.xlsx",
    "Mac & Cheese": "data/Productos_Mac_and_Cheese_SmartScore.xlsx",
    "Ready to Eat": "data/Productos_ReadyToEat_SmartScore.xlsx",
}

RESULTS_PATH_IN_REPO = "data/Resultados_SmartScore.xlsx"   # se crea/actualiza vía API de GitHub

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
    """
    Extrae minutos de cadenas como '5 minutos', 'Listo para comer', etc.
    'Listo...' => 0 min.
    """
    if not isinstance(s, str):
        return 0.0
    s_low = s.lower().strip()
    if "listo" in s_low:  # listo para comer/snack
        return 0.0
    m = re.search(r"(\d+)", s_low)
    return float(m.group(1)) if m else 0.0

def _to_bool_natural(x) -> int:
    """Devuelve 1 si el texto contiene 'sí'/'si'/'organic'/'orgánico', 0 en otro caso."""
    try:
        s = str(x).lower()
    except Exception:
        return 0
    if any(k in s for k in ["sí", "si", "orgánico", "organico", "organic"]):
        return 1
    return 0

def normalize_minmax(series: pd.Series) -> pd.Series:
    """(x - min) / (max - min) con manejo de división por cero."""
    smin, smax = series.min(), series.max()
    denom = (smax - smin) if (smax - smin) != 0 else 1.0
    return (series - smin) / denom

# =========================================================
# 1) CUESTIONARIO → PESOS (mismos rangos que tu script)
# =========================================================
st.header("1) Cuestionario de preferencias → cálculo de PESOS")

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

# Normalización EXACTA a los denominadores usados en tu lógica
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
# 2) CARGA Y NORMALIZACIÓN DE ATRIBUTOS DE PRODUCTOS
# =========================================================
st.header("2) Carga y normalización de atributos")

try:
    df_all = _read_all_products(DATA_FILES)
except Exception as e:
    st.error(f"No pude leer los Excel en /data: {e}")
    st.stop()

df_calc = df_all.copy()

# Atributos esperados por nombre (ajusta si tu cabecera es distinta)
# - Calorías, Sodio_mg, Grasa Saturada_g, Proteína_g, Naturales, Tiempo_Preparación, Precio_USD
# Invertidos (menos es mejor): sodio, grasa, precio, minutos preparación
# Directos (más es mejor): proteína (dieta), calorías (porción), naturales->binario
try:
    # INVERTIDOS
    df_calc["Sodio_norm"] = 1 - normalize_minmax(df_calc["Sodio_mg"])
    df_calc["Grasa_norm"] = 1 - normalize_minmax(df_calc["Grasa Saturada_g"])
    df_calc["Precio_norm"] = 1 - normalize_minmax(df_calc["Precio_USD"])

    minutos = df_calc["Tiempo_Preparación"].apply(_extract_minutes)
    df_calc["Conveniencia_norm"] = 1 - normalize_minmax(minutos)

    # DIRECTOS
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
        ].head(12)
    )

# =========================================================
# 3) SMART SCORE POR PRODUCTO (promedio ponderado / suma de pesos)
# =========================================================
st.header("3) Cálculo del Smart Score y Ranking por categoría")

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

    # Resumen por categoría
    st.subheader("📊 Resumen estadístico por categoría")
    stats = df_resultado.groupby("Categoría__App")["SmartScore"].agg(["mean", "std", "min", "max"]).reset_index()
    stats.columns = ["Categoría", "Promedio", "Desviación Std", "Mínimo", "Máximo"]
    st.dataframe(stats)

    # =====================================================
    # 4) (OPCIONAL) GUARDADO EN GITHUB
    # =====================================================
    st.header("4) Guardado en GitHub (opcional)")
    st.caption("Configura en Streamlit Cloud un secret llamado `GITHUB_TOKEN` y el repo público `app_Estancia`.")
    usuario = st.text_input("Tu nombre o identificador (para registro):", "")

    if usuario and st.button("💾 Guardar resultados en GitHub"):
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_user().get_repo("app_Estancia")

            # Leer archivo existente o crear DataFrame vacío
            try:
                contents = repo.get_contents(RESULTS_PATH_IN_REPO)
                excel_data = base64.b64decode(contents.content)
                df_saved = pd.read_excel(BytesIO(excel_data))
            except Exception:
                df_saved = pd.DataFrame(columns=["Usuario", "Fecha", "Pesos", "TopPorCategoria"])

            # serializar pesos y top por categoría
            pesos_str = str(weights)
            # string con "CAT: producto (score)"
            top_lines = []
            for _, r in topk.iterrows():
                top_lines.append(f"{r['Categoría__App']}: {r['Producto']} ({r['SmartScore']:.3f})")
            top_str = " | ".join(top_lines)

            newrow = {
                "Usuario": usuario,
                "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Pesos": pesos_str,
                "TopPorCategoria": top_str,
            }
            df_saved = pd.concat([df_saved, pd.DataFrame([newrow])], ignore_index=True)

            buf = BytesIO()
            df_saved.to_excel(buf, index=False)

            if "contents" in locals():
                repo.update_file(
                    contents.path,
                    "Actualización de resultados SmartCore desde Streamlit",
                    buf.getvalue(),
                    contents.sha
                )
            else:
                repo.create_file(
                    RESULTS_PATH_IN_REPO,
                    "Creación de Resultados_SmartScore.xlsx",
                    buf.getvalue()
                )
            st.success("✅ Resultados guardados correctamente en GitHub.")
        except Exception as e:
            st.error(f"❌ No pude guardar en GitHub: {e}")

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption("Estancia Profesional · Smart Core · 2025")
