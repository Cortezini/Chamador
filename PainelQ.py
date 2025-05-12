import numpy as np
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import pygame
import random

# Inicializa o mixer do pygame apenas uma vez
pygame.mixer.init()

# Parâmetros do som
SAMPLE_RATE = 44100  # Hz
DURATION = 2         # segundos
FREQUENCY = 440      # Hz (nota Lá)
SOM_ALERTA = "som_alerta.wav"  # Arquivo de som para chamada

# Caminho relativo para o som amigável
SOM_AMIGAVEL = os.path.join("assets", "chamada.mp3")

# Lista de músicas para IA escolher aleatoriamente
MUSICAS = [
    "/home/lukc_br/Área de Trabalho/Painel Chamador/chamada.mp3.mp3",  # Substitua pelos nomes dos arquivos reais de músicas
    "/home/lukc_br/Área de Trabalho/Painel Chamador/chamada.mp3.mp3",
    "/home/lukc_br/Área de Trabalho/Painel Chamador/chamada.mp3.mp3",
    "/home/lukc_br/Área de Trabalho/Painel Chamador/chamada.mp3.mp3"
]

# Configuração da página
st.set_page_config(page_title="Sistema de Chamadas", layout="wide")
st.title("🚛 Sistema de Chamadas de Motoristas")

# Constantes
ARQUIVO_CSV = "chamados.csv"

# Estado inicial da sessão
if "modo" not in st.session_state:
    st.session_state["modo"] = "Painel Motorista"  # Define o Painel dos Motoristas como padrão
if "som_ativado" not in st.session_state:
    st.session_state["som_ativado"] = True  # Som inicialmente desativado
if "pilha_chamados" not in st.session_state:
    st.session_state["pilha_chamados"] = []  # Pilha que guarda os motoristas chamados

# Função para gerar o som de alerta se o arquivo ainda não existir
def gerar_som_alerta():
    if not os.path.exists(SOM_ALERTA):
        t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION), False)
        sine_wave = 0.5 * np.sin(2 * np.pi * FREQUENCY * t)
        audio_data = np.int16(sine_wave * 32767)
        os.write(SOM_ALERTA, SAMPLE_RATE, audio_data)

# Função para tocar o som amigável
def tocar_som_amigavel():
    if os.path.exists(SOM_AMIGAVEL):
        pygame.mixer.music.load(SOM_AMIGAVEL)  # Carrega o arquivo de áudio
        pygame.mixer.music.play()  # Toca o som
    else:
        st.error("Arquivo de som amigável não encontrado!")

# Função para tocar música aleatória
def tocar_musica_aleatoria():
    musica_escolhida = random.choice(MUSICAS)  # Seleciona uma música aleatoriamente
    if os.path.exists(musica_escolhida):
        pygame.mixer.music.load(musica_escolhida)  # Carrega a música escolhida
        pygame.mixer.music.play()  # Toca a música
    else:
        st.error(f"Música {musica_escolhida} não encontrada!")

# Funções auxiliares
def carregar_dados():
    """Carrega os dados do arquivo CSV ou retorna um DataFrame vazio."""
    try:
        df = pd.read_csv(ARQUIVO_CSV)
        if "chamado_em" in df.columns:
            df["chamado_em"] = pd.to_datetime(df["chamado_em"], errors="coerce")
        else:
            df["chamado_em"] = pd.NaT
    except FileNotFoundError:
        df = pd.DataFrame(columns=["motorista", "destino", "doca", "status", "chamado_em"])
        salvar_dados(df)
    return df

def salvar_dados(df):
    """Salva os dados no arquivo CSV."""
    try:
        df.to_csv(ARQUIVO_CSV, index=False)
    except Exception as e:
        st.error(f"Erro ao salvar os dados: {e}")

def alternar_som(ativar: bool):
    """Alterna o estado do som."""
    st.session_state["som_ativado"] = ativar

# Seleção de modo
modo_atual = st.sidebar.radio(
    "Selecione o modo de uso:",
    ["Painel ADM", "Painel Motorista"],
    key="modo"
)

# Atualiza o estado do modo ao alterar no sidebar
if modo_atual != st.session_state["modo"]:
    st.session_state["modo"] = modo_atual
    st.rerun()

# -------------------- PAINEL ADM --------------------
if st.session_state["modo"] == "Painel ADM":
    st.header("📋 Painel Administrativo")
    df = carregar_dados()

    # Removendo a função de chamada do motorista por nome
    st.subheader("🚚 Lista de Motoristas")
    if not df.empty:
        for i, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([3, 3, 2, 2, 2])
            col1.markdown(f"**{row['motorista']}**")
            col2.write(f"Destino: {row['destino']}")
            col3.write(f"Doca: {row['doca']}")
            col4.write(f"Status: {row['status']}")
            if col5.button(f"🔔 Chamar", key=f"chamar_{i}"):
                # Chama o motorista e armazena na pilha
                st.session_state["pilha_chamados"] = [row["motorista"]]  # Apenas o último chamado
                df.at[i, "status"] = "Chamado"
                df.at[i, "chamado_em"] = datetime.now()
                salvar_dados(df)
                st.success(f"Motorista {row['motorista']} chamado!")
                if st.session_state["som_ativado"]:
                    tocar_som_amigavel()
                # Toca música aleatória
                tocar_musica_aleatoria()
                st.rerun()
    else:
        st.info("Nenhum motorista cadastrado ainda.")

    st.subheader("➕ Adicionar Motorista")
    with st.form("form_add"):
        nome = st.text_input("Nome do motorista", key="nome_input")
        destino = st.text_input("Destino", key="destino_input")
        doca = st.text_input("Doca", key="doca_input")
        enviar = st.form_submit_button("Adicionar")

        if enviar:
            if nome and destino and doca:
                df = carregar_dados()
                if nome in df["motorista"].values:
                    st.error("Motorista já registrado!")
                else:
                    novo = {
                        "motorista": nome,
                        "destino": destino,
                        "doca": doca,
                        "status": "Aguardando",
                        "chamado_em": pd.NaT,
                    }
                    df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
                    salvar_dados(df)
                    st.success("Motorista adicionado com sucesso!")
                    st.rerun()
            else:
                st.error("Preencha todos os campos.")

# -------------------- PAINEL MOTORISTA --------------------
else:
    st.header("📣 Painel do Motorista")
    
    # Tela amigável para o último motorista chamado
    if st.session_state["pilha_chamados"]:
        motorista_chamado = st.session_state["pilha_chamados"][0]
        # Painel amigável visual
        with st.container():
            st.markdown(
                f"""
                <div style="border-radius: 10px; padding: 10px; background-color: #f0f8ff; border: 2px solid #00bcd4; text-align: center;">
                    <h2 style="color: #00bcd4;">Último Motorista Chamado</h2>
                    <p style="font-size: 1.5em; font-weight: bold; color: #00bcd4;">{motorista_chamado}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("Nenhum motorista foi chamado ainda.")

    som_col1, som_col2 = st.columns([4, 1])
    if st.session_state["som_ativado"]:
        with som_col1:
            st.success("🔊 Som ativado. Você será alertado quando chamado.")
        with som_col2:
            if st.button("🔇 Desativar Som"):
                alternar_som(False)
    else:
        with som_col1:
            st.info("🔇 Som desativado. Ative para ouvir o alerta.")
        with som_col2:
            if st.button("🔊 Ativar Som"):
                alternar_som(True)


    st.subheader("🔍 Procurar seu nome")
    nome_busca = st.text_input("Digite seu nome:")
    if nome_busca:
        resultados = [["motorista"].str.contains(nome_busca, case=False, na=False)]
        if not resultados.empty:
            st.table(resultados[["motorista", "destino", "doca", "status", "chamado_em"]])
            for _, row in resultados.iterrows():
                if row["status"] == "Chamado" and st.session_state["som_ativado"]:
                    tocar_som_amigavel()
        else:
            st.warning("Motorista não encontrado.")
    else:
        st.info("Digite seu nome acima para verificar chamadas.")
