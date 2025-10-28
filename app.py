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
st.title("🧠 Smart Core – Cuestionario")
st.caption(
    "Comparte tu nombre, edad y género, responde el cuestionario y obtén tu SmartScore personalizado."
)

DATA_FILES = {
    "Instant Noodles": "data/Productos_Instant_Noodles_SmartScore.xlsx",
    "Mac & Cheese": "data/Productos_Mac_and_Cheese_SmartScore.xlsx",
    "Ready to Eat": "data/Productos_ReadyToEat_SmartScore.xlsx",
}

RESULTS_PATH_IN_REPO = "Resultados_SmartScore.xlsx"  # se crea/actualiza vía API de GitHub

INITIAL_FORM_VALUES = {
    "nombre_completo": "",
    "edad": 1,
    "genero": "Femenino",
    "w_portion": 3,
    "w_diet": 5,
    "w_salt": 3,
    "w_fat": 3,
    "w_natural": 3,
    "w_convenience": 3,
    "w_price": 3,
}

RESET_FORM_VALUES = {
    "nombre_completo": "",
    "edad": 1,
    "genero": "Femenino",
    "w_portion": 0,
    "w_diet": 0,
    "w_salt": 0,
    "w_fat": 0,
    "w_natural": 0,
    "w_convenience": 0,
    "w_price": 0,
}

for key, value in INITIAL_FORM_VALUES.items():
    st.session_state.setdefault(key, value)

st.session_state.setdefault("success_path", "")
st.session_state.setdefault("trigger_balloons", False)
st.session_state.setdefault("_reset_form_requested", False)

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


def _apply_reset_form_state() -> None:
    """Aplica los valores de reinicio cuando se solicitó un reset."""

    if not st.session_state.get("_reset_form_requested", False):
        return

    for key, value in RESET_FORM_VALUES.items():
        st.session_state[key] = value

    st.session_state["_reset_form_requested"] = False


def reset_form_state() -> None:
    """Marca que el formulario debe reiniciarse en el próximo ciclo."""

    st.session_state["_reset_form_requested"] = True


def _df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer.getvalue()


def append_record_to_results(
    repo, ruta_archivo: str, nuevo_registro: pd.DataFrame, persona_nombre: str
) -> None:
    try:
        contents = repo.get_contents(ruta_archivo)
    except GithubException as gh_error:
        if gh_error.status == 404:
            repo.create_file(
                path=ruta_archivo,
                message=f"Creación inicial de {ruta_archivo} ({persona_nombre})",
                content=_df_to_excel_bytes(nuevo_registro),
            )
            return
        raise

    for intento in range(2):
        excel_data = base64.b64decode(contents.content)
        df_existente = pd.read_excel(BytesIO(excel_data))
        df_existente = _reorder_person_columns(df_existente)
        df_nuevo = pd.concat([df_existente, nuevo_registro], ignore_index=True)
        df_nuevo = _reorder_person_columns(df_nuevo)
        try:
            repo.update_file(
                path=ruta_archivo,
                message=f"Actualización SmartScore desde Streamlit ({persona_nombre})",
                content=_df_to_excel_bytes(df_nuevo),
                sha=contents.sha,
            )
            return
        except GithubException as update_error:
            if update_error.status == 409 and intento == 0:
                contents = repo.get_contents(ruta_archivo)
                continue
            raise


def show_success_message(path: str) -> None:
    st.session_state["success_path"] = path
    st.session_state["trigger_balloons"] = True
    reset_form_state()
    st.experimental_rerun()


# =========================================================
# 1) DATOS DE LA PERSONA + CUESTIONARIO
# =========================================================
_apply_reset_form_state()

st.header("Cuestionario de preferencias")

if st.session_state.get("success_path"):
    st.success(
        f"🎈 Tus respuestas fueron guardadas con éxito en '{st.session_state['success_path']}'."
    )
    if st.session_state.get("trigger_balloons", False):
        st.balloons()
    st.session_state["success_path"] = ""
    st.session_state["trigger_balloons"] = False

with st.form("cuestionario_form"):
    st.subheader("Datos de quien responde")
    nombre_completo = st.text_input("Nombre completo", key="nombre_completo")
    col_info_1, col_info_2 = st.columns(2)
    with col_info_1:
        edad = st.number_input(
            "Edad", min_value=1, max_value=120, step=1, key="edad"
        )
    with col_info_2:
        genero = st.selectbox(
            "Género",
            ("Femenino", "Masculino", "Prefiero no decir"),
            key="genero",
        )

    st.subheader("Importancia de cada aspecto")
    st.caption("Desliza hacia la derecha para indicar mayor importancia en cada aspecto.")
    col1, col2 = st.columns(2)
    with col1:
        w_portion = st.slider(
            "🔹 ¿Qué tan importante es el tamaño de la porción?",
            0,
            5,
            value=st.session_state["w_portion"],
            key="w_portion",
        )
        w_diet = st.slider(
            "🔹 ¿Qué tan importante es llevar una dieta sana?",
            0,
            7,
            value=st.session_state["w_diet"],
            key="w_diet",
        )
        w_salt = st.slider(
            "🔹 ¿Qué tan importante es bajo en sal?",
            0,
            5,
            value=st.session_state["w_salt"],
            key="w_salt",
        )
        w_fat = st.slider(
            "🔹 ¿Qué tan importante es bajo en grasa saturada?",
            0,
            5,
            value=st.session_state["w_fat"],
            key="w_fat",
        )
    with col2:
        w_natural = st.slider(
            "🔹 ¿Qué tan importante es que use ingredientes naturales/orgánicos?",
            0,
            5,
            value=st.session_state["w_natural"],
            key="w_natural",
        )
        w_convenience = st.slider(
            "🔹 ¿Qué tan importante es que sea rápido y fácil de preparar?",
            0,
            5,
            value=st.session_state["w_convenience"],
            key="w_convenience",
        )
        w_price = st.slider(
            "🔹 ¿Qué tan importante es precio bajo / buena relación calidad-precio?",
            0,
            5,
            value=st.session_state["w_price"],
            key="w_price",
        )

    submitted = st.form_submit_button("Enviar respuestas")

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

        persona_nombre = nombre_completo.strip()
        persona_edad = int(edad)
        persona_genero = genero

        if "GITHUB_TOKEN" not in st.secrets:
            st.warning("⚠️ Configura el secret `GITHUB_TOKEN` para guardar automáticamente en GitHub.")
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
                st.error(f"❌ No se pudo acceder al repositorio 'app_Estancia': {mensaje_repo}")
            except Exception as generic_error:
                st.error(f"❌ Error al conectar con GitHub: {generic_error}")
            else:
                ruta_archivo = RESULTS_PATH_IN_REPO
                pesos_actuales = weights.copy()
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
                            "Nombre Completo": persona_nombre,
                            "Edad": persona_edad,
                            "Género": persona_genero,
                            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Pesos": json.dumps(pesos_actuales, ensure_ascii=False, indent=2),
                            **top_columns,
                        }
                    ]
                )

                nuevo_registro = _reorder_person_columns(nuevo_registro)

                try:
                    append_record_to_results(
                        repo=repo,
                        ruta_archivo=ruta_archivo,
                        nuevo_registro=nuevo_registro,
                        persona_nombre=persona_nombre,
                    )
                except GithubException as gh_error:
                    datos_archivo = getattr(gh_error, "data", {})
                    mensaje_archivo = (
                        datos_archivo.get("message", str(gh_error))
                        if isinstance(datos_archivo, dict)
                        else str(gh_error)
                    )
                    st.error(f"❌ Error al sincronizar '{ruta_archivo}' con GitHub: {mensaje_archivo}")
                except Exception as update_error:
                    st.error(f"❌ Error al actualizar '{ruta_archivo}': {update_error}")
                else:
                    show_success_message(ruta_archivo)

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption("Estancia Profesional · Smart Core · 2025")
