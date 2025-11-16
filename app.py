# app.py
import re
import json
import random
import base64
import html
import threading
import time
import unicodedata
from difflib import SequenceMatcher
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

try:
    WORLD_TIMESTAMPS = np.load("world_timestamps.npy")
except Exception:
    WORLD_TIMESTAMPS = None
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
        "tab1_title": "📝 SmartScore Questionnaire",
        "tab2_title": "👁️ Visual Experiment",
        "tab2_header": "👁️ Visual Experiment – Product Viewing Task",
        "tab2_caption": "Explore different visual layouts and pick the product you prefer in each mode.",
        "tab2_name_reused_warning": "The name you used to sign in is no longer available. Select another name to continue.",
        "tab2_requires_response_info": "To access this section, first save at least one response from the SmartScore tab.",
        "tab2_select_name_prompt": "Type your registered full name",
        "tab2_choose_name_info": "Type your registered name and click Start experiment. We'll suggest close matches if more than one person fits.",
        "tab2_name_matches_prompt": "We found several similar names. Select the correct one.",
        "tab2_name_match_found": "Matched with the registered name: {match}",
        "tab2_name_no_matches": "No close matches yet. Try adding more of your registered name.",
        "tab2_name_required_error": "Enter a registered name to continue.",
        "tab2_logged_in_as": "Signed in as: {user}",
        "tab2_switch_user": "Switch user",
        "tab2_start_experiment": "Start experiment",
        "tab2_no_modes_warning": "No viewing modes are configured for the visual experiment. Contact the administrator.",
        "tab2_completed_with_path": "✅ Experiment completed. Results saved at: {path}",
        "tab2_completed": "✅ Experiment completed.",
        "tab2_download_results": "Download results as Excel",
        "tab2_no_data_info": "No data found to download.",
        "tab2_restart_experiment": "Restart experiment",
        "tab2_mode_info": "Viewing mode {current} of {total}: {mode}",
        "tab2_no_images_warning": "No images were found for this mode. Check the 'data/images/' folder.",
        "tab2_need_four_images_ab": "At least 4 images are required for A/B mode.",
        "tab2_need_two_images_grid": "At least 2 images are required for Grid mode.",
        "tab2_selected_label": "✅ Selected",
        "tab2_choose_product": "Choose this product",
        "tab2_product_position": "Product {current} of {total}",
        "tab2_prev_product": "◀️ Previous product",
        "tab2_next_product": "Next product ▶️",
        "tab2_select_to_continue": "Select a product to enable the next step.",
        "tab2_next_mode": "Next mode ▶️",
        "tab2_finish_experiment": "Finish experiment",
        "tab2_grid_instruction": "📋 Grid tips: Compare every product at once and click ‘Choose this product’ under your favorite.",
        "tab2_seq_instruction": "📋 Sequential tips: Use Previous/Next to revisit any product and press ‘Choose this product’ when ready.",
        "tab2_ab_step_one": "Step 1 of 3: Choose your favorite from the first pair.",
        "tab2_ab_step_two": "Step 2 of 3: Choose your favorite from the second pair.",
        "tab2_ab_step_three": "Final step: Choose your favorite between the two finalists.",
        "tab2_ab_finalists": "Finalists: {first} vs {second}.",
        "smartscore_recommended": "Rec. prod. • Compat. {score:.0f}\u202f%",
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
        "tab1_title": "📝 Cuestionario SmartScore",
        "tab2_title": "👁️ Experimento Visual",
        "tab2_header": "👁️ Experimento Visual – Tarea de Observación de Productos",
        "tab2_caption": "Explora diferentes presentaciones visuales y selecciona el producto que prefieras en cada modalidad.",
        "tab2_name_reused_warning": "El nombre con el que accediste ya no está disponible. Selecciona otro nombre para continuar.",
        "tab2_requires_response_info": "Para acceder a esta sección primero guarda al menos una respuesta desde la pestaña de SmartScore.",
        "tab2_select_name_prompt": "Escribe tu nombre completo registrado",
        "tab2_choose_name_info": "Escribe tu nombre registrado y haz clic en Empezar experimento. Si encontramos varias coincidencias podrás elegir la correcta.",
        "tab2_name_matches_prompt": "Encontramos varias coincidencias. Selecciona tu nombre correcto.",
        "tab2_name_match_found": "Coincidencia encontrada: {match}",
        "tab2_name_no_matches": "Aún no vemos coincidencias. Escribe un poco más de tu nombre registrado.",
        "tab2_name_required_error": "Ingresa un nombre registrado antes de empezar.",
        "tab2_logged_in_as": "Accediendo como: {user}",
        "tab2_switch_user": "Cambiar de usuario",
        "tab2_start_experiment": "Empezar experimento",
        "tab2_no_modes_warning": "No hay modalidades configuradas para el experimento visual. Contacta al administrador.",
        "tab2_completed_with_path": "✅ Experimento finalizado. Resultados guardados en: {path}",
        "tab2_completed": "✅ Experimento finalizado.",
        "tab2_download_results": "Descargar resultados en Excel",
        "tab2_no_data_info": "No se encontraron datos para descargar.",
        "tab2_restart_experiment": "Reiniciar experimento",
        "tab2_mode_info": "Modo de visualización {current} de {total}: {mode}",
        "tab2_no_images_warning": "No se encontraron imágenes para esta modalidad. Verifica la carpeta 'data/images/'.",
        "tab2_need_four_images_ab": "Se necesitan al menos 4 imágenes para el modo A/B.",
        "tab2_need_two_images_grid": "Se necesitan al menos 2 imágenes para el modo Grid.",
        "tab2_selected_label": "✅ Seleccionado",
        "tab2_choose_product": "Elegir este producto",
        "tab2_product_position": "Producto {current} de {total}",
        "tab2_prev_product": "◀️ Producto anterior",
        "tab2_next_product": "Siguiente producto ▶️",
        "tab2_select_to_continue": "Selecciona un producto para habilitar el siguiente paso.",
        "tab2_next_mode": "Siguiente modo ▶️",
        "tab2_finish_experiment": "Finalizar experimento",
        "tab2_grid_instruction": "📋 Consejos Grid: Compara todos los productos a la vez y haz clic en ‘Elegir este producto’ debajo de tu favorito.",
        "tab2_seq_instruction": "📋 Consejos secuencial: Usa Anterior/Siguiente para volver a cualquier producto e indica tu elección con ‘Elegir este producto’.",
        "tab2_ab_step_one": "Paso 1 de 3: Elige tu favorito del primer par.",
        "tab2_ab_step_two": "Paso 2 de 3: Elige tu favorito del segundo par.",
        "tab2_ab_step_three": "Paso final: Elige tu favorito entre los dos finalistas.",
        "tab2_ab_finalists": "Finalistas: {first} vs {second}.",
        "smartscore_recommended": "Prod. recom. • Compat. {score:.0f}\u202f%",
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
    "grupo_experimental": "Con SmartScore",
    "w_portion": 0,
    "w_diet": 0,
    "w_salt": 0,
    "w_fat": 0,
    "w_natural": 0,
    "w_convenience": 0,
    "w_price": 0,
}

RESET_FORM_VALUES = {
    "nombre_completo": "",
    "edad": 1,
    "genero": GENDER_KEYS[0],
    "grupo_experimental": "Con SmartScore",
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
st.session_state.setdefault("tab1_persona_id", "")
st.session_state.setdefault("tab1_persona_group", "")
st.session_state.setdefault("tab2_user_id", "")
st.session_state.setdefault("tab2_user_group", "")
st.session_state.setdefault("tab2_smartscore_map", {})
st.session_state.setdefault("tab2_smartscore_owner", "")
st.session_state.setdefault("tab2_name_query", "")
VISUAL_MODE_OPTIONS = ["A/B", "Grid", "Sequential"]
VISUAL_SUBFOLDERS = {"A/B": "A_B", "Grid": "Grid", "Sequential": "Sequential"}
VALID_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
VISUAL_BASE_PATH = Path("data/images")
VISUAL_RESULTS_DIR = Path("data/experimentos")

IMAGE_STEM_TO_PRODUCT = {
    "annies": "Annie’s Shells & White Cheddar",
    "mac&cheese": "Kraft Macaroni & Cheese Dinner",
    "velveeta": "Velveeta Original Shells & Cheese (microwave cups)",
    "hormel": "Amy’s Macaroni & Cheese (frozen)",
    "maruchan": "Maruchan Ramen Sabor Pollo",
    "migoreng": "Nissin Chow Mein Teriyaki Beef",
    "neu": "Nongshim Neoguri Spicy Seafood",
    "shin-ramyun": "Nongshim Shin Ramyun",
    "tuna": "Wild Planet Wild Tuna Pasta Salad",
    "chicken": "StarKist Chicken Creations (Chicken Salad)",
    "indian": "Kitchens of India Variety Pack",
    "jacklinks": "Jack Link’s Beef Jerky Original",
}

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


.tab2-image-container.ab img {
    height: min(40vh, 420px);
}

.tab2-image-container.grid img {
    height: min(28vh, 320px);
}

.tab2-image-container.seq img {
    height: min(70vh, 700px);
}

.tab2-image-container.seq + div[data-testid="stHorizontalBlock"] {
    justify-content: center;
    margin-top: 0.5rem;
    gap: 0.75rem;
}

.tab2-image-container.seq + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    flex: 0 0 190px;
}

.tab2-image-container.seq + div[data-testid="stHorizontalBlock"] button {
    width: 100%;
}

.seq-selection-label {
    text-align: center;
    margin: 0.35rem 0 0;
    font-size: 0.9rem;
}

.seq-product-position {
    text-align: center;
    font-weight: 600;
    margin: 0.2rem 0 0.4rem;
}

.smartscore-label {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    margin-top: 6px;
}

.smartscore-label .smartscore-text {
    background: linear-gradient(135deg, rgba(255, 215, 0, 0.95), rgba(255, 165, 0, 0.95));
    color: #1f1400;
    font-size: 0.9rem;
    font-weight: 700;
    border-radius: 6px;
    padding: 4px 8px;
    border: 1px solid rgba(255, 255, 255, 0.35);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
    display: inline-block;
}

.smartscore-label .smartscore-star {
    font-size: 1rem;
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.25));
}

@media (max-width: 1200px) {
    .tab2-image-container.ab img {
        height: min(34vh, 360px);
    }

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


def _normalize_product_key(value: str) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(
        ch for ch in normalized if unicodedata.category(ch) != "Mn"
    )
    normalized = normalized.casefold()
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _load_user_smartscore_map(user_name: str) -> dict[str, float]:
    cleaned = user_name.strip()
    if not cleaned:
        return {}

    results_path = Path(RESULTS_PATH_IN_REPO)
    if not results_path.exists():
        return {}

    try:
        df = pd.read_excel(results_path)
    except Exception:
        return {}

    if "Nombre Completo" not in df.columns:
        return {}

    nombres = df["Nombre Completo"].astype(str).str.strip()
    mask = nombres.str.casefold() == cleaned.casefold()
    if not mask.any():
        return {}

    fila = df[mask].iloc[-1]
    resultados: dict[str, float] = {}

    for columna in df.columns:
        if not columna.endswith("· Producto"):
            continue

        producto_valor = fila.get(columna)
        if not isinstance(producto_valor, str):
            continue
        producto = producto_valor.strip()
        if not producto:
            continue

        columna_smartscore = columna.replace("· Producto", "· SmartScore")
        smartscore_valor = fila.get(columna_smartscore)
        if pd.isna(smartscore_valor):
            continue

        try:
            smartscore = float(smartscore_valor)
        except (TypeError, ValueError):
            try:
                smartscore = float(str(smartscore_valor).replace(",", "."))
            except (TypeError, ValueError):
                continue

        resultados[producto] = smartscore

    return resultados


def _lookup_participant_metadata(user_name: str) -> tuple[str, str]:
    cleaned = user_name.strip()
    if not cleaned:
        return "", ""

    results_path = Path(RESULTS_PATH_IN_REPO)
    if not results_path.exists():
        return "", ""

    try:
        df = pd.read_excel(results_path)
    except Exception:
        return "", ""

    if "Nombre Completo" not in df.columns:
        return "", ""

    nombres = df["Nombre Completo"].astype(str).str.strip()
    mask = nombres.str.casefold() == cleaned.casefold()
    if not mask.any():
        return "", ""

    fila = df[mask].iloc[-1]

    participant_id = fila.get("ID_Participante", "")
    participant_group = fila.get("Grupo_Experimental", "")

    if pd.isna(participant_id):
        participant_id = ""
    else:
        participant_id = str(participant_id)

    if pd.isna(participant_group):
        participant_group = ""
    else:
        participant_group = str(participant_group)

    return participant_id, participant_group


def _normalize_name_for_match(value: str) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized.casefold())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _find_registered_name_matches(
    query: str, registered_names: list[str], limit: int = 10
) -> list[str]:
    normalized_query = _normalize_name_for_match(query)
    if not normalized_query:
        return []

    compact_query = normalized_query.replace(" ", "")
    min_threshold = 0.55 if len(compact_query) >= 3 else 0.7

    scored_matches: list[tuple[float, str]] = []
    for name in registered_names:
        normalized_candidate = _normalize_name_for_match(name)
        if not normalized_candidate:
            continue

        if normalized_query == normalized_candidate:
            score = 1.0
        elif normalized_query in normalized_candidate:
            score = 0.95
        elif normalized_candidate in normalized_query:
            score = 0.9
        else:
            score = SequenceMatcher(None, normalized_query, normalized_candidate).ratio()
            tokens = [token for token in normalized_query.split(" ") if token]
            if tokens:
                hits = sum(1 for token in tokens if token in normalized_candidate)
                score += 0.05 * hits

        scored_matches.append((min(score, 1.0), name))

    scored_matches.sort(key=lambda item: item[0], reverse=True)
    filtered = [name for score, name in scored_matches if score >= min_threshold]
    return filtered[:limit]


def get_user_group(user_name: str) -> str:
    cleaned = (user_name or "").strip()
    if not cleaned:
        return ""

    if "GITHUB_TOKEN" not in st.secrets:
        return ""

    try:
        github_client = Github(st.secrets["GITHUB_TOKEN"])
        github_user = github_client.get_user()
        repo = github_user.get_repo("app_Estancia")
        contents = repo.get_contents(RESULTS_PATH_IN_REPO)
        excel_bytes = base64.b64decode(contents.content)
        df = pd.read_excel(BytesIO(excel_bytes))
    except GithubException:
        return ""
    except Exception:
        return ""

    required_columns = {"Nombre Completo", "Grupo_Experimental"}
    if not required_columns.issubset(df.columns):
        return ""

    nombres = df["Nombre Completo"].astype(str).str.strip().str.casefold()
    mask = nombres == cleaned.casefold()
    if not mask.any():
        return ""

    grupo_valor = df.loc[mask, "Grupo_Experimental"].iloc[-1]
    if pd.isna(grupo_valor):
        return ""

    grupo_str = str(grupo_valor).strip()
    return grupo_str


def _set_tab2_smartscore_map(user_name: str) -> None:
    cleaned = user_name.strip()
    if not cleaned:
        st.session_state["tab2_smartscore_map"] = {}
        st.session_state["tab2_smartscore_owner"] = ""
        sessions = st.session_state.get("mode_sessions", {})
        for mode_state in sessions.values():
            if isinstance(mode_state, dict) and "ab_highlighted_product" in mode_state:
                mode_state["ab_highlighted_product"] = None
        st.session_state["mode_sessions"] = sessions
        return

    st.session_state["tab2_smartscore_map"] = _load_user_smartscore_map(cleaned)
    st.session_state["tab2_smartscore_owner"] = cleaned
    sessions = st.session_state.get("mode_sessions", {})
    for mode_state in sessions.values():
        if isinstance(mode_state, dict) and "ab_highlighted_product" in mode_state:
            mode_state["ab_highlighted_product"] = None
    st.session_state["mode_sessions"] = sessions


def _ensure_tab2_smartscore_map(user_name: str) -> None:
    owner = st.session_state.get("tab2_smartscore_owner", "")
    cleaned = user_name.strip()

    if not cleaned:
        if owner:
            _set_tab2_smartscore_map("")
        return

    if owner.casefold() != cleaned.casefold():
        _set_tab2_smartscore_map(cleaned)


def _find_smartscore_for_image(
    stem: str, smartscore_map: dict[str, float]
) -> Optional[tuple[str, float]]:
    if not stem or not smartscore_map:
        return None

    normalizados: dict[str, tuple[str, float]] = {}
    for producto, puntaje in smartscore_map.items():
        clave = _normalize_product_key(producto)
        if not clave:
            continue
        normalizados[clave] = (producto, puntaje)

    alias_producto = IMAGE_STEM_TO_PRODUCT.get(stem.casefold())
    if alias_producto:
        clave_alias = _normalize_product_key(alias_producto)
        if clave_alias in normalizados:
            return normalizados[clave_alias]

    clave_imagen = _normalize_product_key(stem)
    if clave_imagen in normalizados:
        return normalizados[clave_imagen]

    for clave, datos in normalizados.items():
        if clave_imagen and (clave_imagen in clave or clave in clave_imagen):
            return datos

    return None


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
    columnas_inicio = [
        "ID_Participante",
        "Grupo_Experimental",
        "Nombre Completo",
        "Edad",
        "Género",
    ]
    presentes = [col for col in columnas_inicio if col in df.columns]
    restantes = [col for col in df.columns if col not in presentes and col != "Usuario"]
    df_reordenado = df[presentes + restantes]
    if "Usuario" in df_reordenado.columns:
        df_reordenado = df_reordenado.drop(columns=["Usuario"])
    return df_reordenado


def buscar_frame(timestamp_segundos):
    if WORLD_TIMESTAMPS is None:
        return None
    try:
        idx = np.searchsorted(WORLD_TIMESTAMPS, timestamp_segundos)
        return int(idx)
    except Exception:
        return None


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
        return image_paths[:4]
    if mode == "Grid":
        return image_paths[:4]
    if mode == "Sequential":
        return image_paths[:4] if len(image_paths) > 4 else image_paths
    return image_paths


def _ensure_ab_mode_defaults(mode_state: dict) -> None:
    images: list[Path] = mode_state.get("images", [])
    total_images = len(images)
    raw_pairs = mode_state.get("ab_pairs")
    if not raw_pairs:
        pairs: list[tuple[int, int]] = []
        if total_images >= 2:
            pairs.append((0, 1))
        if total_images >= 4:
            pairs.append((2, 3))
        mode_state["ab_pairs"] = pairs
    else:
        normalized_pairs: list[tuple[int, int]] = []
        for pair in raw_pairs:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            first, second = pair
            if not isinstance(first, int) or not isinstance(second, int):
                continue
            normalized_pairs.append((first, second))
        mode_state["ab_pairs"] = normalized_pairs

    pairs = mode_state.get("ab_pairs", [])
    max_stage = len(pairs) + 1 if pairs else 1

    mode_state.setdefault("ab_stage", 0)
    mode_state.setdefault("ab_winner_indexes", [])
    mode_state.setdefault("ab_stage_choices", [])
    mode_state.setdefault("ab_final_options", [])
    mode_state.setdefault("ab_stage_starts", {})
    mode_state.setdefault("ab_stage_durations", {})
    mode_state.setdefault("ab_highlighted_product", None)

    if mode_state["ab_stage"] > max_stage:
        mode_state["ab_stage"] = max_stage

    winner_indexes: list[int] = mode_state.get("ab_winner_indexes", [])
    if len(mode_state.get("ab_final_options", [])) < 2 and len(winner_indexes) >= 2:
        finalists: list[str] = []
        for idx in winner_indexes[:2]:
            if 0 <= idx < total_images:
                finalists.append(images[idx].stem)
        if len(finalists) == 2:
            mode_state["ab_final_options"] = finalists


def _get_ab_stage_label(stage: int, total_pairs: int) -> Optional[str]:
    if total_pairs <= 0:
        return None
    if stage < total_pairs:
        return f"pair_{stage + 1}"
    if stage == total_pairs:
        return "final"
    return None


def _ensure_ab_stage_started(mode_state: dict) -> None:
    pairs: list[tuple[int, int]] = mode_state.get("ab_pairs", [])
    stage: int = mode_state.get("ab_stage", 0)
    stage_label = _get_ab_stage_label(stage, len(pairs))
    if stage_label is None:
        return
    stage_starts: dict = mode_state.setdefault("ab_stage_starts", {})
    if stage_label not in stage_starts:
        stage_starts[stage_label] = datetime.now()
        mode_state["ab_stage_starts"] = stage_starts


def _get_ab_display_indexes(mode_state: dict) -> list[int]:
    images: list[Path] = mode_state.get("images", [])
    total_images = len(images)
    stage: int = mode_state.get("ab_stage", 0)
    pairs: list[tuple[int, int]] = mode_state.get("ab_pairs", [])
    if stage < len(pairs):
        current_pair = pairs[stage]
        return [idx for idx in current_pair if 0 <= idx < total_images]
    winner_indexes: list[int] = mode_state.get("ab_winner_indexes", [])
    return [idx for idx in winner_indexes[:2] if 0 <= idx < total_images]


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
    st.session_state["experiment_start_time"] = None
    st.session_state["experiment_end_time"] = None


def _ensure_mode_initialized(mode: str) -> None:
    sessions: dict = st.session_state.setdefault("mode_sessions", {})
    mode_state = sessions.get(mode)
    if mode_state and mode_state.get("images"):
        if mode == "A/B":
            _ensure_ab_mode_defaults(mode_state)
            sessions[mode] = mode_state
            st.session_state["mode_sessions"] = sessions
        elif mode == "Sequential":
            mode_state.setdefault("seq_product_durations", {})
            mode_state.setdefault("seq_product_visits", {})
            mode_state.setdefault("seq_navigation_history", [])
            mode_state.setdefault("seq_back_clicks", 0)
            mode_state.setdefault("seq_next_clicks", 0)
            mode_state.setdefault("seq_view_start", None)
            mode_state.setdefault("seq_current_image", None)
            sessions[mode] = mode_state
            st.session_state["mode_sessions"] = sessions
        return
    images = _load_mode_images(mode)
    mode_state = {
        "images": images,
        "options": [img.stem for img in images],
        "selected": None,
        "start_time": None,
        "selection_timestamp": None,
        "selection_duration": None,
        "completion_timestamp": None,
        "navigation_index": 0,
    }
    if mode == "A/B":
        _ensure_ab_mode_defaults(mode_state)
        mode_state.setdefault("ab_highlighted_product", None)
    if mode == "Sequential":
        mode_state.setdefault("seq_product_durations", {})
        mode_state.setdefault("seq_product_visits", {})
        mode_state.setdefault("seq_navigation_history", [])
        mode_state.setdefault("seq_back_clicks", 0)
        mode_state.setdefault("seq_next_clicks", 0)
        mode_state.setdefault("seq_view_start", None)
        mode_state.setdefault("seq_current_image", None)
    sessions[mode] = mode_state
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


def _ensure_seq_view_state(mode_state: dict, current_image: Optional[Path]) -> dict:
    if current_image is None:
        return mode_state
    now = datetime.now()
    durations: dict = mode_state.setdefault("seq_product_durations", {})
    visits: dict = mode_state.setdefault("seq_product_visits", {})
    history: list = mode_state.setdefault("seq_navigation_history", [])
    current_stem = current_image.stem
    last_stem = mode_state.get("seq_current_image")
    view_start: Optional[datetime] = mode_state.get("seq_view_start")

    if current_stem != last_stem:
        if last_stem and view_start:
            durations[last_stem] = durations.get(last_stem, 0.0) + (
                now - view_start
            ).total_seconds()
            history.append(
                {
                    "timestamp": now.isoformat(),
                    "event": "leave",
                    "image": last_stem,
                }
            )
        mode_state["seq_current_image"] = current_stem
        mode_state["seq_view_start"] = now
        visits[current_stem] = visits.get(current_stem, 0) + 1
        history.append(
            {
                "timestamp": now.isoformat(),
                "event": "view",
                "image": current_stem,
            }
        )
    elif view_start is None:
        mode_state["seq_view_start"] = now
        visits[current_stem] = visits.get(current_stem, 0) + 1
        history.append(
            {
                "timestamp": now.isoformat(),
                "event": "view",
                "image": current_stem,
            }
        )
    return mode_state


def _record_seq_navigation(mode_state: dict, new_index: int, action: str) -> None:
    now = datetime.now()
    durations: dict = mode_state.setdefault("seq_product_durations", {})
    history: list = mode_state.setdefault("seq_navigation_history", [])
    current_stem = mode_state.get("seq_current_image")
    view_start: Optional[datetime] = mode_state.get("seq_view_start")
    if current_stem and view_start:
        durations[current_stem] = durations.get(current_stem, 0.0) + (
            now - view_start
        ).total_seconds()
        history.append(
            {
                "timestamp": now.isoformat(),
                "event": "leave",
                "image": current_stem,
            }
        )
    if action == "prev":
        mode_state["seq_back_clicks"] = mode_state.get("seq_back_clicks", 0) + 1
    elif action == "next":
        mode_state["seq_next_clicks"] = mode_state.get("seq_next_clicks", 0) + 1
    history.append(
        {
            "timestamp": now.isoformat(),
            "event": action,
            "image": current_stem,
        }
    )
    mode_state["navigation_index"] = new_index
    mode_state["seq_current_image"] = None
    mode_state["seq_view_start"] = None


def _finalize_sequential_state(mode_state: dict) -> None:
    current_stem = mode_state.get("seq_current_image")
    view_start: Optional[datetime] = mode_state.get("seq_view_start")
    if current_stem and view_start:
        now = datetime.now()
        durations: dict = mode_state.setdefault("seq_product_durations", {})
        history: list = mode_state.setdefault("seq_navigation_history", [])
        durations[current_stem] = durations.get(current_stem, 0.0) + (
            now - view_start
        ).total_seconds()
        history.append(
            {
                "timestamp": now.isoformat(),
                "event": "finalize",
                "image": current_stem,
            }
        )
        mode_state["seq_view_start"] = None


def _format_metric_dict(metrics: dict) -> str:
    if not metrics:
        return ""
    formatted = {
        key.replace("_", " "): round(value, 3) if isinstance(value, float) else value
        for key, value in sorted(metrics.items())
    }
    return json.dumps(formatted, ensure_ascii=False)


def _handle_ab_mode_selection(mode: str, choice_label: str, participant: str) -> None:
    sessions: dict = st.session_state.get("mode_sessions", {})
    mode_state = sessions.get(mode)
    if not mode_state:
        return

    now = datetime.now()
    images: list[Path] = mode_state.get("images", [])
    if mode_state.get("start_time") is None:
        mode_state["start_time"] = now

    stage: int = mode_state.get("ab_stage", 0)
    pairs: list[tuple[int, int]] = mode_state.get("ab_pairs", [])
    winner_indexes: list[int] = mode_state.setdefault("ab_winner_indexes", [])
    stage_choices: list[str] = mode_state.setdefault("ab_stage_choices", [])
    stage_starts: dict = mode_state.setdefault("ab_stage_starts", {})
    stage_durations: dict = mode_state.setdefault("ab_stage_durations", {})
    total_pairs = len(pairs)

    def _find_index(candidate_indexes: list[int]) -> Optional[int]:
        for idx in candidate_indexes:
            if 0 <= idx < len(images) and images[idx].stem == choice_label:
                return idx
        for idx, image in enumerate(images):
            if image.stem == choice_label:
                return idx
        return None

    if stage < len(pairs):
        current_pair = [idx for idx in pairs[stage] if 0 <= idx < len(images)]
        selected_index = _find_index(current_pair)
        if selected_index is None:
            return
        stage_label = _get_ab_stage_label(stage, total_pairs)
        if stage_label and stage_label in stage_starts:
            stage_durations[stage_label] = stage_durations.get(stage_label, 0.0) + (
                now - stage_starts[stage_label]
            ).total_seconds()
        elif stage_label and mode_state.get("start_time"):
            stage_durations[stage_label] = stage_durations.get(stage_label, 0.0) + (
                now - mode_state["start_time"]
            ).total_seconds()

        if len(winner_indexes) <= stage:
            winner_indexes.append(selected_index)
        else:
            winner_indexes[stage] = selected_index
        if len(stage_choices) <= stage:
            stage_choices.append(choice_label)
        else:
            stage_choices[stage] = choice_label

        mode_state["ab_winner_indexes"] = winner_indexes[:2]
        mode_state["ab_stage_choices"] = stage_choices[:2]
        mode_state["ab_stage"] = stage + 1

        if mode_state["ab_stage"] == len(pairs):
            finalists = [
                images[idx].stem
                for idx in mode_state["ab_winner_indexes"]
                if 0 <= idx < len(images)
            ]
            if len(finalists) == 2:
                mode_state["ab_final_options"] = finalists

        next_stage_label = _get_ab_stage_label(stage + 1, total_pairs)
        if next_stage_label:
            stage_starts[next_stage_label] = now
        mode_state["ab_stage_durations"] = stage_durations
        mode_state["ab_stage_starts"] = stage_starts

        sessions[mode] = mode_state
        st.session_state["mode_sessions"] = sessions
        return

    finalists_indexes = [
        idx
        for idx in mode_state.get("ab_winner_indexes", [])[:2]
        if 0 <= idx < len(images)
    ]
    if len(finalists_indexes) < 2:
        return

    selected_index = _find_index(finalists_indexes)
    if selected_index is None:
        return

    mode_state["selected"] = choice_label
    mode_state["selection_timestamp"] = now
    start_time = mode_state.get("start_time")
    if start_time:
        mode_state["selection_duration"] = (now - start_time).total_seconds()
    mode_state["ab_stage"] = len(pairs) + 1

    final_stage_label = _get_ab_stage_label(total_pairs, total_pairs)
    if final_stage_label and final_stage_label in stage_starts:
        stage_durations[final_stage_label] = stage_durations.get(
            final_stage_label, 0.0
        ) + (now - stage_starts[final_stage_label]).total_seconds()
    elif final_stage_label and mode_state.get("start_time"):
        stage_durations[final_stage_label] = stage_durations.get(
            final_stage_label, 0.0
        ) + (now - mode_state["start_time"]).total_seconds()
    mode_state["ab_stage_durations"] = stage_durations
    mode_state["ab_stage_starts"] = stage_starts

    finalists = [
        images[idx].stem
        for idx in finalists_indexes
        if 0 <= idx < len(images)
    ]
    if len(finalists) == 2:
        mode_state["ab_final_options"] = finalists

    sessions[mode] = mode_state
    st.session_state["mode_sessions"] = sessions

    log_entry = {
        "timestamp": now.isoformat(),
        "participant_name": participant,
        "mode": mode,
        "choice": choice_label,
        "options": mode_state.get("ab_final_options") or mode_state.get("options", []),
        "selection_duration_seconds": mode_state.get("selection_duration"),
    }

    filtered_log = [
        entry for entry in st.session_state.get("visual_log", []) if entry.get("mode") != mode
    ]
    filtered_log.append(log_entry)
    st.session_state["visual_log"] = filtered_log


def _handle_mode_selection(mode: str, choice_label: str, participant: str) -> None:
    if mode == "A/B":
        _handle_ab_mode_selection(mode, choice_label, participant)
        return
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
    if current_mode == "Sequential":
        _finalize_sequential_state(mode_state)
    if mode_state.get("completion_timestamp") is None:
        mode_state["completion_timestamp"] = datetime.now()
    sessions[current_mode] = mode_state
    st.session_state["mode_sessions"] = sessions
    if index < len(sequence) - 1:
        st.session_state["current_mode_index"] = index + 1
    _trigger_streamlit_rerun()


def obtener_aoi_layout(state, modo):
    """
    Devuelve un dict con bounding boxes por producto.
    Cada bounding box es [x1, y1, x2, y2] en coordenadas normalizadas 0-1.
    """
    aoi_dict = {}

    # Para A/B (dos imágenes lado a lado)
    if modo == "A/B":
        productos = state.get("images", [])
        if len(productos) == 2:
            aoi_dict[productos[0].name] = [0.0, 0.0, 0.5, 1.0]
            aoi_dict[productos[1].name] = [0.5, 0.0, 1.0, 1.0]

    # Para Grid (usando filas × columnas desde state)
    if modo == "Grid":
        productos = state.get("images", [])
        rows = state.get("grid_rows", 2)
        cols = state.get("grid_cols", 3)

        for i, p in enumerate(productos):
            r = i // cols
            c = i % cols
            x1 = c / cols
            y1 = r / rows
            x2 = (c + 1) / cols
            y2 = (r + 1) / rows
            aoi_dict[p.name] = [x1, y1, x2, y2]

    # Para Sequential (solo el producto mostrado)
    if modo == "Sequential":
        producto = state.get("current_image")
        if producto:
            aoi_dict[producto.name] = [0.0, 0.0, 1.0, 1.0]

    return aoi_dict


def calcular_atencion_recomendado(aois, gaze_data, recomendado):
    # aois es el dict generado en AOIs
    # gaze_data viene de state.get("gaze_history", [])
    if not recomendado or recomendado not in aois:
        return {"tiempo": None, "fijaciones": None, "primera_mirada": None}

    x1, y1, x2, y2 = aois[recomendado]

    tiempo = 0
    fijaciones = 0
    primera = None

    for g in gaze_data:
        ts = g["t"]
        x = g["x"]
        y = g["y"]

        dentro = x >= x1 and x <= x2 and y >= y1 and y <= y2

        if dentro:
            tiempo += g.get("dt", 0)
            fijaciones += 1
            if primera is None:
                primera = ts

    return {
        "tiempo": tiempo,
        "fijaciones": fijaciones,
        "primera_mirada": primera,
    }


def obtener_layout_modo(modo, state):
    if modo == "A/B":
        return "AB-2col"
    if modo == "Grid":
        rows = state.get("grid_rows", 2)
        cols = state.get("grid_cols", 3)
        return f"Grid-{rows}x{cols}"
    if modo == "Sequential":
        return "Sequential-1"
    return "Desconocido"


def _build_experiment_results(
    user_name: str, user_id: str, user_group: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sequence: list = st.session_state.get("mode_sequence", [])
    sessions: dict = st.session_state.get("mode_sessions", {})
    experiment_start = st.session_state.get("experiment_start_time")
    experiment_end = st.session_state.get("experiment_end_time")
    experiment_start_iso = (
        experiment_start.isoformat()
        if isinstance(experiment_start, datetime)
        else ""
    )
    experiment_end_iso = (
        experiment_end.isoformat() if isinstance(experiment_end, datetime) else ""
    )
    experiment_duration = None
    if isinstance(experiment_start, datetime) and isinstance(experiment_end, datetime):
        experiment_duration = (experiment_end - experiment_start).total_seconds()
    records: list[dict] = []
    participant_group = user_group or st.session_state.get("tab2_user_group", "")
    for mode in sequence:
        state = sessions.get(mode, {})
        start_time = state.get("start_time")
        selection_time = state.get("selection_timestamp")
        completion_time = state.get("completion_timestamp") or selection_time
        selection_duration = state.get("selection_duration")
        mode_duration = None
        if start_time and completion_time:
            mode_duration = (completion_time - start_time).total_seconds()
        recomendado = state.get("producto_recomendado")
        record = {
            "Usuario": user_name,
            "ID_Participante": user_id or st.session_state.get("tab2_user_id", ""),
            "Grupo_Experimental": participant_group,
            "Modo": mode,
            "Opciones Presentadas": ", ".join(state.get("options", [])),
            "Producto Seleccionado": state.get("selected") or "",
            "Tiempo hasta selección (s)": selection_duration,
            "Duración del modo (s)": mode_duration,
            "Inicio del modo": start_time.isoformat() if start_time else "",
            "Inicio del modo (s)": start_time.timestamp() if start_time else None,
            "Momento de selección": selection_time.isoformat() if selection_time else "",
            "Momento de selección (s)": selection_time.timestamp()
            if selection_time
            else None,
            "Momento de finalización": completion_time.isoformat() if completion_time else "",
            "Momento de finalización (s)": completion_time.timestamp()
            if completion_time
            else None,
            "Inicio del experimento": experiment_start_iso,
            "Fin del experimento": experiment_end_iso,
            "Inicio experimento (s)": experiment_start.timestamp()
            if isinstance(experiment_start, datetime)
            else None,
            "Fin experimento (s)": experiment_end.timestamp()
            if isinstance(experiment_end, datetime)
            else None,
            "Duración total experimento (s)": experiment_duration,
        }
        inicio_s = record["Inicio del modo (s)"]
        fin_s = record["Momento de finalización (s)"]
        record["Frame_inicio"] = buscar_frame(inicio_s)
        record["Frame_fin"] = buscar_frame(fin_s)
        record["Pantalla_mostrada"] = obtener_layout_modo(mode, state)
        aois = obtener_aoi_layout(state, mode)

        if participant_group == "Con SmartScore":
            atn = calcular_atencion_recomendado(
                aois, state.get("gaze_history", []), recomendado
            )
        else:
            atn = {"tiempo": None, "fijaciones": None, "primera_mirada": None}

        record["Atencion_Recomendado_Tiempo"] = atn["tiempo"]
        record["Atencion_Recomendado_Fijaciones"] = atn["fijaciones"]
        record["Atencion_Recomendado_PrimeraMirada"] = atn["primera_mirada"]

        record["AOIs"] = json.dumps(aois, ensure_ascii=False)

        if mode == "A/B":
            stage_durations = state.get("ab_stage_durations", {})
            record["Tiempo comparación A/B · Par 1 (s)"] = stage_durations.get("pair_1")
            record["Tiempo comparación A/B · Par 2 (s)"] = stage_durations.get("pair_2")
            record["Tiempo comparación A/B · Final (s)"] = stage_durations.get("final")

        if mode == "Sequential":
            durations_map = state.get("seq_product_durations", {})
            visits_map = state.get("seq_product_visits", {})
            history = state.get("seq_navigation_history", [])
            record["Secuencial · Tiempo por producto (s)"] = _format_metric_dict(
                durations_map
            )
            record["Secuencial · Visitas por producto"] = _format_metric_dict(
                visits_map
            )
            record["Secuencial · Veces botón regresar"] = state.get(
                "seq_back_clicks", 0
            )
            record["Secuencial · Veces botón siguiente"] = state.get(
                "seq_next_clicks", 0
            )
            record["Secuencial · Historial navegación"] = (
                json.dumps(history, ensure_ascii=False) if history else ""
            )

        records.append(record)

    summary_df = pd.DataFrame(records)

    for column in ("Frame_inicio", "Frame_fin"):
        if column in summary_df.columns:
            summary_df[column] = pd.to_numeric(
                summary_df[column], errors="coerce"
            ).astype("Int64")

    if not summary_df.empty and "Pantalla_mostrada" in summary_df.columns:
        summary_df["Pantalla_mostrada"] = (
            summary_df["Pantalla_mostrada"].fillna("").astype(str)
        )

    return summary_df, pd.DataFrame()


def _complete_visual_experiment(user_name: str) -> None:
    sessions: dict = st.session_state.get("mode_sessions", {})
    current_mode = st.session_state.get("mode_sequence", [None])[st.session_state.get("current_mode_index", 0)]
    if current_mode in sessions:
        mode_state = sessions[current_mode]
        if mode_state.get("completion_timestamp") is None:
            if current_mode == "Sequential":
                _finalize_sequential_state(mode_state)
            mode_state["completion_timestamp"] = datetime.now()
            sessions[current_mode] = mode_state
            st.session_state["mode_sessions"] = sessions

    for mode_name, mode_state in sessions.items():
        if mode_name == "Sequential":
            _finalize_sequential_state(mode_state)
            sessions[mode_name] = mode_state
    st.session_state["mode_sessions"] = sessions

    st.session_state["experiment_end_time"] = datetime.now()

    summary_df, _ = _build_experiment_results(
        user_name,
        st.session_state.get("tab2_user_id", ""),
        st.session_state.get("tab2_user_group", ""),
    )
    VISUAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = _sanitize_filename_component(user_name)
    file_path = VISUAL_RESULTS_DIR / f"experimento_{safe_name}_{timestamp}.xlsx"

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Resumen", index=False)

    st.session_state["experiment_result_df"] = summary_df
    st.session_state["experiment_result_path"] = str(file_path)
    st.session_state["experiment_completed"] = True
    st.session_state["last_selection_feedback"] = ""



def _select_highest_smartscore_product(
    image_paths: list[Path], smartscore_map: dict[str, float]
) -> Optional[tuple[str, float]]:
    best_entry: Optional[tuple[str, float]] = None
    best_score = float("-inf")
    for image_path in image_paths:
        entry = _find_smartscore_for_image(image_path.stem, smartscore_map)
        if not entry:
            continue
        _, score_value = entry
        if best_entry is None or score_value > best_score:
            best_entry = entry
            best_score = score_value
    return best_entry


def _render_visual_image(
    image_path: Path, mode: str, highlighted_product: Optional[str] = None
) -> None:
    mode_class = {"A/B": "ab", "Grid": "grid", "Sequential": "seq"}.get(mode, "grid")
    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    extension = image_path.suffix.lower().lstrip(".") or "png"
    if extension == "jpg":
        extension = "jpeg"
    caption = html.escape(image_path.stem.replace("_", " "))
    smartscore_html = ""
    grupo = st.session_state.get("tab2_user_group", "")
    mostrar_smartscore = grupo == "Con SmartScore"

    if mostrar_smartscore:
        smartscore_map: dict[str, float] = st.session_state.get("tab2_smartscore_map", {})
        smartscore_entry = _find_smartscore_for_image(image_path.stem, smartscore_map)
        if smartscore_entry and highlighted_product and (
            smartscore_entry[0] == highlighted_product
        ):
            _, score_value = smartscore_entry
            smartscore_html = (
                "<div class=\"smartscore-label\">"
                "<span class=\"smartscore-star\" aria-hidden=\"true\">⭐</span>"
                f"<span class=\"smartscore-text\">{t('smartscore_recommended', score=score_value * 100)}</span>"
                "</div>"
            )
    st.markdown(
        f"""
        <div class="tab2-image-container {mode_class}">
            <img src="data:image/{extension};base64,{encoded}" alt="{caption}" />
            <p class="tab2-image-caption">{caption}</p>
            {smartscore_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer.getvalue()


def _experiment_results_to_excel_bytes(summary_df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Resumen", index=False)

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
tab1, tab2, tab_admin = st.tabs(
    [
        t("tab1_title"),
        t("tab2_title"),
        "🛠️ Admin",
    ]
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
            persona_id = f"{persona_nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            persona_grupo = ""

            st.session_state["tab1_persona_id"] = persona_id
            st.session_state["tab1_persona_group"] = persona_grupo

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
                                "ID_Participante": persona_id,
                                "Grupo_Experimental": "",
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
    st.header(t("tab2_header"))
    st.caption(t("tab2_caption"))

    registered_names, names_error = _load_registered_names(Path(RESULTS_PATH_IN_REPO))

    if names_error:
        st.warning(names_error)

    tab2_can_continue = True

    if (
        st.session_state.get("tab2_authenticated", False)
        and st.session_state.get("tab2_user_name") not in registered_names
    ):
        st.warning(t("tab2_name_reused_warning"))
        st.session_state["tab2_authenticated"] = False
        st.session_state["tab2_user_name"] = ""
        st.session_state["tab2_user_id"] = ""
        st.session_state["tab2_user_group"] = ""
        _set_tab2_smartscore_map("")

    if not registered_names:
        st.info(t("tab2_requires_response_info"))
        _set_tab2_smartscore_map("")
        tab2_can_continue = False

    if tab2_can_continue and not st.session_state.get("tab2_authenticated", False):
        name_query = st.text_input(
            t("tab2_select_name_prompt"),
            key="tab2_name_query",
        )
        normalized_query = _normalize_name_for_match(name_query)
        matches = _find_registered_name_matches(name_query, registered_names)
        selected_name: Optional[str] = None

        if matches:
            if len(matches) == 1:
                selected_name = matches[0]
                st.caption(t("tab2_name_match_found", match=selected_name))
            else:
                selected_name = st.selectbox(
                    t("tab2_name_matches_prompt"),
                    matches,
                    key="tab2_match_choice",
                )
        elif normalized_query and len(normalized_query.replace(" ", "")) >= 3:
            st.caption(t("tab2_name_no_matches"))

        start_clicked = st.button(
            t("tab2_start_experiment"),
            key="tab2_start_experiment_button",
            disabled=not bool(selected_name),
        )

        if start_clicked and selected_name:
            st.session_state["tab2_authenticated"] = True
            st.session_state["tab2_user_name"] = selected_name
            participant_id, participant_group = _lookup_participant_metadata(selected_name)
            if not participant_id:
                participant_id = st.session_state.get("tab1_persona_id", "")
            persona_id = participant_id
            grupo = get_user_group(selected_name)
            if not grupo:
                grupo = participant_group
            st.session_state["tab2_user_id"] = persona_id
            st.session_state["tab2_user_group"] = grupo
            _reset_visual_experiment_state()
            _set_tab2_smartscore_map(selected_name)
            st.session_state["experiment_start_time"] = datetime.now()
            st.session_state["experiment_end_time"] = None
            _trigger_streamlit_rerun()
        elif start_clicked and not selected_name:
            st.error(t("tab2_name_required_error"))

        if not st.session_state.get("tab2_authenticated", False):
            st.info(t("tab2_choose_name_info"))
            tab2_can_continue = False

    if tab2_can_continue:
        usuario_activo = st.session_state.get("tab2_user_name", "")
        _ensure_tab2_smartscore_map(usuario_activo)
        st.success(t("tab2_logged_in_as", user=usuario_activo))

        if st.button(t("tab2_switch_user"), key="tab2_logout"):
            st.session_state["tab2_authenticated"] = False
            st.session_state["tab2_user_name"] = ""
            st.session_state["tab2_user_id"] = ""
            st.session_state["tab2_user_group"] = ""
            _reset_visual_experiment_state()
            _set_tab2_smartscore_map("")
            _trigger_streamlit_rerun()

        sequence = st.session_state.get("mode_sequence", [])
    else:
        usuario_activo = ""
        sequence = []
        _ensure_tab2_smartscore_map("")

    if tab2_can_continue and not sequence:
        st.warning(t("tab2_no_modes_warning"))
        tab2_can_continue = False

    if tab2_can_continue:
        for mode_option in sequence:
            _ensure_mode_initialized(mode_option)

        if st.session_state.get("experiment_completed"):
            result_path = st.session_state.get("experiment_result_path", "")
            result_df = st.session_state.get("experiment_result_df")
            if result_path:
                st.success(t("tab2_completed_with_path", path=result_path))
            else:
                st.success(t("tab2_completed"))

            if isinstance(result_df, pd.DataFrame) and not result_df.empty:
                st.dataframe(result_df)
                download_name = (
                    Path(result_path).name
                    if result_path
                    else "resultados_experimento_visual.xlsx"
                )
                st.download_button(
                    t("tab2_download_results"),
                    data=_experiment_results_to_excel_bytes(result_df),
                    file_name=download_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.info(t("tab2_no_data_info"))

            if st.button(t("tab2_restart_experiment"), key="restart_experiment"):
                _reset_visual_experiment_state()
                _trigger_streamlit_rerun()

            tab2_can_continue = False

    selection_made = False
    is_last_mode = True

    if tab2_can_continue:
        total_modes = len(sequence)
        current_index = st.session_state.get("current_mode_index", 0)
        current_index = max(0, min(current_index, total_modes - 1))
        st.session_state["current_mode_index"] = current_index
        current_mode = sequence[current_index]

        _ensure_mode_started(current_mode)
        mode_sessions = st.session_state.get("mode_sessions", {})
        current_state = mode_sessions.get(current_mode, {})

        images = current_state.get("images", [])
        smartscore_map = st.session_state.get("tab2_smartscore_map", {})

        info_message = t(
            "tab2_mode_info",
            current=current_index + 1,
            total=total_modes,
            mode=current_mode,
        )

        ab_stage = current_state.get("ab_stage", 0)
        ab_finalists = current_state.get("ab_final_options", [])
        stage_messages = []

        next_clicked = False

        if current_mode == "A/B" and len(images) >= 4:
            _ensure_ab_stage_started(current_state)
            mode_sessions[current_mode] = current_state
            st.session_state["mode_sessions"] = mode_sessions

            ab_stage = current_state.get("ab_stage", ab_stage)
            ab_finalists = current_state.get("ab_final_options", ab_finalists)

            if ab_stage == 0:
                stage_messages.append(t("tab2_ab_step_one"))
            elif ab_stage == 1:
                stage_messages.append(t("tab2_ab_step_two"))
            else:
                if len(ab_finalists) == 2:
                    first_finalist = ab_finalists[0].replace("_", " ")
                    second_finalist = ab_finalists[1].replace("_", " ")
                    stage_messages.append(
                        t(
                            "tab2_ab_finalists",
                            first=first_finalist,
                            second=second_finalist,
                        )
                    )
                if not current_state.get("selected"):
                    stage_messages.append(t("tab2_ab_step_three"))

        if current_mode == "Grid":
            stage_messages.append(t("tab2_grid_instruction"))
        elif current_mode == "Sequential":
            stage_messages.append(t("tab2_seq_instruction"))

        if stage_messages:
            info_message = f"{info_message}\n\n" + "\n".join(stage_messages)

        st.info(info_message)

        st.markdown(TAB2_IMAGE_STYLES, unsafe_allow_html=True)

        if not images:
            st.warning(t("tab2_no_images_warning"))
        else:
            if current_mode == "A/B":
                if len(images) < 4:
                    st.warning(t("tab2_need_four_images_ab"))
                else:
                    display_indexes = _get_ab_display_indexes(current_state)
                    highlighted_product = current_state.get(
                        "ab_highlighted_product"
                    )
                    if highlighted_product is None:
                        best_entry = _select_highest_smartscore_product(
                            images, smartscore_map
                        )
                        highlighted_product = best_entry[0] if best_entry else None
                        current_state["ab_highlighted_product"] = highlighted_product
                        mode_sessions[current_mode] = current_state
                        st.session_state["mode_sessions"] = mode_sessions
                    if len(display_indexes) != 2:
                        st.warning(t("tab2_no_images_warning"))
                    else:
                        columns = st.columns(2)
                        for idx, (col, image_index) in enumerate(
                            zip(columns, display_indexes)
                        ):
                            if not (0 <= image_index < len(images)):
                                continue
                            image_path = images[image_index]
                            with col:
                                _render_visual_image(
                                    image_path, current_mode, highlighted_product
                                )
                                if current_state.get("selected") == image_path.stem:
                                    st.caption(t("tab2_selected_label"))
                                if st.button(
                                    t("tab2_choose_product"),
                                    key=f"choose_{current_mode}_{ab_stage}_{idx}",
                                ):
                                    _handle_mode_selection(
                                        current_mode, image_path.stem, usuario_activo
                                    )
                                    st.session_state["last_selection_feedback"] = (
                                        image_path.stem
                                    )
                                    _trigger_streamlit_rerun()
            elif current_mode == "Grid":
                if len(images) < 2:
                    st.warning(t("tab2_need_two_images_grid"))
                else:
                    grid_best = _select_highest_smartscore_product(
                        images, smartscore_map
                    )
                    highlighted_product = grid_best[0] if grid_best else None
                    for start in range(0, len(images), 2):
                        columns = st.columns(2)
                        for offset, (col, image_path) in enumerate(
                            zip(columns, images[start : start + 2])
                        ):
                            with col:
                                _render_visual_image(
                                    image_path, current_mode, highlighted_product
                                )
                                if current_state.get("selected") == image_path.stem:
                                    st.caption(t("tab2_selected_label"))
                                if st.button(
                                    t("tab2_choose_product"),
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

                current_image = images[index]
                seq_best = _select_highest_smartscore_product(images, smartscore_map)
                highlighted_product = seq_best[0] if seq_best else None
                current_state = _ensure_seq_view_state(current_state, current_image)
                mode_sessions[current_mode] = current_state
                st.session_state["mode_sessions"] = mode_sessions

                _render_visual_image(
                    current_image, current_mode, highlighted_product
                )

                prev_clicked = False
                choose_clicked = False
                next_clicked = False

                button_columns = st.columns([1, 1, 1], gap="small")

                with button_columns[0]:
                    prev_clicked = st.button(
                        t("tab2_prev_product"),
                        key=f"prev_{current_mode}",
                        disabled=index <= 0,
                        use_container_width=True,
                    )

                with button_columns[1]:
                    choose_clicked = st.button(
                        t("tab2_choose_product"),
                        key=f"choose_{current_mode}_{index}",
                        use_container_width=True,
                    )

                with button_columns[2]:
                    next_clicked = st.button(
                        t("tab2_next_product"),
                        key=f"next_{current_mode}",
                        disabled=index >= total_images - 1,
                        use_container_width=True,
                    )

                if current_state.get("selected") == current_image.stem:
                    st.markdown(
                        f"<p class='seq-selection-label'>{html.escape(t('tab2_selected_label'))}</p>",
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f"<p class='seq-product-position'>{html.escape(t('tab2_product_position', current=index + 1, total=total_images))}</p>",
                    unsafe_allow_html=True,
                )

                if prev_clicked:
                    new_index = max(0, index - 1)
                    _record_seq_navigation(current_state, new_index, "prev")
                    mode_sessions[current_mode] = current_state
                    st.session_state["mode_sessions"] = mode_sessions
                    _trigger_streamlit_rerun()

                if choose_clicked:
                    _handle_mode_selection(current_mode, current_image.stem, usuario_activo)
                    mode_sessions = st.session_state.get("mode_sessions", {})
                    current_state = mode_sessions.get(current_mode, current_state)
                    current_state["navigation_index"] = index
                    mode_sessions[current_mode] = current_state
                    st.session_state["mode_sessions"] = mode_sessions
                    st.session_state["last_selection_feedback"] = current_image.stem
                    _trigger_streamlit_rerun()
                if next_clicked:
                    new_index = min(total_images - 1, index + 1)
                    _record_seq_navigation(current_state, new_index, "next")
                    mode_sessions[current_mode] = current_state
                    st.session_state["mode_sessions"] = mode_sessions
                    _trigger_streamlit_rerun()

        selection_made = bool(current_state.get("selected"))
        is_last_mode = current_index == total_modes - 1

    if not is_last_mode:
        if st.button(
            t("tab2_next_mode"),
            key=f"next_mode_{current_mode}",
            disabled=not selection_made,
        ):
            _advance_visual_mode()
    else:
        if (
            selection_made
            and not st.session_state.get("experiment_completed")
        ):
            _complete_visual_experiment(usuario_activo)
            _trigger_streamlit_rerun()


def asignar_grupos_experimentales():
    def _normalizar_genero(valor: str) -> str:
        genero = (
            unicodedata.normalize("NFKD", str(valor))
            .encode("ascii", "ignore")
            .decode("ascii")
            .strip()
            .upper()
        )
        if genero in {"M", "MALE", "HOMBRE", "MASCULINO"}:
            return "MASCULINO"
        if genero in {"F", "FEMALE", "MUJER", "FEMENINO", "FEMENINA"}:
            return "FEMENINO"
        return "OTRO"

    if "GITHUB_TOKEN" not in st.secrets:
        return {"status": "error", "msg": "Falta configurar GITHUB_TOKEN."}

    try:
        github_client = Github(st.secrets["GITHUB_TOKEN"])
        github_user = github_client.get_user()
        repo = github_user.get_repo("app_Estancia")
    except GithubException as gh_error:
        datos_error = getattr(gh_error, "data", {})
        mensaje = (
            datos_error.get("message", str(gh_error))
            if isinstance(datos_error, dict)
            else str(gh_error)
        )
        return {"status": "error", "msg": mensaje}
    except Exception as generic_error:
        return {"status": "error", "msg": str(generic_error)}

    for intento in range(2):
        try:
            contents = repo.get_contents(RESULTS_PATH_IN_REPO)
        except GithubException as gh_error:
            if gh_error.status == 404:
                return {
                    "status": "error",
                    "msg": "Archivo Resultados_SmartScore.xlsx no encontrado en GitHub.",
                }
            datos_error = getattr(gh_error, "data", {})
            mensaje = (
                datos_error.get("message", str(gh_error))
                if isinstance(datos_error, dict)
                else str(gh_error)
            )
            return {"status": "error", "msg": mensaje}

        try:
            excel_data = base64.b64decode(contents.content)
            df = pd.read_excel(BytesIO(excel_data))
        except Exception as read_error:
            return {"status": "error", "msg": f"No se pudo leer el archivo: {read_error}"}

        columnas_minimas = ["Nombre Completo", "Edad", "Género", "Grupo_Experimental"]
        for columna in columnas_minimas:
            if columna not in df.columns:
                return {"status": "error", "msg": f"Falta columna: {columna}"}

        df_clean = df.dropna(subset=["Edad", "Género"]).copy()
        df_clean.loc[:, "Edad"] = pd.to_numeric(df_clean["Edad"], errors="coerce")
        df_clean = df_clean.dropna(subset=["Edad"]).copy()

        if df_clean.empty:
            return {
                "status": "error",
                "msg": "No hay registros válidos para asignar grupos.",
            }

        df_clean.loc[:, "Género_Normalizado"] = df_clean["Género"].map(_normalizar_genero)

        max_cuartiles = min(4, df_clean["Edad"].nunique())
        if max_cuartiles <= 1:
            df_clean.loc[:, "Edad_Cuartil"] = 0
        else:
            try:
                df_clean.loc[:, "Edad_Cuartil"] = pd.qcut(
                    df_clean["Edad"],
                    q=max_cuartiles,
                    labels=False,
                    duplicates="drop",
                )
            except ValueError:
                df_clean = df_clean.sort_values("Edad").reset_index()
                df_clean.loc[:, "Edad_Cuartil"] = pd.cut(
                    np.arange(len(df_clean)),
                    bins=max_cuartiles,
                    labels=False,
                    include_lowest=True,
                )
                df_clean = df_clean.set_index("index")

        df_clean.loc[:, "Edad_Cuartil"] = df_clean["Edad_Cuartil"].astype(int)

        asignacion: dict[int, str] = {}
        con_indices: list[int] = []
        sin_indices: list[int] = []
        rng = random.Random(42)

        for (genero, cuartil), group in df_clean.groupby(
            ["Género_Normalizado", "Edad_Cuartil"],
            sort=True,
        ):
            indices = list(group.index)
            if not indices:
                continue

            rng.shuffle(indices)
            base = len(indices) // 2
            con_count = base
            sin_count = base

            if len(indices) % 2:
                if len(con_indices) <= len(sin_indices):
                    con_count += 1
                else:
                    sin_count += 1

            for idx in indices[:con_count]:
                asignacion[idx] = "Con SmartScore"
                con_indices.append(idx)

            for idx in indices[con_count : con_count + sin_count]:
                asignacion[idx] = "Sin SmartScore"
                sin_indices.append(idx)

        while abs(len(con_indices) - len(sin_indices)) > 1:
            if len(con_indices) > len(sin_indices):
                idx = con_indices.pop()
                asignacion[idx] = "Sin SmartScore"
                sin_indices.append(idx)
            else:
                idx = sin_indices.pop()
                asignacion[idx] = "Con SmartScore"
                con_indices.append(idx)

        for idx, grupo in asignacion.items():
            df.at[idx, "Grupo_Experimental"] = grupo

        try:
            repo.update_file(
                path=RESULTS_PATH_IN_REPO,
                message="Actualización automática de grupos experimentales",
                content=_df_to_excel_bytes(df),
                sha=contents.sha,
            )
            return {"status": "ok"}
        except GithubException as update_error:
            if update_error.status == 409 and intento == 0:
                continue
            datos_error = getattr(update_error, "data", {})
            mensaje = (
                datos_error.get("message", str(update_error))
                if isinstance(datos_error, dict)
                else str(update_error)
            )
            return {"status": "error", "msg": mensaje}
        except Exception as generic_error:
            return {"status": "error", "msg": str(generic_error)}

    return {
        "status": "error",
        "msg": "Conflicto al guardar los cambios en GitHub tras múltiples intentos.",
    }


with tab_admin:
    st.header("🛠️ Panel de Administración")
    st.session_state.setdefault("admin_authenticated", False)

    if not st.session_state["admin_authenticated"]:
        st.info("Esta pestaña es solo para administradores.")
        admin_password = st.text_input(
            "Ingresa la contraseña para continuar",
            type="password",
            key="admin_password_input",
        )
        if st.button("Acceder", key="admin_login_button"):
            if admin_password == "Chava":
                st.session_state["admin_authenticated"] = True
                st.success("Acceso concedido. Puedes continuar.")
            else:
                st.error("Contraseña incorrecta. Intenta nuevamente.")
        st.stop()

    st.caption("Asignación automática de grupos experimentales equilibrados.")
    st.subheader("Asignación automática de grupos experimentales")

    if st.button("⚖️ Ejecutar asignación equilibrada"):
        resultado = asignar_grupos_experimentales()
        if resultado["status"] == "ok":
            st.success("Grupos asignados correctamente en GitHub.")
        else:
            st.error(
                resultado.get(
                    "msg", "Ocurrió un error durante la asignación de grupos."
                )
            )
