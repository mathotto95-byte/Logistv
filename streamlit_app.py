import html
import hmac
import json
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


APP_DIR = Path(__file__).resolve().parent
PANELS_PATH = APP_DIR / "panels.json"
DEFAULT_SECONDS = 60
DEFAULT_ACCESS = "publico"
MANAGER_PARAM_VALUES = {"1", "true", "sim", "admin", "gerenciar"}
ACCESS_ALIASES = {
    "publico": "publico",
    "public": "publico",
    "diretoria": "diretoria",
    "directoria": "diretoria",
    "diretor": "diretoria",
}


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


def bool_param(name: str) -> bool:
    return query_param(name).strip().lower() in MANAGER_PARAM_VALUES


def selected_access() -> str:
    value = query_param("acesso", DEFAULT_ACCESS).strip().lower()
    return ACCESS_ALIASES.get(value, DEFAULT_ACCESS)


def normalize_audiences(panel: dict) -> set[str]:
    audiences = panel.get("audiences", ["publico", "diretoria"])
    if isinstance(audiences, str):
        audiences = [item.strip() for item in audiences.split(",")]
    if not isinstance(audiences, list):
        audiences = [DEFAULT_ACCESS]
    return {ACCESS_ALIASES.get(str(item).strip().lower(), str(item).strip().lower()) for item in audiences}


def panel_allowed(panel: dict, access: str) -> bool:
    return access in normalize_audiences(panel)


def load_panels_data() -> dict:
    if not PANELS_PATH.exists():
        return {"panels": []}
    data = json.loads(PANELS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"panels": []}
    if not isinstance(data.get("panels"), list):
        data["panels"] = []
    return data


def save_panels_data(data: dict) -> None:
    PANELS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_panels(access: str) -> list[dict]:
    data = load_panels_data()
    panels = data.get("panels", [])
    return [
        panel
        for panel in panels
        if isinstance(panel, dict)
        and panel.get("enabled", True) is not False
        and str(panel.get("url", "")).strip()
        and panel_allowed(panel, access)
    ]


def add_streamlit_embed_params(url: str) -> str:
    parts = urlsplit(url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    keys = {key for key, _ in query_items}
    if "embed" not in keys:
        query_items.insert(0, ("embed", "true"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment))


def admin_password() -> str:
    try:
        secret_value = st.secrets.get("LOGISTV_ADMIN_PASSWORD", "")
    except Exception:
        secret_value = ""
    return str(secret_value or os.environ.get("LOGISTV_ADMIN_PASSWORD", "")).strip()


def manager_is_unlocked() -> bool:
    password = admin_password()
    if not password:
        st.warning("Gerenciador sem senha configurada. Para proteger, defina LOGISTV_ADMIN_PASSWORD nos Secrets do Streamlit.")
        return True
    if st.session_state.get("manager_unlocked"):
        return True
    with st.form("manager_login"):
        typed = st.text_input("Senha do gerenciador", type="password")
        submitted = st.form_submit_button("Entrar", type="primary")
    if submitted and hmac.compare_digest(typed, password):
        st.session_state["manager_unlocked"] = True
        st.rerun()
    elif submitted:
        st.error("Senha incorreta.")
    return False


def audiences_from_flags(publico: bool, diretoria: bool) -> list[str]:
    audiences = []
    if publico:
        audiences.append("publico")
    if diretoria:
        audiences.append("diretoria")
    return audiences or [DEFAULT_ACCESS]


def panels_to_editor_rows(panels: list[dict]) -> list[dict]:
    rows = []
    for panel in panels:
        audiences = normalize_audiences(panel)
        rows.append(
            {
                "Ativo": panel.get("enabled", True) is not False,
                "Titulo": str(panel.get("title") or ""),
                "Grupo": str(panel.get("group") or ""),
                "Publico": "publico" in audiences,
                "Diretoria": "diretoria" in audiences,
                "Segundos": int(pd.to_numeric(pd.Series([panel.get("seconds", DEFAULT_SECONDS)]), errors="coerce").fillna(DEFAULT_SECONDS).iloc[0]),
                "Zoom": float(pd.to_numeric(pd.Series([panel.get("zoom", 0.9)]), errors="coerce").fillna(0.9).iloc[0]),
                "URL": str(panel.get("url") or ""),
                "Descricao": str(panel.get("description") or ""),
            }
        )
    return rows


def editor_rows_to_panels(rows: pd.DataFrame) -> list[dict]:
    panels = []
    for row in rows.to_dict(orient="records"):
        title = str(row.get("Titulo") or "").strip()
        url = str(row.get("URL") or "").strip()
        if not title and not url:
            continue
        seconds = int(pd.to_numeric(pd.Series([row.get("Segundos", DEFAULT_SECONDS)]), errors="coerce").fillna(DEFAULT_SECONDS).iloc[0])
        zoom = float(pd.to_numeric(pd.Series([row.get("Zoom", 0.9)]), errors="coerce").fillna(0.9).iloc[0])
        panels.append(
            {
                "title": title or "Painel",
                "description": str(row.get("Descricao") or "").strip(),
                "url": url,
                "group": str(row.get("Grupo") or "").strip(),
                "audiences": audiences_from_flags(bool(row.get("Publico")), bool(row.get("Diretoria"))),
                "zoom": max(0.5, min(1.25, zoom)),
                "seconds": max(15, min(900, seconds)),
                "enabled": bool(row.get("Ativo")),
            }
        )
    return panels


def render_manager() -> None:
    st.markdown(
        """
        <style>
        .block-container {max-width: 1180px; padding-top: 1.5rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Gerenciar acessos da LogisTV")
    st.caption("Marque em qual link cada painel deve aparecer. O link sem parametro usa o acesso Publico.")
    if not manager_is_unlocked():
        return

    data = load_panels_data()
    rows = panels_to_editor_rows(data.get("panels", []))
    edited = st.data_editor(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Ativo": st.column_config.CheckboxColumn("Ativo"),
            "Publico": st.column_config.CheckboxColumn("Publico"),
            "Diretoria": st.column_config.CheckboxColumn("Diretoria"),
            "Segundos": st.column_config.NumberColumn("Segundos", min_value=15, max_value=900, step=15),
            "Zoom": st.column_config.NumberColumn("Zoom", min_value=0.5, max_value=1.25, step=0.01),
            "URL": st.column_config.LinkColumn("URL"),
        },
        key="panels_access_editor",
    )

    edited_panels = editor_rows_to_panels(edited)
    edited_payload = {"panels": edited_panels}
    edited_json = json.dumps(edited_payload, ensure_ascii=False, indent=2) + "\n"

    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("Salvar acessos", type="primary", use_container_width=True):
        invalid = [panel["title"] for panel in edited_panels if panel.get("enabled") and not panel.get("url")]
        if invalid:
            st.error("Painel ativo sem URL: " + ", ".join(invalid))
        else:
            save_panels_data(edited_payload)
            st.success("Acessos salvos. Recarregue a TV para aplicar imediatamente.")
            st.rerun()
    if c2.button("Recarregar arquivo", use_container_width=True):
        st.rerun()
    c3.download_button(
        "Baixar panels.json",
        edited_json,
        "panels.json",
        "application/json",
        use_container_width=True,
    )

    st.markdown("**Links**")
    st.markdown("- Publico: https://logistv.streamlit.app/")
    st.markdown("- Diretoria: https://logistv.streamlit.app/?acesso=diretoria")

    preview_cols = st.columns(2)
    for col, access in zip(preview_cols, ["publico", "diretoria"]):
        with col:
            visible = [panel.get("title", "Painel") for panel in edited_panels if panel_allowed(panel, access) and panel.get("enabled", True)]
            st.subheader(access.title())
            st.write(f"{len(visible)} painel(is)")
            st.write(visible)


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
          left: 6px;
          right: 6px;
          z-index: 5;
          display: flex;
          justify-content: space-between;
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
          font-size: 16px;
          font-weight: 900;
          line-height: 1.05;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
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
          <div>
            <div id="panel-title" class="title">LogisTV</div>
          </div>
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
        const panelTitle = document.getElementById("panel-title");
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

        function freshUrl(url) {{
          const parsed = new URL(url, window.location.href);
          parsed.searchParams.set("_tv_refresh", String(Date.now()));
          return parsed.toString();
        }}

        function showPanel(nextIndex) {{
          clearTimeout(switchTimer);
          clearInterval(progressTimer);
          index = (nextIndex + panels.length) % panels.length;
          const panel = currentPanel();
          startedAt = Date.now();
          applyZoom(savedZoomFor(panel), false);
          panelTitle.textContent = `${{panel.title}} | ${{panel.seconds}}s`;
          openDirect.href = panel.url;
          loadingTitle.textContent = "Carregando painel";
          loading.classList.remove("hidden");
          progressBar.style.width = "0%";
          frame.src = freshUrl(panel.embedUrl);
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
    if bool_param("gerenciar") or bool_param("admin"):
        render_manager()
        return
    inject_shell_css()
    access = selected_access()
    panels = load_panels(access)
    if not panels:
        st.error(f"Nenhum painel configurado para o acesso: {access}.")
        return
    default_seconds = int_param("tempo", DEFAULT_SECONDS, 15, 900)
    render_tv_player(panels, default_seconds)


if __name__ == "__main__":
    main()
