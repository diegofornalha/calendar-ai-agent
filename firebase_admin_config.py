"""
Configurações do Firebase Admin SDK para a aplicação Calendário IA.
Este arquivo contém as credenciais padrão e funções para gerenciar o Firebase Admin SDK.
"""

import os
import json
import streamlit as st
import tempfile
import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth as firebase_auth

# Credenciais padrão do Firebase Admin SDK
DEFAULT_FIREBASE_ADMIN_CONFIG = {
  "type": "service_account",
  "project_id": "calendario-ia-coflow",
  "private_key_id": "INSIRA_SEU_PRIVATE_KEY_ID_AQUI",
  "private_key": "INSIRA_SUA_PRIVATE_KEY_AQUI",
  "client_email": "INSIRA_SEU_CLIENT_EMAIL_AQUI",
  "client_id": "INSIRA_SEU_CLIENT_ID_AQUI",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "INSIRA_SUA_CLIENT_X509_CERT_URL_AQUI",
  "universe_domain": "googleapis.com"
}

# Variável para controlar a inicialização do Firebase Admin SDK
_firebase_admin_initialized = False

def get_admin_credentials():
    """
    Obtém as credenciais do Firebase Admin SDK da sessão ou usa as padrões
    """
    if 'firebase_admin_config' in st.session_state:
        return st.session_state.firebase_admin_config
    return DEFAULT_FIREBASE_ADMIN_CONFIG

def initialize_firebase_admin():
    """
    Inicializa o Firebase Admin SDK com as credenciais configuradas
    """
    global _firebase_admin_initialized
    
    if _firebase_admin_initialized:
        return True
    
    try:
        # Obter as credenciais atuais
        config = get_admin_credentials()
        
        # Criar um arquivo temporário para as credenciais
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name
            json.dump(config, temp_file)
        
        # Inicializar o Firebase Admin SDK
        try:
            # Tentar inicializar o app Firebase Admin
            cred = credentials.Certificate(temp_path)
            firebase_admin.initialize_app(cred)
        except ValueError:
            # Se já estiver inicializado, reiniciar com as novas credenciais
            firebase_admin.delete_app(firebase_admin.get_app())
            cred = credentials.Certificate(temp_path)
            firebase_admin.initialize_app(cred)
        
        # Limpar o arquivo temporário
        os.unlink(temp_path)
        
        # Marcar como inicializado
        _firebase_admin_initialized = True
        return True
        
    except Exception as e:
        st.error(f"Erro ao inicializar Firebase Admin SDK: {str(e)}")
        return False

def save_admin_credentials(config):
    """
    Salva novas credenciais do Firebase Admin SDK
    """
    # Validar o formato básico das credenciais
    required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
    for field in required_fields:
        if field not in config:
            return False, f"Credenciais inválidas: campo '{field}' ausente"
    
    # Salvar na sessão
    st.session_state.firebase_admin_config = config
    
    # Reinicializar o Firebase Admin SDK
    global _firebase_admin_initialized
    _firebase_admin_initialized = False
    
    return True, "Credenciais salvas com sucesso!"

def admin_config_component():
    """
    Componente Streamlit para configuração do Firebase Admin SDK
    """
    st.write("### Configuração do Firebase Admin SDK")
    
    # Mostrar as credenciais atuais
    current_config = get_admin_credentials()
    
    # Exibir informações sobre o projeto
    st.write(f"**Projeto atual:** `{current_config['project_id']}`")
    st.write(f"**Conta de serviço:** `{current_config['client_email']}`")
    
    # Opções de configuração
    config_option = st.radio(
        "Como você deseja configurar o Firebase Admin SDK?",
        ["Usar credenciais padrão", "Carregar arquivo JSON", "Inserir JSON manualmente"],
        index=0,
        key="admin_sdk_config_option"
    )
    
    # Link para instruções em vez de expander aninhado
    st.markdown("[Como obter credenciais do Firebase Admin SDK?](#firebase-admin-sdk-credentials)")
    
    # Mostrar informações sobre como obter credenciais
    if config_option == "Usar credenciais padrão":
        if st.button("Restaurar credenciais padrão"):
            if 'firebase_admin_config' in st.session_state:
                del st.session_state.firebase_admin_config
            
            # Reinicializar o Firebase Admin SDK
            global _firebase_admin_initialized
            _firebase_admin_initialized = False
            
            st.success("Credenciais padrão restauradas com sucesso!")
            st.rerun()
        
        # Instruções para obter credenciais - movidas para fora para evitar erros de aninhamento
        st.markdown("📘 Veja a seção de ajuda abaixo para saber como obter suas próprias credenciais.")

    elif config_option == "Carregar arquivo JSON":
        uploaded_file = st.file_uploader(
            "Carregar arquivo de credenciais do Firebase",
            type=["json"],
            help="Faça upload do arquivo JSON de credenciais da conta de serviço do Firebase"
        )
        
        if uploaded_file is not None:
            try:
                # Ler e validar o arquivo JSON
                config = json.load(uploaded_file)
                
                if st.button("Salvar credenciais carregadas"):
                    success, message = save_admin_credentials(config)
                    if success:
                        st.success(message)
                        st.rerun()
            
            except Exception as e:
                st.error(f"Erro ao processar o arquivo: {str(e)}")

    elif config_option == "Inserir JSON manualmente":
        # Converter as credenciais atuais para JSON formatado
        default_json = json.dumps(current_config, indent=2)
        
        # Campo para inserção manual de JSON
        json_input = st.text_area(
            "Cole o JSON de credenciais do Firebase",
            value=default_json,
            height=400,
            help="Cole o conteúdo do arquivo JSON de credenciais da conta de serviço do Firebase"
        )
        
        if st.button("Salvar credenciais inseridas"):
            try:
                # Validar e processar o JSON
                config = json.loads(json_input)
                success, message = save_admin_credentials(config)
                if success:
                    st.success(message)
                    st.rerun()
            
            except json.JSONDecodeError:
                st.error("JSON inválido. Verifique o formato e tente novamente.")
            except Exception as e:
                st.error(f"Erro ao processar credenciais: {str(e)}")

    # Adicionar seção sobre regras do Firestore
    st.write("### Regras de Segurança do Firestore")
    st.write("""
    As regras de segurança determinam quem pode ler e escrever nos seus dados do Firestore. 
    Por padrão, o Firebase bloqueia todos os acessos.
    """)

    # Exemplo de regras do Firestore
    with st.expander("Exemplo de regras do Firestore"):
        st.code("""rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if false;
    }
  }
}""", language="javascript")
        
        st.markdown("""
        #### Explicação:
        - `rules_version = '2'` - Versão das regras do Firestore
        - `service cloud.firestore` - Indica que estas regras são para o Firestore
        - `match /databases/{database}/documents` - Aplica as regras a todos os documentos
        - `match /{document=**}` - Aplica as regras a todos os documentos em todas as coleções
        - `allow read, write: if false;` - Bloqueia todas as leituras e escritas
        
        ### Exemplos de Regras Personalizadas:
        
        **Permitir acesso apenas para usuários autenticados:**
        ```javascript
        rules_version = '2';
        service cloud.firestore {
          match /databases/{database}/documents {
            match /{document=**} {
              allow read, write: if request.auth != null;
            }
          }
        }
        ```
        
        **Permitir que os usuários leiam todos os dados, mas apenas escrevam seus próprios:**
        ```javascript
        rules_version = '2';
        service cloud.firestore {
          match /databases/{database}/documents {
            match /users/{userId} {
              allow read: if request.auth != null;
              allow write: if request.auth.uid == userId;
            }
          }
        }
        ```
        """)
        
        st.info("""
        ⚠️ **Importante**: Configure as regras de segurança apropriadas para o seu aplicativo!
        O exemplo padrão bloqueia todo o acesso. Você precisará configurar regras que permitam
        os acessos necessários para seu aplicativo funcionar corretamente.
        """)
        
        # Link para documentação
        st.markdown("[Documentação oficial de regras de segurança do Firestore](https://firebase.google.com/docs/firestore/security/get-started)")

# Seção de ajuda fora da função para evitar problemas de aninhamento
def show_admin_sdk_help():
    """
    Exibe instruções para obter credenciais do Firebase Admin SDK
    """
    st.markdown("<a name='firebase-admin-sdk-credentials'></a>", unsafe_allow_html=True)
    st.header("Como obter credenciais do Firebase Admin SDK")
    
    st.markdown("""
    ## Instruções para obter credenciais do Firebase Admin SDK

    1. **Acesse o Console do Firebase**
       - Vá para [console.firebase.google.com](https://console.firebase.google.com/)
       - Selecione seu projeto existente ou crie um novo

    2. **Acesse as configurações do projeto**
       - Clique no ícone ⚙️ (Configurações) no menu lateral
       - Selecione "Configurações do projeto"

    3. **Vá para Contas de serviço**
       - Clique na aba "Contas de serviço"
       - Selecione "Firebase Admin SDK"

    4. **Gere uma nova chave privada**
       - Clique no botão "Gerar nova chave privada"
       - Confirme no diálogo que aparecer
       - O arquivo JSON será baixado automaticamente

    5. **Use o arquivo baixado**
       - Carregue este arquivo JSON nesta página de configuração
       - Ou copie e cole o conteúdo do arquivo no campo de texto

    6. **Configuração das regras de segurança**
       - Não se esqueça de configurar as regras de segurança no Firebase para permitir acesso aos seus dados
       - Acesse as seções "Firestore", "Realtime Database" e "Storage" no console do Firebase para configurar as regras
    """)

def test_admin_connection():
    """
    Testa a conexão com o Firebase Admin SDK
    """
    if initialize_firebase_admin():
        try:
            # Tentar listar usuários (limitado a 1) para verificar a conexão
            page = firebase_auth.list_users(max_results=1)
            
            # Retorna sucesso e uma mensagem com a informação do projeto
            config = get_admin_credentials()
            return True, f"Conexão bem-sucedida com o projeto '{config['project_id']}'"
        
        except Exception as e:
            return False, f"Erro ao conectar: {str(e)}"
    else:
        return False, "Erro ao inicializar o Firebase Admin SDK" 