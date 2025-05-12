import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import numpy as np  # type: ignore
from datetime import datetime
from scipy.io.wavfile import write  # type: ignore
from sqlalchemy import create_engine  # type: ignore
import os

# Constantes
SAMPLE_RATE = 44100
DURATION = 2
FREQUENCY = 440
SOM_ALERTA = "som_alerta.wav"
ARQUIVO_CSV = "chamados.csv"
DATABASE_URL = "sqlite:///chamados.db"

# Configuração inicial
st.set_page_config(page_title="Sistema de Chamadas", layout="wide")
st.title("🚛 Sistema de Chamadas de Motoristas")
engine = create_engine(DATABASE_URL)

# Carregamento dos parâmetros da URL
# Carregamento dos parâmetros da URL

query_params = st.query_params


modo_url = query_params.get("modo", [None])[0]
modo_opcoes = ["Painel ADM", "Painel Pátio", "Painel Motorista"]

# Inicialização segura do session_state
if "modo" not in st.session_state:
    st.session_state["modo"] = modo_url if modo_url in modo_opcoes else "Painel Motorista"
if "som_ativado" not in st.session_state:
    st.session_state["som_ativado"] = True
if "df_cache" not in st.session_state:
    st.session_state["df_cache"] = None

# Funções
def atualizar_url(modo):
    st.query_params["modo"] = modo


def gerar_som():
    if not os.path.exists(SOM_ALERTA):
        t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), False)
        wave = 0.5 * np.sin(2 * np.pi * FREQUENCY * t)
        audio = np.int16(wave * 32767)
        write(SOM_ALERTA, SAMPLE_RATE, audio)

def tocar_som():
    with open(SOM_ALERTA, "rb") as file:
        st.audio(file.read(), format="audio/wav")

def carregar_dados():
    try:
        df = pd.read_csv(ARQUIVO_CSV)
        if "chamado_em" in df.columns:
            df["chamado_em"] = pd.to_datetime(df["chamado_em"], errors="coerce")
        return df
    except FileNotFoundError:
        df = pd.DataFrame(columns=[
            "motorista", "contato", "transportadora", "senha",
            "placa", "cliente", "vendedor", "destino", "doca",
            "status", "chamado_em"
        ])
        salvar_dados(df)
        return df

def salvar_dados(df):
    df.to_csv(ARQUIVO_CSV, index=False)

def alternar_som(ativo: bool):
    st.session_state["som_ativado"] = ativo

# Seletor de modo (sidebar)
modo_atual = st.sidebar.radio(
    "Selecione o modo:",
    modo_opcoes,
    index=modo_opcoes.index(st.session_state["modo"]),
    key="modo_radio"
)

# Atualiza session_state e URL se mudar
if modo_atual != st.session_state["modo"]:
    st.session_state["modo"] = modo_atual
    atualizar_url(modo_atual)
    st.rerun()

# Painel ADM
if st.session_state["modo"] == "Painel ADM":
    st.header("📋 Painel Administrativo")
    df = carregar_dados()
    st.session_state["df_cache"] = df.copy()

    if st.button("🧹 Limpar visualização"):
        st.session_state["df_cache"] = pd.DataFrame(columns=df.columns)
        st.success("Visualização limpa (dados salvos no CSV).")

    st.subheader("🚚 Lista de Motoristas")
    if not st.session_state["df_cache"].empty:
        for i, row in st.session_state["df_cache"].iterrows():
            col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 2, 2])
            col1.markdown(f"**{row['motorista']}**")
            col2.write(f"Status: {row['status']}")
            col3.write(f"Placa: {row['placa']}")
            col4.write(f"Cliente: {row['cliente']}")
            col5.write(f"Vendedor: {row['vendedor']}")
    else:
        st.info("Nenhum motorista na visualização atual.")

    st.subheader("➕ Adicionar Motorista")
    with st.form("form_add"):
        nome = st.text_input("Nome do motorista")
        contato = st.text_input("Contato")
        transportadora = st.text_input("Transportadora")
        senha = st.text_input("Senha")
        placa = st.text_input("Placa")
        cliente = st.text_input("Cliente")
        vendedor = st.text_input("Vendedor")
        enviar = st.form_submit_button("Adicionar")

        if enviar:
            if nome and contato and transportadora and senha and placa and cliente and vendedor:
                df = carregar_dados()
                if nome in df["motorista"].values:
                    st.error("Motorista já registrado!")
                else:
                    novo = {
                        "motorista": nome,
                        "contato": contato,
                        "transportadora": transportadora,
                        "senha": senha,
                        "placa": placa,
                        "cliente": cliente,
                        "vendedor": vendedor,
                        "destino": "",
                        "doca": "",
                        "status": "Aguardando",
                        "chamado_em": pd.NaT,
                    }
                    df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
                    salvar_dados(df)
                    st.success("Motorista adicionado com sucesso!")
                    st.rerun()
            else:
                st.error("Preencha todos os campos.")

# Painel Pátio
elif st.session_state["modo"] == "Painel Pátio":
    st.header("🏭 Painel do Pátio")
    df = carregar_dados()
    aguardando_df = df[df["status"] == "Aguardando"]

    if aguardando_df.empty:
        st.info("Nenhum motorista aguardando.")
    else:
        for i, row in aguardando_df.iterrows():
            with st.expander(f"{row['motorista']} - {row['placa']}"):
                doca = st.text_input(f"Doca para {row['motorista']}", key=f"doca_{i}")
                destino = st.text_input(f"Destino para {row['motorista']}", key=f"destino_{i}")
                if st.button("✅ Confirmar", key=f"confirmar_{i}"):
                    df.at[i, "doca"] = doca
                    df.at[i, "destino"] = destino
                    df.at[i, "status"] = "Chamado"
                    df.at[i, "chamado_em"] = datetime.now()
                    salvar_dados(df)
                    st.success(f"{row['motorista']} chamado com sucesso!")
                    tocar_som()
                    st.rerun()

# Painel Motorista
else:
    st.header("📣 Painel do Motorista")
    df = carregar_dados()

    col1, col2 = st.columns([5, 1])
    if st.session_state["som_ativado"]:
        with col1:
            st.success("Som ativado.")
        with col2:
            if st.button("🔇 Desativar"):
                alternar_som(False)
    else:
        with col1:
            st.info("Som desativado.")
        with col2:
            if st.button("🔊 Ativar"):
                alternar_som(True)

    df_chamados = df[df["status"] == "Chamado"].sort_values(by="chamado_em", ascending=False)

    if not df_chamados.empty:
        st.subheader("📢 Últimos Chamados")

        ultimo = df_chamados.iloc[0]
        st.markdown(
            f"""
            <div style='background-color: #d4edda; padding: 20px; border-radius: 10px; border-left: 6px solid green;'>
                <h3>🚛 {ultimo['motorista']}</h3>
                <p><strong>Doca:</strong> {ultimo['doca']}</p>
                <p><strong>Destino:</strong> {ultimo['destino']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.session_state["som_ativado"]:
            st.audio(SOM_ALERTA, format="audio/wav")

        if len(df_chamados) > 1:
            st.markdown("### Chamadas anteriores:")
            for i in range(1, len(df_chamados)):
                row = df_chamados.iloc[i]
                st.info(f"{row['motorista']} | Doca: {row['doca']} | Destino: {row['destino']}")
    else:
        st.info("Nenhum motorista chamado no momento.")

# Geração e sincronização final
gerar_som()
try:
    df.to_sql("chamados", engine, if_exists="replace", index=False)
    st.success("📦 Dados sincronizados com banco de dados.")
except Exception as e:
    st.error(f"Erro ao salvar no banco de dados: {e}")
