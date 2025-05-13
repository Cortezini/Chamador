import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.io.wavfile import write
import os
import random

# ----- Configurações -----
st.set_page_config(page_title='Sistema de Chamadas', layout='wide', page_icon='🚛')  # DEVE SER O PRIMEIRO COMANDO

# ----- Estilo customizado com CSS -----
custom_css = '''
:root {
    --primary: #4e73df;
    --secondary: #1cc88a;
    --background: #f8f9fc;
    --card-bg: #ffffff;
    --text: #5a5c69;
    --radius: 12px;
    --spacing: 1rem;
    --font: 'Roboto', sans-serif;
}
body, .stApp {
    background: var(--background);
    color: var(--text);
    font-family: var(--font);
}
.header {
    font-size: 2.5rem;
    color: var(--primary);
    margin-bottom: var(--spacing);
}
.card {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: var(--spacing);
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    margin-bottom: var(--spacing);
}
''' 
st.markdown(f'<style>{custom_css}</style>', unsafe_allow_html=True)

# ----- Parâmetros de som e arquivo -----
SAMPLE_RATE, DURATION, FREQUENCY = 44100, 2, 440
ALERT_PATH = os.path.join('assets', 'alert.wav')
MUSIC_LIST = [os.path.join('assets', 'chamada.mp3')]  # Atualizado para o nome correto
DATA_CSV = 'chamados.csv'

# ----- Funções de áudio -----
def gerar_som():
    if not os.path.exists(ALERT_PATH):
        t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), False)
        wave = 0.5 * np.sin(2 * np.pi * FREQUENCY * t)
        audio = np.int16(wave * 32767)
        write(ALERT_PATH, SAMPLE_RATE, audio)

def tocar_som():
    """Toca o som de chamada."""
    if os.path.exists(MUSIC_LIST[0]):  # Verifica se o arquivo existe
        with open(MUSIC_LIST[0], 'rb') as f:
            st.audio(f.read(), format='audio/mp3')
    else:
        st.error("Erro: O arquivo de som 'chamada.mp3' não foi encontrado no diretório 'assets'.")

# ----- Leitura e gravação de dados -----
def carregar_dados():
    try:
        df = pd.read_csv(DATA_CSV, parse_dates=['chamado_em'])
    except FileNotFoundError:
        cols = ['motorista','contato','transportadora','senha','placa',
                'cliente','vendedor','destino','doca','status','chamado_em']
        df = pd.DataFrame(columns=cols)
        df.to_csv(DATA_CSV, index=False)
    return df

def salvar_dados(df):
    df.to_csv(DATA_CSV, index=False)

# ----- Sidebar -----
st.sidebar.title('Controles')
modo = st.sidebar.selectbox('Modo', ['Painel ADM', 'Painel Pátio', 'Painel Motorista'])
som_ativo = st.sidebar.checkbox('Som Ativo', True)
auto_update = st.sidebar.checkbox('Auto Refresh', False)
interval = st.sidebar.slider('Intervalo (s)', 1, 30, 5)

# ----- Auto refresh -----
if auto_update:
    st.experimental_rerun()

# ----- Título -----
st.markdown('<div class=\'header\'>🚛 Sistema de Chamadas Moderno</div>', unsafe_allow_html=True)

df = carregar_dados()

# ----- Painel ADM -----
if modo == 'Painel ADM':
    st.subheader('Painel Administrativo')
    with st.expander('Estatísticas'):
        total = len(df)
        counts = df['status'].value_counts().to_dict()
        st.write(f'Total: **{total}**')
        for k, v in counts.items():
            st.write(f'- {k}: **{v}**')
    if st.button('Limpar Tudo'):
        salvar_dados(pd.DataFrame(columns=df.columns))
        st.experimental_rerun()
    st.write('---')
    st.subheader('Adicionar Motorista')
    with st.form('add'):
        nome = st.text_input('Nome')
        contato = st.text_input('Contato')
        transportadora = st.text_input('Transportadora')
        senha = st.text_input('Senha')
        placa = st.text_input('Placa')
        cliente = st.text_input('Cliente')
        vendedor = st.text_input('Vendedor')
        ok = st.form_submit_button('Adicionar')
        if ok:
            if nome and contato:
                novo = {'motorista': nome, 'contato': contato, 'transportadora': transportadora, 'senha': senha,
                        'placa': placa, 'cliente': cliente, 'vendedor': vendedor,
                        'destino': '', 'doca': '', 'status': 'Aguardando', 'chamado_em': pd.NaT}
                df = df.append(novo, ignore_index=True)
                salvar_dados(df)
                st.success('Motorista adicionado!')
    st.write('---')
    st.dataframe(df)

# ----- Painel Pátio -----
elif modo == 'Painel Pátio':
    st.subheader('Painel do Pátio')
    aguardando = df[df['status'] == 'Aguardando']
    if aguardando.empty:
        st.info('Nenhum aguardando.')
    else:
        for idx, row in aguardando.iterrows():
            st.markdown('<div class=\'card\'>', unsafe_allow_html=True)
            st.write(f"**{row['motorista']}** - {row['placa']}")
            doca = st.text_input('Doca', value=row['doca'], key=f'doca{idx}')
            destino = st.text_input('Destino', value=row['destino'], key=f'dest{idx}')
            if st.button('Chamar', key=f'call{idx}'):
                df.at[idx, 'doca'] = doca
                df.at[idx, 'destino'] = destino
                df.at[idx, 'status'] = 'Chamado'
                df.at[idx, 'chamado_em'] = datetime.now()
                salvar_dados(df)
                st.success(f"{row['motorista']} chamado!")
                if som_ativo:
                    tocar_som()
            st.markdown('</div>', unsafe_allow_html=True)

# ----- Painel Motorista -----
else:
    st.subheader('Painel Motorista')
    chamados = df[df['status'] == 'Chamado'].sort_values('chamado_em', ascending=False)
    if chamados.empty:
        st.info('Nenhum chamado.')
    else:
        for _, row in chamados.iterrows():
            wait = datetime.now() - row['chamado_em']
            m, s = divmod(int(wait.total_seconds()), 60)
            st.markdown('<div class=\'card\'>', unsafe_allow_html=True)
            st.write(f"🚛 **{row['motorista']}**")
            st.write(f"Cliente: {row['cliente']}")
            st.write(f"Doca: {row['doca']}")
            st.write(f"Destino: {row['destino']}")
            st.write(f"Tempo: {m}m {s}s")
            if som_ativo:
                tocar_som()
                som_ativo = False
            st.markdown('</div>', unsafe_allow_html=True)

    # Som apenas para o primeiro da fila
    if not st.session_state["som_tocado"]:
        if st.session_state["som_ativado"]:
            st.audio(som_ativo, format="audio/wav")
        st.session_state["som_tocado"] = True