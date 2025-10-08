# app.py (Versão final corrigida)
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import traceback
from streamlit.errors import StreamlitSecretNotFoundError

# --- CONFIGURAções ---
st.set_page_config(
    page_title="Dashboard de Relatórios",
    layout="wide",
    page_icon="pet-logo.png"
)
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

# --- FUNÇÃO PARA CARREGAR DADOS ---
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
        
        # --- CREDENCIAIS ---
        try:
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            else:
                creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        except StreamlitSecretNotFoundError:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        except FileNotFoundError:
            st.error("O arquivo 'credentials.json' não foi encontrado. Coloque-o no diretório para execução local.")
            return pd.DataFrame()

        client = gspread.authorize(creds)
        sheet = client.open_by_url(URL_DA_PLANILHA).sheet1
        all_values = sheet.get_all_values()
        
        if len(all_values) > 1:
            header = all_values[0]
            data = all_values[1:]
            dados = pd.DataFrame(data, columns=header)
            dados.columns = dados.columns.str.strip()
            
            # Corrige datas
            if 'Data da atividade' in dados.columns:
                dados['Data da atividade'] = pd.to_datetime(
                    dados['Data da atividade'], errors='coerce', dayfirst=False
                )
                dados.dropna(subset=['Data da atividade'], inplace=True)
            
            # Corrige horários
            if 'Horário de Início' in dados.columns:
                temp_time = pd.to_datetime(dados['Horário de Início'], errors='coerce')
                dados['Horário de Início'] = temp_time.dt.strftime('%H:%M')

            return dados
        else:
            st.warning("A planilha está vazia ou não contém dados.")
            return pd.DataFrame()
            
    except Exception:
        st.error("Ocorreu um erro ao carregar os dados.")
        st.code(traceback.format_exc())
        return pd.DataFrame()


# --- INTERFACE ---
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

        # Caso de apenas um dia
        if data_min >= data_max:
            st.sidebar.date_input(
                "Data dos Relatórios:",
                value=data_min,
                disabled=True
            )
            data_inicio, data_fim = data_min, data_max
        else:
            data_selecionada = st.sidebar.date_input(
                "Selecione o Período:", 
                value=(data_min, data_max), 
                min_value=data_min, 
                max_value=data_max
            )
            if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
                data_inicio, data_fim = data_selecionada

    # --- FILTROS ---
    df_filtrado = df.copy()
    if monitor_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Nome do monitor'].isin(monitor_selecionado)]
    if preceptor_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Nome do preceptor'].isin(preceptor_selecionado)]
    if data_inicio and data_fim:
        df_filtrado = df_filtrado[
            (df_filtrado['Data da atividade'].dt.date >= data_inicio) & 
            (df_filtrado['Data da atividade'].dt.date <= data_fim)
        ]
    
    # --- TABELA ---
    st.header(f"Relatórios Encontrados: {len(df_filtrado)}")
    st.dataframe(df_filtrado)
    st.markdown("---")

    # --- DETALHES ---
    st.header("Visualizar Relatório Detalhado")
    if not df_filtrado.empty:
        opcoes_relatorios = [
            f"{row['Data da atividade'].strftime('%d/%m/%Y')} - {row['Nome do monitor']}" 
            for _, row in df_filtrado.iterrows()
        ]
        relatorio_escolhido = st.selectbox("Selecione um relatório:", options=opcoes_relatorios)
        
        if relatorio_escolhido:
            indice_selecionado = opcoes_relatorios.index(relatorio_escolhido)
            id_real = df_filtrado.index[indice_selecionado]
            relatorio_completo = df.loc[id_real]

            tutores = relatorio_completo.get('tutores presentes')
            texto_tutores = 'Nenhuma' if pd.isna(tutores) or tutores == '' else tutores
            horario = relatorio_completo.get('Horário de Início')
            texto_horario = 'Não informado' if pd.isna(horario) or horario == '' else horario
            
            st.subheader(f"Relatório de: {relatorio_completo['Nome do monitor']}")
            st.write(
                f"**Data:** {relatorio_completo['Data da atividade'].strftime('%d/%m/%Y')} "
                f"| **Preceptor(a):** {relatorio_completo['Nome do preceptor']} "
                f"| **Tutoras presentes:** {texto_tutores}"
            )
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
