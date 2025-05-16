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


class ModuloRelatorios:
    """Módulo para geração de relatórios analíticos"""
    
    @classmethod
    def exibir_painel(cls, dataframe):
        """Interface principal do módulo de relatórios"""
        st.subheader("Relatórios Analíticos")
        filtros = cls._obter_filtros()
        dados_filtrados = cls._aplicar_filtros(dataframe, filtros)
        
        if not dados_filtrados.empty:
            dados_processados = cls._processar_dados(dados_filtrados)
            cls._exibir_tabela_relatorio(dados_processados)
            cls._exibir_metricas(dados_processados)
        else:
            st.info("Nenhum registro encontrado com os filtros selecionados")

    @classmethod
    def _obter_filtros(cls):
        """Obtém parâmetros de filtragem"""
        with st.container():
            colunas = st.columns(3)
            status_selecionado = colunas[0].selectbox(
                'Status',
                ['Todos', 'Aguardando', 'Chamado', 'Em Progresso', 'Finalizado']
            )
            periodo_selecionado = colunas[1].selectbox(
                'Período',
                ['Últimas 24h', 'Últimos 7 dias', 'Personalizado']
            )
            
            return {
                'status': status_selecionado,
                'periodo': periodo_selecionado,
                'datas': cls._obter_periodo_personalizado(colunas[2], periodo_selecionado)
            }

    @staticmethod
    def _obter_periodo_personalizado(coluna, periodo_selecionado):
        """Obtém intervalo de datas personalizado"""
        if periodo_selecionado == 'Personalizado':
            return (
                coluna.date_input("Data inicial"),
                coluna.date_input("Data final")
            )
        return (None, None)

    @classmethod
    def _aplicar_filtros(cls, dataframe, filtros):
        """Aplica filtros ao conjunto de dados"""
        df_filtrado = dataframe.copy()
        
        # Filtro por status
        if filtros['status'] != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['status'] == filtros['status']]
        
        # Filtro por período
        if filtros['periodo'] == 'Últimas 24h':
            corte = datetime.now() - timedelta(hours=24)
            df_filtrado = df_filtrado[df_filtrado['chamado_em'] >= corte]
        elif filtros['periodo'] == 'Últimos 7 dias':
            corte = datetime.now() - timedelta(days=7)
            df_filtrado = df_filtrado[df_filtrado['chamado_em'] >= corte]
        elif filtros['periodo'] == 'Personalizado' and all(filtros['datas']):
            inicio = datetime.combine(filtros['datas'][0], datetime.min.time())
            fim = datetime.combine(filtros['datas'][1], datetime.max.time())
            df_filtrado = df_filtrado[
                (df_filtrado['chamado_em'] >= inicio) & 
                (df_filtrado['chamado_em'] <= fim)
            ]
        
        return df_filtrado

    @classmethod
    def _processar_dados(cls, dataframe):
        """Processa dados para exibição"""
        df_processado = dataframe.copy()
        
        # Converter datas
        for coluna in ['chamado_em', 'finalizado_em']:
            df_processado[coluna] = pd.to_datetime(
                df_processado[coluna], errors='coerce', dayfirst=True
            )
        
        # Calcular tempo de espera
        agora = datetime.now()
        condicao = (df_processado['status'] == 'Finalizado') & df_processado['finalizado_em'].notna()
        
        df_processado['tempo_espera'] = np.where(
            condicao,
            (df_processado['finalizado_em'] - df_processado['chamado_em']).dt.total_seconds() / 60,
            (agora - df_processado['chamado_em']).dt.total_seconds() / 60
        )
        
        return df_processado

    @staticmethod
    def _exibir_tabela_relatorio(dataframe):
        """Exibe tabela de relatório formatada"""
        df_exibicao = dataframe.copy()
        
        # Formatar colunas temporais
        df_exibicao['chamado_em'] = df_exibicao['chamado_em'].dt.strftime('%d/%m/%Y %H:%M')
        df_exibicao['finalizado_em'] = df_exibicao['finalizado_em'].apply(
            lambda x: x.strftime('%d/%m/%Y %H:%M') if pd.notnull(x) else '--'
        )
        
        df_exibicao['tempo_formatado'] = df_exibicao['tempo_espera'].apply(
            lambda x: f"{int(x//60)}h {int(x%60)}min" if pd.notnull(x) else '--'
        )
        
        st.dataframe(
            df_exibicao[
                ['motorista', 'placa', 'transportadora', 'status',
                 'chamado_em', 'finalizado_em', 'tempo_formatado']
            ],
            use_container_width=True,
            height=600
        )

    @staticmethod
    def _exibir_metricas(dataframe):
        """Exibe métricas de desempenho"""
        with st.expander("📈 Métricas Detalhadas", expanded=True):
            colunas = st.columns(3)
            tempos_medios = dataframe.groupby('status')['tempo_espera'].mean()
            
            metricas = {
                'Aguardando': tempos_medios.get('Aguardando', 0),
                'Em Progresso': tempos_medios.get('Em Progresso', 0),
                'Finalizado': tempos_medios.get('Finalizado', 0)
            }
            
            for col, (status, valor) in zip(colunas, metricas.items()):
                col.metric(
                    f"Tempo Médio ({status})",
                    f"{valor:.1f} minutos" if valor > 0 else "N/A"
                )