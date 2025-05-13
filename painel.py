import streamlit as st
import pandas as pd
import os
import numpy as np
from datetime import datetime
from scipy.io.wavfile import write

# ----- Configurações da Página -----
st.set_page_config(page_title='Painel BDM', layout='wide', page_icon='🚛')

# ----- Session State -----
if 'som_ativado' not in st.session_state:
    st.session_state.som_ativado = True
if 'auto_update' not in st.session_state:
    st.session_state.auto_update = False

# ----- Paths e Constantes -----
CSV_PATH = 'chamados.csv'
ASSETS_DIR = 'assets'
ALERT_FILE = os.path.join(ASSETS_DIR, 'som_alerta.wav')

# ----- Estilo CSS -----
custom_css = '''
:root {
  --bg: #f8f9fc;
  --card: #ffffff;
  --primary: #4e73df;
  --highlight: #ffe4b5;
  --text: #5a5c69;
  --radius: 10px;
  --spacing: 1rem;
  --font: 'Roboto', sans-serif;
}
body, .stApp { background: var(--bg); color: var(--text); font-family: var(--font); }
.header { font-size: 2rem; color: var(--primary); margin-bottom: var(--spacing); }
.card { background: var(--card); border-radius: var(--radius); padding: var(--spacing); margin-bottom: var(--spacing); box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.highlight { background: var(--highlight); }
''' 
st.markdown(f'<style>{custom_css}</style>', unsafe_allow_html=True)

# ----- Funções de Áudio -----
def gerar_alerta():
    RATE, DURA, FREQ = 44100, 0.5, 600
    t = np.linspace(0, DURA, int(RATE * DURA), False)
    wave = 0.5 * np.sin(2 * np.pi * FREQ * t)
    audio = np.int16(wave * 32767)
    write(ALERT_FILE, RATE, audio)

if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)
if not os.path.exists(ALERT_FILE):
    gerar_alerta()

def tocar_alerta():
    with open(ALERT_FILE, 'rb') as f:
        st.audio(f.read(), format='audio/wav')

# ----- Carregamento e Salvamento de Dados -----
def carregar_dados():
    cols = ['motorista','senha','placa','cliente','destino','doca','status','chamado_em']
    if not os.path.exists(CSV_PATH):
        pd.DataFrame(columns=cols).to_csv(CSV_PATH, index=False)
    df = pd.read_csv(CSV_PATH, parse_dates=['chamado_em'])
    return df

def salvar_dados(df):
    df.to_csv(CSV_PATH, index=False)

# ----- Sidebar -----
st.sidebar.title('Controles')
modo = st.sidebar.radio('Painel:', ['ADM','Pátio','Motorista'])
st.sidebar.checkbox('Som Ativo', value=st.session_state.som_ativado, key='som_ativado')
st.sidebar.checkbox('Auto Refresh', value=st.session_state.auto_update, key='auto_update')
interval = st.sidebar.slider('Intervalo (s)', 1, 30, 5)
if st.session_state.auto_update:
    st.experimental_rerun()

# ----- Cabeçalho -----
st.markdown('<div class="header">🚛 Painel de Chamadas BDM</div>', unsafe_allow_html=True)

# ----- Main -----
df = carregar_dados()

# --- Painel Administrativo ---
if modo == 'ADM':
    st.header('📋 Painel Administrativo')
    total = len(df)
    st.markdown(f'**Total de Registros:** {total}')
    st.markdown('**Status por Categoria:**')
    st.write(df['status'].value_counts())
    st.markdown('---')
    with st.form('form_add'):
        st.subheader('Adicionar Motorista')
        c1, c2, c3, c4 = st.columns(4)
        nome = c1.text_input('Motorista')
        senha = c2.text_input('Senha')
        placa = c3.text_input('Placa')
        cliente = c4.text_input('Cliente')
        destino = c1.text_input('Destino')
        doca = c2.text_input('Doca')
        submit = st.form_submit_button('Adicionar')
        if submit:
            if nome and senha:
                novo = {'motorista':nome,'senha':senha,'placa':placa,'cliente':cliente,
                        'destino':destino,'doca':doca,'status':'Aguardando','chamado_em':pd.NaT}
                df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
                salvar_dados(df)
                st.success('Motorista adicionado!')
            else:
                st.error('Preencha pelo menos motorista e senha.')
    st.dataframe(df)

# --- Painel Pátio ---
elif modo == 'Pátio':
    st.header('🏭 Painel do Pátio')
    aguardando = df[df['status']=='Aguardando']
    if aguardando.empty:
        st.info('Nenhum motorista aguardando.')
    else:
        for idx, row in aguardando.iterrows():
            st.markdown(f"<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"**Motorista:** {row['motorista']}  |  **Senha:** {row['senha']}")
            st.markdown(f"**Placa:** {row['placa']}  |  **Cliente:** {row['cliente']}")
            if st.button('Chamar', key=f'ch_{idx}'):
                df.at[idx,'status']='Chamado'
                df.at[idx,'chamado_em']=datetime.now()
                salvar_dados(df)
                st.success(f"{row['motorista']} chamado!")
                if st.session_state.som_ativado:
                    tocar_alerta()
            st.markdown('</div>', unsafe_allow_html=True)

# --- Painel Motorista ---
elif modo == 'Motorista':
    st.header('📣 Painel do Motorista')
    chamados = df[df['status']=='Chamado'].sort_values('chamado_em')
    if chamados.empty:
        st.info('Nenhum chamado ativo.')
    else:
        # Primeiro chamado em destaque
        first = chamados.iloc[0]
        st.markdown("<div class='card highlight'>", unsafe_allow_html=True)
        st.markdown(f"### 🚛 {first['motorista']}  |  Senha: {first['senha']}")
        st.markdown(f"**Placa:** {first['placa']}  |  **Cliente:** {first['cliente']}")
        st.markdown('</div>', unsafe_allow_html=True)
        # Histórico
        if len(chamados) > 1:
            st.subheader('Histórico de Chamados')
            for idx, row in chamados.iloc[1:].iterrows():
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown(f"- {row['motorista']} (Senha: {row['senha']}) às {row['chamado_em'].strftime('%H:%M:%S')}")
                st.markdown('</div>', unsafe_allow_html=True)
else:
    st.warning('Selecione um modo válido no sidebar.')
