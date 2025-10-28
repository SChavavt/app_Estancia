# app.py
import re
import json
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
st.caption(
    "Comparte tu nombre, edad y género, responde el cuestionario y obtén tu SmartScore personalizado."
)

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


def _reorder_person_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Coloca Nombre/Edad/Género al inicio y elimina 'Usuario' si aparece."""
    columnas_inicio = ["Nombre Completo", "Edad", "Género"]
    presentes = [col for col in columnas_inicio if col in df.columns]
    restantes = [col for col in df.columns if col not in presentes and col != "Usuario"]
    df_reordenado = df[presentes + restantes]
    if "Usuario" in df_reordenado.columns:
        df_reordenado = df_reordenado.drop(columns=["Usuario"])
    return df_reordenado


# =========================================================
# 1) DATOS DE LA PERSONA + CUESTIONARIO
# =========================================================
st.header("1) Cuestionario de preferencias")

with st.form("cuestionario_form"):
    st.subheader("Datos de quien responde")
    nombre_completo = st.text_input("Nombre completo")
    col_info_1, col_info_2 = st.columns(2)
    with col_info_1:
        edad = st.number_input("Edad", min_value=1, max_value=120, step=1)
    with col_info_2:
        genero = st.selectbox("Género", ("Femenino", "Masculino", "Prefiero no decir"))

    st.subheader("Importancia de cada aspecto")
    col1, col2 = st.columns(2)
    with col1:
        w_portion = st.slider(
            "🔹 ¿Qué tan importante es el tamaño de la porción? (Desliza hacia la derecha para indicar mayor importancia)",
            0,
            5,
            3,
        )
        w_diet = st.slider(
            "🔹 ¿Qué tan importante es llevar una dieta sana? (Desliza hacia la derecha para indicar mayor importancia)",
            1,
            7,
            5,
        )
        w_salt = st.slider(
            "🔹 ¿Qué tan importante es bajo en sal? (Desliza hacia la derecha para indicar mayor importancia)",
            0,
            5,
            3,
        )
        w_fat = st.slider(
            "🔹 ¿Qué tan importante es bajo en grasa saturada? (Desliza hacia la derecha para indicar mayor importancia)",
            0,
            5,
            3,
        )
    with col2:
        w_natural = st.slider(
            "🔹 ¿Qué tan importante es que use ingredientes naturales/orgánicos? (Desliza hacia la derecha para indicar mayor importancia)",
            0,
            5,
            3,
        )
        w_convenience = st.slider(
            "🔹 ¿Qué tan importante es que sea rápido y fácil de preparar? (Desliza hacia la derecha para indicar mayor importancia)",
            0,
            5,
            3,
        )
        w_price = st.slider(
            "🔹 ¿Qué tan importante es precio bajo / buena relación calidad-precio? (Desliza hacia la derecha para indicar mayor importancia)",
            0,
            5,
            3,
        )

    submitted = st.form_submit_button("Enviar respuestas")

# =========================================================
# 2) CARGA Y NORMALIZACIÓN DE ATRIBUTOS
# =========================================================
st.header("2) Carga y normalización de atributos")

try:
    df_all = _read_all_products(DATA_FILES)
except Exception as e:
    st.error(f"No pude leer los Excel en /data: {e}")
    st.stop()

df_base = df_all.copy()

try:
    df_base["Sodio_norm"] = 1 - normalize_minmax(df_base["Sodio_mg"])
    df_base["Grasa_norm"] = 1 - normalize_minmax(df_base["Grasa Saturada_g"])
    df_base["Precio_norm"] = 1 - normalize_minmax(df_base["Precio_USD"])
    minutos = df_base["Tiempo_Preparación"].apply(_extract_minutes)
    df_base["Conveniencia_norm"] = 1 - normalize_minmax(minutos)
    df_base["Dieta_norm"] = normalize_minmax(df_base["Proteína_g"])
    df_base["Porción_norm"] = normalize_minmax(df_base["Calorías"])
    df_base["Natural_norm"] = df_base["Naturales"].apply(_to_bool_natural).astype(float)
except KeyError as e:
    st.error(f"Falta una columna esperada en tus Excel: {e}")
    st.stop()

with st.expander("Ver muestra de atributos normalizados"):
    st.dataframe(
        df_base[
            [
                "Producto",
                "Categoría",
                "Sodio_norm",
                "Grasa_norm",
                "Precio_norm",
                "Conveniencia_norm",
                "Dieta_norm",
                "Porción_norm",
                "Natural_norm",
            ]
        ].head(10)
    )

# =========================================================
# 3) SMART SCORE Y RANKING
# =========================================================
st.header("3) Resultados del Smart Score")

if submitted:
    errores = []
    if not nombre_completo.strip():
        errores.append("Ingresa tu nombre completo para continuar.")
    if edad <= 0:
        errores.append("La edad debe ser mayor a 0.")

    if errores:
        for err in errores:
            st.error(err)
    else:
        weights = {
            "portion": w_portion / 5.0,
            "diet": w_diet / 7.0,
            "salt": w_salt / 5.0,
            "fat": w_fat / 5.0,
            "natural": w_natural / 5.0,
            "convenience": w_convenience / 5.0,
            "price": w_price / 5.0,
        }

        df_calc = df_base.copy()
        sum_w = sum(weights.values()) if sum(weights.values()) != 0 else 1.0
        df_calc["SmartScore"] = (
            weights["salt"] * df_calc["Sodio_norm"]
            + weights["fat"] * df_calc["Grasa_norm"]
            + weights["natural"] * df_calc["Natural_norm"]
            + weights["convenience"] * df_calc["Conveniencia_norm"]
            + weights["price"] * df_calc["Precio_norm"]
            + weights["portion"] * df_calc["Porción_norm"]
            + weights["diet"] * df_calc["Dieta_norm"]
        ) / sum_w

        df_resultado = df_calc[
            ["Producto", "Categoría", "Categoría__App", "SmartScore", "Comentarios Clave"]
        ].copy()
        df_resultado = df_resultado.sort_values("SmartScore", ascending=False).reset_index(drop=True)

        topk = (
            df_resultado.sort_values("SmartScore", ascending=False)
            .groupby("Categoría__App")
            .head(3)
            .reset_index(drop=True)
        )

        stats = (
            df_resultado.groupby("Categoría__App")["SmartScore"]
            .agg(["mean", "std", "min", "max"])
            .reset_index()
        )
        stats.columns = ["Categoría", "Promedio", "Desviación Std", "Mínimo", "Máximo"]

        st.session_state["df_resultado"] = df_resultado
        st.session_state["topk"] = topk
        st.session_state["stats"] = stats
        st.session_state["weights_snapshot"] = weights.copy()
        st.session_state["persona_nombre"] = nombre_completo.strip()
        st.session_state["persona_edad"] = int(edad)
        st.session_state["persona_genero"] = genero

        st.session_state["save_feedback"] = []

        if "GITHUB_TOKEN" not in st.secrets:
            st.session_state["save_feedback"].append(
                ("warning", "⚠️ Configura el secret `GITHUB_TOKEN` para guardar automáticamente en GitHub.")
            )
        else:
            try:
                github_client = Github(st.secrets["GITHUB_TOKEN"])
                github_user = github_client.get_user()
                repo = github_user.get_repo("app_Estancia")
            except GithubException as gh_error:
                datos_repo = getattr(gh_error, "data", {})
                mensaje_repo = (
                    datos_repo.get("message", str(gh_error))
                    if isinstance(datos_repo, dict)
                    else str(gh_error)
                )
                st.session_state["save_feedback"].append(
                    ("error", f"❌ No se pudo acceder al repositorio 'app_Estancia': {mensaje_repo}")
                )
            except Exception as generic_error:
                st.session_state["save_feedback"].append(
                    ("error", f"❌ Error al conectar con GitHub: {generic_error}")
                )
            else:
                ruta_archivo = RESULTS_PATH_IN_REPO
                pesos_actuales = st.session_state.get("weights_snapshot", weights.copy())
                topk_df = topk.sort_values(["Categoría__App", "SmartScore"], ascending=[True, False])

                top_columns = {}
                for categoria, group in topk_df.groupby("Categoría__App"):
                    for rank, (_, fila) in enumerate(group.iterrows(), start=1):
                        base_col = f"{categoria} · Top {rank}"
                        top_columns[f"{base_col} · Producto"] = fila["Producto"]
                        top_columns[f"{base_col} · SmartScore"] = f"{fila['SmartScore']:.3f}"
                        comentario = fila.get("Comentarios Clave", "")
                        if isinstance(comentario, str) and comentario.strip():
                            top_columns[f"{base_col} · Comentarios"] = comentario.strip()

                nuevo_registro = pd.DataFrame(
                    [
                        {
                            "Nombre Completo": st.session_state["persona_nombre"],
                            "Edad": st.session_state["persona_edad"],
                            "Género": st.session_state["persona_genero"],
                            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Pesos": json.dumps(pesos_actuales, ensure_ascii=False, indent=2),
                            **top_columns,
                        }
                    ]
                )

                nuevo_registro = _reorder_person_columns(nuevo_registro)

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
                                message=(
                                    f"Creación inicial de {ruta_archivo} ({st.session_state['persona_nombre']})"
                                ),
                                content=buffer.getvalue(),
                            )
                            st.session_state["save_feedback"].append(
                                ("success", f"✅ Archivo '{ruta_archivo}' creado y resultados guardados correctamente.")
                            )
                        except Exception as create_error:
                            st.session_state["save_feedback"].append(
                                ("error", f"❌ Error al crear '{ruta_archivo}': {create_error}")
                            )
                    else:
                        datos_archivo = getattr(gh_error, "data", {})
                        mensaje_archivo = (
                            datos_archivo.get("message", str(gh_error))
                            if isinstance(datos_archivo, dict)
                            else str(gh_error)
                        )
                        st.session_state["save_feedback"].append(
                            ("error", f"❌ No se pudo leer '{ruta_archivo}': {mensaje_archivo}")
                        )
                except Exception as read_error:
                    st.session_state["save_feedback"].append(
                        ("error", f"❌ Error al leer '{ruta_archivo}': {read_error}")
                    )
                else:
                    try:
                        excel_data = base64.b64decode(contents.content)
                        df_existente = pd.read_excel(BytesIO(excel_data))
                        df_existente = _reorder_person_columns(df_existente)
                        df_nuevo = pd.concat([df_existente, nuevo_registro], ignore_index=True)
                        df_nuevo = _reorder_person_columns(df_nuevo)
                        buffer = BytesIO()
                        df_nuevo.to_excel(buffer, index=False)
                        buffer.seek(0)
                        repo.update_file(
                            path=ruta_archivo,
                            message=(
                                f"Actualización SmartScore desde Streamlit ({st.session_state['persona_nombre']})"
                            ),
                            content=buffer.getvalue(),
                            sha=contents.sha,
                        )
                        st.session_state["save_feedback"].append(
                            ("success", f"✅ Archivo '{ruta_archivo}' actualizado con tus resultados.")
                        )
                    except Exception as update_error:
                        st.session_state["save_feedback"].append(
                            ("error", f"❌ Error al actualizar '{ruta_archivo}': {update_error}")
                        )

if "weights_snapshot" in st.session_state:
    with st.expander("Ver pesos normalizados"):
        st.json(st.session_state["weights_snapshot"])

if "df_resultado" in st.session_state:
    st.success("✅ SmartScore personalizado calculado para cada producto.")
    st.dataframe(st.session_state["df_resultado"].head(20))

if "topk" in st.session_state:
    st.subheader("🏆 Top por categoría (3 mejores)")
    st.dataframe(st.session_state["topk"])

if "stats" in st.session_state:
    st.subheader("📊 Resumen por categoría")
    st.dataframe(st.session_state["stats"])

# =========================================================
# 4) ESTADO DEL GUARDADO EN GITHUB
# =========================================================
st.header("4) Guardado en GitHub")
st.caption(
    "El guardado sucede automáticamente al enviar tus respuestas si existe el secret `GITHUB_TOKEN`."
)

if "save_feedback" in st.session_state:
    for level, message in st.session_state["save_feedback"]:
        if level == "success":
            st.success(message)
        elif level == "warning":
            st.warning(message)
        else:
            st.error(message)
elif "weights_snapshot" in st.session_state:
    st.info("Envía el formulario para guardar tus resultados en GitHub.")

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption("Estancia Profesional · Smart Core · 2025")
