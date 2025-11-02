# app.py
import re
import json
import random
import base64
import html
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
from github import Github, GithubException

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="Smart Core – Estancia", page_icon="🧠", layout="wide")
DEFAULT_LANGUAGE = "English"
LANGUAGE_CONTENT = {
    "English": {
        "page_title": "🧠 Smart Core – Questionnaire",
        "page_caption": "Share your name, age, and gender, answer the questionnaire, and receive your personalized SmartScore.",
        "intro_text": "Use this short form to tell us what matters most when choosing instant food products so we can tailor your SmartScore recommendations.",
        "questionnaire_header": "Preference questionnaire",
        "respondent_data_subheader": "Respondent details",
        "name_label": "Full name",
        "age_label": "Age",
        "gender_label": "Gender",
        "aspects_subheader": "Importance of each aspect",
        "aspects_caption": "Slide to the right to indicate higher importance for each aspect.",
        "slider_portion": "🔹 How important is portion size?",
        "slider_diet": "🔹 How important is maintaining a healthy diet?",
        "slider_salt": "🔹 How important is being low in salt?",
        "slider_fat": "🔹 How important is being low in saturated fat?",
        "slider_natural": "🔹 How important is using natural/organic ingredients?",
        "slider_convenience": "🔹 How important is being quick and easy to prepare?",
        "slider_price": "🔹 How important is a low price / good value?",
        "submit_button": "Submit responses",
        "success_saved": "🎈 Your answers were successfully saved to '{path}'.",
        "error_name_required": "Enter your full name to continue.",
        "error_age_positive": "Age must be greater than 0.",
        "error_read_excel": "I couldn't read the Excel files in /data: {error}",
        "error_missing_column": "An expected column is missing in your Excel files: {column}",
        "warning_github_token": "⚠️ Configure the `GITHUB_TOKEN` secret to automatically save to GitHub.",
        "error_repo_access": "❌ Couldn't access the 'app_Estancia' repository: {error}",
        "error_github_connection": "❌ Error connecting to GitHub: {error}",
        "error_sync_repo": "❌ Error syncing '{path}' with GitHub: {error}",
        "error_update_file": "❌ Error updating '{path}': {error}",
        "page_header": "🧠 Smart Core – Questionnaire",
    },
    "Español": {
        "page_title": "🧠 Smart Core – Cuestionario",
        "page_caption": "Comparte tu nombre, edad y género, responde el cuestionario para poder obtener tu SmartScore personalizado.",
        "intro_text": "Este breve cuestionario nos ayuda a entender qué valoras al elegir productos de comida instantánea y nos permite personalizar tu SmartScore.",
        "questionnaire_header": "Cuestionario de preferencias",
        "respondent_data_subheader": "Datos de quien responde",
        "name_label": "Nombre completo",
        "age_label": "Edad",
        "gender_label": "Género",
        "aspects_subheader": "Importancia de cada aspecto",
        "aspects_caption": "Desliza hacia la derecha para indicar mayor importancia en cada aspecto.",
        "slider_portion": "🔹 ¿Qué tan importante es el tamaño de la porción?",
        "slider_diet": "🔹 ¿Qué tan importante es llevar una dieta sana?",
        "slider_salt": "🔹 ¿Qué tan importante es bajo en sal?",
        "slider_fat": "🔹 ¿Qué tan importante es bajo en grasa saturada?",
        "slider_natural": "🔹 ¿Qué tan importante es que use ingredientes naturales/orgánicos?",
        "slider_convenience": "🔹 ¿Qué tan importante es que sea rápido y fácil de preparar?",
        "slider_price": "🔹 ¿Qué tan importante es precio bajo / buena relación calidad-precio?",
        "submit_button": "Enviar respuestas",
        "success_saved": "🎈 Tus respuestas fueron guardadas con éxito en '{path}'.",
        "error_name_required": "Ingresa tu nombre completo para continuar.",
        "error_age_positive": "La edad debe ser mayor a 0.",
        "error_read_excel": "No pude leer los Excel en /data: {error}",
        "error_missing_column": "Falta una columna esperada en tus Excel: {column}",
        "warning_github_token": "⚠️ Configura el secret `GITHUB_TOKEN` para guardar automáticamente en GitHub.",
        "error_repo_access": "❌ No se pudo acceder al repositorio 'app_Estancia': {error}",
        "error_github_connection": "❌ Error al conectar con GitHub: {error}",
        "error_sync_repo": "❌ Error al sincronizar '{path}' con GitHub: {error}",
        "error_update_file": "❌ Error al actualizar '{path}': {error}",
        "page_header": "🧠 Smart Core – Cuestionario",
    },
}

LANGUAGE_OPTIONS = list(LANGUAGE_CONTENT.keys())

GENDER_KEYS = ("female", "male", "prefer_not")
GENDER_LABELS = {
    "English": {
        "female": "Female",
        "male": "Male",
        "prefer_not": "Prefer not to say",
    },
    "Español": {
        "female": "Femenino",
        "male": "Masculino",
        "prefer_not": "Prefiero no decir",
    },
}

st.session_state.setdefault("language", DEFAULT_LANGUAGE)

language_index = LANGUAGE_OPTIONS.index(st.session_state["language"])
selected_language = st.selectbox(
    "Choose language / Escoge idioma",
    options=LANGUAGE_OPTIONS,
    index=language_index,
)
st.session_state["language"] = selected_language


def t(key: str, **kwargs) -> str:
    text = LANGUAGE_CONTENT[st.session_state["language"]][key]
    return text.format(**kwargs)


st.title(t("page_header"))
st.caption(t("page_caption"))
st.markdown(t("intro_text"))

DATA_FILES = {
    "Instant Noodles": "data/Productos_Instant_Noodles_SmartScore.xlsx",
    "Mac & Cheese": "data/Productos_Mac_and_Cheese_SmartScore.xlsx",
    "Ready to Eat": "data/Productos_ReadyToEat_SmartScore.xlsx",
}

RESULTS_PATH_IN_REPO = "Resultados_SmartScore.xlsx"  # se crea/actualiza vía API de GitHub

INITIAL_FORM_VALUES = {
    "nombre_completo": "",
    "edad": 1,
    "genero": GENDER_KEYS[0],
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
    "genero": GENDER_KEYS[0],
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
st.session_state.setdefault("visual_log", [])
st.session_state.setdefault("tab2_authenticated", False)
st.session_state.setdefault("tab2_user_name", "")

VISUAL_MODE_OPTIONS = ["A/B", "Grid", "Sequential"]
VISUAL_SUBFOLDERS = {"A/B": "A_B", "Grid": "Grid", "Sequential": "Sequential"}
VALID_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
VISUAL_BASE_PATH = Path("data/images")
VISUAL_RESULTS_DIR = Path("data/experimentos")

TAB2_IMAGE_STYLES = """
<style>
.tab2-image-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
}

.tab2-image-container img {
    width: 100%;
    object-fit: contain;
    border-radius: 8px;
    background-color: #ffffff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.tab2-image-caption {
    font-size: 0.85rem;
    text-align: center;
    margin: 0;
    color: inherit;
}

.tab2-image-container.ab img,
.tab2-image-container.grid img {
    height: min(28vh, 320px);
}

.tab2-image-container.seq img {
    height: min(70vh, 700px);
}

@media (max-width: 1200px) {
    .tab2-image-container.ab img,
    .tab2-image-container.grid img {
        height: min(26vh, 260px);
    }

    .tab2-image-container.seq img {
        height: min(60vh, 600px);
    }
}
</style>
"""

st.session_state.setdefault("mode_sequence", VISUAL_MODE_OPTIONS.copy())
st.session_state.setdefault("current_mode_index", 0)
st.session_state.setdefault("mode_sessions", {})
st.session_state.setdefault("experiment_completed", False)
st.session_state.setdefault("experiment_result_path", "")
st.session_state.setdefault("experiment_result_df", pd.DataFrame())
st.session_state.setdefault("last_selection_feedback", "")

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


def _trigger_streamlit_rerun() -> None:
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
        return

    experimental_rerun = getattr(st, "experimental_rerun", None)
    if callable(experimental_rerun):
        experimental_rerun()
        return

    raise AttributeError("Streamlit no dispone de 'st.rerun' ni 'st.experimental_rerun'.")


def _load_image_paths(folder: Path) -> list:
    if not folder.exists():
        return []
    return [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in VALID_IMAGE_EXTENSIONS
    ]


def _load_mode_images(mode: str) -> list[Path]:
    folder_name = VISUAL_SUBFOLDERS.get(mode)
    if folder_name is None:
        return []
    folder = VISUAL_BASE_PATH / folder_name
    image_paths = _load_image_paths(folder)
    random.shuffle(image_paths)
    if mode == "A/B":
        return image_paths[:2]
    if mode == "Grid":
        return image_paths[:4]
    if mode == "Sequential":
        return image_paths[:4] if len(image_paths) > 4 else image_paths
    return image_paths


def _sanitize_filename_component(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_-]", "_", value.strip())
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("_") or "usuario"


def _reset_visual_experiment_state() -> None:
    st.session_state["mode_sequence"] = VISUAL_MODE_OPTIONS.copy()
    st.session_state["current_mode_index"] = 0
    st.session_state["mode_sessions"] = {}
    st.session_state["visual_log"] = []
    st.session_state["experiment_completed"] = False
    st.session_state["experiment_result_path"] = ""
    st.session_state["experiment_result_df"] = pd.DataFrame()
    st.session_state["last_selection_feedback"] = ""


def _ensure_mode_initialized(mode: str) -> None:
    sessions: dict = st.session_state.setdefault("mode_sessions", {})
    if mode in sessions:
        if sessions[mode].get("images"):
            return
    images = _load_mode_images(mode)
    sessions[mode] = {
        "images": images,
        "options": [img.stem for img in images],
        "selected": None,
        "start_time": None,
        "selection_timestamp": None,
        "selection_duration": None,
        "completion_timestamp": None,
        "navigation_index": 0,
    }
    st.session_state["mode_sessions"] = sessions


def _ensure_mode_started(mode: str) -> None:
    sessions: dict = st.session_state.get("mode_sessions", {})
    mode_state = sessions.get(mode)
    if not mode_state:
        return
    if mode_state.get("start_time") is None:
        mode_state["start_time"] = datetime.now()
        sessions[mode] = mode_state
        st.session_state["mode_sessions"] = sessions


def _handle_mode_selection(mode: str, choice_label: str, participant: str) -> None:
    sessions: dict = st.session_state.get("mode_sessions", {})
    mode_state = sessions.get(mode)
    if not mode_state:
        return
    now = datetime.now()
    if mode_state.get("start_time") is None:
        mode_state["start_time"] = now
    mode_state["selected"] = choice_label
    mode_state["selection_timestamp"] = now
    start_time = mode_state.get("start_time")
    if start_time:
        mode_state["selection_duration"] = (now - start_time).total_seconds()
    sessions[mode] = mode_state
    st.session_state["mode_sessions"] = sessions

    log_entry = {
        "timestamp": now.isoformat(),
        "participant_name": participant,
        "mode": mode,
        "choice": choice_label,
        "options": mode_state.get("options", []),
        "selection_duration_seconds": mode_state.get("selection_duration"),
    }

    filtered_log = [entry for entry in st.session_state.get("visual_log", []) if entry.get("mode") != mode]
    filtered_log.append(log_entry)
    st.session_state["visual_log"] = filtered_log


def _advance_visual_mode() -> None:
    sequence: list = st.session_state.get("mode_sequence", [])
    index: int = st.session_state.get("current_mode_index", 0)
    if not sequence:
        return
    current_mode = sequence[index]
    sessions: dict = st.session_state.get("mode_sessions", {})
    mode_state = sessions.get(current_mode, {})
    mode_state.setdefault("completion_timestamp", datetime.now())
    sessions[current_mode] = mode_state
    st.session_state["mode_sessions"] = sessions
    if index < len(sequence) - 1:
        st.session_state["current_mode_index"] = index + 1
    _trigger_streamlit_rerun()


def _build_experiment_dataframe(user_name: str) -> pd.DataFrame:
    sequence: list = st.session_state.get("mode_sequence", [])
    sessions: dict = st.session_state.get("mode_sessions", {})
    records: list[dict] = []
    for mode in sequence:
        state = sessions.get(mode, {})
        start_time = state.get("start_time")
        selection_time = state.get("selection_timestamp")
        completion_time = state.get("completion_timestamp") or selection_time
        selection_duration = state.get("selection_duration")
        mode_duration = None
        if start_time and completion_time:
            mode_duration = (completion_time - start_time).total_seconds()
        records.append(
            {
                "Usuario": user_name,
                "Modo": mode,
                "Opciones Presentadas": ", ".join(state.get("options", [])),
                "Producto Seleccionado": state.get("selected") or "",
                "Tiempo hasta selección (s)": selection_duration,
                "Duración del modo (s)": mode_duration,
                "Inicio del modo": start_time.isoformat() if start_time else "",
                "Momento de selección": selection_time.isoformat() if selection_time else "",
                "Momento de finalización": completion_time.isoformat() if completion_time else "",
            }
        )
    return pd.DataFrame(records)


def _complete_visual_experiment(user_name: str) -> None:
    sessions: dict = st.session_state.get("mode_sessions", {})
    current_mode = st.session_state.get("mode_sequence", [None])[st.session_state.get("current_mode_index", 0)]
    if current_mode in sessions:
        mode_state = sessions[current_mode]
        if mode_state.get("completion_timestamp") is None:
            mode_state["completion_timestamp"] = datetime.now()
            sessions[current_mode] = mode_state
            st.session_state["mode_sessions"] = sessions

    df = _build_experiment_dataframe(user_name)
    VISUAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = _sanitize_filename_component(user_name)
    file_path = VISUAL_RESULTS_DIR / f"experimento_{safe_name}_{timestamp}.xlsx"
    df.to_excel(file_path, index=False)

    st.session_state["experiment_result_df"] = df
    st.session_state["experiment_result_path"] = str(file_path)
    st.session_state["experiment_completed"] = True
    st.session_state["last_selection_feedback"] = ""



def _render_visual_image(image_path: Path, mode: str) -> None:
    mode_class = {"A/B": "ab", "Grid": "grid", "Sequential": "seq"}.get(mode, "grid")
    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    extension = image_path.suffix.lower().lstrip(".") or "png"
    if extension == "jpg":
        extension = "jpeg"
    caption = html.escape(image_path.stem.replace("_", " "))
    st.markdown(
        f"""
        <div class="tab2-image-container {mode_class}">
            <img src="data:image/{extension};base64,{encoded}" alt="{caption}" />
            <p class="tab2-image-caption">{caption}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    _trigger_streamlit_rerun()


def _load_registered_names(path: Path) -> tuple[list[str], Optional[str]]:
    if not path.exists():
        return [], f"El archivo '{path}' no existe aún."

    try:
        df = pd.read_excel(path)
    except Exception as error:
        return [], f"No se pudo leer el archivo '{path}': {error}"

    if "Nombre Completo" not in df.columns:
        return [], "El archivo no contiene la columna 'Nombre Completo'."

    nombres_crudos = df["Nombre Completo"].dropna().astype(str).str.strip()
    nombres_unicos = []
    nombres_vistos = set()

    for nombre in nombres_crudos:
        if not nombre:
            continue
        clave = nombre.casefold()
        if clave in nombres_vistos:
            continue
        nombres_vistos.add(clave)
        nombres_unicos.append(nombre)

    return nombres_unicos, None


# =========================================================
# INTERFACES
# =========================================================
tab1, tab2 = st.tabs(
    ["📝 SmartScore Questionnaire", "👁️ Experimento Visual (Sin Smart Score)"]
)

with tab1:
    _apply_reset_form_state()

    st.header(t("questionnaire_header"))

    with st.form("cuestionario_form"):
        st.subheader(t("respondent_data_subheader"))
        nombre_completo = st.text_input(t("name_label"), key="nombre_completo")
        col_info_1, col_info_2 = st.columns(2)
        with col_info_1:
            edad = st.number_input(
                t("age_label"), min_value=1, max_value=120, step=1, key="edad"
            )
        with col_info_2:
            genero = st.selectbox(
                t("gender_label"),
                GENDER_KEYS,
                format_func=lambda key: GENDER_LABELS[st.session_state["language"]][key],
                key="genero",
            )

        st.subheader(t("aspects_subheader"))
        st.caption(t("aspects_caption"))
        col1, col2 = st.columns(2)
        with col1:
            w_portion = st.slider(
                t("slider_portion"),
                0,
                5,
                value=st.session_state["w_portion"],
                key="w_portion",
            )
            w_diet = st.slider(
                t("slider_diet"),
                0,
                7,
                value=st.session_state["w_diet"],
                key="w_diet",
            )
            w_salt = st.slider(
                t("slider_salt"),
                0,
                5,
                value=st.session_state["w_salt"],
                key="w_salt",
            )
            w_fat = st.slider(
                t("slider_fat"),
                0,
                5,
                value=st.session_state["w_fat"],
                key="w_fat",
            )
        with col2:
            w_natural = st.slider(
                t("slider_natural"),
                0,
                5,
                value=st.session_state["w_natural"],
                key="w_natural",
            )
            w_convenience = st.slider(
                t("slider_convenience"),
                0,
                5,
                value=st.session_state["w_convenience"],
                key="w_convenience",
            )
            w_price = st.slider(
                t("slider_price"),
                0,
                5,
                value=st.session_state["w_price"],
                key="w_price",
            )

        submitted = st.form_submit_button(t("submit_button"))

        if st.session_state.get("success_path"):
            st.success(
                t("success_saved", path=st.session_state["success_path"])
            )
            if st.session_state.get("trigger_balloons", False):
                st.balloons()
            st.session_state["success_path"] = ""
            st.session_state["trigger_balloons"] = False

    if submitted:
        errores = []
        if not nombre_completo.strip():
            errores.append(t("error_name_required"))
        if edad <= 0:
            errores.append(t("error_age_positive"))

        if errores:
            for err in errores:
                st.error(err)
        else:
            try:
                df_all = _read_all_products(DATA_FILES)
            except Exception as e:
                st.error(t("error_read_excel", error=e))
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
                st.error(t("error_missing_column", column=e))
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
            persona_genero = GENDER_LABELS[st.session_state["language"]][genero]

            if "GITHUB_TOKEN" not in st.secrets:
                st.warning(t("warning_github_token"))
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
                    st.error(t("error_repo_access", error=mensaje_repo))
                except Exception as generic_error:
                    st.error(t("error_github_connection", error=generic_error))
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
                        st.error(t("error_sync_repo", path=ruta_archivo, error=mensaje_archivo))
                    except Exception as update_error:
                        st.error(t("error_update_file", path=ruta_archivo, error=update_error))
                    else:
                        show_success_message(ruta_archivo)

    st.markdown("---")

with tab2:
    st.header("👁️ Visual Experiment – Product Viewing Task (No Smart Score)")
    st.caption(
        "Explora diferentes presentaciones visuales y selecciona el producto que prefieras en cada modalidad."
    )

    registered_names, names_error = _load_registered_names(Path(RESULTS_PATH_IN_REPO))

    if names_error:
        st.warning(names_error)

    if (
        st.session_state.get("tab2_authenticated", False)
        and st.session_state.get("tab2_user_name") not in registered_names
    ):
        st.warning(
            "El nombre con el que accediste ya no está disponible. Selecciona otro nombre para continuar."
        )
        st.session_state["tab2_authenticated"] = False
        st.session_state["tab2_user_name"] = ""

    if not registered_names:
        st.info(
            "Para acceder a esta sección primero guarda al menos una respuesta desde la pestaña de SmartScore."
        )
        st.stop()

    if not st.session_state.get("tab2_authenticated", False):
        with st.form("tab2_login_form"):
            selected_name = st.selectbox(
                "Selecciona tu nombre completo registrado",
                registered_names,
            )
            login_submitted = st.form_submit_button("Ingresar")

        if login_submitted:
            st.session_state["tab2_authenticated"] = True
            st.session_state["tab2_user_name"] = selected_name
            _reset_visual_experiment_state()

    if not st.session_state.get("tab2_authenticated", False):
        st.info("Selecciona un nombre para ver el experimento visual.")
        st.stop()

    usuario_activo = st.session_state.get("tab2_user_name", "")
    st.success(f"Accediendo como: {usuario_activo}")

    if st.button("Cambiar de usuario", key="tab2_logout"):
        st.session_state["tab2_authenticated"] = False
        st.session_state["tab2_user_name"] = ""
        _reset_visual_experiment_state()
        _trigger_streamlit_rerun()

    sequence = st.session_state.get("mode_sequence", [])
    if not sequence:
        st.warning(
            "No hay modalidades configuradas para el experimento visual. Contacta al administrador."
        )
        st.stop()

    for mode_option in sequence:
        _ensure_mode_initialized(mode_option)

    if st.session_state.get("experiment_completed"):
        result_path = st.session_state.get("experiment_result_path", "")
        result_df = st.session_state.get("experiment_result_df")
        if result_path:
            st.success(f"✅ Experimento finalizado. Resultados guardados en: {result_path}")
        else:
            st.success("✅ Experimento finalizado.")

        if isinstance(result_df, pd.DataFrame) and not result_df.empty:
            st.dataframe(result_df)
            download_name = (
                Path(result_path).name
                if result_path
                else "resultados_experimento_visual.xlsx"
            )
            st.download_button(
                "Descargar resultados en Excel",
                data=_df_to_excel_bytes(result_df),
                file_name=download_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No se encontraron datos para descargar.")

        if st.button("Reiniciar experimento", key="restart_experiment"):
            _reset_visual_experiment_state()
            _trigger_streamlit_rerun()

        st.stop()

    total_modes = len(sequence)
    current_index = st.session_state.get("current_mode_index", 0)
    current_index = max(0, min(current_index, total_modes - 1))
    st.session_state["current_mode_index"] = current_index
    current_mode = sequence[current_index]

    _ensure_mode_started(current_mode)
    mode_sessions = st.session_state.get("mode_sessions", {})
    current_state = mode_sessions.get(current_mode, {})

    st.markdown("#### Progreso del experimento")
    progress_records = []
    for idx, mode_name in enumerate(sequence, start=1):
        state = mode_sessions.get(mode_name, {})
        status = state.get("selected") or "Pendiente"
        progress_records.append(
            {"Paso": f"{idx}/{total_modes}", "Modo": mode_name, "Estado": status}
        )
    progress_df = pd.DataFrame(progress_records)
    st.table(progress_df)

    feedback = st.session_state.get("last_selection_feedback", "")
    if feedback:
        st.success(f"Has seleccionado: {feedback}")
        st.session_state["last_selection_feedback"] = ""

    st.info(f"Modo de visualización {current_index + 1} de {total_modes}: {current_mode}")

    st.markdown(TAB2_IMAGE_STYLES, unsafe_allow_html=True)

    images = current_state.get("images", [])

    if not images:
        st.warning(
            "No se encontraron imágenes para esta modalidad. Verifica la carpeta 'data/images/'."
        )
    else:
        if current_mode == "A/B":
            if len(images) < 2:
                st.warning("Se necesitan al menos 2 imágenes para el modo A/B.")
            else:
                columns = st.columns(len(images))
                for idx, (col, image_path) in enumerate(zip(columns, images)):
                    with col:
                        _render_visual_image(image_path, current_mode)
                        if current_state.get("selected") == image_path.stem:
                            st.caption("✅ Seleccionado")
                        if st.button(
                            "Elegir este producto",
                            key=f"choose_{current_mode}_{idx}",
                        ):
                            _handle_mode_selection(
                                current_mode, image_path.stem, usuario_activo
                            )
                            st.session_state["last_selection_feedback"] = image_path.stem
                            _trigger_streamlit_rerun()
        elif current_mode == "Grid":
            if len(images) < 2:
                st.warning("Se necesitan al menos 2 imágenes para el modo Grid.")
            else:
                for start in range(0, len(images), 2):
                    columns = st.columns(2)
                    for offset, (col, image_path) in enumerate(
                        zip(columns, images[start : start + 2])
                    ):
                        with col:
                            _render_visual_image(image_path, current_mode)
                            if current_state.get("selected") == image_path.stem:
                                st.caption("✅ Seleccionado")
                            if st.button(
                                "Elegir este producto",
                                key=f"choose_{current_mode}_{start + offset}",
                            ):
                                _handle_mode_selection(
                                    current_mode, image_path.stem, usuario_activo
                                )
                                st.session_state["last_selection_feedback"] = image_path.stem
                                _trigger_streamlit_rerun()
        else:
            total_images = len(images)
            index = current_state.get("navigation_index", 0)
            index = max(0, min(index, total_images - 1))
            if index != current_state.get("navigation_index"):
                current_state["navigation_index"] = index
                mode_sessions[current_mode] = current_state
                st.session_state["mode_sessions"] = mode_sessions

            nav_cols = st.columns([1, 2, 1])
            with nav_cols[0]:
                if st.button(
                    "◀️ Producto anterior",
                    key=f"prev_{current_mode}",
                    disabled=index <= 0,
                ):
                    current_state["navigation_index"] = max(0, index - 1)
                    mode_sessions[current_mode] = current_state
                    st.session_state["mode_sessions"] = mode_sessions
                    _trigger_streamlit_rerun()

            nav_cols[1].markdown(
                f"<div style='text-align:center;font-weight:bold;'>Producto {index + 1} de {total_images}</div>",
                unsafe_allow_html=True,
            )

            with nav_cols[2]:
                if st.button(
                    "Siguiente producto ▶️",
                    key=f"next_{current_mode}",
                    disabled=index >= total_images - 1,
                ):
                    current_state["navigation_index"] = min(total_images - 1, index + 1)
                    mode_sessions[current_mode] = current_state
                    st.session_state["mode_sessions"] = mode_sessions
                    _trigger_streamlit_rerun()

            current_image = images[index]
            _render_visual_image(current_image, current_mode)
            if current_state.get("selected") == current_image.stem:
                st.caption("✅ Seleccionado")
            if st.button(
                "Elegir este producto",
                key=f"choose_{current_mode}_{index}",
            ):
                _handle_mode_selection(current_mode, current_image.stem, usuario_activo)
                mode_sessions = st.session_state.get("mode_sessions", {})
                current_state = mode_sessions.get(current_mode, current_state)
                current_state["navigation_index"] = index
                mode_sessions[current_mode] = current_state
                st.session_state["mode_sessions"] = mode_sessions
                st.session_state["last_selection_feedback"] = current_image.stem
                _trigger_streamlit_rerun()

    selection_made = bool(current_state.get("selected"))
    is_last_mode = current_index == total_modes - 1

    if not selection_made:
        st.info("Selecciona un producto para habilitar el siguiente paso.")

    if not is_last_mode:
        if st.button(
            "Siguiente modo ▶️",
            key=f"next_mode_{current_mode}",
            disabled=not selection_made,
        ):
            _advance_visual_mode()
    else:
        if st.button(
            "Finalizar experimento",
            key="finish_experiment",
            disabled=not selection_made,
        ):
            _complete_visual_experiment(usuario_activo)
            _trigger_streamlit_rerun()
