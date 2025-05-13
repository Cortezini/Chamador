import streamlit as st
import pandas as pd
import numpy as np
import re
import os
import base64
from datetime import datetime, timedelta
from scipy.io.wavfile import write
from pathlib import Path

# ================ CONFIGURAÇÕES GLOBAIS ================
CONFIG = {
    'colors': {
        'primary': '#FF5733',
        'secondary': '#C70039',
        'text': '#2c3e50',
        'background': '#f8f9fa'
    },
    'page_title': 'Painel BDM',
    'page_icon': 'assets/bdm.ico',
    'layout': 'wide',
    'data_file': 'chamados.csv',
    'sound_settings': {
        'sample_rate': 44100,
        'duration': 2,
        'frequency': 440,
        'alert_path': Path('assets/som_alerta.wav')   
    },
    'css_file': 'style.css',
    'validations': {
        'phone_regex': r'^\(\d{2}\) \d{4,5}-\d{4}$',
        'plate_regex': r'^[A-Za-z]{3}[- ]?[\dA-Za-z]{4}$',
        'password_regex': r'^\d{3}$',
        'name_regex': r'^[A-Za-zÀ-ÿ\s]{5,}$'
    }
}

# ================ INICIALIZAÇÃO DO SESSION STATE ================
SESSION_DEFAULTS = {
    'last_update': datetime.now(),
    'last_call_time': None,
    'sound_played': False,
    'som_ativado': True,
    'auto_update': False,
    'current_mode': None
}

for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ================ FUNÇÕES DE UTILIDADE ================
def setup_page():
    """Configurações iniciais da página"""
    st.set_page_config(
        page_title=CONFIG['page_title'],
        layout=CONFIG['layout'],
        page_icon=CONFIG['page_icon']
    )
    
    Path('assets').mkdir(exist_ok=True)
    load_external_css(CONFIG['css_file'])
    ensure_alert_sound()

def load_external_css(file_path: str):
    """Carrega CSS externo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            css = f.read()
        st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Arquivo de estilo não encontrado: {file_path}")

# ================ GERENCIAMENTO DE ÁUDIO ================
def ensure_alert_sound():
    """Garante a existência do arquivo de som"""
    sound_path = CONFIG['sound_settings']['alert_path']
    if not sound_path.exists():
        generate_alert_sound()

def generate_alert_sound():
    """Gera o arquivo de som"""
    settings = CONFIG['sound_settings']
    t = np.linspace(0, settings['duration'], int(settings['sample_rate'] * settings['duration']), False)
    wave = 0.5 * np.sin(2 * np.pi * settings['frequency'] * t)
    audio = np.int16(wave * 32767)
    write(str(settings['alert_path']), settings['sample_rate'], audio)

def play_alert_sound():
    """Reproduz o som de alerta uma única vez por chamado"""
    if st.session_state.som_ativado and not st.session_state.sound_played:
        try:
            with open(CONFIG['sound_settings']['alert_path'], 'rb') as f:
                audio_bytes = f.read()
                st.audio(audio_bytes, format='audio/wav', autoplay=True)
                st.session_state.sound_played = True
        except Exception as e:
            st.error(f"Falha ao reproduzir som: {str(e)}")

# ================ GERENCIAMENTO DE DADOS ================
def load_data() -> pd.DataFrame:
    """Carrega ou inicializa os dados"""
    columns = [
        'motorista', 'contato', 'transportadora', 'senha', 'placa',
        'cliente', 'vendedor', 'destino', 'doca', 'status', 'chamado_em'
    ]
    
    try:
        df = pd.read_csv(
            CONFIG['data_file'],
            parse_dates=['chamado_em'],
            dtype={col: str for col in columns if col != 'chamado_em'}
        )
        df['doca'] = df['doca'].fillna('')
        df['destino'] = df['destino'].fillna('')
        return df
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=columns)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame(columns=columns)

def save_data(df: pd.DataFrame):
    """Salva os dados atualizados"""
    try:
        df.to_csv(CONFIG['data_file'], index=False)
    except Exception as e:
        st.error(f"Erro ao salvar dados: {str(e)}")

# ================ COMPONENTES DA INTERFACE ================
def render_header():
    """Renderiza o cabeçalho com ícone correto"""
    try:
        # Converter o ícone para base64
        with open(CONFIG['page_icon'], "rb") as f:
            icon_data = base64.b64encode(f.read()).decode()
        
        st.markdown(f'''
            <div class='header'>
                <img src="data:image/x-icon;base64,{icon_data}" width="30" style="vertical-align: middle;">
                Painel de Chamadas BDM
            </div>
        ''', unsafe_allow_html=True)
        
    except FileNotFoundError:
        st.error("Ícone não encontrado em: {}".format(CONFIG['page_icon']))
        st.markdown('''
            <div class='header'>
                Painel de Chamadas BDM
            </div>
        ''', unsafe_allow_html=True)

def render_controls() -> dict:
    """Renderiza os controles da sidebar"""
    with st.sidebar:
        st.title('Controles')
        return {
            'modo': st.selectbox('Modo', ['Painel ADM', 'Painel Pátio', 'Painel Motorista']),
            'som_ativado': st.checkbox('Som Ativo', st.session_state.som_ativado),
            'auto_update': st.checkbox('Auto Refresh (15s)', st.session_state.auto_update)
        }

# ================ PAINEL ADMINISTRATIVO ================
def render_admin_panel(df: pd.DataFrame):
    """Interface do Painel Administrativo"""
    st.subheader('Gestão de Motoristas')
    
    with st.expander('📊 Estatísticas Operacionais'):
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Cadastrados", len(df))
        col2.metric("Aguardando", len(df[df['status'] == 'Aguardando']))
        col3.metric("Em Operação", len(df[df['status'].isin(['Chamado', 'Em Progresso'])]))

    with st.form("Novo Motorista", clear_on_submit=True):
        st.markdown("**Dados Obrigatórios** (*)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            motorista = st.text_input(
                'Nome Completo*',
                placeholder="Ex: João da Silva"
            )
            
            contato = st.text_input(
                'Contato*', 
                max_chars=15,
                placeholder="(XX) 99999-9999"
            )
            
            placa = st.text_input(
                'Placa do Veículo*',
                max_chars=7,
                placeholder="AAA0A00"
            )

        with col2:
            senha = st.text_input(
                'Senha de Acesso',
                max_chars=3,
                placeholder="123"
            )
            
            transportadora = st.text_input(
                'Transportadora*',
                placeholder="Nome da transportadora"
            )
            
            cliente = st.text_input(
                'Cliente',
                placeholder="Destinatário da carga"
            )

        vendedor = st.text_input('Vendedor Responsável')

        if st.form_submit_button('Cadastrar Motorista'):
            errors = []
            valid = CONFIG['validations']

            if not motorista or not re.match(valid['name_regex'], motorista, re.IGNORECASE):
                errors.append("Nome inválido (mínimo 5 caracteres alfabéticos)")
                
            if not contato or not re.match(valid['phone_regex'], contato):
                errors.append("Formato de contato inválido (use (XX) XXXX-XXXX)")
                
            if not placa or not re.fullmatch(valid['plate_regex'], placa.upper().replace(' ', '').replace('-', ''), re.IGNORECASE):
                errors.append("Placa inválida (formato incorreto)")
                
            if senha and not re.fullmatch(valid['password_regex'], senha):
                errors.append("Senha deve conter exatamente 3 dígitos")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                novo_registro = {
                    'motorista': motorista.title(),
                    'contato': contato,
                    'transportadora': transportadora.strip().title(),
                    'senha': senha or 'N/A',
                    'placa': placa.upper().replace('-', ''),
                    'cliente': cliente.title() if cliente else 'Não informado',
                    'vendedor': vendedor.title() if vendedor else 'Não informado',
                    'destino': '',
                    'doca': '',
                    'status': 'Aguardando',
                    'chamado_em': pd.NaT
                }
                
                df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
                save_data(df)
                st.success('Cadastro realizado com sucesso!')
                st.balloons()

    st.divider()
    st.dataframe(
        df[['motorista', 'placa', 'transportadora', 'status']],
        use_container_width=True,
        column_config={
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["Aguardando", "Chamado", "Em Progresso", "Finalizado"],
                default="Aguardando"
            )
        }
    )

# ================ PAINEL PÁTIO ================
def render_yard_panel(df: pd.DataFrame):
    """Interface de Controle Operacional"""
    st.subheader("Controle de Docas")
    
    # Mostrar operações em andamento
    operacoes_ativas = df[df['status'].isin(['Chamado', 'Em Progresso'])]
    
    if not operacoes_ativas.empty:
        st.markdown("### Operações em Andamento")
        for idx, row in operacoes_ativas.iterrows():
            with st.container(border=True):
                cols = st.columns([3, 1, 1, 2, 2])
                
                cols[0].markdown(f"""
                **Motorista:** {row['motorista']}  
                **Transportadora:** {row['transportadora']}  
                **Placa:** `{row['placa']}`
                """)
                
                cols[1].markdown(f"**Doca:**  \n`{row['doca'] or '---'}`")
                cols[2].markdown(f"**Destino:**  \n`{row['destino'] or '---'}`")
                
                with cols[3]:
                    nova_doca = st.text_input(
                        "Nova Doca",
                        value=row['doca'],
                        key=f'nova_doca_{idx}',
                        placeholder="Nº doca"
                    )
                    
                with cols[4]:
                    novo_destino = st.text_input(
                        "Novo Destino",
                        value=row['destino'],
                        key=f'novo_destino_{idx}',
                        placeholder="Localização"
                    )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🔄 Atualizar", key=f'update_{idx}'):
                        df.at[idx, 'doca'] = nova_doca
                        df.at[idx, 'destino'] = novo_destino
                        df.at[idx, 'status'] = 'Em Progresso'
                        save_data(df)
                        st.rerun()
                
                with col_btn2:
                    if st.button("✅ Finalizar", key=f'finish_{idx}', type='primary'):
                        df.at[idx, 'status'] = 'Finalizado'
                        save_data(df)
                        st.rerun()

    # Mostrar motoristas aguardando
    st.markdown("### Novos Chamados")
    aguardando = df[df['status'] == 'Aguardando']
    
    if aguardando.empty:
        st.info('Nenhum motorista aguardando')
        return

    for idx, row in aguardando.iterrows():
        with st.container(border=True):
            cols = st.columns([3, 1, 1, 2])
            
            cols[0].markdown(f"""
            **Motorista:** {row['motorista']}  
            **Transportadora:** {row['transportadora']}
            """)
            
            cols[1].metric("Placa", row['placa'])
            cols[2].metric("Senha", row['senha'])
            
            with cols[3]:
                doca = st.text_input(
                    "Doca Inicial",
                    key=f'doca_{idx}',
                    placeholder="Nº doca"
                )
                destino = st.text_input(
                    "Destino Inicial",
                    key=f'dest_{idx}',
                    placeholder="Localização"
                )
                
                if st.button("▶️ Iniciar Operação", key=f'start_{idx}'):
                    df.at[idx, 'status'] = 'Chamado'
                    df.at[idx, 'chamado_em'] = datetime.now()
                    df.at[idx, 'doca'] = doca
                    df.at[idx, 'destino'] = destino
                    save_data(df)
                    st.rerun()

# ================ PAINEL MOTORISTA ================
def render_driver_panel(df: pd.DataFrame):
    """Interface de Informações para Motoristas"""
    st.subheader("Painel de Orientação")
    
    # Verificar operações ativas
    operacoes = df[df['status'].isin(['Chamado', 'Em Progresso'])].sort_values('chamado_em', ascending=False)
    
    if operacoes.empty:
        st.info('Nenhuma operação ativa no momento')
        st.session_state.sound_played = False
        return

    # Verificar novo chamado
    current_call = operacoes.iloc[0]['chamado_em']
    if st.session_state.last_call_time != current_call:
        st.session_state.last_call_time = current_call
        st.session_state.sound_played = False
    
    if not st.session_state.sound_played:
        play_alert_sound()
        st.session_state.sound_played = True

    # Exibir operação atual
    operacao = operacoes.iloc[0]
    with st.container(border=True):
        cols = st.columns([2, 1, 1, 2])
        
        cols[0].markdown(f"""
        ### {operacao['motorista']}
        **Placa:** {operacao['placa']}  
        **Transportadora:** {operacao['transportadora']}
        """)
        
        cols[1].markdown(f"""
        <div style="font-size:26px; color:{CONFIG['colors']['primary']}; 
                    font-weight:bold; text-align:center;">
        DOCA<br>
        {operacao['doca'] or '---'}
        </div>
        """, unsafe_allow_html=True)
        
        cols[2].markdown(f"""
        <div style="font-size:26px; color:{CONFIG['colors']['text']}; 
                    font-weight:bold; text-align:center;">
        DESTINO<br>
        {operacao['destino'] or '---'}
        </div>
        """, unsafe_allow_html=True)
        
        cols[3].markdown(f"""
        **Início da Operação:**  
        {operacao['chamado_em'].strftime('%d/%m/%Y %H:%M')}
        """)

# ================ CONTROLE DE ATUALIZAÇÃO ================
def handle_auto_refresh():
    """Gerencia a atualização automática com intervalo de 15 segundos"""
    if st.session_state.auto_update and st.session_state.current_mode in ['Painel Pátio', 'Painel Motorista']:
        now = datetime.now()
        elapsed = (now - st.session_state.last_update).total_seconds()
        
        if elapsed >= 15:
            st.session_state.last_update = now
            st.rerun()

# ================ EXECUÇÃO PRINCIPAL ================
def main():
    setup_page()
    render_header()
    
    controls = render_controls()
    st.session_state.current_mode = controls['modo']
    df = load_data()
    
    st.session_state.update({
        'som_ativado': controls['som_ativado'],
        'auto_update': controls['auto_update']
    })

    if controls['modo'] == 'Painel ADM':
        render_admin_panel(df)
    elif controls['modo'] == 'Painel Pátio':
        render_yard_panel(df)
    else:
        render_driver_panel(df)

    handle_auto_refresh()
    
    # Exibir status de atualização
    if st.session_state.auto_update and st.session_state.current_mode in ['Painel Pátio', 'Painel Motorista']:
        st.markdown(f"""
        <div class='auto-update-status'>
            Última atualização: {datetime.now().strftime('%H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)

if __name__ == '__main__':
    main()