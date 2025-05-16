import streamlit as st
import pandas as pd
import numpy as np
import re
import base64
import time
from data.config import CONFIGURACOES
from datetime import datetime, timedelta
from pathlib import Path
from data.manager import GerenciadorDados
from components.interface import ComponentesInterface
from components.audio import AudioManager


class ModuloMotoristas:
    """Módulo para exibição de informações aos motoristas"""
    
    @classmethod
    def exibir_painel(cls, dataframe):
        """Interface principal do módulo de motoristas"""
        st.subheader("Painel de Orientação para Motoristas")
        operacoes_ativas = cls._filtrar_operacoes_ativas(dataframe)
        
        if operacoes_ativas.empty:
            st.info('Nenhuma operação ativa no momento')
            st.session_state.alerta_reproduzido = False
            return
        
        cls._verificar_novo_chamado(operacoes_ativas)
        cls._exibir_operacao_atual(operacoes_ativas.iloc[0])

    @staticmethod
    def _filtrar_operacoes_ativas(dataframe):
        """Filtra operações ativas por data"""
        return dataframe[
            dataframe['status'].isin(['Chamado', 'Em Progresso'])
        ].sort_values('chamado_em', ascending=False)
    

    @staticmethod
    def _calcular_duracao(registro):
        """Calcula duração da operação formatada"""
        if pd.notnull(registro.get('chamado_em')) and pd.notnull(registro.get('finalizado_em')):
            delta = registro['finalizado_em'] - registro['chamado_em']
            horas = delta.seconds // 3600
            minutos = (delta.seconds % 3600) // 60
            return f"{horas}h {minutos}min"
        return "-"

    @classmethod
    def _verificar_novo_chamado(cls, operacoes):
        """Verifica e controla reprodução de alerta"""
        ultimo_chamado = operacoes.iloc[0]['chamado_em']
        
        if st.session_state.ultimo_chamado != ultimo_chamado:
            st.session_state.ultimo_chamado = ultimo_chamado
            st.session_state.alerta_reproduzido = False
        
        if not st.session_state.alerta_reproduzido and st.session_state.audio_habilitado:
            cls._reproduzir_alerta()
            st.session_state.alerta_reproduzido = True

    @staticmethod
    def _reproduzir_alerta():
        """Reproduz o alerta sonoro"""
        try:
            with open(CONFIGURACOES['audio']['caminho_audio'], 'rb') as arquivo_audio:
                st.audio(arquivo_audio.read(), format='audio/wav', autoplay=True)
        except Exception as erro:
            st.error(f"Falha ao reproduzir alerta: {str(erro)}")

    @staticmethod
    def _exibir_operacao_atual(operacao):
        """Exibe detalhes da operação atual"""
        with st.container(border=True):
            colunas = st.columns([2, 1, 1, 2])
            
            colunas[0].markdown(
                f"### {operacao.get('motorista', 'N/A')}  \n"
                f"**Placa:** {operacao.get('placa', 'N/A')}  \n"
                f"**Transportadora:** {operacao.get('transportadora', 'N/A')}"
            )
            
            colunas[1].markdown(
                f"<div class='doca-font'>DOCA<br>{operacao['doca'] or '---'}</div>", 
                unsafe_allow_html=True
            )
            
            colunas[2].markdown(
                f"<div class='destino-font'>DESTINO<br>{operacao['destino'] or '---'}</div>", 
                unsafe_allow_html=True
            )
            
            colunas[3].markdown(
                f"**Início:**  \n{operacao['chamado_em'].strftime('%d/%m/%Y %H:%M')}"
            )
    
    @classmethod
    def _verificar_novo_chamado(cls, operacoes):
        if (st.session_state.audio_habilitado and 
            not st.session_state.alerta_reproduzido and
            AudioManager.inicializar()):  # Verifica se o áudio está disponível
            
            if AudioManager.reproduzir_alerta():
                st.session_state.alerta_reproduzido = True