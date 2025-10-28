# app.py
import re
import base64
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st
from github import Github, GithubException

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

RESULTS_PATH_IN_REPO = "Resultados_SmartScore.xlsx"  # se crea/actualiza vía API de GitHub

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
    """Extrae minutos de cadenas como '5 minutos', 'Listo para comer', etc."""
    if not isinstance(s, str):
        return 0.0
    s_low = s.lower().strip()
    if "listo" in s_low:
        return 0.0
    m = re.search(r"(\d+)", s_low)
    return float(m.group(1)) if m else 0.0

def _to_bool_natural(x) -> int:
    """Devuelve 1 si contiene 'sí'/'si'/'organic'/'orgánico', 0 en otro caso."""
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
# 1) CUESTIONARIO → PESOS
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
# 2) CARGA Y NORMALIZACIÓN DE ATRIBUTOS
# =========================================================
st.header("2) Carga y normalización de atributos")

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
# 3) SMART SCORE Y RANKING
# =========================================================
st.header("3) Cálculo del Smart Score y Ranking por categoría")

calcular = st.button("🧮 Calcular SmartScore y Rankear")

if calcular:
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

    topk = (
        df_resultado.sort_values("SmartScore", ascending=False)
        .groupby("Categoría__App")
        .head(3)
        .reset_index(drop=True)
    )

    stats = df_resultado.groupby("Categoría__App")["SmartScore"].agg(["mean", "std", "min", "max"]).reset_index()
    stats.columns = ["Categoría", "Promedio", "Desviación Std", "Mínimo", "Máximo"]

    st.session_state["df_resultado"] = df_resultado
    st.session_state["topk"] = topk
    st.session_state["stats"] = stats
    st.session_state["weights_snapshot"] = weights.copy()

if "df_resultado" in st.session_state:
    st.success("✅ SmartScore personalizado calculado para cada producto.")
    st.dataframe(st.session_state["df_resultado"].head(20))

if "topk" in st.session_state:
    st.subheader("🏆 Top por categoría (3 mejores)")
    st.dataframe(st.session_state["topk"])

if "stats" in st.session_state:
    st.subheader("📊 Resumen por categoría")
    st.dataframe(st.session_state["stats"])

    # =====================================================
    # 4) GUARDADO EN GITHUB (versión final corregida)
    # =====================================================
    st.header("4) Guardado en GitHub (opcional)")
    st.caption("Configura en Streamlit Cloud un secret llamado `GITHUB_TOKEN` con permiso `repo` y usa el repo público `app_Estancia`.")

    github_client = None
    github_user = None

    if "GITHUB_TOKEN" in st.secrets:
        try:
            github_client = Github(st.secrets["GITHUB_TOKEN"])
            github_user = github_client.get_user()
            st.info(f"Conectado como: {github_user.login}")
            try:
                github_user.get_repo("app_Estancia")
                st.success("✅ Repositorio 'app_Estancia' encontrado.")
            except GithubException as repo_error:
                if repo_error.status == 404:
                    st.warning("⚠️ No se encontró el repo 'app_Estancia'. Revisa el nombre o permisos del token.")
                else:
                    datos_repo = getattr(repo_error, "data", {})
                    mensaje_repo = datos_repo.get("message", str(repo_error)) if isinstance(datos_repo, dict) else str(repo_error)
                    st.error(f"❌ Error al verificar el repositorio: {mensaje_repo}")
        except Exception as e:
            st.error(f"❌ Error al conectar con GitHub: {e}")
            github_client = None
            github_user = None
    else:
        st.warning("⚠️ Configura el secret `GITHUB_TOKEN` con permisos de repo para habilitar el guardado automático.")

    if "df_resultado" not in st.session_state or "topk" not in st.session_state:
        st.info("Calcula tu SmartScore antes de intentar guardar los resultados.")
    else:
        usuario = st.text_input("Tu nombre o identificador (para registro):", "").strip()
        save_status = st.empty()

        if not usuario:
            st.info("Ingresa tu nombre para mostrar el botón de guardado.")
        else:
            if st.button("💾 Guardar resultados", key="guardar_resultados"):
                if github_client is None or github_user is None:
                    save_status.error("❌ No se pudo conectar a GitHub. Verifica el secret `GITHUB_TOKEN`.")
                else:
                    try:
                        repo = github_user.get_repo("app_Estancia")
                    except GithubException as repo_error:
                        if repo_error.status == 404:
                            save_status.error("❌ No se encontró el repositorio 'app_Estancia'.")
                        else:
                            datos_repo = getattr(repo_error, "data", {})
                            mensaje_repo = datos_repo.get("message", str(repo_error)) if isinstance(datos_repo, dict) else str(repo_error)
                            save_status.error(f"❌ Error al acceder al repositorio: {mensaje_repo}")
                    except Exception as repo_generic_error:
                        save_status.error(f"❌ Error al acceder al repositorio: {repo_generic_error}")
                    else:
                        ruta_archivo = RESULTS_PATH_IN_REPO
                        pesos_actuales = st.session_state.get("weights_snapshot", weights.copy())
                        topk_df = st.session_state["topk"]
                        top_lines = [
                            f"{r['Categoría__App']}: {r['Producto']} ({r['SmartScore']:.3f})"
                            for _, r in topk_df.iterrows()
                        ]
                        top_str = " | ".join(top_lines)
                        nuevo_registro = pd.DataFrame([
                            {
                                "Usuario": usuario,
                                "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Pesos": str(pesos_actuales),
                                "TopPorCategoria": top_str,
                            }
                        ])

                        try:
                            contents = repo.get_contents(ruta_archivo)
                        except GithubException as gh_error:
                            if gh_error.status == 404:
                                try:
                                    buffer = BytesIO()
                                    nuevo_registro.to_excel(buffer, index=False)
                                    buffer.seek(0)
                                    repo.create_file(
                                        path=ruta_archivo,
                                        message=f"Creación inicial de {ruta_archivo} ({usuario})",
                                        content=buffer.getvalue()
                                    )
                                    save_status.success(f"✅ Archivo '{ruta_archivo}' creado y resultados guardados correctamente.")
                                except Exception as create_error:
                                    save_status.error(f"❌ Error al crear '{ruta_archivo}': {create_error}")
                            else:
                                datos_archivo = getattr(gh_error, "data", {})
                                mensaje_archivo = datos_archivo.get("message", str(gh_error)) if isinstance(datos_archivo, dict) else str(gh_error)
                                save_status.error(f"❌ No se pudo leer '{ruta_archivo}': {mensaje_archivo}")
                        except Exception as read_error:
                            save_status.error(f"❌ Error al leer '{ruta_archivo}': {read_error}")
                        else:
                            try:
                                excel_data = base64.b64decode(contents.content)
                                df_existente = pd.read_excel(BytesIO(excel_data))
                                df_nuevo = pd.concat([df_existente, nuevo_registro], ignore_index=True)
                                buffer = BytesIO()
                                df_nuevo.to_excel(buffer, index=False)
                                buffer.seek(0)
                                repo.update_file(
                                    path=ruta_archivo,
                                    message=f"Actualización SmartScore desde Streamlit ({usuario})",
                                    content=buffer.getvalue(),
                                    sha=contents.sha
                                )
                                save_status.success(f"✅ Archivo '{ruta_archivo}' actualizado con tus resultados.")
                            except Exception as update_error:
                                save_status.error(f"❌ Error al actualizar '{ruta_archivo}': {update_error}")

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption("Estancia Profesional · Smart Core · 2025")
