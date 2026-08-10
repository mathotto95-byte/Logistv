import html
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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


def int_param(name: str, default: int, minimum: int, maximum: int) -> int:
    value = pd.to_numeric(pd.Series([query_param(name, str(default))]), errors="coerce").fillna(default).iloc[0]
    return max(minimum, min(maximum, int(value)))


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


def add_streamlit_embed_params(url: str) -> str:
    parts = urlsplit(url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    keys = {key for key, _ in query_items}
    if "embed" not in keys:
        query_items.insert(0, ("embed", "true"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment))


def inject_shell_css() -> None:
    st.markdown(
        """
        <style>
        html, body, .stApp {
            background: #030914 !important;
            color: #f8fafc !important;
            overflow: hidden !important;
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
            padding: 0 !important;
            background: #030914;
        }
        iframe {
            background: #030914 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_panel_payload(panels: list[dict], default_seconds: int) -> list[dict]:
    payload = []
    for panel in panels:
        seconds = int(pd.to_numeric(pd.Series([panel.get("seconds", default_seconds)]), errors="coerce").fillna(default_seconds).iloc[0])
        payload.append(
            {
                "title": str(panel.get("title") or "Painel"),
                "description": str(panel.get("description") or ""),
                "url": str(panel.get("url") or ""),
                "embedUrl": add_streamlit_embed_params(str(panel.get("url") or "")),
                "seconds": max(15, min(900, seconds)),
                "zoom": max(0.5, min(1.25, float(pd.to_numeric(pd.Series([panel.get("zoom", 0.82)]), errors="coerce").fillna(0.82).iloc[0]))),
            }
        )
    return payload


def render_tv_player(panels: list[dict], default_seconds: int) -> None:
    panel_payload = build_panel_payload(panels, default_seconds)
    start_index = int_param("inicio", 0, 0, max(len(panel_payload) - 1, 0))
    player_html = f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
      <meta charset="utf-8">
      <style>
        * {{ box-sizing: border-box; }}
        html, body {{
          width: 100%;
          height: 100%;
          margin: 0;
          background: #030914;
          color: #f8fafc;
          font-family: Arial, Helvetica, sans-serif;
          overflow: hidden;
        }}
        .player {{
          width: 100%;
          height: 100vh;
          min-height: 0;
          position: relative;
          padding: 0;
          background: #030914;
        }}
        .player:fullscreen {{
          min-height: 100vh;
          padding: 0;
        }}
        .player:fullscreen .topbar {{
          min-height: 34px;
        }}
        .topbar {{
          position: absolute;
          top: 6px;
          right: 6px;
          z-index: 5;
          display: flex;
          justify-content: flex-end;
          gap: 6px;
          align-items: center;
          min-height: 34px;
          padding: 3px 6px;
          background: rgba(7, 21, 38, 0.72);
          border: 1px solid rgba(214,169,51,0.42);
          border-radius: 6px;
          opacity: 0.72;
          transition: opacity .15s ease;
        }}
        .topbar:hover {{
          opacity: 1;
        }}
        .title {{
          color: #f8fafc;
          font-size: 30px;
          font-weight: 900;
          line-height: 1.05;
        }}
        .subtitle {{
          color: rgba(248,250,252,0.76);
          font-size: 14px;
          font-weight: 700;
          margin-top: 4px;
        }}
        .actions {{
          display: flex;
          gap: 6px;
          align-items: center;
          flex-wrap: wrap;
          justify-content: flex-end;
        }}
        .zoom-badge {{
          min-height: 28px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 54px;
          padding: 0 8px;
          border: 1px solid rgba(214,169,51,0.42);
          border-radius: 8px;
          background: #071526;
          color: #d6a933;
          font-size: 11px;
          font-weight: 900;
          white-space: nowrap;
        }}
        button, a.button {{
          min-height: 28px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 0 8px;
          border: 1px solid #d6a933;
          border-radius: 8px;
          background: #0f2438;
          color: #f8fafc;
          font-size: 11px;
          font-weight: 900;
          text-decoration: none;
          cursor: pointer;
          white-space: nowrap;
        }}
        .stage {{
          position: absolute;
          inset: 0;
          min-height: 100%;
          overflow: hidden;
          background: #030914;
          border: 0;
          border-radius: 0;
        }}
        .frame-viewport {{
          position: absolute;
          inset: 0;
          overflow: hidden;
          background: #030914;
        }}
        #panel-frame {{
          width: 100%;
          height: 100%;
          border: 0;
          background: #030914;
          transform-origin: top left;
        }}
        .loading {{
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          background: rgba(3,9,20,0.90);
          text-align: center;
          z-index: 2;
        }}
        .loading.hidden {{ display: none; }}
        .box {{
          width: min(760px, 92vw);
          padding: 20px;
          background: #071526;
          border: 1px solid rgba(214,169,51,0.42);
          border-radius: 8px;
        }}
        .box h2 {{
          margin: 0 0 8px;
          color: #d6a933;
          font-size: 26px;
        }}
        .box p {{
          margin: 8px 0 0;
          color: rgba(248,250,252,0.78);
          font-size: 16px;
          line-height: 1.35;
        }}
        .progress {{
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          height: 5px;
          background: rgba(255,255,255,0.12);
          z-index: 3;
        }}
        #progress-bar {{
          display: block;
          width: 0%;
          height: 100%;
          background: #d6a933;
        }}
      </style>
    </head>
    <body>
      <main id="player" class="player">
        <header class="topbar">
          <div class="actions">
            <button id="fullscreen" type="button">Tela cheia</button>
            <button id="previous" type="button">Anterior</button>
            <button id="next" type="button">Proximo</button>
            <button id="zoom-out" type="button">Zoom -</button>
            <span id="zoom-badge" class="zoom-badge">100%</span>
            <button id="zoom-in" type="button">Zoom +</button>
            <a id="open-direct" class="button" href="#" target="_blank" rel="noopener">Abrir direto</a>
          </div>
        </header>
        <section class="stage">
          <div class="frame-viewport">
            <iframe id="panel-frame" title="Painel atual" allow="fullscreen" referrerpolicy="no-referrer-when-downgrade"></iframe>
          </div>
          <div id="loading" class="loading">
            <div class="box">
              <h2 id="loading-title">Carregando painel</h2>
              <p>O Logistv apenas espelha o painel original. Se algum app bloquear exibicao embutida, use Abrir direto.</p>
            </div>
          </div>
          <div class="progress"><span id="progress-bar"></span></div>
        </section>
      </main>
      <script>
        const panels = {json.dumps(panel_payload, ensure_ascii=False)};
        const storagePrefix = "logistv:v1:";
        let index = initialIndex({start_index});
        let startedAt = Date.now();
        let switchTimer = null;
        let progressTimer = null;
        let activeZoom = 1;

        const player = document.getElementById("player");
        const frame = document.getElementById("panel-frame");
        const openDirect = document.getElementById("open-direct");
        const loading = document.getElementById("loading");
        const loadingTitle = document.getElementById("loading-title");
        const progressBar = document.getElementById("progress-bar");
        const zoomBadge = document.getElementById("zoom-badge");

        if (window.frameElement) {{
          window.frameElement.setAttribute("allowfullscreen", "true");
          window.frameElement.setAttribute("allow", "fullscreen");
        }}

        function currentPanel() {{
          return panels[(index + panels.length) % panels.length];
        }}

        function storageGet(key, fallback = "") {{
          try {{
            return window.localStorage.getItem(storagePrefix + key) ?? fallback;
          }} catch (error) {{
            return fallback;
          }}
        }}

        function storageSet(key, value) {{
          try {{
            window.localStorage.setItem(storagePrefix + key, String(value));
          }} catch (error) {{}}
        }}

        function initialIndex(defaultIndex) {{
          if (!panels.length) {{
            return 0;
          }}
          const requested = Number(defaultIndex);
          if (Number.isFinite(requested)) {{
            return Math.max(0, Math.min(panels.length - 1, Math.trunc(requested)));
          }}
          return 0;
        }}

        function panelStorageKey(panel) {{
          return `zoom:${{panel.url || panel.title || "painel"}}`;
        }}

        function savedZoomFor(panel) {{
          const saved = Number(storageGet(panelStorageKey(panel), ""));
          return Number.isFinite(saved) && saved > 0 ? saved : Number(panel.zoom || 0.82);
        }}

        function updateProgress() {{
          const panel = currentPanel();
          const elapsed = Date.now() - startedAt;
          const percent = Math.min(100, elapsed / (panel.seconds * 1000) * 100);
          progressBar.style.width = `${{percent}}%`;
        }}

        function applyZoom(zoom, persist = true) {{
          activeZoom = Math.max(0.5, Math.min(1.25, Number(zoom) || 0.82));
          frame.style.transform = `scale(${{activeZoom}})`;
          frame.style.width = `${{100 / activeZoom}}%`;
          frame.style.height = `${{100 / activeZoom}}%`;
          zoomBadge.textContent = `${{Math.round(activeZoom * 100)}}%`;
          if (persist && panels.length) {{
            storageSet(panelStorageKey(currentPanel()), activeZoom.toFixed(2));
          }}
        }}

        function changeZoom(delta) {{
          applyZoom(Math.round((activeZoom + delta) * 100) / 100);
        }}

        function showPanel(nextIndex) {{
          clearTimeout(switchTimer);
          clearInterval(progressTimer);
          index = (nextIndex + panels.length) % panels.length;
          const panel = currentPanel();
          startedAt = Date.now();
          applyZoom(savedZoomFor(panel), false);
          openDirect.href = panel.url;
          loadingTitle.textContent = "Carregando painel";
          loading.classList.remove("hidden");
          progressBar.style.width = "0%";
          frame.src = panel.embedUrl;
          switchTimer = setTimeout(() => showPanel(index + 1), panel.seconds * 1000);
          progressTimer = setInterval(updateProgress, 1000);
        }}

        frame.addEventListener("load", () => {{
          setTimeout(() => loading.classList.add("hidden"), 1400);
        }});

        document.getElementById("next").addEventListener("click", () => showPanel(index + 1));
        document.getElementById("previous").addEventListener("click", () => showPanel(index - 1));
        document.getElementById("zoom-out").addEventListener("click", () => changeZoom(-0.05));
        document.getElementById("zoom-in").addEventListener("click", () => changeZoom(0.05));
        document.getElementById("fullscreen").addEventListener("click", async () => {{
          try {{
            if (document.fullscreenElement) {{
              await document.exitFullscreen();
            }} else {{
              const target = player.requestFullscreen ? player : document.documentElement;
              await target.requestFullscreen();
            }}
          }} catch (error) {{
            try {{
              await window.parent.document.documentElement.requestFullscreen();
            }} catch (parentError) {{
              console.error("Nao foi possivel abrir tela cheia", error, parentError);
            }}
          }}
        }});

        if (panels.length) {{
          showPanel(index);
        }}
      </script>
    </body>
    </html>
    """
    components.html(player_html, height=1080, scrolling=False)


def main() -> None:
    st.set_page_config(page_title="TV Operacional", layout="wide", initial_sidebar_state="collapsed")
    inject_shell_css()
    panels = load_panels()
    if not panels:
        st.error("Nenhum painel configurado em panels.json.")
        return
    default_seconds = int_param("tempo", DEFAULT_SECONDS, 15, 900)
    render_tv_player(panels, default_seconds)


if __name__ == "__main__":
    main()
