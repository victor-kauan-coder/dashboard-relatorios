import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import traceback
import locale
from streamlit.errors import StreamlitSecretNotFoundError
from fpdf import FPDF
from datetime import date, datetime, timedelta

# --- CONFIGURA LOCALE ---
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except:
        pass

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Relatórios",
    layout="wide",
    page_icon="pet-logo.png"
)

# Estilo para o Banner
st.markdown(
    """
    <style>
        div[data-testid="stSidebarUserContent"] { padding-top: 1rem; }
        div[data-testid="stSidebarUserContent"] img { margin-top: -50px; }
    </style>
    """,
    unsafe_allow_html=True,
)

URL_DA_PLANILHA = "https://docs.google.com/spreadsheets/d/1PwDHHAD4ITWZoHuPpFVBE7t3kJy3Wxaw5APSVomBVOA/edit?usp=sharing"

# --- CARREGAR DADOS ---
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
        try:
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            else:
                creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        except (StreamlitSecretNotFoundError, FileNotFoundError):
            return pd.DataFrame()

        client = gspread.authorize(creds)
        sheet = client.open_by_url(URL_DA_PLANILHA).sheet1
        all_values = sheet.get_all_values()

        if len(all_values) > 1:
            header = [h.strip() for h in all_values[0]]
            data = all_values[1:]
            dados = pd.DataFrame(data, columns=header)
            
            # 1. Trata Data (Lendo mm/dd/yyyy conforme vem do Forms)
            if 'Data da atividade' in dados.columns:
                dados['Data da atividade'] = pd.to_datetime(dados['Data da atividade'], errors='coerce', dayfirst=False)
                dados.dropna(subset=['Data da atividade'], inplace=True)

            # 2. Trata Horário (Formato 24h)
            if 'Horário de Início' in dados.columns:
                temp_time = pd.to_datetime(dados['Horário de Início'], errors='coerce')
                dados['Horário de Início'] = temp_time.dt.strftime('%H:%M')

            return dados
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame()

# --- UTILITÁRIOS PDF ---
def limpar_texto(texto):
    if pd.isna(texto) or texto == "": return ""
    texto_str = str(texto).replace('–', '-').replace('—', '-').replace('“', '"').replace('”', '"')
    return texto_str.encode('latin-1', 'replace').decode('latin-1')

def _desenhar_pagina(pdf, df_monitor, nome_monitor, mes, ano, preceptora, adicionar_visto=False):
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 5, "UNIVERSIDADE FEDERAL DO PIAUÍ - UFPI", ln=True, align='C')
    pdf.cell(0, 5, "PROJETO PET SAÚDE/I&SD - INFORMAÇÃO E SAÚDE DIGITAL", ln=True, align='C')
    pdf.ln(5)
    pdf.cell(0, 7, "FOLHA DE FREQUÊNCIA", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, limpar_texto(f"MÊS DE REFERÊNCIA: {meses[mes-1].upper()} / {ano}"), ln=True)
    pdf.cell(0, 5, "Grupo Tutorial: Grupo 1 - Letramento para Usuários dos Serviços Digitais do SUS", ln=True)
    
    # Busca a função ou assume MONITOR(A)
    func = str(df_monitor.iloc[0].get('Função', 'MONITOR(A)')).upper()
    if func == 'NAN' or func == '': func = 'MONITOR(A)'
    
    pdf.cell(0, 5, limpar_texto(f"Preceptora: {preceptora}"), ln=True)
    pdf.cell(0, 5, limpar_texto(f"{func}: {nome_monitor}"), ln=True)
    pdf.ln(5)

    # Tabela
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(25, 7, "Data", 1, 0, 'C')
    pdf.cell(25, 7, "Entrada", 1, 0, 'C')
    pdf.cell(25, 7, "Saída", 1, 0, 'C')
    pdf.cell(85, 7, "Atividades", 1, 1, 'C')
    
    pdf.set_font("Arial", size=8)
    for _, row in df_monitor.sort_values('Data da atividade').iterrows():
        data = row['Data da atividade'].strftime('%d/%m/%y')
        entrada = str(row.get('Horário de Início', ''))
        
        # Cálculo automático de saída (Entrada + 4h)
        saida = ""
        if entrada:
            try:
                saida = (datetime.strptime(entrada, "%H:%M") + timedelta(hours=4)).strftime("%H:%M")
            except: pass
            
        ativ = str(row.get('ATIVIDADE(S) REALIZADA(S)', '')).upper()
        
        y_ini = pdf.get_y()
        pdf.multi_cell(160, 5, "", border=0) # Reserva espaço
        y_fim = pdf.get_y()
        # Aqui simplificamos a lógica da tabela para evitar quebras
        pdf.set_y(y_ini)
        pdf.cell(25, 5, data, 1, 0, 'C')
        pdf.cell(25, 5, entrada, 1, 0, 'C')
        pdf.cell(25, 5, saida, 1, 0, 'C')
        pdf.multi_cell(85, 5, limpar_texto(ativ), 1, 'L')

    if adicionar_visto:
        pdf.ln(10)
        pdf.cell(0, 5, "VISTO DO PRECEPTOR: _________________________________________ ", ln=True)

# --- INTERFACE ---
st.title("📊 Dashboard PET Saúde")
df = carregar_dados()

if not df.empty:
    # IMPORTANTE: Verificação de nomes de colunas para evitar o KeyError
    col_monitor = 'Nome do monitor' if 'Nome do monitor' in df.columns else 'Nome'
    
    st.sidebar.image("banner-pet.png", use_container_width=True)
    st.sidebar.header("Filtros")
    
    lista_monitores = sorted(df[col_monitor].unique())
    sel_monitores = st.sidebar.multiselect("Monitores:", options=lista_monitores)
    
    # Filtro de Data
    data_min_df = df['Data da atividade'].min().date()
    data_max_df = df['Data da atividade'].max().date()
    
    periodo = st.sidebar.date_input(
        "Período:", 
        value=(data_min_df, data_max_df),
        min_value=data_min_df,
        max_value=data_max_df,
        format="DD/MM/YY"
    )

    # Aplicar Filtros
    df_f = df.copy()
    if sel_monitores:
        df_f = df_f[df_f[col_monitor].isin(sel_monitores)]
    if isinstance(periodo, tuple) and len(periodo) == 2:
        df_f = df_f[(df_f['Data da atividade'].dt.date >= periodo[0]) & (df_f['Data da atividade'].dt.date <= periodo[1])]

    # Exibição
    st.header(f"Registos: {len(df_f)}")
    st.dataframe(df_f)

    # Detalhes do Relatório
    st.markdown("---")
    st.subheader("Visualizar Relatório Detalhado")
    if not df_f.empty:
        opcoes = [f"{r['Data da atividade'].strftime('%d/%m/%y')} - {r[col_monitor]}" for _, r in df_f.iterrows()]
        escolha = st.selectbox("Escolha um relatório:", opcoes)
        
        if escolha:
            rel = df_f.iloc[opcoes.index(escolha)]
            st.write(f"**Monitor:** {rel[col_monitor]} | **Data:** {rel['Data da atividade'].strftime('%d/%m/%y')}")
            
            # Campos com nomes flexíveis (get evita erro se a coluna mudar)
            with st.expander("Atividades Realizadas"):
                st.write(rel.get('ATIVIDADE(S) REALIZADA(S)', 'Não informado'))
            with st.expander("Objetivo"):
                st.write(rel.get('OBJETIVO DA(S) ATIVIDADE(S)', 'Não informado'))
            with st.expander("Fundamentação Teórica"):
                st.write(rel.get('RELATO COM FUNDAMENTAÇÃO TEÓRICA', rel.get('RELATO FUNDAMENTADO', 'Não informado')))
            with st.expander("Reflexões Críticas"):
                st.write(rel.get('REFLEXÕES CRÍTICAS', 'Não informado'))
    
else:
    st.warning("Nenhum dado carregado. Verifique as credenciais e a planilha.")