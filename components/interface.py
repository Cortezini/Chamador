import streamlit as st
import base64
import streamlit as st
from pathlib import Path
from data.config import CONFIGURACOES, PERMISSOES
from datetime import datetime, timedelta

class ComponentesInterface:
    @staticmethod
    def configurar_pagina():
        st.set_page_config(
            page_title=CONFIGURACOES['interface']['titulo_pagina'],
            page_icon=CONFIGURACOES['interface']['icone_pagina'],
            layout=CONFIGURACOES['interface']['layout']
        )
        ComponentesInterface.carregar_estilos()
        ComponentesInterface.verificar_assets()

    @staticmethod
    def carregar_estilos():
        try:
            with open('style.css', 'r', encoding='utf-8') as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        except FileNotFoundError:
            st.error("Arquivo CSS não encontrado")

    @staticmethod
    def verificar_assets():
        Path('assets').mkdir(exist_ok=True)

    @staticmethod
    def exibir_cabecalho():
        try:
            with open(CONFIGURACOES['interface']['icone_pagina'], "rb") as f:
                icone = base64.b64encode(f.read()).decode()
            st.markdown(f'''
                <div class='cabecalho'>
                    <img src="data:image/x-icon;base64,{icone}" width="30">
                    {CONFIGURACOES['interface']['titulo_pagina']}
                </div>
            ''', unsafe_allow_html=True)
        except FileNotFoundError:
            st.markdown(f"<div class='cabecalho'>{CONFIGURACOES['interface']['titulo_pagina']}</div>",
                        unsafe_allow_html=True)

    @staticmethod
    def criar_painel_controle():
        with st.sidebar:
            st.title('Configurações')
            papel = st.session_state.get('user_role')
            opcoes = PERMISSOES.get(papel, [])
            
            if not opcoes:
                st.error("Sem permissões")
                st.stop()
                
            modo = st.selectbox('Modo', opcoes)
            audio = st.checkbox('Ativar Som', st.session_state.audio_habilitado)
            auto = st.checkbox('Atualização Automática', st.session_state.atualizacao_automatica)
            
        return {'modo_operacao': modo, 'audio_ativo': audio, 'atualizacao_automatica': auto}

    @staticmethod
    def gerenciar_atualizacao_automatica():
        if st.session_state.atualizacao_automatica:
            tempo_decorrido = (datetime.now() - st.session_state.ultima_atualizacao).seconds
            if tempo_decorrido >= 15:
                st.session_state.ultima_atualizacao = datetime.now()
                st.rerun()


    @staticmethod
    def exibir_notificacao():
        """Exibe notificações do sistema"""
        if st.session_state.get('feedback_patio'):
            tipo, mensagem = st.session_state.feedback_patio
            if tipo == 'sucesso':
                st.success(mensagem, icon="✅")
            else:
                st.error(mensagem, icon="⚠️")
            del st.session_state.feedback_patio