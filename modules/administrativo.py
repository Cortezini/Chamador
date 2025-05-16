import streamlit as st
import pandas as pd
import numpy as np
import re
import base64
import time
from data.config import CONFIGURACOES
from datetime import datetime, timedelta
from data.manager import GerenciadorDados


class ModuloAdministrativo:
    """Módulo para gestão de cadastros e dados mestres"""
    
    @classmethod
    def exibir_painel(cls, dataframe):
        """Interface principal do módulo administrativo"""
        st.subheader('Gestão de Motoristas')
        cls._exibir_metricas_operacionais(dataframe)
        cls._formulario_cadastro_motorista(dataframe)
        cls._tabela_edicao_registros(dataframe)

    @staticmethod
    def _exibir_metricas_operacionais(dataframe):
        """Exibe indicadores-chave de desempenho"""
        with st.expander('📊 Métricas Operacionais', expanded=True):
            colunas = st.columns(3)
            metricas = {
                'Total Cadastrados': len(dataframe),
                'Aguardando': len(dataframe[dataframe['status'] == 'Aguardando']),
                'Em Operação': len(dataframe[dataframe['status'].isin(['Chamado', 'Em Progresso'])])
            }
            for col, (rotulo, valor) in zip(colunas, metricas.items()):
                col.metric(rotulo, valor)

    @classmethod
    def _formulario_cadastro_motorista(cls, dataframe):
        """Formulário para cadastro de novos motoristas"""
        with st.form("Novo Motorista", clear_on_submit=True):
            st.markdown("**Dados Obrigatórios** (*)")
            col1, col2 = st.columns(2)
            
            with col1:
                dados = {
                    'motorista': st.text_input('Nome Completo*', placeholder="Ex: João Silva"),
                    'contato': st.text_input('Contato*', max_chars=15, placeholder="(XX) 99999-9999"),
                    'placa': st.text_input('Placa*', max_chars=7, placeholder="AAA0A00"),
                    'destino': st.text_input('Destino', placeholder="Destino da carga")
                }
            
            with col2:
                dados.update({
                    'senha': st.text_input('Senha', max_chars=3, placeholder="123"),
                    'transportadora': st.text_input('Transportadora*', placeholder="Nome da empresa"),
                    'cliente': st.text_input('Cliente', placeholder="Destinatário"),
                })
            
            dados['vendedor'] = st.text_input('Vendedor Responsável')
            
            if st.form_submit_button('Cadastrar'):
                erros = cls._validar_dados_cadastro(dados)
                if not erros:
                    cls._adicionar_novo_registro(dataframe, dados)

    @classmethod
    def _validar_dados_cadastro(cls, dados):
        """Valida os dados do formulário de cadastro"""
        validacoes = CONFIGURACOES['validacoes']
        erros = []
        
        # Processar telefone
        raw_contato = dados['contato']
        digits = re.sub(r'\D', '', raw_contato)
        if len(digits) not in [10, 11]:
            erros.append("Número de telefone inválido. Deve ter 10 ou 11 dígitos.")
        else:
            # Formatar o telefone
            if len(digits) == 11:
                formatted_contato = f'({digits[:2]}) {digits[2:7]}-{digits[7:]}'
            else:
                formatted_contato = f'({digits[:2]}) {digits[2:6]}-{digits[6:]}'
            dados['contato'] = formatted_contato
            if not re.match(validacoes['telefone'], dados['contato']):
                erros.append("Formato de telefone inválido após formatação.")
        
        if not re.match(validacoes['nome'], dados['motorista'], re.IGNORECASE):
            erros.append("Nome inválido (mín. 5 caracteres alfabéticos)")
        if not re.fullmatch(validacoes['placa'], dados['placa'].upper().replace(' ', '')):
            erros.append("Placa inválida")
        if dados['senha'] and not re.fullmatch(validacoes['senha'], dados['senha']):
            erros.append("Senha deve ter 3 dígitos")
        
        for erro in erros:
            st.error(erro)
        return erros

    @staticmethod
    def _adicionar_novo_registro(dataframe, dados):
        """Adiciona novo registro ao DataFrame"""
        novo_registro = {
            **dados,
            'doca': '',
            'status': 'Aguardando',
            'chamado_em': pd.NaT,
            'finalizado_em': pd.NaT
        }
        novo_registro['placa'] = novo_registro['placa'].upper().replace('-', '')
        dataframe = pd.concat([dataframe, pd.DataFrame([novo_registro])], ignore_index=True)
        GerenciadorDados.salvar_registros(dataframe)
        st.success('Cadastro realizado!')
        st.balloons()

    @staticmethod
    def _tabela_edicao_registros(dataframe):
        """Tabela editável para gestão de registros"""
        st.divider()
        colunas = ['motorista', 'placa', 'transportadora', 'status' , 'destino']
        df_editado = st.data_editor(
            dataframe[colunas],
            use_container_width=True,
            column_config={
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Aguardando", "Chamado", "Em Progresso", "Finalizado"]
                )
            }
        )
        if not df_editado.equals(dataframe[colunas]):
            dataframe.update(df_editado)
            GerenciadorDados.salvar_registros(dataframe)
            st.rerun()