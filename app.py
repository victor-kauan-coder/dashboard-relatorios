# app.py (Versão final correta para funcionar ONLINE e LOCALMENTE)
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import traceback
import os
import sys

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Dashboard de Relatórios", layout="wide")
URL_DA_PLANILHA = "https://docs.google.com/spreadsheets/d/1foi-8QcpCwqgB_MkFKRyZ-FXFWAGQ4eUgHz2uqO2VvU/edit?resourcekey=&gid=526405481#gid=526405481"

# --- FUNÇÃO PARA CARREGAR DADOS (COM LÓGICA PARA ONLINE E LOCAL) ---
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
        
        # --- LÓGICA INTELIGENTE PARA AS CREDENCIAIS ---
        # Tenta ler a partir dos Secrets do Streamlit (quando está online)
        if st.secrets.has_key("gcp_service_account"):
            creds_dict = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        # Se não conseguir, lê a partir do arquivo local (para desenvolvimento no seu PC)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        
        client = gspread.authorize(creds)
        
        sheet = client.open_by_url(URL_DA_PLANILHA).sheet1
        all_values = sheet.get_all_values()
        
        if len(all_values) > 1:
            header = all_values[0]
            data = all_values[1:]
            dados = pd.DataFrame(data, columns=header)
            dados.columns = dados.columns.str.strip()
            
            if 'Data da atividade' in dados.columns:
                dados['Data da atividade'] = pd.to_datetime(dados['Data da atividade'], errors='coerce', dayfirst=True)
                dados.dropna(subset=['Data da atividade'], inplace=True)
            
            return dados
        else:
            st.warning("A planilha está vazia ou não contém dados.")
            return pd.DataFrame()
            
    except Exception as e:
        st.error("Ocorreu um erro ao carregar os dados. Verifique os logs ou a configuração dos Secrets.")
        st.code(traceback.format_exc())
        return pd.DataFrame()

# --- O RESTO DA INTERFACE (NÃO PRECISA MUDAR) ---
st.title("📊 Dashboard de Relatórios e Presenças")
st.markdown("---")
df = carregar_dados()
if not df.empty:
    st.sidebar.header("Filtros:")
    monitores = sorted(df['Nome do monitor'].unique())
    monitor_selecionado = st.sidebar.multiselect("Selecione o Monitor:", options=monitores, default=[])
    preceptores = sorted(df['Nome do preceptor'].unique())
    preceptor_selecionado = st.sidebar.multiselect("Selecione o(a) Preceptor(a):", options=preceptores, default=[])
    if 'Data da atividade' in df.columns and not df['Data da atividade'].isnull().all():
        data_min = df['Data da atividade'].min().date()
        data_max = df['Data da atividade'].max().date()
        data_selecionada = st.sidebar.date_input("Selecione o Período:", value=(data_min, data_max), min_value=data_min, format="DD/MM/YYYY")
        if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
            data_inicio, data_fim = data_selecionada
        else:
            data_inicio, data_fim = None, None
    else:
        data_inicio, data_fim = None, None
    df_filtrado = df.copy()
    if monitor_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Nome do monitor'].isin(monitor_selecionado)]
    if preceptor_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Nome do preceptor'].isin(preceptor_selecionado)]
    if data_inicio and data_fim:
        df_filtrado = df_filtrado[(df_filtrado['Data da atividade'].dt.date >= data_inicio) & (df_filtrado['Data da atividade'].dt.date <= data_fim)]
    st.header(f"Relatórios Encontrados: {len(df_filtrado)}")
    st.dataframe(df_filtrado)
    st.markdown("---")
    st.header("Visualizar Relatório Detalhado")
    if not df_filtrado.empty:
        opcoes_relatorios = [f"{row['Data da atividade'].strftime('%d/%m/%Y')} - {row['Nome do monitor']}" for index, row in df_filtrado.iterrows()]
        relatorio_escolhido = st.selectbox("Selecione um relatório para ler os detalhes:", options=opcoes_relatorios)
        if relatorio_escolhido:
            indice_selecionado = opcoes_relatorios.index(relatorio_escolhido)
            id_real = df_filtrado.index[indice_selecionado]
            relatorio_completo = df.loc[id_real]
            st.subheader(f"Relatório de: {relatorio_completo['Nome do monitor']}")
            st.write(f"**Data:** {relatorio_completo['Data da atividade'].strftime('%d/%m/%Y')} | **Preceptor(a):** {relatorio_completo['Nome do preceptor']}")
            
            with st.expander("Atividade(s) Realizada(s)"):
                st.write(relatorio_completo['ATIVIDADE(S) REALIZADA(S)'])
            with st.expander("Atividade(s) Realizada(s)"):
                st.write(relatorio_completo['OBJETIVO DA(S) ATIVIDADE(S)'])    
            with st.expander("Relato com Fundamentação Teórica"):
                st.write(relatorio_completo['RELATO COM FUNDAMENTAÇÃO TEÓRICA'])
            with st.expander("Reflexões Críticas"):
                st.write(relatorio_completo['REFLEXÕES CRÍTICAS'])
    else:
        st.warning("Nenhum relatório encontrado com os filtros atuais.")
else:
    st.warning("Não foi possível carregar os dados. Verifique a URL da planilha e as permissões.")