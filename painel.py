import streamlit as st
import pandas as pd
import numpy as np
import re
import os
import base64
from datetime import datetime
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
    'last_call': None,
    'sound_played': False,
    'som_ativado': True,
    'auto_update': False
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

def get_image_base64(path: str) -> str:
    """Converte imagem para base64"""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.error(f"Imagem não encontrada: {path}")
        return ""

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
    """Reproduz o som de alerta"""
    if st.session_state.som_ativado:
        try:
            with open(CONFIG['sound_settings']['alert_path'], 'rb') as f:
                audio_bytes = f.read()
                st.audio(audio_bytes, format='audio/wav', autoplay=True)
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
        # Garante campos vazios como string
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
    """Renderiza o cabeçalho"""
    img_base64 = get_image_base64(CONFIG['page_icon'])
    st.markdown(f'''
        <div class='header'>
            <img src="data:image/x-icon;base64,{img_base64}" width="30">
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
            'auto_update': st.checkbox('Auto Refresh', st.session_state.auto_update),
            'intervalo': st.slider('Intervalo (s)', 1, 30, 5)
        }

# ================ PAINEL ADMINISTRATIVO ================
def render_admin_panel(df: pd.DataFrame):
    """Interface do Painel Administrativo"""
    st.subheader('Gestão de Motoristas')
    
    with st.expander('📊 Estatísticas Operacionais'):
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Cadastrados", len(df))
        col2.metric("Aguardando", len(df[df['status'] == 'Aguardando']))
        col3.metric("Em Operação", len(df[df['status'] == 'Chamado']))

    with st.form("Novo Motorista", clear_on_submit=True):
        st.markdown("**Dados Obrigatórios** (*)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            motorista = st.text_input(
                'Nome Completo*',
                placeholder="Ex: João da Silva",
                help="Nome completo conforme documento oficial"
            )
            
            contato = st.text_input(
                'Contato*', 
                max_chars=15,
                placeholder="(XX) 99999-9999",
                help="Número para contato imediato"
            )
            
            placa = st.text_input(
                'Placa do Veículo*',
                max_chars=8,
                placeholder="AAA0A00",
                help="Formato Mercosul ou antigo"
            )

        with col2:
            senha = st.text_input(
                'Senha de Acesso',
                max_chars=3,
                placeholder="123",
                help="3 dígitos numéricos"
            )
            
            transportadora = st.text_input(
                'Transportadora*',
                placeholder="Nome completo da empresa",
                help="Razão social cadastrada"
            )
            
            cliente = st.text_input(
                'Cliente',
                placeholder="Destinatário da carga",
                help="Empresa beneficiária"
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
                options=["Aguardando", "Chamado", "Finalizado"],
                default="Aguardando"
            )
        }
    )

# ================ PAINEL PÁTIO ================
def render_yard_panel(df: pd.DataFrame):
    """Interface de Controle Operacional"""
    st.subheader("Controle de Docas")
    
    with st.expander("➕ Nova Operação", expanded=True):
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
                **Cliente:** {row['cliente']}
                """)
                
                cols[1].metric("Placa", row['placa'])
                cols[2].metric("Senha", row['senha'])
                
                with cols[3]:
                    with st.form(key=f'form_{idx}'):
                        doca = st.text_input(
                            "Nº Doca",
                            value='',
                            key=f'doca_{idx}',
                            placeholder="Digite o número",
                            max_chars=3
                        )
                        
                        destino = st.text_input(
                            "Destino Final",
                            value='',
                            key=f'dest_{idx}',
                            placeholder="Informe o destino",
                            max_chars=20
                        )
                        
                        if st.form_submit_button("Iniciar Operação", type='primary'):
                            df.at[idx, 'status'] = 'Chamado'
                            df.at[idx, 'chamado_em'] = datetime.now()
                            df.at[idx, 'doca'] = doca
                            df.at[idx, 'destino'] = destino
                            save_data(df)
                            st.session_state.last_call = datetime.now()
                            st.rerun()

# ================ PAINEL MOTORISTA ================
def render_driver_panel(df: pd.DataFrame):
    """Interface de Informações para Motoristas"""
    st.subheader("Painel de Orientação")
    
    # Verificar novos chamados
    current_calls = df[df['status'] == 'Chamado']
    if not current_calls.empty:
        latest_call = current_calls.iloc[0]['chamado_em']
        
        if st.session_state.last_call != latest_call:
            play_alert_sound()
            st.session_state.last_call = latest_call
            st.session_state.sound_played = True
    
    # Exibir informações
    if current_calls.empty:
        st.info('Nenhuma operação ativa no momento')
        return

    operacao = current_calls.iloc[0]
    
    with st.container(border=True):
        cols = st.columns([2, 1, 1, 2])
        
        # Informações Principais
        cols[0].markdown(f"""
        ### {operacao['motorista']}
        **Placa:** {operacao['placa']}  
        **Transportadora:** {operacao['transportadora']}
        """)
        
        # Doca com destaque
        cols[1].markdown(f"""
        <div style="font-size:26px; color:{CONFIG['colors']['primary']}; 
                    font-weight:bold; text-align:center;">
        DOCA<br>
        {operacao['doca'] or '---'}
        </div>
        """, unsafe_allow_html=True)
        
        # Destino com destaque
        cols[2].markdown(f"""
        <div style="font-size:26px; color:{CONFIG['colors']['text']}; 
                    font-weight:bold; text-align:center;">
        DESTINO<br>
        {operacao['destino'] or '---'}
        </div>
        """, unsafe_allow_html=True)
        
        # Detalhes Temporais
        cols[3].markdown(f"""
        **Início da Operação:**  
        {operacao['chamado_em'].strftime('%d/%m/%Y %H:%M')}
        """)

    # Histórico de Chamados
    st.divider()
    st.markdown("### Histórico Recente")
    
    historico = df[df['status'] == 'Chamado'].sort_values('chamado_em', ascending=False).iloc[1:]
    
    if historico.empty:
        st.info('Nenhuma operação anterior registrada')
        return

    for _, row in historico.iterrows():
        with st.container(border=True):
            cols = st.columns([3, 1, 1, 2])
            
            cols[0].markdown(f"**{row['motorista']}**")
            cols[1].markdown(f"`Doca {row['doca']}`")
            cols[2].markdown(f"`{row['destino']}`")
            cols[3].markdown(f"_{row['chamado_em'].strftime('%d/%m %H:%M')}_")

# ================ EXECUÇÃO PRINCIPAL ================
def main():
    setup_page()
    render_header()
    
    controls = render_controls()
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

    if controls['auto_update'] and st.session_state.auto_update:
        st.rerun()

if __name__ == '__main__':
    main()