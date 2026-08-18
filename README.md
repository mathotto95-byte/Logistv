# TV Operacional

Projeto estatico para exibir paineis operacionais na TV sem depender de outro app Streamlit como tela principal.

## Como funciona

- `index.html` carrega a lista de paineis em `panels.json`.
- Cada painel e exibido em tela cheia e alternado automaticamente.
- O botao `Abrir direto` abre o painel atual fora do iframe, util quando o Streamlit acusa redirecionamento em excesso.
- Para alterar paineis, edite apenas `panels.json`.

## Paineis configurados

- Publico: paineis MotoristasRW.
- Diretoria: paineis MotoristasRW e Controle Integrado Coupa.

## Links de acesso

- Publico: `https://logistv.streamlit.app/`
- Diretoria: `https://logistv.streamlit.app/?acesso=diretoria`

O link sem parametro, ou com `?acesso=publico`, mostra apenas os paineis publicos.

## Publicacao no Streamlit Cloud

Use estes campos:

- Repository: `mathotto95-byte/Logistv`
- Branch: `main`
- Main file path: `streamlit_app.py`
- App URL: `logistv`

## Publicacao no GitHub Pages

1. Criar um repositorio vazio no GitHub, por exemplo `TV-Operacional`.
2. Enviar estes arquivos para a branch `main`.
3. Em `Settings > Pages`, selecionar:
   - Source: `Deploy from a branch`
   - Branch: `main`
   - Folder: `/root`
4. Abrir a URL publicada do GitHub Pages na TV.

## Parametros

- `?acesso=publico`: mostra somente os paineis publicos.
- `?acesso=diretoria`: mostra os paineis publicos e os paineis da diretoria.
- `?tempo=90`: altera o tempo padrao para 90 segundos quando o painel nao tiver `seconds`.
- `?inicio=1`: inicia pelo segundo painel da lista.
