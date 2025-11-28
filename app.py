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
    page_icon="pet-logo.png" # Certifique-se que este arquivo existe ou remova a linha
)

# CSS para ajuste do sidebar
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

# ==========================================
# FUNÇÕES DE DADOS (Google Sheets)
# ==========================================
@st.cache_data(ttl=60)
def carregar_dados():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]

        # Tenta carregar credenciais (Secrets ou Arquivo JSON)
        try:
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            else:
                creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        except (StreamlitSecretNotFoundError, FileNotFoundError):
            st.error("Arquivo 'credentials.json' não encontrado e secrets não configurados.")
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
                temp_time = pd.to_datetime(dados['Horário de Início'], errors='coerce')
                dados['Horário de Início'] = temp_time.dt.strftime('%H:%M')

            return dados
        else:
            return pd.DataFrame()

    except Exception:
        st.error("Ocorreu um erro ao carregar os dados.")
        st.code(traceback.format_exc())
        return pd.DataFrame()

# ==========================================
# FUNÇÕES DE PDF
# ==========================================

def limpar_texto(texto):
    """
    Limpa o texto para ser compatível com PDF (Latin-1).
    Remove caracteres Unicode complexos e mantêm acentos básicos.
    """
    if pd.isna(texto) or texto == "":
        return ""
    
    texto_str = str(texto)
    # Substituições manuais comuns
    texto_str = texto_str.replace('–', '-').replace('—', '-')
    texto_str = texto_str.replace('“', '"').replace('”', '"')
    texto_str = texto_str.replace('‘', "'").replace('’', "'")
    texto_str = texto_str.replace('•', '-')
    
    # Codificação forçada para Latin-1 (Core fonts do FPDF)
    try:
        return texto_str.encode('latin-1', 'replace').decode('latin-1')
    except Exception:
        return texto_str

def _desenhar_pagina_monitor(pdf, df_monitor, nome_monitor, mes, ano, preceptora):
    """
    Desenha o conteúdo (cabeçalho + tabela) de UM monitor na página atual.
    """
    meses_ptbr = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    # Tenta usar Arial, fallback para Helvetica
    try:
        pdf.set_font("Arial", 'B', 12)
        fonte_padrao = "Arial"
    except:
        pdf.set_font("Helvetica", 'B', 12)
        fonte_padrao = "Helvetica"

    # --- CABEÇALHO ---
    pdf.cell(0, 5, limpar_texto("UNIVERSIDADE FEDERAL DO PIAUÍ - UFPI"), ln=True, align='C') 
    pdf.cell(0, 5, limpar_texto("PROJETO PET SAÚDE/I&SD - INFORMAÇÃO E SAÚDE DIGITAL"), ln=True, align='C') 
    pdf.ln(5)
    pdf.cell(0, 7, limpar_texto("FOLHA DE FREQUÊNCIA - MONITORES"), ln=True, align='C') 
    pdf.ln(5)

    # --- METADADOS ---
    pdf.set_font(fonte_padrao, size=10)
    
    # Garante que o mês seja um índice válido (1-12)
    mes_idx = int(mes) - 1 if 1 <= int(mes) <= 12 else 0
    
    pdf.cell(0, 5, limpar_texto(f"MÊS DE REFERÊNCIA: {meses_ptbr[mes_idx].upper()} / {ano}"), ln=True) 
    pdf.cell(0, 5, limpar_texto("Grupo Tutorial: Grupo 1 - Letramento para Usuários dos Serviços Digitais do SUS"), ln=True)
    pdf.cell(0, 5, limpar_texto("Local de Atuação: CAPS AD - Teresina / PI"), ln=True)
    pdf.cell(0, 5, limpar_texto(f"Preceptora: {preceptora}"), ln=True)
    pdf.cell(0, 5, limpar_texto(f"Monitor: {nome_monitor}"), ln=True)
    pdf.ln(5)

    # --- TABELA ---
    pdf.set_font(fonte_padrao, 'B', 8)
    w_data, w_ent, w_sai, w_ati = 25, 25, 25, 85
    
    pdf.cell(w_data, 7, limpar_texto("Data"), border=1, align='C')
    pdf.cell(w_ent, 7, limpar_texto("Horário de Entrada"), border=1, align='C')
    pdf.cell(w_sai, 7, limpar_texto("Horário de Saída"), border=1, align='C')
    pdf.cell(w_ati, 7, limpar_texto("Atividades Desenvolvidas"), border=1, align='C')
    pdf.ln()

    # --- CONTEÚDO DA TABELA ---
    pdf.set_font(fonte_padrao, size=8)
    if not df_monitor.empty:
        df_monitor = df_monitor.sort_values(by='Data da atividade')
    
    altura_linha_base = 5
    
    for _, row in df_monitor.iterrows():
        # Data
        data_val = row['Data da atividade']
        data = limpar_texto(data_val.strftime('%d/%m/%Y')) if not pd.isna(data_val) else ""

        # Horários
        entrada_str = str(row.get('Horário de Início', '')).strip()
        try:
            entrada_dt = datetime.strptime(entrada_str, "%H:%M")
            saida_dt = entrada_dt + timedelta(hours=4)
            saida = saida_dt.strftime("%H:%M")
        except ValueError:
            saida = ""
        
        entrada = limpar_texto(entrada_str)
        saida = limpar_texto(saida)
        
        # Atividade
        raw_ativ = str(row.get('ATIVIDADE(S) REALIZADA(S)', ''))
        if raw_ativ.lower() == 'nan': raw_ativ = ''
        atividade_texto = limpar_texto(raw_ativ.upper())
        
        # Renderização
        y_inicial = pdf.get_y()
        
        pdf.cell(w_data, altura_linha_base, data, border=0, align='C')
        pdf.cell(w_ent, altura_linha_base, entrada, border=0, align='C')
        pdf.cell(w_sai, altura_linha_base, saida, border=0, align='C')

        x_ati = pdf.get_x()
        pdf.multi_cell(w_ati, altura_linha_base, atividade_texto, border=1, align='L')
        y_final_ati = pdf.get_y()
        
        h_real = y_final_ati - y_inicial
        
        # Bordas laterais para acompanhar altura
        pdf.rect(pdf.l_margin, y_inicial, w_data, h_real)
        pdf.rect(pdf.l_margin + w_data, y_inicial, w_ent, h_real)
        pdf.rect(pdf.l_margin + w_data + w_ent, y_inicial, w_sai, h_real)

        pdf.set_y(y_final_ati)
        
        # Quebra de página se necessário
        if pdf.get_y() > 260: 
             pdf.add_page()

    # --- RODAPÉ ---
    pdf.ln(10)
    pdf.set_font(fonte_padrao, size=10)
    pdf.cell(0, 5, limpar_texto("Observações:"), ln=True)
    pdf.cell(0, 5, "", border='B', ln=True)
    pdf.ln(15)
    pdf.cell(0, 5, limpar_texto("ASSINATURA DO MONITOR: _________________________________________ "), align='L')
    pdf.ln(15)
    
    dia, mes_hj, ano_hj = date.today().day, date.today().month, date.today().year
    pdf.cell(0, 5, limpar_texto(f"VISTO DO PRECEPTOR: _________________________________________ DATA: {dia} / {mes_hj} / {ano_hj}"), align='L')


def gerar_pdf_monitores(df_geral, lista_nomes, mes, ano, col_nome_monitor='Nome do monitor'):
    """
    Gera um único arquivo PDF contendo as frequências de todos os monitores listados.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for nome in lista_nomes:
        pdf.add_page()
        
        # Filtra dados do monitor específico
        df_indiv = df_geral[df_geral[col_nome_monitor] == nome].copy()
        
        if not df_indiv.empty:
            # Descobre o preceptor automaticamente baseado nos dados filtrados
            if 'Nome do preceptor' in df_indiv.columns:
                precep = df_indiv['Nome do preceptor'].iloc[0]
            else:
                precep = "______________"
            
            _desenhar_pagina_monitor(pdf, df_indiv, nome, mes, ano, precep)
        else:
            # Caso raro: Monitor selecionado mas sem dados no período
            pdf.cell(0, 10, limpar_texto(f"Sem dados para {nome} neste período."), ln=True)

    # Retorna os bytes do arquivo (compatível com FPDF antigo e novo)
    saida = pdf.output(dest='S')
    if isinstance(saida, str):
        return saida.encode('latin-1')
    else:
        return bytes(saida)


# ==========================================
# INTERFACE STREAMLIT
# ==========================================
st.title("📊 Dashboard de Relatórios e Presenças")
st.markdown("---")

df = carregar_dados()

# Imagem do banner (se existir)
# st.sidebar.image("banner-pet.png", width=300) 

if not df.empty:
    st.sidebar.header("Filtros:")
    
    # Filtros
    monitores = sorted(df['Nome do monitor'].unique())
    monitor_selecionado = st.sidebar.multiselect("Selecione o(s) Monitor(es):", options=monitores, default=[])
    
    preceptores = sorted(df['Nome do preceptor'].unique())
    preceptor_selecionado = st.sidebar.multiselect("Selecione o(a) Preceptor(a):", options=preceptores, default=[])

    # Datas
    data_inicio, data_fim = None, None
    if 'Data da atividade' in df.columns:
        hoje = date.today()
        d_min = hoje.replace(day=1)
        d_max = hoje
        sel_data = st.sidebar.date_input("Selecione o Período:", value=(d_min, d_max), format="DD/MM/YYYY")
        
        if isinstance(sel_data, tuple) and len(sel_data) == 2:
            data_inicio, data_fim = sel_data
        else:
            data_inicio, data_fim = d_min, d_max
            
        st.sidebar.write(f"📅 Período: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")

    # --- APLICAÇÃO DOS FILTROS ---
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

    # ==========================================
    # BOTÃO DE DOWNLOAD (PDF UNIFICADO)
    # ==========================================
    if monitor_selecionado and not df_filtrado.empty:
        st.sidebar.markdown("---")
        st.sidebar.write(f"📑 **Gerar PDF para {len(monitor_selecionado)} monitor(es)**")
        
        # Pega dados de referência para o nome do arquivo
        d_ini_str = df_filtrado['Data da atividade'].min().strftime('%d-%m')
        d_fim_str = df_filtrado['Data da atividade'].max().strftime('%d-%m')
        
        # Pega mês/ano de referência (da primeira data encontrada)
        mes_ref = df_filtrado['Data da atividade'].iloc[0].month
        ano_ref = df_filtrado['Data da atividade'].iloc[0].year

        if st.sidebar.button("Preparar Arquivo PDF"):
            try:
                # Gera o PDF usando a função unificada
                pdf_bytes = gerar_pdf_monitores(
                    df_geral=df_filtrado, 
                    lista_nomes=monitor_selecionado, 
                    mes=mes_ref, 
                    ano=ano_ref
                )
                
                label_btn = "📥 Baixar PDF Individual" if len(monitor_selecionado) == 1 else "📥 Baixar PDF Consolidado"
                nome_arquivo = f"Frequencia_{len(monitor_selecionado)}_Monitores_{d_ini_str}_a_{d_fim_str}.pdf"
                
                st.sidebar.download_button(
                    label=label_btn,
                    data=pdf_bytes,
                    file_name=nome_arquivo,
                    mime="application/pdf"
                )
            except Exception as e:
                st.sidebar.error(f"Erro ao gerar PDF: {e}")
                st.sidebar.code(traceback.format_exc())
    elif monitor_selecionado:
        st.sidebar.info("Sem dados para os monitores selecionados neste período.")

    # --- EXIBIÇÃO DA TABELA ---
    st.header(f"Relatórios Encontrados: {len(df_filtrado)}")
    st.dataframe(df_filtrado)
    st.markdown("---")

    # --- DETALHES ---
    st.header("Visualizar Relatório Detalhado")
    df_detalhes = df_filtrado.sort_values(by='Data da atividade', ascending=False)
    
    if not df_detalhes.empty:
        opcoes = [f"{row['Data da atividade'].strftime('%d/%m/%Y')} - {row['Nome do monitor']}" for _, row in df_detalhes.iterrows()]
        escolha = st.selectbox("Selecione um relatório:", options=opcoes)

        if escolha:
            idx = opcoes.index(escolha)
            id_real = df_detalhes.index[idx]
            rel = df.loc[id_real]

            # Tratamento de Nulos para exibição
            tutores = str(rel.get('tutores presentes', 'Nenhuma'))
            orient = str(rel.get('Orientadora de serviço', 'Ausente'))
            horario = str(rel.get('Horário de Início', 'Não informado'))
            
            st.subheader(f"Relatório de: {rel['Nome do monitor']}")
            st.write(f"**Data:** {rel['Data da atividade'].strftime('%d/%m/%Y')} | **Preceptor(a):** {rel['Nome do preceptor']}")
            st.write(f"**Orientadora:** {orient} | **Tutoras:** {tutores} | **Horário:** {horario}")
            st.write(f"**Local:** {rel.get('Local Específico:', '')}")

            with st.expander("Atividade(s) Realizada(s)", expanded=True):
                st.write(rel.get('ATIVIDADE(S) REALIZADA(S)', ''))
            with st.expander("Objetivo"):
                st.write(rel.get('OBJETIVO DA(S) ATIVIDADE(S)', ''))
            with st.expander("Relato Fundamentado"):
                st.write(rel.get('RELATO FUNDAMENTADO', ''))
            with st.expander("Reflexões Críticas"):
                st.write(rel.get('REFLEXÕES CRÍTICAS', ''))
    else:
        st.warning("Nenhum relatório encontrado.")
else:
    st.warning("Não foi possível carregar os dados. Verifique credenciais e planilha.")