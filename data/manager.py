import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from data.db import ENGINE

class GerenciadorDados:
    @staticmethod
    def carregar_registros():
        try:
            return pd.read_sql_table('chamados', ENGINE, parse_dates=['chamado_em', 'finalizado_em'])
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return pd.DataFrame()

    @staticmethod
    def salvar_registros(df):
        try:
            df.to_sql('chamados', ENGINE, index=False, if_exists='replace')
        except Exception as e:
            st.error(f"Erro ao salvar dados: {e}")