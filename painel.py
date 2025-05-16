# main.py
import streamlit as st
import time
from datetime import datetime
from data.db import criar_tabela_if_not_exists
from components.interface import ComponentesInterface
from data.manager import GerenciadorDados
from modules.administrativo import ModuloAdministrativo
from modules.patio import ModuloPatioOperacional
from modules.motoristas import ModuloMotoristas
from modules.relatorios import ModuloRelatorios
from components.auth import AuthManager

def inicializar_estado():
    defaults = {
        'logged_in': False,
        'user': None,
        'user_role': None,
        'login_time': 0,
        'ultima_atualizacao': datetime.now(),
        'ultimo_chamado': None,
        'alerta_reproduzido': False,
        'audio_habilitado': True,
        'atualizacao_automatica': False,
        'modo_atual': 'Controle Pátio',
        'feedback_patio': None
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

def main():
    
    criar_tabela_if_not_exists()
    inicializar_estado()

    auth = AuthManager()
    
    # Verifica cookie válido
    if not st.session_state.get('logged_in'):
        auth.validate_token()

    # Interface de login
    if not st.session_state.get('logged_in'):
        with st.sidebar:
            st.title("🔒 Login BDM")
            username = st.text_input("Usuário").strip()
            password = st.text_input("Senha", type="password")
            
            if st.button("Acessar"):
                if auth.login(username, password):
                    st.rerun()
                else:
                    st.error("Credenciais inválidas")
        return
        
    # Interface principal
    with st.sidebar:
        st.title(f"👤 {st.session_state.user}")
        if st.button("🚪 Logout"):
            auth.logout()
            st.rerun()

    if time.time() - st.session_state.login_time > 1800:
        st.warning("Sessão expirada. Faça login novamente.")
        st.session_state.logged_in = False
        st.rerun()

    ComponentesInterface.configurar_pagina()
    ComponentesInterface.exibir_cabecalho()
    
    controles = ComponentesInterface.criar_painel_controle()
    st.session_state.modo_atual = controles['modo_operacao']
    
    dados = GerenciadorDados.carregar_registros()
    
    modulos = {
        'Administrativo': ModuloAdministrativo.exibir_painel,
        'Controle Pátio': ModuloPatioOperacional.exibir_painel,
        'Informações Motoristas': ModuloMotoristas.exibir_painel,
        'Relatórios': ModuloRelatorios.exibir_painel
    }
    
    modulos[st.session_state.modo_atual](dados)
    ComponentesInterface.gerenciar_atualizacao_automatica()

if __name__ == '__main__':
    main()