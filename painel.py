import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.io.wavfile import write
import os
import base64

# ----- Configurações -----
st.set_page_config(page_title='Painel BDM', layout='wide', page_icon='assets/bdm.ico')

# Inicialização do session_state
if "som_tocado" not in st.session_state:
    st.session_state["som_tocado"] = False
if "som_ativado" not in st.session_state:
    st.session_state["som_ativado"] = True
if "auto_update" not in st.session_state:
    st.session_state["auto_update"] = False

def load_external_css(path: str):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            css = f.read()
        st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    else:
        st.error(f"Arquivo de estilo não encontrado: {path}")

# 2) Agora que a função existe, você pode chamá-la:
load_external_css('style.css')  # ou 'style.css', dependendo de onde você colocou

# ----- Parâmetros de som e arquivo -----
SAMPLE_RATE, DURATION, FREQUENCY = 44100, 2, 440
ALERT_PATH = os.path.join('assets', 'som_alerta.wav')
DATA_CSV = 'chamados.csv'

# Verifica se o diretório 'assets' existe, senão cria
if not os.path.exists('assets'):
    os.makedirs('assets')

# ----- Funções de áudio -----
def gerar_som():
    """Gera o som de alerta e salva como som_alerta.wav no diretório assets."""
    if not os.path.exists('assets'):
        os.makedirs('assets')
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), False)
    wave = 0.5 * np.sin(2 * np.pi * FREQUENCY * t)
    audio = np.int16(wave * 32767)
    write(ALERT_PATH, SAMPLE_RATE, audio)

# Verifica se o arquivo de som existe, senão o gera automaticamente
if not os.path.exists(ALERT_PATH):
    print(f"O arquivo {ALERT_PATH} não foi encontrado. Gerando som...")
    gerar_som()

def tocar_som():
    """Toca o som de alerta, gerando-o caso não exista."""
    if not os.path.exists(ALERT_PATH):
        st.warning("O arquivo de som 'som_alerta.wav' não foi encontrado. Gerando som de alerta automaticamente...")
        gerar_som()
    try:
        with open(ALERT_PATH, 'rb') as f:
            st.audio(f.read(), format='audio/wav')
    except Exception as e:
        st.error(f"Erro ao tentar reproduzir o som: {str(e)}")

# ----- Leitura e gravação de dados -----
def carregar_dados():
    """Carrega os dados do CSV ou inicializa um DataFrame vazio se o arquivo não existir."""
    try:
        df = pd.read_csv(DATA_CSV, parse_dates=['chamado_em'])
    except FileNotFoundError:
        cols = ['motorista', 'contato', 'transportadora', 'senha', 'placa',
                'cliente', 'vendedor', 'destino', 'doca', 'status', 'chamado_em']
        df = pd.DataFrame(columns=cols)
        df.to_csv(DATA_CSV, index=False)
    except pd.errors.EmptyDataError:
        cols = ['motorista', 'contato', 'transportadora', 'senha', 'placa',
                'cliente', 'vendedor', 'destino', 'doca', 'status', 'chamado_em']
        df = pd.DataFrame(columns=cols)
    return df

def salvar_dados(df):
    """Salva o DataFrame no arquivo CSV."""
    if isinstance(df, pd.DataFrame):
        df.to_csv(DATA_CSV, index=False)
    else:
        raise ValueError("O objeto fornecido para salvar não é um DataFrame válido!")

# ----- Sidebar -----
st.sidebar.title('Controles')
modo = st.sidebar.selectbox('Modo', ['Painel ADM', 'Painel Pátio', 'Painel Motorista'])
som_ativo = st.sidebar.checkbox('Som Ativo', True)
auto_update = st.sidebar.checkbox('Auto Refresh', False)
interval = st.sidebar.slider('Intervalo (s)', 1, 30, 5)

# ----- Auto refresh -----
if auto_update:
    st.rerun()

# ----- Título -----
def get_image_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

img_base64 = get_image_base64("assets/bdm.ico")

st.markdown(f'''
<div class='header'>
    <img src="data:image/x-icon;base64,{img_base64}" width="30" style="vertical-align: middle; margin-right: 10px;">
    Painel de Chamadas BDM
</div>
''', unsafe_allow_html=True)

df = carregar_dados()

# ----- Painel ADM -----
if modo == 'Painel ADM':
    st.subheader('Painel Administrativo')

    # Validação de df
    if not isinstance(df, pd.DataFrame):
        st.error("Erro: Os dados carregados não são um DataFrame válido.")
        st.stop()

    with st.expander('Estatísticas'):
        total = len(df)
        counts = df['status'].value_counts().to_dict()
        st.write(f'Total: **{total}**')
        for k, v in counts.items():
            st.write(f'- {k}: **{v}**')

    if st.button('Limpar Tudo'):
        salvar_dados(pd.DataFrame(columns=df.columns))
        st.rerun()

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
                novo = {
                    'motorista': nome, 'contato': contato, 'transportadora': transportadora,
                    'senha': senha, 'placa': placa, 'cliente': cliente, 'vendedor': vendedor,
                    'destino': '', 'doca': '', 'status': 'Aguardando', 'chamado_em': pd.NaT
                }
                df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
                salvar_dados(df)
                st.success('Motorista adicionado com sucesso!')
            else:
                st.error("Por favor, preencha os campos obrigatórios.")

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
            st.markdown(f"### Motorista: {row['motorista']}")
            st.markdown(f"**Senha:** {row['senha']}")
            st.text_input('Doca', value=row['doca'], key=f'doca{idx}', disabled=True)
            st.text_input('Destino', value=row['destino'], key=f'dest{idx}', disabled=True)
            if st.button('Chamar', key=f'call{idx}'):
                df.at[idx, 'status'] = 'Chamado'
                df.at[idx, 'chamado_em'] = datetime.now()
                salvar_dados(df)
                st.success(f"{row['motorista']} chamado!")
                if som_ativo:
                    tocar_som()
            st.markdown('</div>', unsafe_allow_html=True)

# ----- Painel Motorista -----
elif modo == 'Painel Motorista':
    st.subheader('🚛 Painel Motorista')
    
    # Pega os chamados em “Chamado”, mais recentes primeiro
    chamados = df[df['status']=='Chamado'].sort_values('chamado_em', ascending=False)

    if chamados.empty:
        st.info('Nenhum chamado no momento.')
    else:
        # === DESTAQUE DO ÚLTIMO CHAMADO ===
        ultimo = chamados.iloc[0]
        with st.container():
            st.markdown('<div class="card-highlight">', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns([1,2,2,2])
            c1.markdown('## 🚨')
            c2.markdown(f"### {ultimo['motorista']}")
            c3.markdown(f"**Doca:** {ultimo['doca'] or '—'}")
            c4.markdown(f"**Destino:** {ultimo['destino'] or '—'}")
            c5, c6, c7 = st.columns([2,2,2])
            c5.markdown(f"**Cliente:** {ultimo['cliente']}")
            c6.markdown(f"**Vendedor:** {ultimo['vendedor']}")
            c7.markdown(f"**Chamado em:** {ultimo['chamado_em'].strftime('%d/%m %H:%M')}")
            st.markdown('</div>', unsafe_allow_html=True)

        # === HISTÓRICO SEMPRE VISÍVEL E ROLÁVEL ===
        st.markdown('### 🕒 Histórico de Chamados')
        st.markdown('<div class="history-container">', unsafe_allow_html=True)

        for idx, row in chamados.iterrows():
            if idx == ultimo.name:
                continue
            st.markdown('<div class="card-muted">', unsafe_allow_html=True)
            r1, r2, r3, r4 = st.columns([2,2,1,2])
            r1.write(f"**{row['motorista']}**")
            r2.write(f"Doca: {row['doca'] or '–'}")
            r3.write(row['chamado_em'].strftime('%H:%M'))
            r4.write(f"Cliente: {row['cliente']}")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # === ALERTA SONORO “POR TRÁS DOS PANOS” ===
    if (not st.session_state.som_tocado 
        and st.session_state.som_ativado 
        and not chamados.empty):
        # só gera o som, mas não chama o st.audio()
        gerar_som()
        st.session_state.som_tocado = True



