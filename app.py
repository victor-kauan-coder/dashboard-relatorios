# app.py (Versão final correta para funcionar ONLINE e LOCALMENTE)
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import traceback
import os
import sys
from streamlit.errors import StreamlitSecretNotFoundError

# --- CONFIGURAções ---
st.set_page_config(page_title="Dashboard de Relatórios", layout="wide",page_icon="pet-logo.png")
st.markdown(
    """
    <style>
        div[data-testid="stSidebarUserContent"] {
            padding-top: 1rem;
        }
        
        div[data-testid="stSidebarUserContent"] img {
            margin-top: -50px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)
URL_DA_PLANILHA = "https://docs.google.com/spreadsheets/d/1PwDHHAD4ITWZoHuPpFVBE7t3kJy3Wxaw5APSVomBVOA/edit?usp=sharing"

# --- FUNÇÃO PARA CARREGAR DADOS (COM LÓGICA PARA ONLINE E LOCAL) ---

@st.cache_data(ttl=60)

def carregar_dados():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
        
        # --- LÓGICA DE CREDENCIAIS CORRIGIDA E FINAL ---
        try:
            # Tenta usar os Secrets primeiro (para a nuvem)
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            else:
                # Se não houver o secret específico, usa o ficheiro local
                creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        except StreamlitSecretNotFoundError:
            # Se o ficheiro de secrets NEM EXISTE, usa o ficheiro local
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        except FileNotFoundError:
            st.error("O arquivo 'credentials.json' não foi encontrado. Certifique-se de que ele está no diretório correto para execução local.")
            return pd.DataFrame()


        client = gspread.authorize(creds)
        
        sheet = client.open_by_url(URL_DA_PLANILHA).sheet1
        all_values = sheet.get_all_values()
        
        if len(all_values) > 1:
            header = all_values[0]
            data = all_values[1:]
            dados = pd.DataFrame(data, columns=header)
            dados.columns = dados.columns.str.strip()
            
            # Trata a coluna de data para o formato correto (lendo mm/dd/yyyy)
            if 'Data da atividade' in dados.columns:
                dados['Data da atividade'] = pd.to_datetime(dados['Data da atividade'], errors='coerce', dayfirst=False)
                dados.dropna(subset=['Data da atividade'], inplace=True)
            
            # ADICIONADO: Trata a coluna de horário para garantir o formato 24h (HH:MM)
            if 'Horário de Início' in dados.columns:
                # Converte para objeto datetime, o que permite ler vários formatos (ex: 2 PM, 14:00)
                temp_time = pd.to_datetime(dados['Horário de Início'], errors='coerce')
                # Formata para string no padrão HH:MM. Horas inválidas se tornarão NaT (Not a Time)
                dados['Horário de Início'] = temp_time.dt.strftime('%H:%M')

            return dados
        else:
            st.warning("A planilha está vazia ou não contém dados.")
            return pd.DataFrame()
            
    except Exception as e:
        st.error("Ocorreu um erro ao carregar os dados. Verifique os logs ou a configuração dos Secrets.")
        st.code(traceback.format_exc())
        return pd.DataFrame()

# --- O RESTO DA INTERFACE ---
st.title("📊 Dashboard de Relatórios e Presenças")
st.markdown("---")
df = carregar_dados()
st.sidebar.image("banner-pet.png", width=300) 
if not df.empty:
    st.sidebar.header("Filtros:")
    monitores = sorted(df['Nome do monitor'].unique())
    monitor_selecionado = st.sidebar.multiselect("Selecione o Monitor:", options=monitores, default=[])
    preceptores = sorted(df['Nome do preceptor'].unique())
    preceptor_selecionado = st.sidebar.multiselect("Selecione o(a) Preceptor(a):", options=preceptores, default=[])
    
    data_inicio, data_fim = None, None
    if 'Data da atividade' in df.columns and not df['Data da atividade'].isnull().all():
        data_min = df['Data da atividade'].min().date()
        data_max = df['Data da atividade'].max().date()

        # CORRIGIDO: Trata o caso de haver apenas um dia de dados para evitar o erro da API
        if data_min >= data_max:
            st.sidebar.date_input(
                "Data dos Relatórios:",
                value=data_min,
                disabled=True,
                format="DD/MM/YY"
            )
            data_inicio, data_fim = data_min, data_max
        else:
            data_selecionada = st.sidebar.date_input(
                "Selecione o Período:", 
                value=(data_min, data_max), 
                min_value=data_min, 
                max_value=data_max, 
                format="DD/MM/YY"
            )
            if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
                data_inicio, data_fim = data_selecionada
            else:
                # Se o intervalo não estiver completo (ex: usuário limpou uma data), não filtra
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
        opcoes_relatorios = [f"{row['Data da atividade'].strftime('%d/%m/%y')} - {row['Nome do monitor']}" for index, row in df_filtrado.iterrows()]
        relatorio_escolhido = st.selectbox("Selecione um relatório para ler os detalhes:", options=opcoes_relatorios)
        if relatorio_escolhido:
            indice_selecionado = opcoes_relatorios.index(relatorio_escolhido)
            id_real = df_filtrado.index[indice_selecionado]
            relatorio_completo = df.loc[id_real]
            tutores = relatorio_completo.get('tutores presentes')

            texto_tutores = 'Nenhuma' if pd.isna(tutores) or tutores == '' else tutores
            horario = relatorio_completo.get('Horário de Início')
            texto_horario = 'Não informado' if pd.isna(horario) or horario == '' else horario
            
            st.subheader(f"Relatório de: {relatorio_completo['Nome do monitor']}")
            st.write(f"**Data:** {relatorio_completo['Data da atividade'].strftime('%d/%m/%y')} | **Preceptor(a):** {relatorio_completo['Nome do preceptor']} | **Tutoras presentes:** {texto_tutores}")
            st.write(f"**Horário:** {texto_horario}")
            st.write(f"**Local:** {relatorio_completo['Local Específico:']}")
            
            with st.expander("Atividade(s) Realizada(s)"):
                st.write(relatorio_completo['ATIVIDADE(S) REALIZADA(S)'])
            with st.expander("Objetivo Da(s) Atividade(s)"):
                st.write(relatorio_completo['OBJETIVO DA(S) ATIVIDADE(S)'])      
            with st.expander("Relato com Fundamentação Teórica"):
                st.write(relatorio_completo['RELATO COM FUNDAMENTAÇÃO TEÓRICA'])
            with st.expander("Referências"):
                st.write(relatorio_completo['REFERÊNCIAS'])      
            with st.expander("Reflexões Críticas"):
                st.write(relatorio_completo['REFLEXÕES CRÍTICAS'])
    else:
        st.warning("Nenhum relatório encontrado com os filtros atuais.")
else:
    st.warning("Não foi possível carregar os dados. Verifique a URL da planilha e as permissões.")

