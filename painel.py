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
from datetime import datetime, timedelta
from pathlib import Path
from scipy.io.wavfile import write

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
        }
    },
    'dados': {
        'arquivo_csv': 'registros_chamados.csv',
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
    'atualizar_patio': False,
    'atualizar_motoristas': False
}

def inicializar_estado_aplicacao():
    """Configura valores padrão no session_state"""
    for chave, valor in ESTADO_INICIAL.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor

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
    """Classe para operações de leitura/gravação de dados"""
    
    @staticmethod
    def carregar_registros():
        """Carrega dados dos registros de operações"""
        try:
            df = pd.read_csv(
                CONFIGURACOES['dados']['arquivo_csv'],
                parse_dates=['chamado_em', 'finalizado_em'],
                dayfirst=True,
                dtype={col: str for col in CONFIGURACOES['dados']['colunas'] 
                       if col not in ['chamado_em', 'finalizado_em']}
            )
            return df.fillna('')
        except FileNotFoundError:
            return pd.DataFrame(columns=CONFIGURACOES['dados']['colunas'])
        except Exception as erro:
            st.error(f"Falha ao carregar dados: {str(erro)}")
            return pd.DataFrame(columns=CONFIGURACOES['dados']['colunas'])

    @staticmethod
    def salvar_registros(dataframe):
        """Persiste os dados em arquivo CSV"""
        try:
            dataframe.to_csv(CONFIGURACOES['dados']['arquivo_csv'], index=False)
        except Exception as erro:
            st.error(f"Erro ao salvar dados: {str(erro)}")

# ==================================================
# COMPONENTES DE INTERFACE
# ==================================================

class ComponentesInterface:
    """Classe para componentes reutilizáveis da interface"""
    
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
            st.markdown(f'<div class="cabecalho">{CONFIGURACOES["interface"]["titulo_pagina"]}</div>', 
                        unsafe_allow_html=True)

    @staticmethod
    def criar_painel_controle():
        """Renderiza a barra lateral de controles"""
        with st.sidebar:
            st.title('Configurações')
            return {
                'modo_operacao': st.selectbox('Modo de Operação', 
                    ['Administrativo', 'Controle Pátio', 'Informações Motoristas', 'Relatórios']),
                'audio_ativo': st.checkbox('Ativar Notificações Sonoras', 
                    st.session_state.audio_habilitado),
                'atualizacao_automatica': st.checkbox('Atualização Automática (15s)', 
                    st.session_state.atualizacao_automatica)
            }

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
                    'placa': st.text_input('Placa*', max_chars=7, placeholder="AAA0A00")
                }
            
            with col2:
                dados.update({
                    'senha': st.text_input('Senha', max_chars=3, placeholder="123"),
                    'transportadora': st.text_input('Transportadora*', placeholder="Nome da empresa"),
                    'cliente': st.text_input('Cliente', placeholder="Destinatário")
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
        
        if not re.match(validacoes['nome'], dados['motorista'], re.IGNORECASE):
            erros.append("Nome inválido (mín. 5 caracteres alfabéticos)")
        if not re.match(validacoes['telefone'], dados['contato']):
            erros.append("Formato de telefone inválido")
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
        # ... código existente ...
        GerenciadorDados.salvar_registros(dataframe)
        st.session_state.atualizar_patio = True  # Nova linha
        st.success('Cadastro realizado!')
        st.balloons()

    @staticmethod
    def _tabela_edicao_registros(dataframe):
        """Tabela editável para gestão de registros"""
        st.divider()
        colunas = ['motorista', 'placa', 'transportadora', 'status']
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
        # Verificar necessidade de atualização
        if st.session_state.atualizar_patio:
            dataframe = GerenciadorDados.carregar_registros()
            st.session_state.atualizar_patio = False

    @classmethod
    def _exibir_operacoes_ativas(cls, operacoes, dataframe):
        """Exibe operações em andamento"""
        st.markdown("### Operações em Andamento")
        for indice, registro in operacoes.iterrows():
            with st.container(border=True):
                colunas = st.columns([3, 1, 1, 2, 2])
                
                colunas[0].markdown(
                    f"**Motorista:** {registro['motorista']}  \n"
                    f"**Transportadora:** {registro['transportadora']}  \n"
                    f"**Placa:** `{registro['placa']}`"
                )
                
                colunas[1].markdown(f"**Doca:**  \n`{registro['doca'] or '---'}`")
                colunas[2].markdown(f"**Destino:**  \n`{registro['destino'] or '---'}`")
                
                nova_doca = colunas[3].text_input(
                    "Nova Doca", 
                    value=registro['doca'], 
                    key=f'nova_doca_{indice}'
                )
                
                novo_destino = colunas[4].text_input(
                    "Novo Destino", 
                    value=registro['destino'], 
                    key=f'novo_destino_{indice}'
                )
                
                col_botoes = st.columns(2)
                if col_botoes[0].button("🔄 Atualizar", key=f'atualizar_{indice}'):
                    cls._atualizar_operacao(dataframe, indice, nova_doca, novo_destino)
                
                if col_botoes[1].button("✅ Finalizar", key=f'finalizar_{indice}', type='primary'):
                    cls._finalizar_operacao(dataframe, indice)

    @classmethod
    def _atualizar_operacao(cls, dataframe, indice, doca, destino):
        """Atualiza informações da operação"""
        # ... código existente ...
        st.session_state.atualizar_motoristas = True  # Nova linha

    @classmethod
    def _finalizar_operacao(cls, dataframe, indice):
        """Finaliza uma operação em andamento"""
        # ... código existente ...
        st.session_state.atualizar_motoristas = True  # Nova linha

    @classmethod
    def _iniciar_operacao(cls, dataframe, indice, doca, destino):
        """Inicia uma nova operação"""
        # ... código existente ...
        st.session_state.atualizar_motoristas = True  # Nova linha

    @classmethod
    def _finalizar_operacao(cls, dataframe, indice):
        """Finaliza uma operação em andamento"""
        try:
            dataframe.at[indice, 'status'] = 'Finalizado'
            dataframe.at[indice, 'finalizado_em'] = datetime.now()
            GerenciadorDados.salvar_registros(dataframe)
            st.session_state.feedback_patio = ('sucesso', 'Operação finalizada com sucesso!')
            st.rerun()
        except Exception as erro:
            st.session_state.feedback_patio = ('erro', f'Erro ao finalizar: {str(erro)}')
            st.rerun()

    @classmethod
    def _exibir_chamados_aguardando(cls, dataframe):
        """Exibe motoristas aguardando atendimento"""
        st.markdown("### Chamados Aguardando")
        aguardando = dataframe[dataframe['status'] == 'Aguardando']
        
        if aguardando.empty:
            st.info('Nenhum motorista aguardando atendimento')
            return

        for indice, registro in aguardando.iterrows():
            with st.container(border=True):
                colunas = st.columns([3, 1, 1, 2])
                
                colunas[0].markdown(
                    f"**Motorista:** {registro['motorista']}  \n"
                    f"**Transportadora:** {registro['transportadora']}"
                )
                
                colunas[1].metric("Placa", registro['placa'])
                colunas[2].metric("Senha", registro['senha'])
                
                doca = colunas[3].text_input("Doca Inicial", key=f'doca_{indice}')
                destino = colunas[3].text_input("Destino Inicial", key=f'dest_{indice}')
                
                if colunas[3].button("▶️ Iniciar Operação", key=f'iniciar_{indice}'):
                    cls._iniciar_operacao(dataframe, indice, doca, destino)

    @classmethod
    def _iniciar_operacao(cls, dataframe, indice, doca, destino):
        """Inicia uma nova operação"""
        try:
            dataframe.at[indice, 'status'] = 'Chamado'
            dataframe.at[indice, 'chamado_em'] = datetime.now()
            dataframe.at[indice, 'doca'] = doca
            dataframe.at[indice, 'destino'] = destino
            GerenciadorDados.salvar_registros(dataframe)
            st.session_state.feedback_patio = ('sucesso', 'Operação iniciada com sucesso!')
            st.rerun()
        except Exception as erro:
            st.session_state.feedback_patio = ('erro', f'Falha ao iniciar operação: {str(erro)}')
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

    @classmethod
    def exibir_painel(cls, dataframe):
        """Interface principal do módulo de motoristas"""
        # Verificar necessidade de atualização
        if st.session_state.atualizar_motoristas:
            dataframe = GerenciadorDados.carregar_registros()
            st.session_state.atualizar_motoristas = False
        
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

def main():
    """Função principal da aplicação"""
    inicializar_estado_aplicacao()
    configurar_pagina()
    ComponentesInterface.exibir_cabecalho()
    
    controles = ComponentesInterface.criar_painel_controle()
    st.session_state.modo_atual = controles['modo_operacao']
    dados = GerenciadorDados.carregar_registros()
    
    st.session_state.update({
        'audio_habilitado': controles['audio_ativo'],
        'atualizacao_automatica': controles['atualizacao_automatica']
    })

    modulos = {
        'Administrativo': ModuloAdministrativo.exibir_painel,
        'Controle Pátio': ModuloPatioOperacional.exibir_painel,
        'Informações Motoristas': ModuloMotoristas.exibir_painel,
        'Relatórios': ModuloRelatorios.exibir_painel
    }
    modulos[controles['modo_operacao']](dados)

    _gerenciar_atualizacao_automatica()

def _gerenciar_atualizacao_automatica():
    """Controla a atualização automática do sistema"""
    if st.session_state.atualizacao_automatica and st.session_state.modo_atual in ['Controle Pátio', 'Informações Motoristas']:
        if (datetime.now() - st.session_state.ultima_atualizacao).seconds >= 15:
            st.session_state.ultima_atualizacao = datetime.now()
            st.rerun()

if __name__ == '__main__':
    main()