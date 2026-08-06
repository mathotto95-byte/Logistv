import html
import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


APP_DIR = Path(__file__).resolve().parent
PANELS_PATH = APP_DIR / "panels.json"
DEFAULT_SECONDS = 60


def query_param(name: str, default: str = "") -> str:
    try:
        value = st.query_params.get(name, default)
    except Exception:
        return default
    if isinstance(value, list):
        return str(value[0] if value else default)
    return str(value if value not in [None, ""] else default)


def load_panels() -> list[dict]:
    if not PANELS_PATH.exists():
        return []
    data = json.loads(PANELS_PATH.read_text(encoding="utf-8"))
    panels = data.get("panels", [])
    return [
        panel
        for panel in panels
        if isinstance(panel, dict)
        and panel.get("enabled", True) is not False
        and str(panel.get("url", "")).strip()
    ]


def int_param(name: str, default: int, minimum: int, maximum: int) -> int:
    value = pd.to_numeric(pd.Series([query_param(name, str(default))]), errors="coerce").fillna(default).iloc[0]
    return max(minimum, min(maximum, int(value)))


def inject_css() -> None:
    st.markdown(
        """
        <style>
        html, body, .stApp {
            background: #030914 !important;
            color: #f8fafc !important;
        }
        [data-testid="stSidebar"],
        [data-testid="stToolbar"],
        [data-testid="stHeader"],
        [data-testid="stDecoration"],
        .stDeployButton,
        #MainMenu,
        footer {
            display: none !important;
        }
        .block-container {
            max-width: 100% !important;
            padding: 0.45rem 0.6rem 0.6rem !important;
            background: #030914;
        }
        .tv-header {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 14px;
            align-items: center;
            min-height: 70px;
            margin-bottom: 8px;
            padding: 10px 14px;
            background: #071526;
            border: 1px solid rgba(214,169,51,0.42);
            border-radius: 8px;
        }
        .tv-title {
            color: #f8fafc;
            font-size: 30px;
            font-weight: 900;
            line-height: 1.05;
        }
        .tv-subtitle {
            color: rgba(248,250,252,0.74);
            font-size: 14px;
            font-weight: 700;
            margin-top: 4px;
        }
        .tv-actions {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .tv-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 38px;
            padding: 0 12px;
            border: 1px solid #d6a933;
            border-radius: 8px;
            background: #0f2438;
            color: #f8fafc !important;
            font-size: 13px;
            font-weight: 800;
            text-decoration: none !important;
            white-space: nowrap;
        }
        iframe {
            background: #030914 !important;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def auto_reload(seconds: int) -> None:
    components.html(
        f"""
        <script>
        setTimeout(function() {{
            try {{
                window.parent.location.reload();
            }} catch (error) {{
                window.location.reload();
            }}
        }}, {int(seconds) * 1000});
        </script>
        """,
        height=0,
    )


def fullscreen_button() -> str:
    return """
    <button class="tv-button" onclick="window.parent.document.documentElement.requestFullscreen && window.parent.document.documentElement.requestFullscreen();">
        Tela cheia
    </button>
    """


def render_panel(panel: dict, seconds: int, panel_index: int, total_panels: int) -> None:
    title = str(panel.get("title") or "TV Operacional")
    description = str(panel.get("description") or "Painel operacional")
    url = str(panel.get("url") or "")
    now = time.strftime("%d/%m/%Y %H:%M")
    next_index = (panel_index + 1) % max(total_panels, 1)
    next_url = f"?inicio={next_index}&tempo={seconds}"
    direct_url = html.escape(url, quote=True)
    st.markdown(
        f"""
        <div class="tv-header">
            <div>
                <div class="tv-title">{html.escape(title)}</div>
                <div class="tv-subtitle">{html.escape(description)} | Atualizacao da tela: {now} | Alterna a cada {seconds}s</div>
            </div>
            <div class="tv-actions">
                {fullscreen_button()}
                <a class="tv-button" href="{html.escape(next_url, quote=True)}">Proximo</a>
                <a class="tv-button" href="{direct_url}" target="_blank" rel="noopener">Abrir direto</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    components.iframe(url, height=930, scrolling=True)


def main() -> None:
    st.set_page_config(page_title="TV Operacional", layout="wide", initial_sidebar_state="collapsed")
    inject_css()
    panels = load_panels()
    if not panels:
        st.error("Nenhum painel configurado em panels.json.")
        return
    default_seconds = int(panels[0].get("seconds") or DEFAULT_SECONDS)
    seconds = int_param("tempo", default_seconds, 15, 900)
    panel_index = int_param("inicio", 0, 0, max(len(panels) - 1, 0))
    render_panel(panels[panel_index], seconds, panel_index, len(panels))
    auto_reload(seconds)


if __name__ == "__main__":
    main()
