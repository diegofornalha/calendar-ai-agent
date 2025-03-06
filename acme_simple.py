import streamlit as st

# Configuração para esconder a interface do Streamlit
st.set_page_config(page_title="ACME Challenge", page_icon="🔒")

# Ocultar elementos da UI do Streamlit
hide_st_style = """
<style>
    #root > div:nth-child(1) > div > div > div > div > section > div {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# O conteúdo do arquivo de verificação
acme_content = "4xyWfTdjON52ZneQEcTUJLlI1Y8hYoKeT5hU8OSLS6-T0L3WQNvIW-5FNaj87G9K.M0-GObbb5ePi63ASQsPKBrDqfgayGnOWpyrEF0nHqug"

# Exibir apenas o conteúdo puro, sem formatação
st.write(acme_content, unsafe_allow_html=False)

# Tentativa adicional para garantir que apareça como texto puro
st.markdown(
    f"""
    <script>
        document.body.innerHTML = '{acme_content}';
        document.contentType = 'text/plain';
    </script>
    """,
    unsafe_allow_html=True
) 