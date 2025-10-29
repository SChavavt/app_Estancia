# app.py
import re
import json
import random
import base64
from io import BytesIO
from datetime import datetime
from pathlib import Path

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

VISUAL_MODE_OPTIONS = ["A/B", "Grid", "Sequential"]
VISUAL_SUBFOLDERS = {"A/B": "A_B", "Grid": "Grid", "Sequential": "Sequential"}
VALID_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
VISUAL_BASE_PATH = Path("data/images")

if "visual_mode" not in st.session_state:
    st.session_state["visual_mode"] = random.choice(VISUAL_MODE_OPTIONS)

st.session_state.setdefault("visual_images", [])
st.session_state.setdefault("visual_index", 0)

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


def _load_image_paths(folder: Path) -> list:
    if not folder.exists():
        return []
    return [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in VALID_IMAGE_EXTENSIONS
    ]


def _initialize_visual_session() -> None:
    mode = st.session_state.get("visual_mode", random.choice(VISUAL_MODE_OPTIONS))
    folder_name = VISUAL_SUBFOLDERS.get(mode)
    if folder_name is None:
        st.session_state["visual_mode"] = random.choice(VISUAL_MODE_OPTIONS)
        folder_name = VISUAL_SUBFOLDERS[st.session_state["visual_mode"]]
        mode = st.session_state["visual_mode"]
    folder = VISUAL_BASE_PATH / folder_name
    image_paths = _load_image_paths(folder)
    random.shuffle(image_paths)
    if mode == "A/B":
        selected = image_paths[:2]
    elif mode == "Grid":
        selected = image_paths[:4]
    else:
        selected = image_paths
    st.session_state["visual_images"] = selected
    st.session_state["visual_index"] = 0


def _register_visual_choice(choice_label: str) -> None:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "participant_name": st.session_state.get("nombre_completo", "").strip(),
        "mode": st.session_state.get("visual_mode", ""),
        "choice": choice_label,
        "smart_score_condition": "OFF",
    }
    st.session_state["visual_log"].append(entry)
    st.success("✅ Choice registered!")


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
    # Streamlit 1.27+ reemplaza ``st.experimental_rerun`` por ``st.rerun``.
    # Para mantener compatibilidad con versiones anteriores, intentamos usar la
    # nueva API y, si no está disponible, recurrimos al nombre experimental.
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
        return

    experimental_rerun = getattr(st, "experimental_rerun", None)
    if callable(experimental_rerun):
        experimental_rerun()
        return

    raise AttributeError("Streamlit no dispone de 'st.rerun' ni 'st.experimental_rerun'.")


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

    if st.session_state.get("visual_mode") not in VISUAL_MODE_OPTIONS:
        st.session_state["visual_mode"] = random.choice(VISUAL_MODE_OPTIONS)
        st.session_state["visual_images"] = []

    if not st.session_state.get("visual_images"):
        _initialize_visual_session()

    mode = st.session_state.get("visual_mode")
    images = st.session_state.get("visual_images", [])

    st.info(f"Modo de visualización activo: {mode}")

    if not images:
        st.warning(
            "No se encontraron imágenes para esta modalidad. Verifica la carpeta 'data/images/'."
        )
    else:
        if mode == "A/B":
            columns = st.columns(2)
            for idx, (col, image_path) in enumerate(zip(columns, images)):
                with col:
                    st.image(str(image_path), use_column_width=True)
                    st.caption(image_path.stem.replace("_", " "))
                    if st.button("Elegir este producto", key=f"choose_ab_{idx}"):
                        _register_visual_choice(image_path.stem)
        elif mode == "Grid":
            for start in range(0, len(images), 2):
                columns = st.columns(2)
                for offset, (col, image_path) in enumerate(
                    zip(columns, images[start : start + 2])
                ):
                    with col:
                        st.image(str(image_path), use_column_width=True)
                        st.caption(image_path.stem.replace("_", " "))
                        if st.button(
                            "Elegir este producto",
                            key=f"choose_grid_{start + offset}",
                        ):
                            _register_visual_choice(image_path.stem)
        else:
            index = st.session_state.get("visual_index", 0)
            if index >= len(images):
                index = len(images) - 1
                st.session_state["visual_index"] = max(index, 0)

            if images:
                current_image = images[index]
                st.image(str(current_image), use_column_width=True)
                st.caption(current_image.stem.replace("_", " "))
                if st.button("Elegir este producto", key=f"choose_seq_{index}"):
                    _register_visual_choice(current_image.stem)

                next_disabled = index >= len(images) - 1
                if st.button(
                    "Next Product ▶️",
                    key="next_product",
                    disabled=next_disabled,
                ):
                    if index < len(images) - 1:
                        st.session_state["visual_index"] = index + 1

                if next_disabled:
                    st.info("Has llegado al último producto de esta secuencia.")

    st.markdown("---")
    st.subheader("📥 Descarga tus elecciones")

    if st.session_state["visual_log"]:
        log_df = pd.DataFrame(st.session_state["visual_log"])
        csv_data = log_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Descargar registros",
            data=csv_data,
            file_name="visual_experiment_log.csv",
            mime="text/csv",
        )
    else:
        st.info("No hay elecciones registradas todavía.")
        st.download_button(
            "Descargar registros",
            data="".encode("utf-8"),
            file_name="visual_experiment_log.csv",
            mime="text/csv",
            disabled=True,
        )
