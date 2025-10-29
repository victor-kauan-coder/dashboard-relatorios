# app.py (Versão final com PDF de Frequência Mensal)
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import traceback
import locale
from streamlit.errors import StreamlitSecretNotFoundError
from fpdf import FPDF  


meses_ptbr = ["Janeiro", "Fevereiro", "Março", "Abril","Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

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

import unicodedata

def limpar_texto(texto):
    """Remove caracteres Unicode problemáticos e normaliza acentos."""
    if not isinstance(texto, str):
        texto = str(texto)
    texto = texto.replace("—", "-").replace("-", "-").replace("•", "-")  # substitui traços e bullets
    texto = unicodedata.normalize('NFKD', texto)
    return texto

def criar_pdf_frequencia(df_monitor, nome_monitor, mes_ano, ano, preceptora):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Adiciona uma fonte Unicode
    pdf.set_font('Arial', '', 10)

    # --- Cabeçalho ---
    pdf.cell(0, 8, "UNIVERSIDADE FEDERAL DO PIAUÍ - UFPI", ln=True, align='C')
    pdf.cell(0, 8, "PROJETO PET SAÚDE/I&SD - INFORMAÇÃO E SAÚDE DIGITAL", ln=True, align='C')
    pdf.ln(6)
    pdf.cell(0, 8, "FOLHA DE FREQUÊNCIA - MONITORES", ln=True, align='C')
    pdf.ln(8)

    pdf.set_font('DejaVu', '', 10)
    pdf.cell(0, 6, f"MÊS DE REFERÊNCIA: {meses_ptbr[mes_ano-1]}/{ano}", ln=True)
    pdf.cell(0, 6, "Grupo Tutorial: Grupo 1 - Letramento para Usuários dos Serviços Digitais do SUS", ln=True)
    pdf.cell(0, 6, "Local de Atuação: CAPS AD - Teresina / PI", ln=True)
    pdf.cell(0, 6, f"Preceptora: {preceptora}", ln=True)
    pdf.cell(0, 6, f"Monitor(a): {nome_monitor}", ln=True)
    pdf.ln(6)

    # --- Tabela ---
    pdf.set_font('DejaVu', 'B', 9)
    w_data, w_ent, w_sai, w_ati, w_ass = 25, 25, 25, 85, 30

    # Cabeçalho
    pdf.cell(w_data, 8, "Data", border=1, align='C')
    pdf.cell(w_ent, 8, "Entrada", border=1, align='C')
    pdf.cell(w_sai, 8, "Saída", border=1, align='C')
    pdf.cell(w_ati, 8, "Atividades Desenvolvidas", border=1, align='C')
    pdf.cell(w_ass, 8, "Assinatura", border=1, align='C')
    pdf.ln()

    pdf.set_font('DejaVu', '', 9)
    df_monitor = df_monitor.sort_values(by='Data da atividade')

    for _, row in df_monitor.iterrows():
        data = row['Data da atividade'].strftime('%d/%m/%Y')
        entrada = str(row.get('Horário de Início', ''))
        saida = "18:00"
        atividade_texto = limpar_texto(row.get('ATIVIDADE(S) REALIZADA(S)', '') or '')

        y_inicio = pdf.get_y()

        pdf.cell(w_data, 6, data, border=1, align='C')
        pdf.cell(w_ent, 6, entrada, border=1, align='C')
        pdf.cell(w_sai, 6, saida, border=1, align='C')

        x_ati = pdf.get_x()
        pdf.multi_cell(w_ati, 6, atividade_texto, border=1, align='L')
        y_final = pdf.get_y()

        h_total = y_final - y_inicio
        x_ass = x_ati + w_ati
        pdf.set_xy(x_ass, y_inicio)
        pdf.cell(w_ass, h_total, "", border=1)

        pdf.rect(pdf.l_margin, y_inicio, w_data, h_total)
        pdf.rect(pdf.l_margin + w_data, y_inicio, w_ent, h_total)
        pdf.rect(pdf.l_margin + w_data + w_ent, y_inicio, w_sai, h_total)

        pdf.set_y(y_final)

    pdf.ln(10)
    pdf.set_font('DejaVu', '', 10)
    pdf.cell(0, 6, "Observações:", ln=True)
    pdf.cell(0, 10, "", border='B', ln=True)
    pdf.ln(15)
    pdf.cell(0, 6, "VISTO DO PRECEPTOR: _________________________________________  DATA: ____ / ____ / ______", ln=True)

    # Retorna bytes diretamente
    return pdf.output(dest='S').encode('latin1')



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

    # --- FILTROS (CÁLCULO) ---
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
        
    # --- (NOVO) BOTÃO DE DOWNLOAD DA FREQUÊNCIA ---
    # Só mostra se UM monitor estiver selecionado
    if len(monitor_selecionado) == 1:
        # Usa o df_filtrado, que já contém os dados corretos
        if not df_filtrado.empty:
            nome_monitor = monitor_selecionado[0]
            # Pega a preceptora do primeiro registro (já que está filtrado)
            preceptora = df_filtrado['Nome do preceptor'].iloc[0] #
            
            # Pega o Mês/Ano da primeira entrada para o título
            mes = df_filtrado['Data da atividade'].iloc[0].month
            ano = df_filtrado['Data da atividade'].iloc[0].year
            data_pdf_inicio = df_filtrado['Data da atividade'].min().strftime('%d-%m')
            data_pdf_fim = df_filtrado['Data da atividade'].max().strftime('%d-%m')

            try:
                # 1. Gera os dados do PDF
                pdf_data_freq = criar_pdf_frequencia(
                    df_filtrado, 
                    nome_monitor, 
                    mes, 
                    ano,
                    preceptora
                )
                
                # --- (ESTA É A CORREÇÃO) ---
                # 2. Garante que os dados estão no formato 'bytes'
                pdf_bytes_freq = bytes(pdf_data_freq)
                
                # 3. Define o nome do arquivo
                nome_arquivo_freq = f"Frequencia_{nome_monitor.replace(' ', '_')}_{data_pdf_inicio}_a_{data_pdf_fim}.pdf"
                
                # 4. Cria o botão de download
                st.sidebar.download_button(
                    label="📥 Baixar Folha de Frequência (PDF)",
                    data=pdf_bytes_freq, # Usa os dados em 'bytes'
                    file_name=nome_arquivo_freq,
                    mime="application/pdf",
                    key="btn_freq_pdf"
                )
            except Exception as e:
                st.sidebar.error(f"Erro ao gerar PDF de frequência: {e}")
                st.sidebar.code(traceback.format_exc()) # Adicionado para debug
        else:
            # Mostra info se o filtro não retornou nada
            st.sidebar.info("Nenhum registro no período para gerar a frequência.")
    # --- FIM DO NOVO BLOCO ---


    # --- TABELA ---
    st.header(f"Relatórios Encontrados: {len(df_filtrado)}")
    st.dataframe(df_filtrado)
    st.markdown("---")

    # --- DETALHES ---
    st.header("Visualizar Relatório Detalhado")
    df_filtrado_detalhes = df_filtrado.sort_values(by='Data da atividade', ascending=False)
    if not df_filtrado_detalhes.empty:
        opcoes_relatorios = [
            f"{row['Data da atividade'].strftime('%d/%m/%Y')} - {row['Nome do monitor']}"
            for _, row in df_filtrado_detalhes.iterrows()
        ]
        relatorio_escolhido = st.selectbox(
            "Selecione um relatório:", options=opcoes_relatorios)

        if relatorio_escolhido:
            indice_selecionado = opcoes_relatorios.index(relatorio_escolhido)
            id_real = df_filtrado_detalhes.index[indice_selecionado]
            relatorio_completo = df.loc[id_real]

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
            
            # --- O BLOCO DE DOWNLOAD INDIVIDUAL FOI REMOVIDO DAQUI ---
            
    else:
        st.warning("Nenhum relatório encontrado com os filtros atuais.")
else:
    st.warning(
        "Não foi possível carregar os dados. Verifique a URL da planilha e as permissões.")
