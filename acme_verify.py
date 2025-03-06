import streamlit as st
from urllib.parse import urlparse
import os

# Configuração para esconder a interface do Streamlit
st.set_page_config(page_title="Verificação de Domínio", page_icon="🔒")

# Ocultar elementos da UI do Streamlit
hide_st_style = """
<style>
    #root > div:nth-child(1) > div > div > div > div > section > div {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Configurações para o desafio ACME
ACME_CHALLENGE_TOKEN = "4xyWfTdjON52ZneQEcTUJLlI1Y8hYoKeT5hU8OSLS6-T0L3WQNvIW-5FNaj87G9K"
ACME_CHALLENGE_RESPONSE = "4xyWfTdjON52ZneQEcTUJLlI1Y8hYoKeT5hU8OSLS6-T0L3WQNvIW-5FNaj87G9K.M0-GObbb5ePi63ASQsPKBrDqfgayGnOWpyrEF0nHqug"

# Verificar a URL atual
path = urlparse(st.experimental_get_query_params().get("_path", [""])[0]).path

# Verificar se a solicitação é para o endpoint de verificação ACME
if path == f"/.well-known/acme-challenge/{ACME_CHALLENGE_TOKEN}":
    # Responder com o conteúdo de verificação
    st.markdown(
        f"<pre>{ACME_CHALLENGE_RESPONSE}</pre>", 
        unsafe_allow_html=True
    )
    
    # Alternativamente, podemos tentar definir o tipo de conteúdo como texto puro
    # (isso pode não funcionar no Streamlit Cloud, mas vale a pena tentar)
    st.markdown(
        f"""
        <script>
            document.getElementsByTagName('html')[0].innerHTML = '{ACME_CHALLENGE_RESPONSE}';
            document.contentType = 'text/plain';
        </script>
        """,
        unsafe_allow_html=True
    )
else:
    # Página padrão para outras solicitações
    st.title("Verificação de Domínio")
    st.write("Este aplicativo gerencia a verificação de domínio para calendario-ia.streamlit.app")
    
    st.subheader("Informações de Configuração")
    st.code(f"""
URL de Verificação:
https://calendario-ia.streamlit.app/.well-known/acme-challenge/{ACME_CHALLENGE_TOKEN}

Resposta Esperada:
{ACME_CHALLENGE_RESPONSE}
    """)
    
    # Para propósitos de depuração
    st.subheader("Informações de Depuração")
    st.write(f"Caminho atual: {path}")
    st.write(f"Parâmetros de URL: {st.experimental_get_query_params()}") 