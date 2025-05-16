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

def login():
    if st.session_state.logged_in: return
    
    st.sidebar.title("🔒 Login")
    username = st.sidebar.text_input("Usuário").strip().upper()
    password = st.sidebar.text_input("Senha", type="password")
    
    if st.sidebar.button("Entrar"):
        from data.config import USUARIOS
        user = USUARIOS.get(username)
        if user and user[0] == password:
            st.session_state.update({
                'logged_in': True,
                'user': username,
                'user_role': user[1],
                'login_time': time.time()
            })
            st.rerun()
        else:
            st.sidebar.error("Credenciais inválidas")

def main():
    criar_tabela_if_not_exists()
    inicializar_estado()
    
    if not st.session_state.logged_in:
        login()
        return

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