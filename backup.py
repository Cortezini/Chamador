# sistema_painel_logistica.py
"""
Sistema Integrado de Gestão Logística - Painel BDM

Módulo principal para gestão operacional de:
- Cadastro de motoristas e transportadoras
- Controle em tempo real de docas e operações
- Painel informativo para motoristas
- Geração de relatórios analíticos

Desenvolvido por: [Matheus Cortezini]
Versão: 2.0
Última atualização: [Data]
"""

import streamlit as st
import pandas as pd
import numpy as np
import re
import base64
import time
from datetime import datetime, timedelta
from pathlib import Path
from scipy.io.wavfile import write
from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime
from sqlalchemy.exc import NoSuchTableError


# 1) Cria o engine SQLite
SQLITE_FILE = 'registros_chamados.db'
ENGINE = create_engine(
    f'sqlite:///{SQLITE_FILE}',
    connect_args={"check_same_thread": False}
)

# 2) Metadata sem bind
META = MetaData()

def criar_tabela_if_not_exists():
    """ Garante que a tabela 'chamados' exista no SQLite """
    try:
        # tenta carregar a tabela existente
        Table('chamados', META, autoload_with=ENGINE)
    except NoSuchTableError:

        tabela = Table(
        'chamados', META,
            Column('motorista', String),
            Column('contato', String),
            Column('transportadora', String),
            Column('senha', String),
            Column('placa', String),
            Column('cliente', String),
            Column('vendedor', String),
            Column('destino', String),
            Column('doca', String),
            Column('status', String),
            Column('chamado_em', DateTime),
            Column('finalizado_em', DateTime),
        )
    META.create_all(ENGINE)


# Chame isto uma vez, assim que o app iniciar:
criar_tabela_if_not_exists()



# ==================================================
# CONFIGURAÇÕES GLOBAIS
# ==================================================

CONFIGURACOES = {
    'interface': {
        'titulo_pagina': 'Painel BDM',
        'icone_pagina': 'assets/bdm.ico',
        'layout': 'wide',
        'cores': {
            'primaria': '#FF5733',
            'secundaria': '#C70039',
            'texto': '#2c3e50',
            'fundo': '#f8f9fa'
        },
        'opcoes_patio': {
            'destinos': ['UNIDADE 1', 'UNIDADE 2', 'NIGRAM'],
            'docas': [f'DOCA {n}' for n in range(1, 9)]
        }
    },
    
    'dados': {
        'colunas': [
            'motorista', 'contato', 'transportadora', 'senha', 'placa',
            'cliente', 'vendedor', 'destino', 'doca', 'status', 
            'chamado_em', 'finalizado_em'
        ]
    },
    'validacoes': {
        'telefone': r'^\(\d{2}\) \d{4,5}-\d{4}$',
        'placa': r'^[A-Za-z]{3}[- ]?[\dA-Za-z]{4}$',
        'senha': r'^\d{3}$',
        'nome': r'^[A-Za-zÀ-ÿ\s]{5,}$'
    },
    'audio': {
        'taxa_amostragem': 44100,
        'duracao_alerta': 2,
        'frequencia_alerta': 440,
        'caminho_audio': Path('assets/alerta_sonoro.wav')
    }
}

# ==================================================
# GERENCIAMENTO DE ESTADO
# ==================================================

ESTADO_INICIAL = {
    'ultima_atualizacao': datetime.now(),
    'ultimo_chamado': None,
    'alerta_reproduzido': False,
    'audio_habilitado': True,
    'atualizacao_automatica': False,
    'modo_atual': None,
    'feedback_patio': None
    
}

for key, value in ESTADO_INICIAL.items():
    if key not in st.session_state:
        st.session_state[key] = value


USUARIOS = {
    "PAULO":("Paulo1405", "administrador"),
    "MATHEUS":("Matheus1405", "administrador"),
    "admin":("senha123", "administrador"),
    "operador":("op@2025", "patio"),
    "faturamento":("fat@2025", "faturamento"),
}

# quem pode ver o quê
PERMISSOES = {
    'administrador': [
        'Administrativo',
        'Controle Pátio',
        'Informações Motoristas',
        'Relatórios'
    ],
    'patio': [
        'Controle Pátio',
        'Informações Motoristas'
    ],
    'faturamento': [
        'informações Motoristas',
        'controle Pátio'
    ]
}


def inicializar_estado_aplicacao():
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
        if key not in st.session_state:
            st.session_state[key] = value

# ==================================================
# UTILITÁRIOS DO SISTEMA
# ==================================================

def configurar_pagina():
    """Define configurações básicas da página"""
    st.set_page_config(
        page_title=CONFIGURACOES['interface']['titulo_pagina'],
        layout=CONFIGURACOES['interface']['layout'],
        page_icon=CONFIGURACOES['interface']['icone_pagina']
    )
    
    Path('assets').mkdir(exist_ok=True)
    carregar_estilos()
    verificar_arquivo_audio()

def carregar_estilos():
    """Carrega folha de estilos personalizada"""
    try:
        with open('style.css', 'r', encoding='utf-8') as arquivo_css:
            st.markdown(f'<style>{arquivo_css.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("Arquivo de estilos CSS não encontrado")

def verificar_arquivo_audio():
    """Garante a existência do arquivo de áudio de alerta"""
    caminho_audio = CONFIGURACOES['audio']['caminho_audio']
    if not caminho_audio.exists():
        gerar_audio_alerta()

def gerar_audio_alerta():
    """Gera arquivo de áudio para notificações"""
    config = CONFIGURACOES['audio']
    tempo = np.linspace(0, config['duracao_alerta'], 
                       int(config['taxa_amostragem'] * config['duracao_alerta']), False)
    onda = 0.5 * np.sin(2 * np.pi * config['frequencia_alerta'] * tempo)
    audio = np.int16(onda * 32767)
    write(str(config['caminho_audio']), config['taxa_amostragem'], audio)

# ==================================================
# GERENCIAMENTO DE DADOS
# ==================================================


class GerenciadorDados:
    @staticmethod
    def carregar_registros():
        try:
            df = pd.read_sql_table(
                'chamados',
                con=ENGINE,
                parse_dates=['chamado_em', 'finalizado_em']
            )
            return df.fillna('')
        except Exception as e:
            st.error(f"Falha ao carregar dados do SQLite: {e}")
            return pd.DataFrame(columns=CONFIGURACOES['dados']['colunas'])

    @staticmethod
    def salvar_registros(dataframe):
        try:
            dataframe.to_sql(
                'chamados',
                con=ENGINE,
                index=False,
                if_exists='replace'
            )
        except Exception as e:
            st.error(f"Erro ao salvar dados no SQLite: {e}")

# ==================================================
# COMPONENTES DE INTERFACE
# ==================================================

class ComponentesInterface:

    @staticmethod
    def criar_painel_controle():
        """Renderiza a barra lateral de controles, filtrando por perfil."""
        with st.sidebar:
            st.title('Configurações')

            # pega o papel do usuário (setado no login)
            papel = st.session_state.get('user_role', None)
            # busca as páginas permitidas; se papel inválido, lista vazia
            opcoes = PERMISSOES.get(papel, [])

            # se não tiver opção, avisa e sai
            if not opcoes:
                st.error("Você não tem permissão para acessar este sistema.")
                st.stop()

            # selectbox só com as opções permitidas
            modo = st.selectbox('Modo de Operação', opcoes)

            audio = st.checkbox(
                'Ativar Notificações Sonoras',
                st.session_state.audio_habilitado
            )
            auto = st.checkbox(
                'Atualização Automática (15s)',
                st.session_state.atualizacao_automatica
            )

        return {
            'modo_operacao': modo,
            'audio_ativo': audio,
            'atualizacao_automatica': auto
        }
    
    
    @staticmethod
    def exibir_cabecalho():
        """Renderiza o cabeçalho da aplicação"""
        try:
            with open(CONFIGURACOES['interface']['icone_pagina'], "rb") as arquivo_icone:
                icone_base64 = base64.b64encode(arquivo_icone.read()).decode()
            
            st.markdown(f'''
                <div class='cabecalho'>
                    <img src="data:image/x-icon;base64,{icone_base64}" width="30">
                    {CONFIGURACOES['interface']['titulo_pagina']}
                </div>
            ''', unsafe_allow_html=True)
        except FileNotFoundError:
            st.markdown(
                f"<div class='cabecalho'>{CONFIGURACOES['interface']['titulo_pagina']}</div>",
                unsafe_allow_html=True
            )

    @staticmethod
    def exibir_notificacao():
        """Exibe notificações do sistema"""
        if st.session_state.feedback_patio:
            tipo, mensagem = st.session_state.feedback_patio
            if tipo == 'sucesso':
                st.success(mensagem, icon="✅")
            else:
                st.error(mensagem, icon="⚠️")
            del st.session_state.feedback_patio

# ==================================================
# MÓDULOS PRINCIPAIS
# ==================================================

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

# ==================================================
# CONTROLE PRINCIPAL
# ==================================================

def login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        return

    st.sidebar.title("🔒 Login")
    raw_username = st.sidebar.text_input("Usuário", key="login_user")
    password = st.sidebar.text_input("Senha", type="password", key="login_pass")

    username = raw_username.strip().upper()
    error_container = st.sidebar.empty()

    if st.sidebar.button("Entrar", key="login_btn"):
        user = USUARIOS.get(username)
        if user and user[0] == password:
            st.session_state.update({
                'user': username,
                'user_role': user[1],
                'logged_in': True,
                'login_time': time.time()    # <— aqui
            })
            st.rerun()
        else:
            error_container.error("Usuário ou senha inválidos")

def main():
    inicializar_estado_aplicacao()

    # 1) se não está logado, mostra o formulário e sai
    if not st.session_state.logged_in:
        login()
        return

    # 2) agora sim: checa expiração a partir de quando foi feito login
    if time.time() - st.session_state.login_time > 1800:
        st.warning("Sessão expirada, faça login novamente.")
        st.session_state.logged_in = False
        st.rerun()

    configurar_pagina()
    ComponentesInterface.exibir_cabecalho()

    controles = ComponentesInterface.criar_painel_controle()
    st.session_state.modo_atual = controles['modo_operacao']

    # 4) carrega dados e chama o módulo
    dados = GerenciadorDados.carregar_registros()
    modulos = {
        'Administrativo': ModuloAdministrativo.exibir_painel,
        'Controle Pátio': ModuloPatioOperacional.exibir_painel,
        'Informações Motoristas': ModuloMotoristas.exibir_painel,
        'Relatórios': ModuloRelatorios.exibir_painel
    }
    modulos[st.session_state.modo_atual](dados)

    _gerenciar_atualizacao_automatica()


def _gerenciar_atualizacao_automatica():
    """Controla a atualização automática do sistema"""
    if st.session_state.atualizacao_automatica and st.session_state.modo_atual in ['Controle Pátio', 'Informações Motoristas']:
        if (datetime.now() - st.session_state.ultima_atualizacao).seconds >= 15:
            st.session_state.ultima_atualizacao = datetime.now()
            st.rerun()

if __name__ == '__main__':
    main()