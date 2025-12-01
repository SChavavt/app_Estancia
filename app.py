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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

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
        "page_caption": "Share your name, age, and gender, answer the questionnaire, and help us prepare your personalized SmartScore for future experiments.",
        "intro_text": "Use this short form to tell us what matters most when choosing instant food products so we can fine-tune the SmartScore you'll likely see in upcoming experiments.",
        "questionnaire_header": "Preference questionnaire",
        "tab1_context_title": "What SmartScore means before you answer",
        "tab1_context_body": (
            "SmartScore is a personalized compatibility score that mixes your priorities to recommend instant or ready-to-eat meals later on. "
            "Before moving the sliders, remember that each one refers to a specific decision criterion when you shop for quick meals:\n"
            "- Portion size = how much you care about servings that fill you up or let you share.\n"
            "- Healthy diet = whether the meal helps you stick to balanced nutrition.\n"
            "- Low in salt = if keeping sodium down is important to you.\n"
            "- Low in saturated fat = if you try to limit this type of fat.\n"
            "- Natural/organic ingredients = whether you prefer recognizable or organic ingredients.\n"
            "- Quick and easy to prepare = you value convenience and minimal prep.\n"
            "- Low price / good value = how strongly price or value influences your choice."
        ),
        "respondent_data_subheader": "Respondent details",
        "name_label": "Full name",
        "age_label": "Age",
        "gender_label": "Gender",
        "aspects_subheader": "Importance of each aspect",
        "aspects_caption": "Slide to the right to indicate higher importance for each aspect.",
        "slider_portion": "🔹 How important is portion size? (Scale: 0 min – 5 max)",
        "slider_diet": "🔹 How important is maintaining a healthy diet? (Scale: 0 min – 7 max)",
        "slider_salt": "🔹 How important is being low in salt? (Scale: 0 min – 5 max)",
        "slider_fat": "🔹 How important is being low in saturated fat? (Scale: 0 min – 5 max)",
        "slider_natural": "🔹 How important is using natural/organic ingredients? (Scale: 0 min – 5 max)",
        "slider_convenience": "🔹 How important is being quick and easy to prepare? (Scale: 0 min – 5 max)",
        "slider_price": "🔹 How important is a low price / good value? (Scale: 0 min – 5 max)",
        "submit_button": "Submit responses",
        "success_saved": "🎈 Your answers were successfully saved to '{path}'.",
        "error_name_required": "Enter your full name to continue.",
        "error_age_positive": "Age must be greater than 0.",
        "error_read_excel": "I couldn't read the Excel files in /data: {error}",
        "error_missing_column": "An expected column is missing in your Excel files: {column}",
        "warning_github_token": "⚠️ Configure the `GITHUB_TOKEN` secret to automatically save to GitHub.",
        "error_repo_access": "❌ Couldn't access the 'SChavavt/app_Estancia' repository: {error}",
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
        "tab2_grid_instruction": "Compare every product at once and click ‘Choose this product’ under your favorite.",
        "tab2_seq_instruction": (
            "You'll review 4 products in total. Use Previous/Next to move forward or back as often as you want, choose "
            "your single favorite with ‘Choose this product’, and confirm your selection to continue."
        ),
        "tab2_ab_step_one": "Step 1 of 3: Choose your favorite from the first pair.",
        "tab2_ab_step_two": "Step 2 of 3: Choose your favorite from the second pair.",
        "tab2_ab_step_three": "Final step: Choose your favorite between the two finalists.",
        "tab2_ab_finalists": "Finalists: {first} vs {second}.",
        "smartscore_recommended": "Rec. prod. • Compat. {score:.0f}\u202f%",
        "tab2_seq_confirm_instruction": "Confirm your selection to continue.",
        "tab2_confirm_selection": "Confirm selection",
    },
    "Español": {
        "page_title": "🧠 Smart Core – Cuestionario",
        "page_caption": "Comparte tu nombre, edad y género, responde el cuestionario y ayúdanos a preparar tu SmartScore personalizado para futuros experimentos.",
        "intro_text": "Este breve cuestionario nos ayuda a entender qué valoras al elegir productos de comida instantánea y a ajustar el SmartScore que probablemente verás en experimentos posteriores (no de inmediato).",
        "questionnaire_header": "Cuestionario de preferencias",
        "tab1_context_title": "Antes de contestar: ¿a qué se refieren las preguntas?",
        "tab1_context_body": (
            "SmartScore es un puntaje de compatibilidad que combina tus prioridades para recomendarte comidas instantáneas o listas para comer en futuras pruebas. "
            "Antes de mover los deslizadores, ten presente que cada pregunta apunta a un criterio al elegir comidas rápidas:\n"
            "- Tamaño de la porción = qué tanto te importa que rinda o te deje satisfecho/a.\n"
            "- Llevar una dieta sana = si buscas que complemente una alimentación equilibrada.\n"
            "- Bajo en sal = qué tan relevante es limitar el sodio.\n"
            "- Bajo en grasa saturada = si tratas de reducir este tipo de grasa.\n"
            "- Ingredientes naturales/orgánicos = si prefieres ingredientes reconocibles u orgánicos.\n"
            "- Que sea rápido y fácil = priorizas conveniencia y poca preparación.\n"
            "- Precio bajo / buena relación valor-precio = cuánto influye el costo en tu decisión."
        ),
        "respondent_data_subheader": "Datos de quien responde",
        "name_label": "Nombre completo",
        "age_label": "Edad",
        "gender_label": "Género",
        "aspects_subheader": "Importancia de cada aspecto",
        "aspects_caption": "Desliza hacia la derecha para indicar mayor importancia en cada aspecto.",
        "slider_portion": "🔹 ¿Qué tan importante es el tamaño de la porción? (Escala: 0 mín – 5 máx)",
        "slider_diet": "🔹 ¿Qué tan importante es llevar una dieta sana? (Escala: 0 mín – 7 máx)",
        "slider_salt": "🔹 ¿Qué tan importante es bajo en sal? (Escala: 0 mín – 5 máx)",
        "slider_fat": "🔹 ¿Qué tan importante es bajo en grasa saturada? (Escala: 0 mín – 5 máx)",
        "slider_natural": "🔹 ¿Qué tan importante es que use ingredientes naturales/orgánicos? (Escala: 0 mín – 5 máx)",
        "slider_convenience": "🔹 ¿Qué tan importante es que sea rápido y fácil de preparar? (Escala: 0 mín – 5 máx)",
        "slider_price": "🔹 ¿Qué tan importante es precio bajo / buena relación calidad-precio? (Escala: 0 mín – 5 máx)",
        "submit_button": "Enviar respuestas",
        "success_saved": "🎈 Tus respuestas fueron guardadas con éxito en '{path}'.",
        "error_name_required": "Ingresa tu nombre completo para continuar.",
        "error_age_positive": "La edad debe ser mayor a 0.",
        "error_read_excel": "No pude leer los Excel en /data: {error}",
        "error_missing_column": "Falta una columna esperada en tus Excel: {column}",
        "warning_github_token": "⚠️ Configura el secret `GITHUB_TOKEN` para guardar automáticamente en GitHub.",
        "error_repo_access": "❌ No se pudo acceder al repositorio 'SChavavt/app_Estancia': {error}",
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
        "tab2_grid_instruction": "Compara todos los productos a la vez y haz clic en ‘Elegir este producto’ debajo de tu favorito.",
        "tab2_seq_instruction": (
            "Verás 4 productos en total. Usa Anterior/Siguiente para avanzar o retroceder cuantas veces necesites, elige "
            "solo tu favorito con ‘Elegir este producto’ y confirma tu selección para continuar."
        ),
        "tab2_ab_step_one": "Paso 1 de 3: Elige tu favorito del primer par.",
        "tab2_ab_step_two": "Paso 2 de 3: Elige tu favorito del segundo par.",
        "tab2_ab_step_three": "Paso final: Elige tu favorito entre los dos finalistas.",
        "tab2_ab_finalists": "Finalistas: {first} vs {second}.",
        "smartscore_recommended": "Prod. recom. • Compat. {score:.0f}\u202f%",
        "tab2_seq_confirm_instruction": "Confirma tu selección para continuar.",
        "tab2_confirm_selection": "Confirmar selección",
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

show_global_language = not st.session_state.get("tab2_authenticated", False)

if show_global_language:
    language_index = LANGUAGE_OPTIONS.index(st.session_state["language"])
    selected_language = st.selectbox(
        "Choose language / Escoge idioma",
        options=LANGUAGE_OPTIONS,
        index=language_index,
    )
    st.session_state["language"] = selected_language
else:
    selected_language = st.session_state["language"]


def t(key: str, **kwargs) -> str:
    text = LANGUAGE_CONTENT[st.session_state["language"]][key]
    return text.format(**kwargs)


if show_global_language:
    st.title(t("page_header"))
    st.caption(t("page_caption"))
    st.markdown(t("intro_text"))

DATA_FILES = {
    "Instant Noodles": "data/Productos_Instant_Noodles_SmartScore.xlsx",
    "Mac & Cheese": "data/Productos_Mac_and_Cheese_SmartScore.xlsx",
    "Ready to Eat": "data/Productos_ReadyToEat_SmartScore.xlsx",
}

RESULTS_PATH_IN_REPO = "Resultados_SmartScore.xlsx"  # se crea/actualiza vía API de GitHub
REPO_FULL_NAME = "SChavavt/app_Estancia"

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
st.session_state.setdefault("smart_scores", {})
st.session_state.setdefault("tab2_name_query", "")
st.session_state.setdefault("auto_assignment_feedback", None)
VISUAL_MODE_OPTIONS = ["A/B", "Grid", "Sequential"]
VISUAL_SUBFOLDERS = {"A/B": "A_B", "Grid": "Grid", "Sequential": "Sequential"}
VALID_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
VISUAL_BASE_PATH = Path("data/images")
VISUAL_RESULTS_DIR = Path("/tmp/experimentos")

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
        repo = github_client.get_repo(REPO_FULL_NAME)
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
        st.session_state["smart_scores"] = {}
        sessions = st.session_state.get("mode_sessions", {})
        for mode_state in sessions.values():
            if isinstance(mode_state, dict) and "ab_highlighted_product" in mode_state:
                mode_state["ab_highlighted_product"] = None
        st.session_state["mode_sessions"] = sessions
        return

    st.session_state["tab2_smartscore_map"] = _load_user_smartscore_map(cleaned)
    st.session_state["tab2_smartscore_owner"] = cleaned
    st.session_state["smart_scores"] = st.session_state["tab2_smartscore_map"]
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
            mode_state.setdefault("seq_product_frames", {})
            mode_state.setdefault("seq_first_view_order", [])
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
        mode_state.setdefault("seq_product_frames", {})
        mode_state.setdefault("seq_first_view_order", [])
        mode_state.setdefault("seq_selection_confirmed", False)
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
    frames: dict = mode_state.setdefault("seq_product_frames", {})
    view_order: list = mode_state.setdefault("seq_first_view_order", [])
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
            if last_stem in frames:
                frames[last_stem]["end"] = now
        mode_state["seq_current_image"] = current_stem
        mode_state["seq_view_start"] = now
        visits[current_stem] = visits.get(current_stem, 0) + 1
        frame_entry = frames.setdefault(current_stem, {})
        if "start" not in frame_entry or frame_entry.get("start") is None:
            frame_entry["start"] = now
        frame_entry["end"] = now
        if current_stem not in view_order:
            view_order.append(current_stem)
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
        frame_entry = frames.setdefault(current_stem, {})
        if "start" not in frame_entry or frame_entry.get("start") is None:
            frame_entry["start"] = now
        frame_entry["end"] = now
        if current_stem not in view_order:
            view_order.append(current_stem)
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
    frames: dict = mode_state.setdefault("seq_product_frames", {})
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
        frame_entry = frames.setdefault(current_stem, {})
        if "start" not in frame_entry or frame_entry.get("start") is None:
            frame_entry["start"] = view_start
        frame_entry["end"] = now
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
        frames: dict = mode_state.setdefault("seq_product_frames", {})
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
        frame_entry = frames.setdefault(current_stem, {})
        if "start" not in frame_entry or frame_entry.get("start") is None:
            frame_entry["start"] = view_start
        frame_entry["end"] = now
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


def obtener_aoi_layout(
    modo: str,
    productos_visibles: list[Any],
    producto_recomendado: Optional[str] = None,
    pantalla_id: Optional[str] = None,
) -> dict:
    """Genera AOIs planos para los productos visibles en la pantalla actual."""

    grupo = st.session_state.get("tab2_user_group", "")
    mostrar_smartcore = grupo == "Con SmartScore"

    layout: dict[str, list[float]] = {}

    def _normalize_entry(entry: Any) -> tuple[str, bool]:
        nombre = ""
        recomendado = False
        if isinstance(entry, dict):
            candidate = (
                entry.get("display_name")
                or entry.get("nombre")
                or entry.get("name")
                or entry.get("product")
                or entry.get("id")
            )
            if candidate is not None:
                nombre = str(candidate).strip()
            recomendado = bool(
                entry.get("es_recomendado")
                or entry.get("recomendado")
                or entry.get("recommended")
                or entry.get("highlighted")
            )
        elif isinstance(entry, (list, tuple)) and entry:
            nombre = str(entry[0]).strip()
            if len(entry) > 1:
                recomendado = bool(entry[1])
        else:
            nombre = str(entry).strip()

        if producto_recomendado and nombre:
            recomendado = nombre == producto_recomendado
        return nombre, recomendado

    def _add_coords(nombre: str, suffix: str, coords: list[float]) -> None:
        if not nombre or not coords or len(coords) != 4:
            return
        try:
            layout[f"{nombre}_{suffix}"] = [float(value) for value in coords]
        except (TypeError, ValueError):
            return

    normalized: list[tuple[str, bool]] = []
    for entry in productos_visibles or []:
        nombre, recomendado = _normalize_entry(entry)
        if nombre:
            normalized.append((nombre, recomendado))

    if modo == "A/B":
        slot_coords = [
            {
                "pack": [0.00, 0.00, 0.50, 0.60],
                "claim": [0.00, 0.60, 0.50, 1.00],
                "smartcore": [0.20, 0.90, 0.30, 1.00],
            },
            {
                "pack": [0.50, 0.00, 1.00, 0.60],
                "claim": [0.50, 0.60, 1.00, 1.00],
                "smartcore": [0.70, 0.90, 0.80, 1.00],
            },
        ]
        for idx, (nombre, recomendado) in enumerate(normalized[:2]):
            slot = slot_coords[idx]
            _add_coords(nombre, "pack", slot["pack"])
            _add_coords(nombre, "claim", slot["claim"])
            if mostrar_smartcore and recomendado:
                _add_coords(nombre, "smartcore", slot["smartcore"])

    elif modo == "Grid":
        grid_slots = [
            {
                "pack": [0.00, 0.00, 0.50, 0.40],
                "claim": [0.00, 0.40, 0.50, 0.80],
                "smartcore": [0.20, 0.75, 0.30, 0.85],
            },
            {
                "pack": [0.50, 0.00, 1.00, 0.40],
                "claim": [0.50, 0.40, 1.00, 0.80],
                "smartcore": [0.70, 0.75, 0.80, 0.85],
            },
            {
                "pack": [0.00, 0.50, 0.50, 0.90],
                "claim": [0.00, 0.90, 0.50, 1.00],
                "smartcore": [0.20, 0.95, 0.30, 1.00],
            },
            {
                "pack": [0.50, 0.50, 1.00, 0.90],
                "claim": [0.50, 0.90, 1.00, 1.00],
                "smartcore": [0.70, 0.95, 0.80, 1.00],
            },
        ]
        for idx, (nombre, recomendado) in enumerate(normalized[:4]):
            slot = grid_slots[idx]
            _add_coords(nombre, "pack", slot["pack"])
            _add_coords(nombre, "claim", slot["claim"])
            if mostrar_smartcore and recomendado:
                _add_coords(nombre, "smartcore", slot["smartcore"])

    elif modo == "Sequential":
        if normalized:
            pantalla_label = str(pantalla_id) if pantalla_id else "Sequential-1"
            producto_layout: dict[str, list[float]] = {}

            def _add_seq_coords(suffix: str, coords: list[float]) -> None:
                if not coords or len(coords) != 4:
                    return
                try:
                    producto_layout[suffix] = [float(value) for value in coords]
                except (TypeError, ValueError):
                    return

            for nombre, recomendado in normalized:
                if producto_layout:
                    break
                producto_nombre = nombre
                _add_seq_coords(f"{producto_nombre}_pack", [0.20, 0.00, 0.80, 0.70])
                _add_seq_coords(f"{producto_nombre}_claim", [0.80, 0.00, 1.00, 1.00])
                _add_seq_coords(f"{producto_nombre}_nutri", [0.00, 0.00, 0.20, 1.00])
                if mostrar_smartcore and recomendado:
                    _add_seq_coords(
                        f"{producto_nombre}_smartcore", [0.40, 0.80, 0.60, 0.95]
                    )

            if producto_layout:
                layout = {pantalla_label: producto_layout}

    return layout


def _flatten_aoi_blocks(aois: Any) -> dict:
    if not isinstance(aois, dict):
        return {}
    flat: dict = {}
    for key, value in aois.items():
        if isinstance(value, dict):
            for inner_key, inner_value in value.items():
                flat[inner_key] = inner_value
        else:
            flat[key] = value
    return flat


def calcular_atencion_recomendado(aois, gaze_data, recomendado):
    # aois es el dict generado en AOIs
    # gaze_data viene de state.get("gaze_history", [])
    if not recomendado:
        return {"tiempo": None, "fijaciones": None, "primera_mirada": None}

    normalized_aois = _flatten_aoi_blocks(aois)

    def _extract_bbox(entry):
        if isinstance(entry, dict):
            try:
                x_min = float(
                    entry.get("x_min")
                    if entry.get("x_min") is not None
                    else entry.get("xmin")
                )
                y_min = float(
                    entry.get("y_min")
                    if entry.get("y_min") is not None
                    else entry.get("ymin")
                )
                x_max = float(
                    entry.get("x_max")
                    if entry.get("x_max") is not None
                    else entry.get("xmax")
                )
                y_max = float(
                    entry.get("y_max")
                    if entry.get("y_max") is not None
                    else entry.get("ymax")
                )
            except (TypeError, ValueError):
                return None
            return (x_min, y_min, x_max, y_max)
        if isinstance(entry, (list, tuple)) and len(entry) >= 4:
            try:
                x1, y1, x2, y2 = [float(value) for value in entry[:4]]
            except (TypeError, ValueError):
                return None
            return (x1, y1, x2, y2)
        return None

    candidate_keys = [recomendado]
    candidate_keys.append(f"{recomendado}_pack")
    candidate_keys.append(f"{recomendado}_claim")
    candidate_keys.append(f"{recomendado}_smartcore")
    bbox = None
    for key in candidate_keys:
        if key not in normalized_aois:
            continue
        bbox = _extract_bbox(normalized_aois[key])
        if bbox:
            break
    if not bbox:
        return {"tiempo": None, "fijaciones": None, "primera_mirada": None}

    x1, y1, x2, y2 = bbox
    
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


def _get_visible_products_by_screen(mode: str, state: dict) -> list[dict[str, list[str]]]:
    images = state.get("images") or []

    def _stem(entry: Any) -> str:
        if isinstance(entry, Path):
            return entry.stem
        return str(entry)

    image_names = [_stem(image) for image in images]
    screens: list[dict[str, list[str]]] = []

    if mode == "A/B":
        pairs = state.get("ab_pairs", []) or []
        for idx, pair in enumerate(pairs, start=1):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            names: list[str] = []
            for product_index in pair:
                if not isinstance(product_index, int):
                    continue
                if 0 <= product_index < len(images):
                    names.append(_stem(images[product_index]))
            if len(names) == 2:
                screens.append({"label": f"A/B · Par {idx}", "productos": names})
        finalists: list[str] = []
        final_options = state.get("ab_final_options")
        if isinstance(final_options, list) and len(final_options) == 2:
            finalists = [str(option) for option in final_options]
        else:
            winner_indexes = state.get("ab_winner_indexes", []) or []
            for winner_idx in winner_indexes:
                if not isinstance(winner_idx, int):
                    continue
                if 0 <= winner_idx < len(images):
                    finalists.append(_stem(images[winner_idx]))
                if len(finalists) == 2:
                    break
        if len(finalists) == 2:
            screens.append({"label": "A/B · Final", "productos": finalists})
        return screens

    if mode == "Grid":
        products = image_names[:4]
        if not products:
            options = state.get("options", []) or []
            products = [str(option) for option in options[:4]]
        if products:
            screens.append({"label": "Grid", "productos": products})
        return screens

    if mode == "Sequential":
        view_order = state.get("seq_first_view_order", []) or []
        if not view_order:
            view_order = image_names
        if not view_order:
            options = state.get("options", []) or []
            view_order = [str(option) for option in options]
        selected_product = state.get("selected")
        if not selected_product and view_order:
            selected_product = view_order[0]
        frames_map: dict = state.get("seq_product_frames", {}) or {}
        frame_entry = frames_map.get(selected_product, {}) if selected_product else {}
        start_time = frame_entry.get("start") if isinstance(frame_entry.get("start"), datetime) else default_start
        end_time = frame_entry.get("end") if isinstance(frame_entry.get("end"), datetime) else default_end or start_time
        screens.append(
            {
                "label": "Sequential",
                "pantalla_id": "Seq-1",
                "productos": [selected_product] if selected_product else [],
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        return screens

    if image_names:
        screens.append({"label": mode, "productos": image_names})
    else:
        options = state.get("options", []) or []
        if options:
            screens.append({"label": mode, "productos": [str(option) for option in options]})
    return screens


def _default_mode_start_time(state: dict) -> Optional[datetime]:
    start_time = state.get("start_time")
    return start_time if isinstance(start_time, datetime) else None


def _default_mode_end_time(state: dict) -> Optional[datetime]:
    for key in ("completion_timestamp", "selection_timestamp"):
        value = state.get(key)
        if isinstance(value, datetime):
            return value
    return None


def _resolve_stage_times(
    stage_label: str,
    next_stage_label: Optional[str],
    stage_starts: dict,
    stage_durations: dict,
    default_start: Optional[datetime],
    default_end: Optional[datetime],
) -> tuple[Optional[datetime], Optional[datetime]]:
    start_time = stage_starts.get(stage_label)
    if not isinstance(start_time, datetime):
        start_time = default_start
    end_time = None
    duration_value = stage_durations.get(stage_label)
    if isinstance(duration_value, (int, float)) and start_time:
        end_time = start_time + timedelta(seconds=float(duration_value))
    if end_time is None and next_stage_label:
        next_start = stage_starts.get(next_stage_label)
        if isinstance(next_start, datetime):
            end_time = next_start
    if end_time is None:
        end_time = default_end or start_time
    return start_time, end_time


def _build_screen_timeline(mode: str, state: dict) -> list[dict[str, Any]]:
    screens: list[dict[str, Any]] = []
    default_start = _default_mode_start_time(state)
    default_end = _default_mode_end_time(state)

    if mode == "A/B":
        images: list[Path] = state.get("images", [])
        pairs: list[tuple[int, int]] = state.get("ab_pairs", []) or []
        stage_starts: dict = state.get("ab_stage_starts", {}) or {}
        stage_durations: dict = state.get("ab_stage_durations", {}) or {}
        finalists: list[str] = []
        raw_finalists = state.get("ab_final_options", []) or []
        if len(raw_finalists) == 2:
            finalists = [str(entry) for entry in raw_finalists]
        else:
            winner_indexes: list[int] = state.get("ab_winner_indexes", []) or []
            for idx in winner_indexes[:2]:
                if 0 <= idx < len(images):
                    finalists.append(images[idx].stem)
        stage_map = [
            ("pair_1", "A/B · Par 1", "A/B-Par1"),
            ("pair_2", "A/B · Par 2", "A/B-Par2"),
            ("final", "A/B · Final", "A/B-Final"),
        ]
        stage_products: dict[str, list[str]] = {}
        for idx, pair in enumerate(pairs[:2]):
            label = f"pair_{idx + 1}"
            product_names: list[str] = []
            for product_index in pair:
                if isinstance(product_index, int) and 0 <= product_index < len(images):
                    product_names.append(images[product_index].stem)
            stage_products[label] = product_names
        if len(finalists) == 2:
            stage_products["final"] = finalists

        for current_idx, (stage_label, label, pantalla_id) in enumerate(stage_map):
            products = stage_products.get(stage_label, [])
            if not products:
                continue
            next_label: Optional[str] = None
            if current_idx + 1 < len(stage_map):
                next_label = stage_map[current_idx + 1][0]
            start_time, end_time = _resolve_stage_times(
                stage_label,
                next_label,
                stage_starts,
                stage_durations,
                default_start,
                default_end,
            )
            screens.append(
                {
                    "label": label,
                    "pantalla_id": pantalla_id,
                    "productos": products,
                    "start_time": start_time or default_start,
                    "end_time": end_time or default_end or start_time,
                }
            )
        return screens

    if mode == "Grid":
        products = [img.stem for img in state.get("images", [])[:4]]
        if not products:
            options = state.get("options", []) or []
            products = [str(option) for option in options[:4]]
        if products:
            screens.append(
                {
                    "label": "Grid",
                    "pantalla_id": "Grid-1",
                    "productos": products,
                    "start_time": default_start,
                    "end_time": default_end or default_start,
                }
            )
        return screens

    if mode == "Sequential":
        view_order: list[str] = state.get("seq_first_view_order", []) or []
        if not view_order:
            images: list[Path] = state.get("images", [])
            view_order = [img.stem for img in images]
        if not view_order:
            options = state.get("options", []) or []
            view_order = [str(option) for option in options]
        selected_product = state.get("selected")
        if not selected_product and view_order:
            selected_product = view_order[0]
        frames_map: dict = state.get("seq_product_frames", {}) or {}
        frame_entry = frames_map.get(selected_product, {}) if selected_product else {}
        start_time = frame_entry.get("start") if isinstance(frame_entry.get("start"), datetime) else default_start
        end_time = frame_entry.get("end") if isinstance(frame_entry.get("end"), datetime) else default_end or start_time
        screens.append(
            {
                "label": "Sequential",
                "pantalla_id": "Seq-1",
                "productos": [selected_product] if selected_product else [],
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        return screens

    fallback = _get_visible_products_by_screen(mode, state)
    for index, screen in enumerate(fallback, start=1):
        label = screen.get("label", mode)
        screens.append(
            {
                "label": label,
                "pantalla_id": f"{mode}-{index}",
                "productos": screen.get("productos", []),
                "start_time": default_start,
                "end_time": default_end or default_start,
            }
        )
    return screens


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
    smartscore_map = _load_user_smartscore_map(user_name)
    st.session_state["smart_scores"] = smartscore_map
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
    smartscore_enabled = participant_group == "Con SmartScore"
    default_atn = {"tiempo": None, "fijaciones": None, "primera_mirada": None}

    product_name_cache: dict[str, str] = {}

    def _resolve_display_name(product: str) -> str:
        if not product:
            return ""
        cached = product_name_cache.get(product)
        if cached is not None:
            return cached
        display = product
        entry = _find_smartscore_for_image(product, smartscore_map)
        if entry:
            display = entry[0]
        product_name_cache[product] = display
        return display

    for mode in sequence:
        state = sessions.get(mode, {})
        start_time = state.get("start_time")
        selection_time = state.get("selection_timestamp")
        completion_time = state.get("completion_timestamp") or selection_time
        selection_duration = state.get("selection_duration")
        mode_duration = None
        if start_time and completion_time:
            mode_duration = (completion_time - start_time).total_seconds()
        base_record = {
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

        (
            producto_top,
            producto_top_stem,
            producto_top_score,
        ) = _get_mode_recommended_product(state, smartscore_map)
        sessions[mode] = state
        st.session_state["mode_sessions"] = sessions
        # =======================================
        # NUEVAS COLUMNAS PARA MODO A/B (compacto)
        # =======================================
        if mode == "A/B":
            pairs = state.get("ab_pairs", [])
            images = state.get("images", [])
            ab_choices = state.get("ab_stage_choices", [])
            finalists = state.get("ab_final_options", [])
            final_choice = state.get("selected", None)

            # Construir pares como texto
            def pair_text(pair):
                if len(pair) != 2:
                    return None
                a_idx, b_idx = pair
                if 0 <= a_idx < len(images) and 0 <= b_idx < len(images):
                    return f"{images[a_idx].stem} vs {images[b_idx].stem}"
                return None

            par1 = pair_text(pairs[0]) if len(pairs) > 0 else None
            par2 = pair_text(pairs[1]) if len(pairs) > 1 else None
            final_pair = (
                f"{finalists[0]} vs {finalists[1]}" if len(finalists) == 2 else None
            )

            base_record["A/B · Par 1"] = par1
            base_record["A/B · Par 1 · Elegida"] = (
                ab_choices[0] if len(ab_choices) > 0 else None
            )

            base_record["A/B · Par 2"] = par2
            base_record["A/B · Par 2 · Elegida"] = (
                ab_choices[1] if len(ab_choices) > 1 else None
            )

            base_record["A/B · Final"] = final_pair
            base_record["A/B · Final · Elegida"] = final_choice

        else:
            base_record["A/B · Par 1"] = None
            base_record["A/B · Par 1 · Elegida"] = None
            base_record["A/B · Par 2"] = None
            base_record["A/B · Par 2 · Elegida"] = None
            base_record["A/B · Final"] = None
            base_record["A/B · Final · Elegida"] = None

        pantalla_layout = obtener_layout_modo(mode, state)
        inicio_s = base_record["Inicio del modo (s)"]
        fin_s = base_record["Momento de finalización (s)"]
        screen_views = _build_screen_timeline(mode, state)
        if not screen_views:
            screen_views = [
                {
                    "label": mode,
                    "pantalla_id": f"{mode}-1",
                    "productos": state.get("options", []) or [],
                    "start_time": _default_mode_start_time(state),
                    "end_time": _default_mode_end_time(state),
                }
            ]

        def _seconds_from_value(value: Any, fallback: Optional[float]) -> Optional[float]:
            if isinstance(value, datetime):
                return value.timestamp()
            if isinstance(value, (int, float)):
                return float(value)
            return fallback

        ab_stage_meta = {
            "A/B-Par1": {"stage_label": "pair_1", "choice_index": 0},
            "A/B-Par2": {"stage_label": "pair_2", "choice_index": 1},
            "A/B-Final": {"stage_label": "final", "choice_index": None},
        }
        stage_choices: list[str] = state.get("ab_stage_choices", []) or []
        stage_durations: dict = state.get("ab_stage_durations", {}) or {}
        stage_starts: dict = state.get("ab_stage_starts", {}) or {}
        gaze_history = state.get("gaze_history", [])

        seq_metrics = {}
        if mode == "Sequential":
            durations_map = state.get("seq_product_durations", {})
            visits_map = state.get("seq_product_visits", {})
            history = state.get("seq_navigation_history", [])
            seq_metrics = {
                "Secuencial · Tiempo por producto (s)": _format_metric_dict(
                    durations_map
                ),
                "Secuencial · Visitas por producto": _format_metric_dict(
                    visits_map
                ),
                "Secuencial · Veces botón regresar": state.get(
                    "seq_back_clicks", 0
                ),
                "Secuencial · Veces botón siguiente": state.get(
                    "seq_next_clicks", 0
                ),
                "Secuencial · Historial navegación": (
                    json.dumps(history, ensure_ascii=False) if history else ""
                ),
            }

        for idx, screen in enumerate(screen_views, start=1):
            pantalla_label = screen.get("label", mode)
            pantalla_id = str(screen.get("pantalla_id") or f"{mode}-{idx}")
            screen_products = [
                str(prod).strip()
                for prod in screen.get("productos", [])
                if str(prod).strip()
            ]
            display_products = [_resolve_display_name(prod) for prod in screen_products]
            productos_visibles = [
                {"display_name": display}
                for display in display_products
                if display
            ]

            screen_start = screen.get("start_time")
            if not isinstance(screen_start, datetime):
                screen_start = _default_mode_start_time(state)
            screen_end = screen.get("end_time")
            if not isinstance(screen_end, datetime):
                screen_end = _default_mode_end_time(state) or screen_start

            stage_meta = ab_stage_meta.get(pantalla_id) if mode == "A/B" else None
            selected_stem = ""
            selection_duration_value = None
            selection_timestamp_value: Optional[datetime] = None
            if stage_meta:
                stage_label = stage_meta["stage_label"]
                choice_idx = stage_meta["choice_index"]
                if choice_idx is not None and len(stage_choices) > choice_idx:
                    selected_stem = stage_choices[choice_idx]
                elif stage_label == "final":
                    selected_stem = state.get("selected") or ""
                duration_candidate = stage_durations.get(stage_label)
                if isinstance(duration_candidate, (int, float)):
                    selection_duration_value = float(duration_candidate)
                if stage_label == "final":
                    final_ts = state.get("selection_timestamp")
                    if isinstance(final_ts, datetime):
                        selection_timestamp_value = final_ts
                if selection_timestamp_value is None:
                    start_candidate = stage_starts.get(stage_label)
                    if (
                        isinstance(start_candidate, datetime)
                        and isinstance(selection_duration_value, (int, float))
                    ):
                        selection_timestamp_value = start_candidate + timedelta(
                            seconds=float(selection_duration_value)
                        )
            else:
                selected_stem = state.get("selected") or ""
                selection_duration_value = selection_duration
                selection_timestamp_value = selection_time

            if selection_timestamp_value is None and isinstance(screen_end, datetime):
                selection_timestamp_value = screen_end
            if selection_duration_value is None and isinstance(screen_start, datetime) and isinstance(screen_end, datetime):
                selection_duration_value = (screen_end - screen_start).total_seconds()

            recommended_display = producto_top
            recommended_score = producto_top_score
            recommended_stem = producto_top_stem
            if recommended_display is None and mode == "Sequential" and screen_products:
                recommended_display = _resolve_display_name(screen_products[0])

            recommended_visible = bool(
                recommended_stem and recommended_stem in screen_products
            )
            producto_top_visible = recommended_display if recommended_visible else None

            productos_visibles = [
                {
                    "display_name": display,
                    "es_recomendado": producto_top_visible == display,
                }
                for display in display_products
                if display
            ]

            aois = obtener_aoi_layout(
                modo=mode,
                productos_visibles=productos_visibles,
                producto_recomendado=producto_top_visible,
                pantalla_id=pantalla_id,
            )

            record = base_record.copy()
            record["Pantalla_mostrada"] = pantalla_layout
            record["Pantalla"] = pantalla_label
            record["Pantalla_ID"] = pantalla_id
            record["Productos visibles en pantalla"] = ", ".join(display_products)
            record["Opciones Presentadas"] = ", ".join(display_products)

            record["Inicio del modo"] = (
                screen_start.isoformat() if isinstance(screen_start, datetime) else ""
            )
            record["Inicio del modo (s)"] = (
                screen_start.timestamp() if isinstance(screen_start, datetime) else inicio_s
            )
            record["Momento de finalización"] = (
                screen_end.isoformat() if isinstance(screen_end, datetime) else ""
            )
            record["Momento de finalización (s)"] = (
                screen_end.timestamp() if isinstance(screen_end, datetime) else fin_s
            )
            if selection_timestamp_value and isinstance(selection_timestamp_value, datetime):
                record["Momento de selección"] = selection_timestamp_value.isoformat()
                record["Momento de selección (s)"] = selection_timestamp_value.timestamp()
            else:
                record["Momento de selección"] = ""
                record["Momento de selección (s)"] = None

            if isinstance(selection_duration_value, (int, float)):
                record["Tiempo hasta selección (s)"] = float(selection_duration_value)
            else:
                record["Tiempo hasta selección (s)"] = None

            if isinstance(screen_start, datetime) and isinstance(screen_end, datetime):
                record["Duración del modo (s)"] = (
                    screen_end - screen_start
                ).total_seconds()
            else:
                record["Duración del modo (s)"] = selection_duration_value

            frame_start_seconds = _seconds_from_value(screen_start, inicio_s)
            frame_end_seconds = _seconds_from_value(screen_end, fin_s)
            if frame_start_seconds is None and frame_end_seconds is not None:
                frame_start_seconds = frame_end_seconds
            if frame_end_seconds is None and frame_start_seconds is not None:
                frame_end_seconds = frame_start_seconds
            record["Frame_inicio"] = buscar_frame(frame_start_seconds)
            record["Frame_fin"] = buscar_frame(frame_end_seconds)

            selected_display = _resolve_display_name(selected_stem)
            selected_score = None
            if selected_stem:
                entry_sel = _find_smartscore_for_image(selected_stem, smartscore_map)
                if entry_sel:
                    selected_display, selected_score = entry_sel

            record["Producto Seleccionado"] = selected_display

            smartscore_nombre_rec = recommended_display or ""
            smartscore_valor_rec = recommended_score
            if not smartscore_nombre_rec and screen_products:
                entry_rec = _find_smartscore_for_image(screen_products[0], smartscore_map)
                if entry_rec:
                    smartscore_nombre_rec, smartscore_valor_rec = entry_rec

            record["SmartScore · Producto Seleccionado"] = selected_display or ""
            record["SmartScore · Puntaje Seleccionado"] = selected_score
            record["SmartScore · Producto Recomendado"] = smartscore_nombre_rec
            record["SmartScore · Puntaje Recomendado"] = smartscore_valor_rec

            if mode == "Sequential" and seq_metrics:
                record.update(seq_metrics)

            if mode == "A/B":
                record["Tiempo comparación A/B · Par 1 (s)"] = (
                    stage_durations.get("pair_1")
                    if pantalla_id == "A/B-Par1"
                    else None
                )
                record["Tiempo comparación A/B · Par 2 (s)"] = (
                    stage_durations.get("pair_2")
                    if pantalla_id == "A/B-Par2"
                    else None
                )
                record["Tiempo comparación A/B · Final (s)"] = (
                    stage_durations.get("final")
                    if pantalla_id == "A/B-Final"
                    else None
                )

            if smartscore_enabled and recommended_display:
                atn = calcular_atencion_recomendado(
                    aois, gaze_history, recommended_display
                )
            else:
                atn = default_atn

            record["Atencion_Recomendado_Tiempo"] = atn["tiempo"]
            record["Atencion_Recomendado_Fijaciones"] = atn["fijaciones"]
            record["Atencion_Recomendado_PrimeraMirada"] = atn["primera_mirada"]
            record["AOIs"] = json.dumps(aois, ensure_ascii=False)

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


def _get_mode_recommended_product(
    mode_state: dict, smartscore_map: dict[str, float]
) -> tuple[Optional[str], Optional[str], Optional[float]]:
    cached_display = mode_state.get("mode_recommended_display")
    cached_stem = mode_state.get("mode_recommended_stem")
    cached_score = mode_state.get("mode_recommended_score")

    if cached_display and cached_stem and isinstance(cached_score, (int, float)):
        return cached_display, cached_stem, float(cached_score)

    images: list[Path] = mode_state.get("images", []) or []
    best_entry = _select_highest_smartscore_product(images, smartscore_map)
    if not best_entry:
        return None, None, None

    best_display, best_score = best_entry
    best_stem: Optional[str] = None
    for image_path in images:
        entry = _find_smartscore_for_image(image_path.stem, smartscore_map)
        if entry and entry[0] == best_display:
            best_stem = image_path.stem
            break

    mode_state["mode_recommended_display"] = best_display
    mode_state["mode_recommended_stem"] = best_stem
    mode_state["mode_recommended_score"] = best_score
    return best_display, best_stem, best_score


def _select_highest_smartscore_from_names(
    product_names: list[str], smartscore_map: dict[str, float]
) -> Optional[tuple[str, float]]:
    best_entry: Optional[tuple[str, float]] = None
    best_score = float("-inf")
    for name in product_names:
        if not name:
            continue
        entry = _find_smartscore_for_image(name, smartscore_map)
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


def guardar_excel_en_github(
    bytes_excel: bytes, id_participante: str, filename: str
) -> bool:
    if not id_participante:
        st.error("No se encontró el ID del participante para guardar en GitHub.")
        return False

    try:
        github_client = Github(st.secrets["GITHUB_TOKEN"])
        repo = github_client.get_repo(REPO_FULL_NAME)
    except KeyError:
        st.error("No se configuró el token de GitHub en st.secrets.")
        return False
    except GithubException as gh_error:
        datos_error = getattr(gh_error, "data", {})
        mensaje_error = (
            datos_error.get("message", str(gh_error))
            if isinstance(datos_error, dict)
            else str(gh_error)
        )
        st.error(f"❌ Error al conectar con GitHub: {mensaje_error}")
        return False
    except Exception as generic_error:
        st.error(f"❌ Error al conectar con GitHub: {generic_error}")
        return False

    folder = f"data_participantes/{id_participante}"
    path = f"{folder}/{filename}"

    try:
        existing_file = repo.get_contents(path)
    except GithubException as gh_error:
        if getattr(gh_error, "status", None) == 404:
            try:
                repo.create_file(
                    path,
                    "Create experiment data",
                    bytes_excel,
                    branch="main",
                )
                st.success(
                    f"Archivo guardado automáticamente en GitHub para el participante {id_participante}"
                )
                return True
            except GithubException as create_error:
                datos_error = getattr(create_error, "data", {})
                mensaje_error = (
                    datos_error.get("message", str(create_error))
                    if isinstance(datos_error, dict)
                    else str(create_error)
                )
                st.error(
                    f"❌ Error al crear el archivo en GitHub: {mensaje_error}"
                )
                return False
            except Exception as generic_error:
                st.error(f"❌ Error al crear el archivo en GitHub: {generic_error}")
                return False
        datos_error = getattr(gh_error, "data", {})
        mensaje_error = (
            datos_error.get("message", str(gh_error))
            if isinstance(datos_error, dict)
            else str(gh_error)
        )
        st.error(f"❌ Error al acceder al archivo en GitHub: {mensaje_error}")
        return False
    except Exception as generic_error:
        st.error(f"❌ Error al acceder al archivo en GitHub: {generic_error}")
        return False

    try:
        repo.update_file(
            path,
            "Update experiment data",
            bytes_excel,
            existing_file.sha,
            branch="main",
        )
        st.success(
            f"Archivo guardado automáticamente en GitHub para el participante {id_participante}"
        )
        return True
    except GithubException as update_error:
        datos_error = getattr(update_error, "data", {})
        mensaje_error = (
            datos_error.get("message", str(update_error))
            if isinstance(datos_error, dict)
            else str(update_error)
        )
        st.error(f"❌ Error al actualizar el archivo en GitHub: {mensaje_error}")
        return False
    except Exception as generic_error:
        st.error(f"❌ Error al actualizar el archivo en GitHub: {generic_error}")
        return False


def _sanitize_participant_id(df_app: pd.DataFrame) -> str:
    """Return a safe identifier for filenames based on the participant ID."""

    if "ID_Participante" not in df_app.columns or df_app.empty:
        return "sin_id"

    raw_value = df_app["ID_Participante"].iloc[0]
    if pd.isna(raw_value):
        return "sin_id"

    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", str(raw_value).strip())
    sanitized = sanitized.strip("_")
    return sanitized or "sin_id"


def _parse_aoi_payload(aoi_payload) -> dict[str, dict]:
    if aoi_payload is None or (isinstance(aoi_payload, float) and np.isnan(aoi_payload)):
        return {}
    parsed = aoi_payload
    if isinstance(aoi_payload, str):
        aoi_payload = aoi_payload.strip()
        if not aoi_payload:
            return {}
        try:
            parsed = json.loads(aoi_payload)
        except json.JSONDecodeError:
            return {}
    if isinstance(parsed, list):
        result: dict[str, dict] = {}
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name") or entry.get("producto") or entry.get("Producto")
            if not name:
                continue
            result[str(name)] = entry
        return result
    if isinstance(parsed, dict):
        return parsed
    return {}


def _first_float(data: dict, keys: list[str]) -> Optional[float]:
    for key in keys:
        if key in data and data[key] is not None:
            try:
                return float(data[key])
            except (TypeError, ValueError):
                continue
    return None


def _aoi_bounds_from_dict(raw_data: dict) -> Optional[dict[str, float]]:
    if not isinstance(raw_data, dict):
        return None
    x_min = _first_float(raw_data, ["x_min", "xmin", "left", "x"])
    y_min = _first_float(raw_data, ["y_min", "ymin", "top", "y"])
    x_max = _first_float(raw_data, ["x_max", "xmax", "right"])
    y_max = _first_float(raw_data, ["y_max", "ymax", "bottom"])
    width = _first_float(raw_data, ["width", "ancho"])
    height = _first_float(raw_data, ["height", "alto"])
    if x_min is None or y_min is None:
        return None
    if x_max is None and width is not None:
        x_max = x_min + width
    if y_max is None and height is not None:
        y_max = y_min + height
    if x_max is None or y_max is None:
        return None
    return {
        "x_min": min(x_min, x_max),
        "x_max": max(x_min, x_max),
        "y_min": min(y_min, y_max),
        "y_max": max(y_min, y_max),
    }


def _normalize_aoi_block(raw_value, row_number: int) -> dict[str, dict[str, float]]:
    if raw_value is None or (isinstance(raw_value, float) and np.isnan(raw_value)):
        return {}
    try:
        parsed = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict) or not parsed:
        return {}

    def _normalize_bounds(bounds) -> Optional[dict[str, float]]:
        if isinstance(bounds, dict):
            return _aoi_bounds_from_dict(bounds)
        if isinstance(bounds, (list, tuple)) and len(bounds) >= 4:
            try:
                x1, y1, x2, y2 = [float(value) for value in bounds[:4]]
            except (TypeError, ValueError):
                return None
            return {
                "x_min": min(x1, x2),
                "x_max": max(x1, x2),
                "y_min": min(y1, y2),
                "y_max": max(y1, y2),
            }
        return None

    cleaned: dict[str, dict[str, float]] = {}
    treat_as_flat = all(_normalize_bounds(bounds) for bounds in parsed.values())
    if treat_as_flat:
        block_entries: dict[str, dict[str, float]] = {}
        for name, bounds in parsed.items():
            normalized = _normalize_bounds(bounds)
            if normalized:
                block_entries[str(name)] = normalized
        if block_entries:
            cleaned["default"] = block_entries
        return cleaned

    for block_name, block_data in parsed.items():
        if not isinstance(block_data, dict):
            continue
        normalized_block: dict[str, dict[str, float]] = {}
        for aoi_name, bounds in block_data.items():
            normalized = _normalize_bounds(bounds)
            if normalized:
                normalized_block[str(aoi_name)] = normalized
        if normalized_block:
            cleaned[str(block_name)] = normalized_block
    return cleaned


def _point_inside_bounds(x: Optional[float], y: Optional[float], bounds: dict[str, float]) -> bool:
    return (
        x is not None
        and y is not None
        and bounds["x_min"] <= x <= bounds["x_max"]
        and bounds["y_min"] <= y <= bounds["y_max"]
    )


def _find_first_column(frame: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None


def _prepare_gaze_dataframe(gaze_df: pd.DataFrame) -> pd.DataFrame:
    timestamp_col = _find_first_column(
        gaze_df, ["timestamp", "gaze_timestamp", "world_timestamp", "time", "ts"]
    )
    if timestamp_col is None:
        raise ValueError(
            "gaze_positions.csv debe incluir una columna de tiempo reconocida (timestamp)."
        )

    x_col = _find_first_column(
        gaze_df, ["norm_pos_x", "x", "gaze_x", "world_x", "px", "norm_pos_x [0]"]
    )
    y_col = _find_first_column(
        gaze_df, ["norm_pos_y", "y", "gaze_y", "world_y", "py", "norm_pos_y [1]"]
    )
    conf_col = _find_first_column(
        gaze_df, ["confidence", "gaze_confidence", "probability", "conf"]
    )

    normalized = pd.DataFrame()
    normalized["timestamp"] = pd.to_numeric(gaze_df[timestamp_col], errors="coerce")
    normalized["norm_pos_x"] = (
        pd.to_numeric(gaze_df[x_col], errors="coerce") if x_col else np.nan
    )
    normalized["norm_pos_y"] = (
        pd.to_numeric(gaze_df[y_col], errors="coerce") if y_col else np.nan
    )
    if conf_col:
        normalized["confidence"] = (
            pd.to_numeric(gaze_df[conf_col], errors="coerce").fillna(0)
        )
    else:
        normalized["confidence"] = 1.0

    normalized = normalized.dropna(subset=["timestamp"]).copy()
    normalized = normalized[normalized["confidence"] >= 0.6]
    normalized = normalized.sort_values("timestamp").reset_index(drop=True)
    normalized["dt"] = normalized["timestamp"].diff().clip(lower=0, upper=1)
    normalized["dt"].fillna(0.016, inplace=True)
    return normalized


def _timestamp_from_frame(
    frame_value: Any, total_frames: int, world_ts: np.ndarray
) -> Optional[float]:
    try:
        frame_index = int(frame_value)
    except (TypeError, ValueError):
        return None
    if frame_index < 0 or frame_index >= total_frames:
        return None
    timestamp = world_ts[frame_index]
    if not np.isfinite(timestamp):
        return None
    return float(timestamp)


def integrate_app_with_pupil(
    excel_df,
    gaze_df,
    world_ts,
    blink_df=None,
    pupil_df=None,
    export_info_df=None,
):
    world_array = np.asarray(world_ts).flatten()
    if world_array.size == 0:
        raise ValueError("Archivo world_timestamps.npy vacío o inválido.")

    gaze_clean = _prepare_gaze_dataframe(gaze_df)
    total_frames = world_array.shape[0]

    framewise_rows: list[dict[str, Any]] = []
    per_screen_rows: list[dict[str, Any]] = []
    screen_intervals: list[tuple[str, float, float]] = []

    for idx, row in excel_df.iterrows():
        mode = str(row.get("Modo", "")).strip() or "Desconocido"
        pantalla_id = str(row.get("Pantalla_ID") or "").strip()
        if not pantalla_id:
            continue

        aois_by_screen = _normalize_aoi_block(row.get("AOIs"), idx + 1)
        block_aois = aois_by_screen.get(pantalla_id) or {}
        if not block_aois:
            continue

        t_start = _timestamp_from_frame(row.get("Frame_inicio"), total_frames, world_array)
        t_end = _timestamp_from_frame(row.get("Frame_fin"), total_frames, world_array)
        if t_start is None or t_end is None or t_end < t_start:
            continue

        screen_duration = float(t_end - t_start)
        screen_intervals.append((mode, t_start, t_end))

        segment = gaze_clean[
            (gaze_clean["timestamp"] >= t_start)
            & (gaze_clean["timestamp"] <= t_end)
        ].copy()

        for _, gaze_point in segment.iterrows():
            aoi_hit = None
            for aoi_name, bounds in block_aois.items():
                if _point_inside_bounds(
                    gaze_point.get("norm_pos_x"),
                    gaze_point.get("norm_pos_y"),
                    bounds,
                ):
                    aoi_hit = aoi_name
                    break
            framewise_rows.append(
                {
                    "timestamp": gaze_point["timestamp"],
                    "norm_pos_x": gaze_point.get("norm_pos_x"),
                    "norm_pos_y": gaze_point.get("norm_pos_y"),
                    "dt": gaze_point.get("dt", 0.0),
                    "AOI": aoi_hit,
                    "Modo": mode,
                    "Pantalla_ID": pantalla_id,
                    "Pantalla": row.get("Pantalla", ""),
                    "Producto_Seleccionado": row.get("Producto Seleccionado", ""),
                }
            )

        for aoi_name, bounds in block_aois.items():
            mask = segment.apply(
                lambda p: _point_inside_bounds(
                    p.get("norm_pos_x"), p.get("norm_pos_y"), bounds
                ),
                axis=1,
            ) if not segment.empty else pd.Series(dtype=bool)

            dwell_time = float(segment.loc[mask, "dt"].sum()) if not segment.empty else 0.0
            fixations = int(mask.sum()) if not segment.empty else 0
            tff = (
                float(segment.loc[mask, "timestamp"].min())
                if not segment.empty and mask.any()
                else np.nan
            )
            product, component = (
                aoi_name.split("_", 1) + [""] if "_" in aoi_name else [aoi_name, ""]
            )[:2]
            per_screen_rows.append(
                {
                    "Modo": mode,
                    "Pantalla_ID": pantalla_id,
                    "Pantalla": row.get("Pantalla", ""),
                    "AOI": aoi_name,
                    "Producto": product,
                    "Componente": component,
                    "Dwell_Time": dwell_time,
                    "Fixaciones": fixations,
                    "TFF": tff,
                    "Segment_Duration": screen_duration,
                    "Frame_inicio": row.get("Frame_inicio"),
                    "Frame_fin": row.get("Frame_fin"),
                }
            )

    df_framewise = (
        pd.DataFrame(framewise_rows)
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    df_per_screen = (
        pd.DataFrame(per_screen_rows)
        .sort_values(["Modo", "Pantalla_ID", "AOI"])
        .reset_index(drop=True)
    )

    if not df_per_screen.empty:
        df_per_mode = (
            df_per_screen.groupby("Modo", as_index=False)
            .agg(
                {
                    "Dwell_Time": "sum",
                    "Fixaciones": "sum",
                    "TFF": "min",
                    "Segment_Duration": "sum",
                }
            )
            .rename(columns={"Segment_Duration": "Total_Duration"})
            .sort_values("Modo")
            .reset_index(drop=True)
        )
    else:
        df_per_mode = pd.DataFrame(
            columns=["Modo", "Dwell_Time", "Fixaciones", "TFF", "Total_Duration"]
        )

    blink_results = pd.DataFrame()
    if blink_df is not None:
        blink_start_col = _find_first_column(
            blink_df,
            [
                "start_timestamp",
                "start_time",
                "start",
                "t_start",
                "timestamp_start",
            ],
        )
        blink_end_col = _find_first_column(
            blink_df,
            ["end_timestamp", "end_time", "end", "t_end", "timestamp_end"],
        )
        if blink_start_col and blink_end_col:
            blinks = blink_df[[blink_start_col, blink_end_col]].copy()
            blinks.columns = ["start", "end"]
            blinks = blinks.dropna()
            per_mode_counts: list[dict[str, Any]] = []
            for mode, start_ts, end_ts in screen_intervals:
                duration = max(0.0, end_ts - start_ts)
                overlap_count = 0
                for _, blink in blinks.iterrows():
                    blink_start = float(blink["start"])
                    blink_end = float(blink["end"])
                    overlap_start = max(start_ts, blink_start)
                    overlap_end = min(end_ts, blink_end)
                    if overlap_end > overlap_start:
                        overlap_count += 1
                per_mode_counts.append(
                    {
                        "Modo": mode,
                        "Blinks": overlap_count,
                        "Duration": duration,
                    }
                )
            blink_results = pd.DataFrame(per_mode_counts)
            if not blink_results.empty:
                blink_results = (
                    blink_results.groupby("Modo", as_index=False)
                    .agg({"Blinks": "sum", "Duration": "sum"})
                    .assign(
                        Blink_Rate_Hz=lambda df: df.apply(
                            lambda r: r["Blinks"] / r["Duration"]
                            if r["Duration"] > 0
                            else np.nan,
                            axis=1,
                        )
                    )
                    .sort_values("Modo")
                    .reset_index(drop=True)
                )

    results = {
        "df_app": excel_df,
        "framewise_gaze": df_framewise,
        "per_screen": df_per_screen,
        "per_mode": df_per_mode,
        "blinks_per_mode": blink_results,
    }

    if isinstance(pupil_df, pd.DataFrame):
        results["pupil_raw"] = pupil_df
    if isinstance(export_info_df, pd.DataFrame):
        results["export_info"] = export_info_df

    return results


def export_final_excel(results_dict) -> bytes:
    buffer = BytesIO()
    sheet_order = [
        ("Resumen_App", results_dict.get("excel_resumen") or results_dict.get("df_app")),
        ("Gaze_Framewise", results_dict.get("framewise_gaze")),
        ("AOI_Por_Pantalla", results_dict.get("per_screen")),
        ("AOI_Por_Modo", results_dict.get("per_mode")),
    ]

    if isinstance(results_dict.get("blinks_per_mode"), pd.DataFrame):
        sheet_order.append(("Blinks_Por_Modo", results_dict.get("blinks_per_mode")))
    if isinstance(results_dict.get("pupil_raw"), pd.DataFrame):
        sheet_order.append(("Pupil_Raw", results_dict.get("pupil_raw")))
    if isinstance(results_dict.get("export_info"), pd.DataFrame):
        sheet_order.append(("Export_Info", results_dict.get("export_info")))

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, df_value in sheet_order:
            if isinstance(df_value, pd.DataFrame) and not df_value.empty:
                df_value.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)

    buffer.seek(0)
    return buffer.getvalue()


def _get_github_repo_instance():
    if "GITHUB_TOKEN" not in st.secrets:
        st.error("No se configuró el token de GitHub en st.secrets.")
        return None
    try:
        github_client = Github(st.secrets["GITHUB_TOKEN"])
        return github_client.get_repo(REPO_FULL_NAME)
    except GithubException as gh_error:
        datos_error = getattr(gh_error, "data", {})
        mensaje_error = (
            datos_error.get("message", str(gh_error))
            if isinstance(datos_error, dict)
            else str(gh_error)
        )
        st.error(f"❌ Error al conectar con GitHub: {mensaje_error}")
    except Exception as generic_error:
        st.error(f"❌ Error al conectar con GitHub: {generic_error}")
    return None


def _list_github_participants(repo, force_refresh: bool = False) -> list[str]:
    cache_key = "admin_participant_ids"
    if not force_refresh and st.session_state.get(cache_key):
        return st.session_state[cache_key]

    if repo is None:
        return []

    try:
        contents = repo.get_contents("data_participantes")
        ids = sorted([item.name for item in contents if item.type == "dir"])
        st.session_state[cache_key] = ids
        return ids
    except GithubException as gh_error:
        if getattr(gh_error, "status", None) == 404:
            st.error("No se encontró la carpeta 'data_participantes' en el repositorio.")
            return []
        datos_error = getattr(gh_error, "data", {})
        mensaje_error = (
            datos_error.get("message", str(gh_error))
            if isinstance(datos_error, dict)
            else str(gh_error)
        )
        st.error(f"❌ Error al listar participantes: {mensaje_error}")
    except Exception as generic_error:
        st.error(f"❌ Error inesperado al listar participantes: {generic_error}")
    return []


def _expected_participant_files(participant_id: str) -> dict[str, str]:
    base = f"data_participantes/{participant_id}"
    return {
        "excel_experimento": f"{base}/experimento_{participant_id}.xlsx",
        "gaze": f"{base}/gaze_positions.csv",
        "timestamps": f"{base}/world_timestamps.npy",
        "blinks": f"{base}/blink_detection_report.csv",
        "pupil": f"{base}/pupil_positions.csv",
        "export_info": f"{base}/export_info.csv",
        "video": f"{base}/world.mp4",
        "excel_final": f"{base}/analisis_final_{participant_id}.xlsx",
    }


def _check_participant_files(repo, participant_id: str, force_refresh: bool = False):
    cache_key = "admin_status_cache"
    cache = st.session_state.setdefault(cache_key, {})
    if not force_refresh and cache.get(participant_id):
        return cache[participant_id]

    status: dict[str, dict[str, Any]] = {}
    expected_files = _expected_participant_files(participant_id)

    if repo is None:
        return status

    for key, path in expected_files.items():
        try:
            contents = repo.get_contents(path)
            status[key] = {"exists": True, "path": path, "sha": contents.sha}
        except GithubException as gh_error:
            if getattr(gh_error, "status", None) == 404:
                status[key] = {"exists": False, "path": path, "sha": None}
            else:
                datos_error = getattr(gh_error, "data", {})
                mensaje_error = (
                    datos_error.get("message", str(gh_error))
                    if isinstance(datos_error, dict)
                    else str(gh_error)
                )
                st.error(f"❌ Error al verificar {path}: {mensaje_error}")
                status[key] = {"exists": False, "path": path, "sha": None}
        except Exception as generic_error:
            st.error(f"❌ Error inesperado al verificar {path}: {generic_error}")
            status[key] = {"exists": False, "path": path, "sha": None}

    cache[participant_id] = status
    st.session_state[cache_key] = cache
    return status


def _upload_to_repo(repo, path: str, content_bytes: bytes, existing_sha: Optional[str] = None) -> bool:
    if repo is None:
        return False
    try:
        if existing_sha:
            repo.update_file(path, "Actualiza archivo de participante", content_bytes, existing_sha, branch="main")
        else:
            repo.create_file(path, "Agrega archivo de participante", content_bytes, branch="main")
        return True
    except GithubException as gh_error:
        datos_error = getattr(gh_error, "data", {})
        mensaje_error = (
            datos_error.get("message", str(gh_error))
            if isinstance(datos_error, dict)
            else str(gh_error)
        )
        st.error(f"❌ Error al subir {path}: {mensaje_error}")
    except Exception as generic_error:
        st.error(f"❌ Error inesperado al subir {path}: {generic_error}")
    return False


def _download_repo_file(repo, path: str) -> tuple[Optional[bytes], Optional[str]]:
    if repo is None:
        return None, None
    try:
        contents = repo.get_contents(path)
        return base64.b64decode(contents.content), contents.sha
    except GithubException as gh_error:
        if getattr(gh_error, "status", None) != 404:
            datos_error = getattr(gh_error, "data", {})
            mensaje_error = (
                datos_error.get("message", str(gh_error))
                if isinstance(datos_error, dict)
                else str(gh_error)
            )
            st.error(f"❌ Error al descargar {path}: {mensaje_error}")
    except Exception as generic_error:
        st.error(f"❌ Error inesperado al descargar {path}: {generic_error}")
    return None, None


def _load_results_dataframe(repo, force_refresh: bool = False) -> tuple[pd.DataFrame, Optional[str]]:
    cache_key = "admin_results_cache"
    cache = st.session_state.get(cache_key)
    if not force_refresh and isinstance(cache, dict):
        cached_df = cache.get("df")
        cached_sha = cache.get("sha")
        if isinstance(cached_df, pd.DataFrame):
            return cached_df, cached_sha

    if repo is None:
        return pd.DataFrame(), None

    try:
        contents = repo.get_contents(RESULTS_PATH_IN_REPO)
        excel_bytes = base64.b64decode(contents.content)
        df = pd.read_excel(BytesIO(excel_bytes))
        df = _reorder_person_columns(df)
        st.session_state[cache_key] = {"df": df, "sha": contents.sha}
        return df, contents.sha
    except GithubException as gh_error:
        status = getattr(gh_error, "status", None)
        if status == 404:
            st.error("No se encontró 'Resultados_SmartScore.xlsx' en el repositorio.")
        else:
            datos_error = getattr(gh_error, "data", {})
            mensaje_error = (
                datos_error.get("message", str(gh_error))
                if isinstance(datos_error, dict)
                else str(gh_error)
            )
            st.error(
                f"❌ Error al leer 'Resultados_SmartScore.xlsx' desde GitHub: {mensaje_error}"
            )
    except Exception as generic_error:
        st.error(
            f"❌ Error inesperado al leer 'Resultados_SmartScore.xlsx': {generic_error}"
        )

    return pd.DataFrame(), None


def _save_results_dataframe(
    repo, df: pd.DataFrame, sha: Optional[str], message: str
) -> bool:
    if repo is None:
        return False
    if not sha:
        st.error("No se pudo determinar la versión actual del archivo en GitHub.")
        return False

    try:
        repo.update_file(
            RESULTS_PATH_IN_REPO,
            message,
            _df_to_excel_bytes(_reorder_person_columns(df)),
            sha,
            branch="main",
        )
        return True
    except GithubException as gh_error:
        datos_error = getattr(gh_error, "data", {})
        mensaje_error = (
            datos_error.get("message", str(gh_error))
            if isinstance(datos_error, dict)
            else str(gh_error)
        )
        st.error(
            "❌ No se pudo guardar el Excel de resultados en GitHub. "
            f"Detalle: {mensaje_error}"
        )
    except Exception as generic_error:
        st.error(
            "❌ Ocurrió un error inesperado al guardar el Excel de resultados. "
            f"Detalle: {generic_error}"
        )
    return False


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
        repo = github_client.get_repo(REPO_FULL_NAME)
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
    st.markdown(f"**{t('tab1_context_title')}**")
    st.info(t("tab1_context_body"))

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
                key="w_portion",
            )
            w_diet = st.slider(
                t("slider_diet"),
                0,
                7,
                key="w_diet",
            )
            w_salt = st.slider(
                t("slider_salt"),
                0,
                5,
                key="w_salt",
            )
            w_fat = st.slider(
                t("slider_fat"),
                0,
                5,
                key="w_fat",
            )
        with col2:
            w_natural = st.slider(
                t("slider_natural"),
                0,
                5,
                key="w_natural",
            )
            w_convenience = st.slider(
                t("slider_convenience"),
                0,
                5,
                key="w_convenience",
            )
            w_price = st.slider(
                t("slider_price"),
                0,
                5,
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

        feedback = st.session_state.get("auto_assignment_feedback")
        if feedback:
            feedback_type, feedback_message = feedback
            if feedback_type == "success":
                st.success(feedback_message)
            else:
                st.warning(feedback_message)
            st.session_state["auto_assignment_feedback"] = None

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
                    repo = github_client.get_repo(REPO_FULL_NAME)
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
                        assignment_feedback = None
                        try:
                            resultado_asignacion = asignar_grupos_experimentales()
                        except Exception as assignment_error:
                            assignment_feedback = (
                                "warning",
                                f"No se pudo reequilibrar 'Grupo_Experimental': {assignment_error}",
                            )
                        else:
                            if resultado_asignacion.get("status") == "ok":
                                assignment_feedback = (
                                    "success",
                                    "'Grupo_Experimental' reequilibrado para todos los participantes.",
                                )
                            else:
                                assignment_feedback = (
                                    "warning",
                                    resultado_asignacion.get(
                                        "msg",
                                        "No se pudo completar el reequilibrio de grupos.",
                                    ),
                                )
                        finally:
                            if assignment_feedback:
                                st.session_state["auto_assignment_feedback"] = assignment_feedback
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
                excel_bytes = _experiment_results_to_excel_bytes(result_df)
                participant_id = st.session_state.get("tab2_user_id", "")
                upload_key = f"github_upload_{participant_id}"
                if not st.session_state.get(upload_key, False):
                    excel_filename = f"experimento_{participant_id}.xlsx"
                    upload_success = guardar_excel_en_github(
                        excel_bytes, participant_id, excel_filename
                    )
                    st.session_state[upload_key] = upload_success
                st.download_button(
                    t("tab2_download_results"),
                    data=excel_bytes,
                    file_name=download_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.info(t("tab2_no_data_info"))

            if st.button(t("tab2_restart_experiment"), key="restart_experiment"):
                _reset_visual_experiment_state()
                st.session_state["experiment_start_time"] = datetime.now()
                st.session_state["experiment_end_time"] = None
                _trigger_streamlit_rerun()

            tab2_can_continue = False

    selection_made = False
    is_last_mode = True
    current_mode: Optional[str] = None

    if tab2_can_continue:
        total_modes = len(sequence)
        current_index = st.session_state.get("current_mode_index", 0)
        current_index = max(0, min(current_index, total_modes - 1))
        st.session_state["current_mode_index"] = current_index
        current_mode = sequence[current_index]
        is_last_mode = current_index == total_modes - 1

        _ensure_mode_started(current_mode)
        mode_sessions = st.session_state.get("mode_sessions", {})
        current_state = mode_sessions.get(current_mode, {})

        images = current_state.get("images", [])
        smartscore_map = st.session_state.get("tab2_smartscore_map", {})
        (
            recommended_display,
            recommended_stem,
            recommended_score,
        ) = _get_mode_recommended_product(current_state, smartscore_map)
        mode_sessions[current_mode] = current_state
        st.session_state["mode_sessions"] = mode_sessions

        info_message = t(
            "tab2_mode_info",
            current=current_index + 1,
            total=total_modes,
            mode=current_mode,
        )

        ab_stage = current_state.get("ab_stage", 0)
        ab_finalists = current_state.get("ab_final_options", [])
        inline_stage_messages = []
        block_stage_messages = []

        next_clicked = False

        if current_mode == "A/B" and len(images) >= 4:
            _ensure_ab_stage_started(current_state)
            mode_sessions[current_mode] = current_state
            st.session_state["mode_sessions"] = mode_sessions

            ab_stage = current_state.get("ab_stage", ab_stage)
            ab_finalists = current_state.get("ab_final_options", ab_finalists)

            if ab_stage == 0:
                block_stage_messages.append(t("tab2_ab_step_one"))
            elif ab_stage == 1:
                block_stage_messages.append(t("tab2_ab_step_two"))
            else:
                if len(ab_finalists) == 2:
                    first_finalist = ab_finalists[0].replace("_", " ")
                    second_finalist = ab_finalists[1].replace("_", " ")
                    block_stage_messages.append(
                        t(
                            "tab2_ab_finalists",
                            first=first_finalist,
                            second=second_finalist,
                        )
                    )
                if not current_state.get("selected"):
                    block_stage_messages.append(t("tab2_ab_step_three"))

        if current_mode == "Grid":
            inline_stage_messages.append(t("tab2_grid_instruction"))
        elif current_mode == "Sequential":
            inline_stage_messages.append(t("tab2_seq_instruction"))

        if inline_stage_messages:
            info_message = f"{info_message}  " + "  ".join(inline_stage_messages)

        if block_stage_messages:
            separator = "\n\n" if inline_stage_messages else "\n\n"
            info_message = f"{info_message}{separator}" + "\n".join(block_stage_messages)

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
                    visible_paths: list[Path] = [
                        images[image_index]
                        for image_index in display_indexes
                        if 0 <= image_index < len(images)
                    ]
                    recommended_in_view = any(
                        image_path.stem == recommended_stem
                        for image_path in visible_paths
                    )
                    highlighted_product = (
                        recommended_display if recommended_in_view else None
                    )
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
                    highlighted_product = None
                    if recommended_stem:
                        for image_path in images:
                            if image_path.stem == recommended_stem:
                                highlighted_product = recommended_display
                                break
                    current_state["producto_recomendado"] = highlighted_product
                    mode_sessions[current_mode] = current_state
                    st.session_state["mode_sessions"] = mode_sessions
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
                highlighted_product = None
                if recommended_stem and current_image.stem == recommended_stem:
                    highlighted_product = recommended_display
                current_state["producto_recomendado"] = highlighted_product
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
                    st.caption(t("tab2_seq_confirm_instruction"))
                    if st.button(
                        t("tab2_confirm_selection"),
                        key=f"confirm_{current_mode}_{index}",
                        use_container_width=True,
                    ):
                        current_state["seq_selection_confirmed"] = True
                        mode_sessions[current_mode] = current_state
                        st.session_state["mode_sessions"] = mode_sessions
                        if is_last_mode:
                            if not st.session_state.get("experiment_completed"):
                                _complete_visual_experiment(usuario_activo)
                        else:
                            _advance_visual_mode()
                        _trigger_streamlit_rerun()

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
                    current_state["seq_selection_confirmed"] = False
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

        if current_mode == "Sequential":
            selection_made = bool(current_state.get("seq_selection_confirmed"))
        else:
            selection_made = bool(current_state.get("selected"))

    if tab2_can_continue and current_mode and current_mode != "Sequential":
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




with tab_admin:
    st.header("🛠️ Panel de Administración")
    st.session_state.setdefault("admin_authenticated", False)
    st.session_state.setdefault("analysis_result", None)

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

    repo = _get_github_repo_instance()
    participant_ids = _list_github_participants(repo)

    tab_delete, tab_participants = st.tabs(
        ["🗑️ Eliminar participantes", "👥 Participantes disponibles"]
    )

    with tab_delete:
        st.markdown("### 🗑️ Eliminar participantes de Resultados_SmartScore.xlsx")
        refresh_results = st.button(
            "🔄 Refrescar resultados", key="refresh_results_excel"
        )
        results_df, results_sha = _load_results_dataframe(
            repo, force_refresh=refresh_results
        )

        if results_df.empty:
            st.info(
                "Aún no hay registros para mostrar o no se pudo leer el Excel de resultados."
            )
        else:
            display_columns = [
                col
                for col in [
                    "Nombre Completo",
                    "ID_Participante",
                    "Fecha",
                    "Edad",
                    "Género",
                    "Grupo_Experimental",
                ]
                if col in results_df.columns
            ]

            st.dataframe(
                results_df[display_columns] if display_columns else results_df,
                use_container_width=True,
                hide_index=True,
            )

            with st.form("delete_results_participant"):
                st.markdown("#### Selecciona el registro que deseas eliminar")

                def _format_result_option(idx_value):
                    fila = results_df.loc[idx_value]
                    nombre = str(fila.get("Nombre Completo", "")).strip() or "Sin nombre"
                    participante_id = str(fila.get("ID_Participante", "")).strip()
                    fecha_valor = str(fila.get("Fecha", "")).strip()
                    partes = [nombre]
                    if participante_id:
                        partes.append(participante_id)
                    if fecha_valor:
                        partes.append(fecha_valor)
                    return " · ".join(partes)

                opciones = list(results_df.index)
                seleccion = st.selectbox(
                    "Registro a eliminar",
                    opciones,
                    format_func=_format_result_option,
                    key="admin_delete_results_selection",
                )

                if seleccion is not None:
                    st.caption("Registro seleccionado:")
                    st.dataframe(
                        results_df.loc[[seleccion]],
                        hide_index=True,
                        use_container_width=True,
                    )

                confirmar = st.checkbox(
                    "Confirmo que deseo eliminar este participante del Excel",
                    key="admin_confirm_delete_results",
                )
                eliminar = st.form_submit_button(
                    "Eliminar del Excel de resultados",
                    disabled=seleccion is None,
                )

                if eliminar:
                    if not confirmar:
                        st.warning(
                            "Marca la casilla de confirmación para continuar con la eliminación."
                        )
                    else:
                        df_actualizado = results_df.drop(index=seleccion).reset_index(
                            drop=True
                        )
                        guardado = _save_results_dataframe(
                            repo,
                            df_actualizado,
                            results_sha,
                            "Elimina participante desde panel de administración",
                        )
                        if guardado:
                            st.success(
                                "Participante eliminado del archivo 'Resultados_SmartScore.xlsx'."
                            )
                            st.session_state.pop("admin_results_cache", None)
                            _trigger_streamlit_rerun()

    with tab_participants:
        st.subheader("👥 Participantes disponibles")
        cols_top = st.columns([3, 1])
        with cols_top[0]:
            selected_id = st.selectbox(
                "Selecciona un participante",
                participant_ids,
                index=0 if participant_ids else None,
                key="admin_selected_participant",
            )
        with cols_top[1]:
            if st.button("🔄 Refrescar lista"):
                participant_ids = _list_github_participants(repo, force_refresh=True)
                st.session_state.pop("admin_status_cache", None)
                _trigger_streamlit_rerun()

        if st.session_state.get("analysis_participant") != selected_id:
            st.session_state["analysis_participant"] = selected_id
            st.session_state.pop("analysis_result", None)
            st.session_state.pop("analysis_final_excel", None)
            st.session_state.pop("analysis_video", None)
    
        if not selected_id:
            st.info("Selecciona un participante para revisar sus archivos.")
            st.stop()
    
        status_map = _check_participant_files(repo, selected_id)
        expected_paths = _expected_participant_files(selected_id)
    
        st.markdown("### 📑 Estado de archivos del participante")
        file_labels = {
            "excel_experimento": f"experimento_{selected_id}.xlsx",
            "gaze": "gaze_positions.csv",
            "timestamps": "world_timestamps.npy",
            "blinks": "blink_detection_report.csv",
            "pupil": "pupil_positions.csv",
            "export_info": "export_info.csv",
            "video": "world.mp4",
            "excel_final": f"analisis_final_{selected_id}.xlsx",
        }
    
        status_rows = []
        for key, label in file_labels.items():
            exists = status_map.get(key, {}).get("exists", False)
            symbol = "✔️" if exists else "❌"
            status_rows.append({"Archivo": label, "Estado": symbol})
        st.dataframe(pd.DataFrame(status_rows), hide_index=True)
    
        st.markdown("### ⬆️ Subir/actualizar archivos de Pupil Labs")
        st.caption("Carga los archivos faltantes o reemplaza los existentes. Se guardan directamente en GitHub.")
    
        upload_fields = [
            ("gaze", "gaze_positions.csv", ["csv"], False),
            ("timestamps", "world_timestamps.npy", ["npy"], False),
            ("blinks", "blink_detection_report.csv", ["csv"], True),
            ("pupil", "pupil_positions.csv", ["csv"], True),
            ("export_info", "export_info.csv", ["csv"], True),
            ("video", "world.mp4", ["mp4"], True),
        ]
    
        with st.form("upload_pupil_files"):
            upload_columns = st.columns(2)
            uploaded_files: dict[str, Any] = {}
            for idx, (key, label, types, optional) in enumerate(upload_fields):
                target_col = upload_columns[idx % 2]
                with target_col:
                    exists = status_map.get(key, {}).get("exists", False)
                    prefix = "✔️" if exists else "❌"
                    st.write(f"{prefix} {label}")
                    if not exists:
                        st.warning(f"{label} no encontrado. Súbelo para continuar." , icon="⚠️")
                    uploaded_files[key] = st.file_uploader(label, type=types, key=f"uploader_{key}")
                    if optional:
                        st.caption(":gray[Opcional]")
            submitted = st.form_submit_button("💾 Guardar archivos en GitHub")
    
        if submitted:
            any_uploaded = False
            for key, file_obj in uploaded_files.items():
                if file_obj is None:
                    continue
                path = expected_paths[key]
                sha = status_map.get(key, {}).get("sha")
                success = _upload_to_repo(repo, path, file_obj.getvalue(), sha)
                if success:
                    any_uploaded = True
            if any_uploaded:
                st.success("Archivos subidos correctamente. Actualizando estado...")
                status_map = _check_participant_files(repo, selected_id, force_refresh=True)
            else:
                st.info("No se seleccionaron archivos para subir.")
    
        st.markdown("### 📊 Análisis del Experimento – Integración App + Pupil Labs")
        mandatory_keys = ["excel_experimento", "gaze", "timestamps"]
        missing = [
            file_labels[key]
            for key in mandatory_keys
            if not status_map.get(key, {}).get("exists")
        ]
    
        analysis_ready = len(missing) == 0
        if not analysis_ready:
            st.error(
                "Faltan archivos obligatorios para este participante. "
                "Sube al menos gaze_positions.csv y world_timestamps.npy para poder ejecutar el análisis."
            )
    
        run_analysis = st.button(
            "🚀 Ejecutar análisis del participante",
            disabled=not analysis_ready,
        )
    
        if run_analysis and analysis_ready:
            try:
                excel_bytes, _ = _download_repo_file(repo, expected_paths["excel_experimento"])
                gaze_bytes, _ = _download_repo_file(repo, expected_paths["gaze"])
                ts_bytes, _ = _download_repo_file(repo, expected_paths["timestamps"])
                blinks_bytes, _ = _download_repo_file(repo, expected_paths["blinks"])
                pupil_bytes, _ = _download_repo_file(repo, expected_paths["pupil"])
                export_info_bytes, _ = _download_repo_file(repo, expected_paths["export_info"])
                video_bytes, _ = _download_repo_file(repo, expected_paths["video"])
    
                excel_df = pd.read_excel(BytesIO(excel_bytes), sheet_name="Resumen")
                gaze_df = pd.read_csv(BytesIO(gaze_bytes))
                world_ts = np.load(BytesIO(ts_bytes), allow_pickle=False)
                blink_df = pd.read_csv(BytesIO(blinks_bytes)) if blinks_bytes else None
                pupil_df = pd.read_csv(BytesIO(pupil_bytes)) if pupil_bytes else None
                export_info_df = (
                    pd.read_csv(BytesIO(export_info_bytes)) if export_info_bytes else None
                )
    
                results = integrate_app_with_pupil(
                    excel_df=excel_df,
                    gaze_df=gaze_df,
                    world_ts=world_ts,
                    blink_df=blink_df,
                    pupil_df=pupil_df,
                    export_info_df=export_info_df,
                )
                results["excel_resumen"] = excel_df
                st.session_state["analysis_result"] = results
                st.session_state["analysis_video"] = video_bytes
    
                final_excel_bytes = export_final_excel(results)
                final_path = expected_paths["excel_final"]
                final_sha = status_map.get("excel_final", {}).get("sha")
                saved = _upload_to_repo(repo, final_path, final_excel_bytes, final_sha)
                if saved:
                    st.success("Análisis completado y Excel final guardado en GitHub.")
                    status_map = _check_participant_files(repo, selected_id, force_refresh=True)
                else:
                    st.warning("El Excel final no pudo guardarse en GitHub, pero puedes descargarlo abajo.")
                st.session_state["analysis_final_excel"] = final_excel_bytes
            except Exception as error:
                st.error(f"No se pudo procesar el análisis: {error}")
    
        analysis_result = st.session_state.get("analysis_result")
        if analysis_result:
            st.markdown("### 📈 Visualizaciones y métricas")
    
            framewise = analysis_result.get("framewise_gaze", pd.DataFrame())
            per_screen = analysis_result.get("per_screen", pd.DataFrame())
            per_mode = analysis_result.get("per_mode", pd.DataFrame())
            blinks_mode = analysis_result.get("blinks_per_mode", pd.DataFrame())
    
            st.markdown("#### 🔥 Heatmap simple")
            heatmap_df = framewise.dropna(subset=["norm_pos_x", "norm_pos_y"]).copy()
            if not heatmap_df.empty:
                st.scatter_chart(heatmap_df, x="norm_pos_x", y="norm_pos_y")
            else:
                st.caption(":gray[Sin muestras de gaze para graficar.]")
    
            st.markdown("#### 🛍️ Atención por producto (AOI por pantalla)")
            if not per_screen.empty:
                dwell_product = (
                    per_screen.groupby("Producto", as_index=False)["Dwell_Time"].sum()
                )
                fix_product = (
                    per_screen.groupby("Producto", as_index=False)["Fixaciones"].sum()
                )
                cols = st.columns(2)
                with cols[0]:
                    st.caption("Tiempo de observación por producto")
                    st.bar_chart(dwell_product.set_index("Producto"))
                with cols[1]:
                    st.caption("Fijaciones por producto")
                    st.bar_chart(fix_product.set_index("Producto"))
                st.dataframe(per_screen)
            else:
                st.caption(":gray[Sin métricas por pantalla disponibles.]")
    
            st.markdown("#### 🧭 Atención por modo")
            if not per_mode.empty:
                col_mode = st.columns(3)
                with col_mode[0]:
                    st.caption("Dwell time total por modo")
                    st.bar_chart(per_mode.set_index("Modo")["Dwell_Time"])
                with col_mode[1]:
                    st.caption("Fijaciones por modo")
                    st.bar_chart(per_mode.set_index("Modo")["Fixaciones"])
                with col_mode[2]:
                    st.caption("Tiempo a primera fijación (TFF)")
                    st.bar_chart(per_mode.set_index("Modo")["TFF"])
                st.dataframe(per_mode)
            else:
                st.caption(":gray[Sin métricas por modo disponibles.]")
    
            st.markdown("#### 👀 Tasa de parpadeo por modo")
            if isinstance(blinks_mode, pd.DataFrame) and not blinks_mode.empty:
                st.dataframe(blinks_mode)
                st.bar_chart(blinks_mode.set_index("Modo")["Blink_Rate_Hz"])
            else:
                st.caption(":gray[No se cargó archivo de parpadeos o no se detectaron eventos.]")
    
            if st.session_state.get("analysis_video"):
                st.markdown("#### 🎬 Vista previa de world.mp4")
                st.video(st.session_state["analysis_video"])
    
            st.markdown("### 💾 Exportar resultados")
            participant_id = _sanitize_participant_id(
                analysis_result.get("excel_resumen") or analysis_result.get("df_app")
                or pd.DataFrame()
            )
            excel_final = st.session_state.get("analysis_final_excel") or export_final_excel(
                analysis_result
            )
            st.download_button(
                "📥 Descargar Excel Final del Participante",
                data=excel_final,
                file_name=f"analisis_final_{participant_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="analysis_download_button",
            )
