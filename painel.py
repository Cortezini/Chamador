import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.io.wavfile import write
import os
import base64

# ----- Configurações -----
st.set_page_config(page_title='Painel BDM', layout='wide', page_icon='assets/bdm.ico')  # DEVE SER O PRIMEIRO COMANDO

# Inicialização do session_state
if "som_tocado" not in st.session_state:
    st.session_state["som_tocado"] = False  # Inicializa com False ou qualquer valor padrão necessário
if "som_ativado" not in st.session_state:
    st.session_state["som_ativado"] = True
if "auto_update" not in st.session_state:
    st.session_state["auto_update"] = False

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
ALERT_PATH = os.path.join('assets', 'som_alerta.wav')  # Caminho atualizado para som_alerta.wav
MUSIC_LIST = [os.path.join('assets', 'som_alerta.wav')]  # Atualizado para o nome correto
DATA_CSV = 'chamados.csv'

# Verifica se o diretório 'assets' existe, senão cria
if not os.path.exists('assets'):
    os.makedirs('assets')

# Verifica se o arquivo de som existe, senão o gera automaticamente
if not os.path.exists(ALERT_PATH):
    print(f"O arquivo {ALERT_PATH} não foi encontrado. Gerando som...")
    gerar_som()

# Verifica se o arquivo de dados existe, senão cria um arquivo vazio
if not os.path.exists(DATA_CSV):
    print(f"O arquivo {DATA_CSV} não foi encontrado. Criando um arquivo vazio...")
    pd.DataFrame(columns=['motorista', 'contato', 'transportadora', 'senha', 'placa',
                          'cliente', 'vendedor', 'destino', 'doca', 'status', 'chamado_em']
                ).to_csv(DATA_CSV, index=False)

# ----- Funções de áudio -----
def gerar_som():
    """Gera o som de alerta e salva como som_alerta.wav no diretório assets."""
    if not os.path.exists('assets'):
        os.makedirs('assets')  # Cria o diretório assets, se não existir
    t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), False)
    wave = 0.5 * np.sin(2 * np.pi * FREQUENCY * t)
    audio = np.int16(wave * 32767)
    write(ALERT_PATH, SAMPLE_RATE, audio)  # Salva o som gerado como som_alerta.wav

def tocar_som():
    """Toca o som de alerta, gerando-o caso não exista."""
    if not os.path.exists(ALERT_PATH):
        st.warning("O arquivo de som 'som_alerta.wav' não foi encontrado. Gerando som de alerta automaticamente...")
        gerar_som()  # Gera o som automaticamente se não existir
    try:
        with open(ALERT_PATH, 'rb') as f:
            st.audio(f.read(), format='audio/wav')  # Reproduz o som
    except Exception as e:
        st.error(f"Erro ao tentar reproduzir o som: {str(e)}")
# ----- Leitura e gravação de dados -----
def carregar_dados():
    """Carrega os dados do CSV ou inicializa um DataFrame vazio se o arquivo não existir."""
    try:
        df = pd.read_csv(DATA_CSV, parse_dates=['chamado_em'])
    except FileNotFoundError:
        # Inicializa um DataFrame vazio se o arquivo não existir
        cols = ['motorista', 'contato', 'transportadora', 'senha', 'placa',
                'cliente', 'vendedor', 'destino', 'doca', 'status', 'chamado_em']
        df = pd.DataFrame(columns=cols)
        df.to_csv(DATA_CSV, index=False)  # Salva o DataFrame vazio no arquivo
    except pd.errors.EmptyDataError:
        # Inicializa um DataFrame vazio se o arquivo estiver vazio
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
    st.experimental_rerun()

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

    # Validação de `df`
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
                novo = {
                    'motorista': nome, 'contato': contato, 'transportadora': transportadora,
                    'senha': senha, 'placa': placa, 'cliente': cliente, 'vendedor': vendedor,
                    'destino': '', 'doca': '', 'status': 'Aguardando', 'chamado_em': pd.NaT
                }
                # Adiciona a nova linha usando pd.concat
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

if modo == 'Painel Motorista':
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
            if st.session_state["som_ativado"] and not st.session_state["som_tocado"]:
                tocar_som()
                st.session_state["som_tocado"] = True  # Marca como tocado para evitar repetição
            st.markdown('</div>', unsafe_allow_html=True)

    # Som apenas para o primeiro da fila
    if not st.session_state["som_tocado"] and st.session_state["som_ativado"]:
        tocar_som()
        st.session_state["som_tocado"] = True