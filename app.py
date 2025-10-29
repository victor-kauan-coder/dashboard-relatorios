# app.py (Versão final com pt-BR e download PDF)
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import traceback
import locale
from streamlit.errors import StreamlitSecretNotFoundError
from fpdf import FPDF  

# --- CONFIGURA LOCALE PARA PORTUGUÊS BRASIL ---
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")  # Linux/macOS
except:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")  # Windows
    except:
        pass  # Se não conseguir, segue padrão do sistema

# --- CONFIGURAÇÕES ---
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
                creds_dict['private_key'] = creds_dict['private_key'].replace(
                    '\\n', '\n')
                creds = Credentials.from_service_account_info(
                    creds_dict, scopes=scopes)
            else:
                creds = Credentials.from_service_account_file(
                    "credentials.json", scopes=scopes)
        except StreamlitSecretNotFoundError:
            creds = Credentials.from_service_account_file(
                "credentials.json", scopes=scopes)
        except FileNotFoundError:
            st.error(
                "O arquivo 'credentials.json' não foi encontrado. Coloque-o no diretório para execução local.")
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
                    dados['Data da atividade'], errors='coerce', dayfirst=True
                )
                dados.dropna(subset=['Data da atividade'], inplace=True)

            # Corrige horários
            if 'Horário de Início' in dados.columns:
                temp_time = pd.to_datetime(
                    dados['Horário de Início'], errors='coerce')
                dados['Horário de Início'] = temp_time.dt.strftime('%H:%M')

            return dados
        else:
            st.warning("A planilha está vazia ou não contém dados.")
            return pd.DataFrame()

    except Exception:
        st.error("Ocorreu um erro ao carregar os dados.")
        st.code(traceback.format_exc())
        return pd.DataFrame()


# --- (NOVA FUNÇÃO) ---
# --- FUNÇÃO PARA CRIAR O PDF ---
def criar_pdf_do_relatorio(relatorio_completo):
    """
    Cria um PDF formatado a partir de uma série (linha) de dados do relatório.
    """
    
    # --- Preparar os dados (lógica similar à da interface) ---
    tutores = relatorio_completo.get('tutores presentes')
    orientadora = relatorio_completo.get('Orientadora de serviço')
    texto_tutores = 'Nenhuma' if pd.isna(tutores) or tutores == '' else str(tutores)
    texto_orientadora = 'Ausente' if pd.isna(orientadora) or orientadora == '' else str(orientadora)
    horario = relatorio_completo.get('Horário de Início')
    texto_horario = 'Não informado' if pd.isna(horario) or horario == '' else str(horario)
    data_str = relatorio_completo['Data da atividade'].strftime('%d/%m/%Y')
    
    # --- Iniciar PDF ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # A biblioteca fpdf2 usa UTF-8 por padrão, então 'Helvetica' deve funcionar
    # para a maioria dos caracteres em português.
    
    # --- TÍTULO ---
    pdf.set_font("Helvetica", 'B', 16)
    # Garante que o nome não quebre e seja tratado como UTF-8
    nome_monitor = relatorio_completo['Nome do monitor']
    pdf.cell(0, 10, f"Relatório de: {nome_monitor}", ln=True, border=0, align='C')
    pdf.ln(5)

    # --- METADADOS (como na imagem) ---
    pdf.set_font("Helvetica", size=10)
    
    # Linha 1: Data | Preceptor | Orientadora | Tutoras
    linha_meta1 = (
        f"Data: {data_str} | "
        f"Preceptor(a): {relatorio_completo['Nome do preceptor']} | "
        f"Orientadora de Serviço: {texto_orientadora} | "
        f"Tutoras presentes: {texto_tutores}"
    )
    pdf.multi_cell(0, 5, linha_meta1, border=0, align='L')
    
    # Linha 2: Horário
    pdf.cell(0, 5, f"Horário: {texto_horario}", ln=True, border=0, align='L')
    
    # Linha 3: Local
    pdf.cell(0, 5, f"Local: {relatorio_completo['Local Específico:']}", ln=True, border=0, align='L')
    
    pdf.ln(5) # Pular linha

    # --- Função auxiliar para criar as seções ---
    def adicionar_secao(titulo, conteudo):
        pdf.set_font("Helvetica", 'B', 12)
        pdf.set_fill_color(240, 240, 240) # Cor cinza claro (como no expander)
        pdf.cell(0, 8, f" {titulo}", ln=True, border=1, align='L', fill=True)
        
        pdf.set_font("Helvetica", size=11)
        # Tratar conteúdo ausente (NaN) e garantir que é string
        conteudo_texto = "Não informado" if pd.isna(conteudo) else str(conteudo)
            
        # Adicionar borda ao redor do texto
        pdf.multi_cell(0, 6, conteudo_texto, border=1, align='L')
        pdf.ln(5) # Espaçamento entre seções

    # --- Adicionar Seções ---
    adicionar_secao("Atividade(s) Realizada(s)", relatorio_completo.get('ATIVIDADE(S) REALIZADA(S)'))
    adicionar_secao("Objetivo Da(s) Atividade(s)", relatorio_completo.get('OBJETIVO DA(S) ATIVIDADE(S)'))
    adicionar_secao("Relato Fundamentado", relatorio_completo.get('RELATO FUNDAMENTADO'))
    adicionar_secao("Reflexões Críticas", relatorio_completo.get('REFLEXÕES CRÍTICAS'))

    # --- Retornar como bytes ---
    return pdf.output()

# --- FIM DA NOVA FUNÇÃO ---


# --- INTERFACE ---
st.title("📊 Dashboard de Relatórios e Presenças")
st.markdown("---")

df = carregar_dados()
st.sidebar.image("banner-pet.png", width=300)

if not df.empty:
    st.sidebar.header("Filtros:")
    monitores = sorted(df['Nome do monitor'].unique())
    monitor_selecionado = st.sidebar.multiselect(
        "Selecione o Monitor:", options=monitores, default=[])
    preceptores = sorted(df['Nome do preceptor'].unique())
    preceptor_selecionado = st.sidebar.multiselect(
        "Selecione o(a) Preceptor(a):", options=preceptores, default=[])

    data_inicio, data_fim = None, None
    if 'Data da atividade' in df.columns and not df['Data da atividade'].isnull().all():
        data_min = df['Data da atividade'].min().date()
        data_max = df['Data da atividade'].max().date()

        # Caso de apenas um dia
        if data_min >= data_max:
            unica_data = st.sidebar.date_input(
                "Data dos Relatórios:",
                value=data_min,
                disabled=True
            )
            data_inicio, data_fim = unica_data, unica_data
            st.sidebar.write("📅 Selecionada:", unica_data.strftime("%d/%m/%Y"))
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
        df_filtrado = df_filtrado[df_filtrado['Nome do monitor'].isin(
            monitor_selecionado)]
    if preceptor_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Nome do preceptor'].isin(
            preceptor_selecionado)]
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
    df_filtrado = df_filtrado.sort_values(by='Data da atividade', ascending=False)
    if not df_filtrado.empty:
        opcoes_relatorios = [
            f"{row['Data da atividade'].strftime('%d/%m/%Y')} - {row['Nome do monitor']}"
            for _, row in df_filtrado.iterrows()
        ]
        relatorio_escolhido = st.selectbox(
            "Selecione um relatório:", options=opcoes_relatorios)

        if relatorio_escolhido:
            indice_selecionado = opcoes_relatorios.index(relatorio_escolhido)
            id_real = df_filtrado.index[indice_selecionado]
            relatorio_completo = df.loc[id_real]

            # --- (MODIFICADO) ---
            # Movido para cima e garantido que data_str exista
            tutores = relatorio_completo.get('tutores presentes')
            orientadora = relatorio_completo.get('Orientadora de serviço')
            texto_tutores = 'Nenhuma' if pd.isna(
                tutores) or tutores == '' else str(tutores)
            texto_orientadora = 'Ausente' if pd.isna(
                orientadora) or orientadora == '' else str(orientadora)
            horario = relatorio_completo.get('Horário de Início')
            texto_horario = 'Não informado' if pd.isna(
                horario) or horario == '' else str(horario)
            data_str = relatorio_completo['Data da atividade'].strftime('%d/%m/%Y')
            nome_monitor_str = str(relatorio_completo['Nome do monitor']).replace(' ', '_')

            st.subheader(
                f"Relatório de: {relatorio_completo['Nome do monitor']}")
            st.write(
                f"**Data:** {data_str} "
                f"| **Preceptor(a):** {relatorio_completo['Nome do preceptor']} "
                f"| **Orientadora de Serviço:** {texto_orientadora} "
                f"| **Tutoras presentes:** {texto_tutores}"
            )
            st.write(f"**Horário:** {texto_horario}")
            st.write(f"**Local:** {relatorio_completo['Local Específico:']}")

            with st.expander("Atividade(s) Realizada(s)"):
                st.write(relatorio_completo['ATIVIDADE(S) REALIZADA(S)'])
            with st.expander("Objetivo Da(s) Atividade(s)"):
                st.write(relatorio_completo['OBJETIVO DA(S) ATIVIDADE(S)'])
            with st.expander("Relato Fundamentado"):
                st.write(relatorio_completo['RELATO FUNDAMENTADO'])
            with st.expander("Reflexões Críticas"):
                st.write(relatorio_completo['REFLEXÕES CRÍTICAS'])
            
            # --- (NOVO) ---
            # --- BOTÃO DE DOWNLOAD PDF ---
            st.markdown("---")
            try:
                # 1. Gera o PDF em memória
                pdf_bytes = criar_pdf_do_relatorio(relatorio_completo)
                
                # 2. Cria o nome do arquivo
                nome_arquivo = f"Relatorio_{nome_monitor_str}_{data_str}.pdf"
                
                # 3. Cria o botão de download
                st.download_button(
                    label="📥 Baixar Relatório em PDF",
                    data=pdf_bytes,
                    file_name=nome_arquivo,
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o PDF: {e}")
                st.code(traceback.format_exc())
            # --- FIM DO NOVO BLOCO ---
            
    else:
        st.warning("Nenhum relatório encontrado com os filtros atuais.")
else:
    st.warning(
        "Não foi possível carregar os dados. Verifique a URL da planilha e as permissões.")