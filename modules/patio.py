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


class ModuloPatioOperacional:
    """Módulo para controle de operações no pátio"""

    @classmethod
    def exibir_painel(cls, dataframe):
        """Interface principal do módulo de pátio"""
        st.subheader("Controle Operacional do Pátio")
        ComponentesInterface.exibir_notificacao()

        # Recarrega do CSV para ter sempre dados atualizados
        dataframe = GerenciadorDados.carregar_registros()

        tab1, tab2, tab3 = st.tabs([
            "🏗️ Operações Ativas",
            "📭 Chamados Aguardando",
            "🕰️ Histórico"
        ])

        with tab1:
            cls._exibir_operacoes_ativas(dataframe)
        with tab2:
            cls._exibir_chamados_aguardando(dataframe)
        with tab3:
            cls._exibir_operacoes_finalizadas(dataframe)

    @classmethod
    def _exibir_operacoes_ativas(cls, dataframe):
        """Exibe operações em andamento com layout otimizado"""
        operacoes = dataframe[dataframe['status'].isin(['Chamado', 'Em Progresso'])]
        
        if operacoes.empty:
            st.info("🌟 Nenhuma operação ativa no momento")
            return

        for indice, registro in operacoes.iterrows():
            with st.container():
                cols = st.columns([3, 1, 1, 2, 2, 1.5])

                # Coluna 0: Informações principais
                cols[0].markdown(
                    f"<div class='info-vertical'>"
                    f"<strong>Destino:</strong> {registro.get('destino','')}<br>"
                    f"<strong>Motorista:</strong> {registro.get('motorista','')}<br>"
                    f"<strong>Transportadora:</strong> {registro.get('transportadora','')}"
                    f"</div>", 
                    unsafe_allow_html=True
                )

                # Coluna da Placa
                cols[1].markdown(
                    f"<div class='info-destaque-box placa-box'>"
                    f"<span class='info-label'>PLACA</span>"
                    f"<div class='info-value'>{registro.get('placa','').upper().replace('-', '')}</div>"
                    f"</div>", 
                    unsafe_allow_html=True
                )

                # Coluna da Senha
                cols[2].markdown(
                    f"<div class='info-destaque-box senha-box'>"
                    f"<span class='info-label'>SENHA</span>"
                    f"<div class='info-value'>{registro.get('senha','')}</div>"
                    f"</div>", 
                    unsafe_allow_html=True
                )

                # Seleção de nova doca com selectbox
                nova_doca = cols[3].selectbox(
                    "📍 Nova Doca",
                    options=CONFIGURACOES['interface']['opcoes_patio']['docas'],
                    index=(CONFIGURACOES['interface']['opcoes_patio']['docas'].index(registro.get('doca',''))
                           if registro.get('doca','') in CONFIGURACOES['interface']['opcoes_patio']['docas'] else 0),
                    key=f'doca_edit_{indice}'
                )

                # Seleção de novo destino com selectbox
                novo_destino = cols[4].selectbox(
                    "🎯 Ajustar Destino",
                    options=CONFIGURACOES['interface']['opcoes_patio']['destinos'],
                    index=(CONFIGURACOES['interface']['opcoes_patio']['destinos'].index(registro.get('destino',''))
                           if registro.get('destino','') in CONFIGURACOES['interface']['opcoes_patio']['destinos'] else 0),
                    key=f'destino_edit_{indice}'
                )

                # Coluna 5: Botões de ação
                with cols[5]:
                    if st.button("🔄 Atualizar", key=f'atualizar_{indice}', use_container_width=True):
                        if cls._validar_atualizacao(nova_doca, novo_destino):
                            cls._atualizar_operacao(dataframe, indice, nova_doca, novo_destino)
                    if st.button("✅ Finalizar", key=f'finalizar_{indice}', use_container_width=True):
                        cls._finalizar_operacao(dataframe, indice)

    @classmethod
    def _exibir_chamados_aguardando(cls, dataframe):
        """Exibe chamados pendentes com destaque no destino"""
        aguardando = dataframe[dataframe['status'] == 'Aguardando']
        if aguardando.empty:
            st.info("✅ Todos os chamados foram atendidos")
            return

        for indice, registro in aguardando.iterrows():
            with st.container():
                cols = st.columns([3, 1, 1, 2, 1.5])

                cols[0].markdown(
                    f"**Chamado para:** {registro.get('destino','')}\n"
                    f"**Motorista:** {registro.get('motorista','')}\n"
                    f"**Transportadora:** {registro.get('transportadora','')}"
                )
                cols[1].metric("🚘 Placa", registro.get('placa',''))
                cols[2].metric("🔑 Senha", registro.get('senha',''))

                with cols[3]:
                    doca = st.selectbox(
                        "📍 Doca Designada",
                        options=CONFIGURACOES['interface']['opcoes_patio']['docas'],
                        index=(CONFIGURACOES['interface']['opcoes_patio']['docas'].index(registro.get('doca',''))
                               if registro.get('doca','') in CONFIGURACOES['interface']['opcoes_patio']['docas'] else 0),
                        key=f'doca_{indice}'
                    )
                    destino = st.selectbox(
                        "🎯 Destino Confirmado",
                        options=CONFIGURACOES['interface']['opcoes_patio']['destinos'],
                        index=(CONFIGURACOES['interface']['opcoes_patio']['destinos'].index(registro.get('destino',''))
                               if registro.get('destino','') in CONFIGURACOES['interface']['opcoes_patio']['destinos'] else 0),
                        key=f'dest_{indice}'
                    )
                with cols[4]:
                    if st.button("▶️ Iniciar Operação", key=f'iniciar_{indice}', use_container_width=True):
                        if cls._validar_inicio(doca, destino):
                            cls._iniciar_operacao(dataframe, indice, doca, destino)

    @classmethod
    def _exibir_operacoes_finalizadas(cls, dataframe):
        """Exibe histórico de operações com possibilidade de reabertura"""
        finalizadas = dataframe[dataframe['status'] == 'Finalizado']
        if finalizadas.empty:
            st.info("🕰️ Sem histórico de operações")
            return

        for indice, registro in finalizadas.iterrows():
            with st.container():
                cols = st.columns([4, 1, 1, 1.5])

                cols[0].markdown(
                    f"### ✅ Operação Finalizada\n"
                    f"**Destino:** {registro.get('destino','')}\n"
                    f"**Motorista:** {registro.get('motorista','')}\n"
                    f"**Transportadora:** {registro.get('transportadora','')}\n"
                    f"**Duração:** {cls._calcular_duracao(registro)}"
                )
                cols[1].metric("🚘 Placa", registro.get('placa',''))
                cols[2].metric("📍 Doca", registro.get('doca','N/A'))

                with cols[3]:
                    if st.button("↩️ Reabrir", key=f'reabrir_{indice}', use_container_width=True):
                        cls._reabrir_operacao(dataframe, indice)

    @staticmethod
    def _calcular_duracao(registro):
        """Calcula duração da operação"""
        if pd.notnull(registro.get('chamado_em')) and pd.notnull(registro.get('finalizado_em')):
            delta = registro['finalizado_em'] - registro['chamado_em']
            h = int(delta.total_seconds() // 3600)
            m = int((delta.total_seconds() % 3600) // 60)
            return f"{h}h {m}min"
        return "—"

    @staticmethod
    def _validar_inicio(doca, destino):
        erros = []
        if not doca.strip():   erros.append("Número da doca obrigatório")
        if not destino.strip(): erros.append("Destino obrigatório")
        for e in erros: st.error(e)
        return not erros

    @staticmethod
    def _validar_atualizacao(doca, destino):
        erros = []
        if not doca.strip():   erros.append("Nova doca obrigatório")
        if not destino.strip(): erros.append("Novo destino obrigatório")
        for e in erros: st.error(e)
        return not erros

    @classmethod
    def _iniciar_operacao(cls, dataframe, indice, doca, destino):
        df = dataframe.copy()
        df.at[indice, 'status']     = 'Chamado'
        df.at[indice, 'chamado_em'] = pd.Timestamp.now()
        df.at[indice, 'doca']       = doca.strip()
        df.at[indice, 'destino']    = destino.strip()
        GerenciadorDados.salvar_registros(df)
        st.session_state.feedback_patio = ('sucesso', f"Operação iniciada na doca {doca}")
        st.rerun()

    @classmethod
    def _atualizar_operacao(cls, dataframe, indice, doca, destino):
        df = dataframe.copy()
        alter = []
        if df.at[indice,'doca']    != doca.strip():
            alter.append(f"Doca: {df.at[indice,'doca']} → {doca}")
            df.at[indice,'doca'] = doca.strip()
        if df.at[indice,'destino'] != destino.strip():
            alter.append(f"Destino: {df.at[indice,'destino']} → {destino}")
            df.at[indice,'destino'] = destino.strip()
        if alter:
            df.at[indice,'status'] = 'Em Progresso'
            GerenciadorDados.salvar_registros(df)
            st.session_state.feedback_patio = ('sucesso', "\n".join(alter))
        st.rerun()

    @classmethod
    def _finalizar_operacao(cls, dataframe, indice):
        df = dataframe.copy()
        df.at[indice, 'status']       = 'Finalizado'
        df.at[indice, 'finalizado_em'] = pd.Timestamp.now()
        GerenciadorDados.salvar_registros(df)
        st.session_state.feedback_patio = ('sucesso', "🕰️ Operação finalizada")
        st.rerun()

    @classmethod
    def _reabrir_operacao(cls, dataframe, indice):
        df = dataframe.copy()
        df.at[indice, 'status'] = 'Em Progresso'
        df.at[indice, 'finalizado_em'] = pd.NaT
        GerenciadorDados.salvar_registros(df)
        st.session_state.feedback_patio = ('sucesso', "↩️ Operação reaberta")
        st.rerun()