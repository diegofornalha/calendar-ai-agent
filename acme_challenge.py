import streamlit as st

# Configuração da página - minimalista
st.set_page_config(page_title="ACME Verification", page_icon=None)

# Esconder todos os elementos Streamlit
hide_streamlit_style = """
<style>
    #root > div:nth-child(1) > div > div > div > div > section > div {display:none !important;}
    header {display:none !important;}
    footer {display:none !important;}
    #MainMenu {display:none !important;}
    .stDeployButton {display:none !important;}
    .viewerBadge_container__1QSob {display:none !important;}
    .viewerBadge_link__1S137 {display:none !important;}
    .css-1adrfps {padding-top: 0rem !important;}
    .css-18e3th9 {padding-top: 0rem !important;}
    .css-1d391kg {padding-top: 0rem !important;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Conteúdo de verificação ACME
acme_content = "4xyWfTdjON52ZneQEcTUJLlI1Y8hYoKeT5hU8OSLS6-T0L3WQNvIW-5FNaj87G9K.M0-GObbb5ePi63ASQsPKBrDqfgayGnOWpyrEF0nHqug"

# Exibir conteúdo como texto puro
st.text(acme_content)

# Carregar diretamente o conteúdo (tentativa mais radical)
st.components.v1.html(f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ACME Challenge</title>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            document.body.innerHTML = '{acme_content}';
            document.title = '';
            document.head.innerHTML = '';
        }});
    </script>
</head>
<body>{acme_content}</body>
</html>
""", height=50) 