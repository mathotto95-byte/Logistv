import html
import json
import time
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


def add_streamlit_embed_params(url: str) -> str:
    parts = urlsplit(url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    if not any(key == "embed" for key, _ in query_items):
        query_items.insert(0, ("embed", "true"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment))


def add_query_params(url: str, params_to_add: dict[str, str | int]) -> str:
    parts = urlsplit(url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    existing = {key for key, _ in query_items}
    for key, value in params_to_add.items():
        if key not in existing:
            query_items.append((key, str(value)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment))


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


def render_panel(panel: dict, seconds: int, panel_index: int, total_panels: int) -> None:
    title = str(panel.get("title") or "TV Operacional")
    description = str(panel.get("description") or "Painel operacional")
    url = str(panel.get("url") or "")
    fallback_urls = panel.get("fallback_urls") or []
    candidate_urls = [url, *fallback_urls]
    iframe_urls = [add_streamlit_embed_params(str(candidate)) for candidate in candidate_urls if str(candidate).strip()]
    now = time.strftime("%d/%m/%Y %H:%M")
    next_index = (panel_index + 1) % max(total_panels, 1)
    next_url = f"?inicio={next_index}&tempo={seconds}&_={int(time.time())}"
    if str(panel.get("open_mode") or "").lower() == "top_redirect":
        return_url = str(panel.get("return_url") or f"https://logistv.streamlit.app/?inicio={next_index}")
        return_url = add_query_params(return_url, {"tempo": seconds, "_": int(time.time())})
        redirect_url = add_query_params(
            url,
            {
                "tempo": seconds,
                "retorno": return_url,
                "retorno_tempo": seconds,
            },
        )
        components.html(
            f"""
            <!doctype html>
            <html lang="pt-BR">
            <head>
              <meta charset="utf-8">
              <style>
                html, body {{
                  width: 100%;
                  height: 100%;
                  margin: 0;
                  background: #030914;
                  color: #f8fafc;
                  font-family: Arial, Helvetica, sans-serif;
                  overflow: hidden;
                }}
                .redirect {{
                  width: 100%;
                  height: 100vh;
                  min-height: 940px;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  padding: 28px;
                  background: #030914;
                }}
                .box {{
                  width: min(780px, 92vw);
                  padding: 24px;
                  text-align: center;
                  background: #071526;
                  border: 1px solid rgba(214,169,51,0.42);
                  border-radius: 8px;
                }}
                h1 {{
                  margin: 0;
                  color: #f8fafc;
                  font-size: 34px;
                  line-height: 1.1;
                }}
                p {{
                  margin: 10px 0 0;
                  color: rgba(248,250,252,0.76);
                  font-size: 16px;
                  font-weight: 700;
                }}
                a {{
                  display: inline-flex;
                  align-items: center;
                  justify-content: center;
                  min-height: 42px;
                  margin-top: 18px;
                  padding: 0 16px;
                  border: 1px solid #d6a933;
                  border-radius: 8px;
                  background: #0f2438;
                  color: #f8fafc;
                  font-size: 14px;
                  font-weight: 900;
                  text-decoration: none;
                }}
              </style>
            </head>
            <body>
              <main class="redirect">
                <section class="box">
                  <h1>{html.escape(title)}</h1>
                  <p>{html.escape(description)} | abrindo em tela inteira para evitar bloqueio de iframe.</p>
                  <p>Se nao abrir automaticamente, clique abaixo.</p>
                  <a href="{html.escape(redirect_url, quote=True)}" target="_top">Abrir Coupa agora</a>
                </section>
              </main>
              <script>
                setTimeout(() => {{
                  window.parent.location.href = {json.dumps(redirect_url)};
                }}, 900);
              </script>
            </body>
            </html>
            """,
            height=1020,
            scrolling=False,
        )
        return
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
          min-height: 940px;
          display: grid;
          grid-template-rows: auto 1fr;
          gap: 8px;
          background: #030914;
        }}
        .tv-header {{
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 14px;
          align-items: center;
          min-height: 70px;
          padding: 10px 14px;
          background: #071526;
          border: 1px solid rgba(214,169,51,0.42);
          border-radius: 8px;
        }}
        .tv-title {{
          color: #f8fafc;
          font-size: 30px;
          font-weight: 900;
          line-height: 1.05;
        }}
        .tv-subtitle {{
          color: rgba(248,250,252,0.74);
          font-size: 14px;
          font-weight: 700;
          margin-top: 4px;
        }}
        .tv-actions {{
          display: flex;
          gap: 8px;
          align-items: center;
        }}
        .tv-button {{
          min-height: 38px;
          padding: 0 12px;
          border: 1px solid #d6a933;
          border-radius: 8px;
          background: #0f2438;
          color: #f8fafc;
          font-size: 13px;
          font-weight: 800;
          text-decoration: none;
          cursor: pointer;
          white-space: nowrap;
        }}
        .stage {{
          position: relative;
          min-height: 0;
          overflow: hidden;
          background: #030914;
          border: 1px solid rgba(214,169,51,0.38);
          border-radius: 8px;
        }}
        iframe {{
          width: 100%;
          height: 100%;
          border: 0;
          background: #030914;
        }}
        .overlay {{
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 26px;
          background: rgba(3,9,20,0.92);
          text-align: center;
          z-index: 3;
        }}
        .overlay.hidden {{
          display: none;
        }}
        .box {{
          width: min(760px, 92vw);
          padding: 22px;
          border: 1px solid rgba(214,169,51,0.42);
          border-radius: 8px;
          background: #071526;
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
        .box a {{
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-height: 38px;
          margin-top: 14px;
          padding: 0 12px;
          border: 1px solid #d6a933;
          border-radius: 8px;
          background: #0f2438;
          color: #f8fafc;
          font-size: 13px;
          font-weight: 800;
          text-decoration: none;
        }}
      </style>
    </head>
    <body>
      <main id="player" class="player">
        <header class="tv-header">
          <div>
            <div class="tv-title">{html.escape(title)}</div>
            <div class="tv-subtitle">{html.escape(description)} | Atualizacao da tela: {now} | Alterna a cada {seconds}s</div>
          </div>
          <div class="tv-actions">
            <button id="fullscreen" class="tv-button" type="button">Tela cheia</button>
            <button id="next" class="tv-button" type="button">Proximo</button>
            <a class="tv-button" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">Abrir direto</a>
          </div>
        </header>
        <section class="stage">
          <iframe id="frame" allow="fullscreen" referrerpolicy="no-referrer-when-downgrade"></iframe>
          <div id="overlay" class="overlay">
            <div class="box">
              <h2>Carregando painel</h2>
              <p id="overlay-text">Tentando abrir o painel embutido.</p>
              <a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">Abrir painel direto</a>
            </div>
          </div>
        </section>
      </main>
      <script>
        const overlay = document.getElementById("overlay");
        const overlayText = document.getElementById("overlay-text");
        const frame = document.getElementById("frame");
        const player = document.getElementById("player");
        const nextUrl = {json.dumps(next_url)};
        const iframeUrls = {json.dumps(iframe_urls)};
        let iframeIndex = 0;
        let loadTimer = null;

        function loadFrame(index) {{
          iframeIndex = index;
          overlay.classList.remove("hidden");
          overlayText.textContent = index === 0
            ? "Tentando abrir o painel embutido."
            : "Tentando rota alternativa do painel.";
          frame.src = iframeUrls[index];
          clearTimeout(loadTimer);
          loadTimer = setTimeout(() => {{
            if (iframeIndex + 1 < iframeUrls.length) {{
              loadFrame(iframeIndex + 1);
              return;
            }}
            overlay.classList.remove("hidden");
            overlayText.textContent = "Se a tela continuar branca, o Streamlit bloqueou este painel embutido. Use Abrir direto para validar o Coupa.";
          }}, 9000);
        }}

        frame.addEventListener("load", () => {{
          clearTimeout(loadTimer);
          setTimeout(() => overlay.classList.add("hidden"), 1800);
        }});
        document.getElementById("next").addEventListener("click", () => {{
          window.parent.location.search = nextUrl;
        }});
        document.getElementById("fullscreen").addEventListener("click", async () => {{
          try {{
            if (document.fullscreenElement) {{
              await document.exitFullscreen();
            }} else if (player.requestFullscreen) {{
              await player.requestFullscreen();
            }} else if (window.frameElement && window.frameElement.requestFullscreen) {{
              await window.frameElement.requestFullscreen();
            }}
          }} catch (error) {{
            console.error("Nao foi possivel abrir em tela cheia", error);
          }}
        }});
        setTimeout(() => {{
          window.parent.location.search = nextUrl;
        }}, {int(seconds) * 1000});
        loadFrame(0);
      </script>
    </body>
    </html>
    """
    components.html(
        player_html,
        height=1020,
        scrolling=False,
    )


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


if __name__ == "__main__":
    main()
