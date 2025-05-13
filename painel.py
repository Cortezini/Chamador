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
    'colors':{
        'primary': '#FF5733',
        'secondary': '#C70039',
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
    'som_tocado': False,
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
                st.audio(f.read(), format='audio/wav')
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

    with st.form("Novo Motorista", clear_on_submit=True):
        st.markdown("**Campos Obrigatórios** (*)")
        
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
                max_chars=8,
                placeholder="AAA-0A00 ou ABC1D23"
            )

        with col2:
            senha = st.text_input(
                'Senha de Acesso',
                max_chars=3,
                placeholder="123"
            )
            
            transportadora = st.text_input(
                'Transportadora*',
                placeholder="Nome completo da transportadora"
        )  
            
            cliente = st.text_input(
                'Cliente',
                placeholder="Nome do cliente"
            )

        vendedor = st.text_input('Vendedor Responsável')

        submitted = st.form_submit_button('Adicionar Motorista')
        
        if submitted:
            errors = []
            valid = CONFIG['validations']

            # Validação de campos
            if not motorista:
                errors.append("Nome do motorista é obrigatório")
            elif not re.match(valid['name_regex'], motorista, re.IGNORECASE):
                errors.append("Nome inválido (mínimo 5 caracteres alfabéticos)")

            if not contato:
                errors.append("Contato é obrigatório")
            elif not re.match(valid['phone_regex'], contato):
                errors.append("Formato de contato inválido (use (XX) XXXX-XXXX)")

            if not placa:
                errors.append("Placa do veículo é obrigatória")
            else:
                cleaned_plate = placa.upper().replace('-', '').replace(' ', '')
                if not re.fullmatch(valid['plate_regex'], cleaned_plate, re.IGNORECASE):
                    errors.append("Formato de placa inválido")

            if senha and not re.fullmatch(valid['password_regex'], senha):
                errors.append("A senha deve conter 3 dígitos numéricos")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                novo_registro = {
                    'motorista': motorista.title(),
                    'contato': contato,
                    'transportadora': transportadora if transportadora else 'Não informada',
                    'senha': senha if senha else 'N/A',
                    'placa': cleaned_plate,
                    'cliente': cliente.title() if cliente else 'Não informado',
                    'vendedor': vendedor.title() if vendedor else 'Não informado',
                    'destino': '',
                    'doca': '',
                    'status': 'Aguardando',
                    'chamado_em': pd.NaT
                    
                }
                
                df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
                save_data(df)
                st.success('Motorista cadastrado com sucesso!')
                st.balloons()

    st.write('---')
    st.dataframe(
        df,
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
    """Interface do Painel do Pátio - Versão Simplificada"""
    st.subheader("Controle de Operações - Pátio")
    aguardando = df[df['status'] == 'Aguardando']

    if aguardando.empty:
        st.info('Nenhum motorista aguardando atendimento')
        return

    for idx, row in aguardando.iterrows():
        with st.container(border=True):
            # Cabeçalho do Card
            cols_header = st.columns([3, 1, 1])
            cols_header[0].subheader(row['motorista'])
            cols_header[1].metric("Placa", row['placa'])
            cols_header[2].metric("Senha", row['senha'])
            
            # Corpo do Card
            with st.form(key=f'form_{idx}'):
                cols_body = st.columns(2)
                
                # Coluna Esquerda - Informações
                with cols_body[0]:
                    st.markdown(f"**Transportadora:** {row['transportadora']}")
                    st.markdown(f"**Cliente:** {row['cliente']}")
                    st.markdown(f"**Vendedor:** {row['vendedor']}")
                
                # Coluna Direita - Controles
                with cols_body[1]:
                    doca = st.text_input(
                        "Nº Doca",
                        value=row['doca'],
                        key=f'doca_{idx}',
                        placeholder="Ex: 05",
                        help="Número da doca designada",
                        max_chars=3
                    )
                    
                    destino = st.text_input(
                        "Destino/Unidade",
                        value=row['destino'],
                        key=f'dest_{idx}',
                        placeholder="Ex: Armazém B",
                        help="Destino final da carga",
                        max_chars=20
                    )
                    
                    if st.form_submit_button("Confirmar Direcionamento", type='primary'):
                        df.at[idx, 'status'] = 'Chamado'
                        df.at[idx, 'chamado_em'] = datetime.now()
                        df.at[idx, 'doca'] = doca
                        df.at[idx, 'destino'] = destino
                        save_data(df)
                        st.rerun()

# ================ PAINEL MOTORISTA ================
def render_driver_panel(df: pd.DataFrame):
    """Interface do Painel do Motorista com Layout Aprimorado"""
    chamados = df[df['status'] == 'Chamado'].sort_values('chamado_em', ascending=False)
    
    if chamados.empty:
        st.info('Nenhum chamado ativo no sistema')
        return

    # Último Chamado
    ultimo = chamados.iloc[0]
    with st.container(border=True):
        cols = st.columns([3, 1, 1, 2])
        
        # Coluna 1: Informações Básicas
        cols[0].markdown(f"""
        **Motorista:** {ultimo['motorista']}<br>
        **Placa:** {ultimo['placa']}<br>
        **Transportadora:** {ultimo['transportadora']}
        """, unsafe_allow_html=True)
        
        # Coluna 2: Doca com fonte maior
        cols[1].markdown(f"""
        <div style="font-size: 24px; color: #0056b3; font-weight: bold;">
        DOCA<br>
        {ultimo['doca'] if ultimo['doca'] else '---'}
        </div>
        """, unsafe_allow_html=True)
        
        # Coluna 3: Destino com fonte maior
        cols[2].markdown(f"""
        <div style="font-size: 24px; color: #2c3e50; font-weight: bold;">
        DESTINO<br>
        {ultimo['destino'] if ultimo['destino'] else '---'}
        </div>
        """, unsafe_allow_html=True)
        
        # Coluna 4: Temporal
        cols[3].markdown(f"""
        **Data:** {ultimo['chamado_em'].strftime('%d/%m/%Y')}<br>
        **Horário:** {ultimo['chamado_em'].strftime('%H:%M')}
        """, unsafe_allow_html=True)

    # Histórico
    st.divider()
    st.markdown("### Histórico de Chamadas")
    for idx, row in chamados.iloc[1:].iterrows():
        with st.container(border=True):
            cols = st.columns([3, 1, 1, 2])
            
            cols[0].markdown(f"**{row['motorista']}**")
            cols[1].markdown(f"**Doca:** `{row['doca'] if pd.notna(row['doca']) and row['doca'] else '---'}`")
            cols[2].markdown(f"**Destino:** `{row['destino'] if pd.notna(row['destino']) and row['destino'] else '---'}`")
            cols[3].markdown(f"_{pd.to_datetime(row['chamado_em']).strftime('%d/%m %H:%M')}_")

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

    if controls['auto_update']:
        st.rerun()

if __name__ == '__main__':
    main()