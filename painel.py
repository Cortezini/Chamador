import streamlit as st
import pandas as pd
import numpy as np
import os
import base64
from datetime import datetime
from scipy.io.wavfile import write
from pathlib import Path

# ================ Configurações Globais ================
CONFIG = {
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
    'css_file': 'style.css'
}

# ================ Inicialização do Session State ================
SESSION_DEFAULTS = {
    'som_tocado': False,
    'som_ativado': True,
    'auto_update': False
}

for key, value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ================ Funções de Utilidade ================
def setup_page():
    """Configurações iniciais da página"""
    st.set_page_config(
        page_title=CONFIG['page_title'],
        layout=CONFIG['layout'],
        page_icon=CONFIG['page_icon']
    )
    
    # Criar diretórios necessários
    Path('assets').mkdir(exist_ok=True)
    
    # Carregar recursos externos
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

# ================ Gerenciamento de Áudio ================
def ensure_alert_sound():
    """Garante a existência do arquivo de som de alerta"""
    sound_path = CONFIG['sound_settings']['alert_path']
    if not sound_path.exists():
        generate_alert_sound()

def generate_alert_sound():
    """Gera o arquivo de som de alerta"""
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
                st.audio(f.read(), format='audio/wav')
        except Exception as e:
            st.error(f"Falha ao reproduzir som: {str(e)}")

# ================ Gerenciamento de Dados ================
def load_data() -> pd.DataFrame:
    """Carrega ou inicializa os dados dos chamados"""
    columns = [
        'motorista', 'contato', 'transportadora', 'senha', 'placa',
        'cliente', 'vendedor', 'destino', 'doca', 'status', 'chamado_em'
    ]
    
    try:
        return pd.read_csv(
            CONFIG['data_file'],
            parse_dates=['chamado_em'],
            dtype={col: str for col in columns if col != 'chamado_em'}
        )
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

# ================ Componentes da Interface ================
def render_header():
    """Renderiza o cabeçalho da página"""
    img_base64 = get_image_base64(CONFIG['page_icon'])
    st.markdown(f'''
        <div class='header'>
            <img src="data:image/x-icon;base64,{img_base64}" width="30">
            Painel de Chamadas BDM
        </div>
    ''', unsafe_allow_html=True)

def render_controls() -> dict:
    """Renderiza os controles da sidebar e retorna configurações"""
    with st.sidebar:
        st.title('Controles')
        return {
            'modo': st.selectbox('Modo', ['Painel ADM', 'Painel Pátio', 'Painel Motorista']),
            'som_ativado': st.checkbox('Som Ativo', st.session_state.som_ativado),
            'auto_update': st.checkbox('Auto Refresh', st.session_state.auto_update),
            'intervalo': st.slider('Intervalo (s)', 1, 30, 5)
        }

# ================ Painéis Específicos ================
def render_admin_panel(df: pd.DataFrame):
    """Interface do Painel Administrativo"""
    st.subheader('Painel Administrativo')

    with st.expander('Estatísticas'):
        total = len(df)
        counts = df['status'].value_counts().to_dict()
        st.metric("Total de Chamados", total)
        for status, quantidade in counts.items():
            st.metric(f"Status: {status}", quantidade)

    if st.button('Limpar Todos os Dados', type='primary'):
        save_data(pd.DataFrame(columns=df.columns))
        st.rerun()

    with st.form("Novo Motorista"):
        campos = {
            'motorista': st.text_input('Nome*'),
            'contato': st.text_input('Contato*'),
            'transportadora': st.text_input('Transportadora'),
            'senha': st.text_input('Senha'),
            'placa': st.text_input('Placa'),
            'cliente': st.text_input('Cliente'),
            'vendedor': st.text_input('Vendedor')
        }
        
        if st.form_submit_button('Adicionar Motorista'):
            if not all([campos['motorista'], campos['contato']]):
                st.error("Campos obrigatórios (*) não preenchidos")
            else:
                novo_registro = {k: v or '' for k, v in campos.items()}
                novo_registro.update({
                    'destino': '',
                    'doca': '',
                    'status': 'Aguardando',
                    'chamado_em': pd.NaT
                })
                df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
                save_data(df)
                st.success('Motorista cadastrado com sucesso!')

    st.dataframe(df, use_container_width=True)

def render_yard_panel(df: pd.DataFrame):
    """Interface do Painel do Pátio"""
    st.subheader('Painel do Pátio')
    aguardando = df[df['status'] == 'Aguardando']

    if aguardando.empty:
        st.info('Nenhum motorista aguardando')
        return

    for idx, row in aguardando.iterrows():
        with st.container():
            st.markdown(f"### {row['motorista']}")
            cols = st.columns([2, 1, 1])
            cols[0].write(f"**Senha:** {row['senha']}")
            cols[1].text_input('Doca', key=f'doca_{idx}', disabled=True)
            cols[2].text_input('Destino', key=f'dest_{idx}', disabled=True)
            
            if st.button('Chamar Motorista', key=f'btn_{idx}'):
                df.at[idx, 'status'] = 'Chamado'
                df.at[idx, 'chamado_em'] = datetime.now()
                save_data(df)
                st.success(f"Motorista {row['motorista']} chamado!")
                play_alert_sound()

def render_driver_panel(df: pd.DataFrame):
    """Interface do Painel do Motorista"""
    chamados = df[df['status'] == 'Chamado'].sort_values('chamado_em', ascending=False)
    
    if chamados.empty:
        st.info('Nenhum chamado ativo')
        return

    # Último chamado
    ultimo = chamados.iloc[0]
    with st.container():
        st.markdown('<div class="card-highlight">', unsafe_allow_html=True)
        cols = st.columns([1, 2, 2, 2])
        cols[0].markdown('## 🚨')
        cols[1].markdown(f"### {ultimo['motorista']}")
        cols[2].markdown(f"**Doca:** {ultimo['doca'] or '—'}")
        cols[3].markdown(f"**Destino:** {ultimo['destino'] or '—'}")
        
        info_cols = st.columns(3)
        info_cols[0].markdown(f"**Cliente:** {ultimo['cliente']}")
        info_cols[1].markdown(f"**Vendedor:** {ultimo['vendedor']}")
        info_cols[2].markdown(f"**Chamado em:** {ultimo['chamado_em'].strftime('%d/%m %H:%M')}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Histórico
    st.markdown('### 🕒 Histórico de Chamados')
    for idx, row in chamados.iloc[1:].iterrows():
        with st.container():
            st.markdown('<div class="card-muted">', unsafe_allow_html=True)
            cols = st.columns([3, 2, 1, 2])
            cols[0].write(f"**{row['motorista']}**")
            cols[1].write(f"Doca: {row['doca'] or '-'}")
            cols[2].write(row['chamado_em'].strftime('%H:%M'))
            cols[3].write(f"Cliente: {row['cliente']}")
            st.markdown('</div>', unsafe_allow_html=True)

# ================ Execução Principal ================
def main():
    setup_page()
    render_header()
    
    controls = render_controls()
    df = load_data()
    
    # Atualizar session state
    st.session_state.update({
        'som_ativado': controls['som_ativado'],
        'auto_update': controls['auto_update']
    })

    # Seleção de modo
    if controls['modo'] == 'Painel ADM':
        render_admin_panel(df)
    elif controls['modo'] == 'Painel Pátio':
        render_yard_panel(df)
    else:
        render_driver_panel(df)

    # Auto refresh
    if controls['auto_update']:
        st.rerun()

if __name__ == '__main__':
    main()