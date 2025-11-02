# app.py (Versão final com PDF de Frequência Mensal)
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import traceback
import locale
from streamlit.errors import StreamlitSecretNotFoundError
from fpdf import FPDF  
from datetime import date,datetime, timedelta

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
    """Remove caracteres Unicode problemáticos para 'latin-1'."""
    if not isinstance(texto, str):
        texto = str(texto)
    
    # 1. Substituições manuais para caracteres comuns
    texto = texto.replace('–', '-') # En dash
    texto = texto.replace('—', '-') # Em dash
    texto = texto.replace('“', '"') # Aspas curvas
    texto = texto.replace('”', '"') # Aspas curvas
    texto = texto.replace('‘', "'") # Apóstrofo curvo
    texto = texto.replace('’', "'") # Apóstrofo curvo
    texto = texto.replace('•', '-') # Bullet
    
    # 2. Normaliza (decompõe acentos) e re-codifica
    # Isso tentará manter os acentos do 'latin-1' e descartará o resto
    try:
        # Tenta normalizar e codificar para latin-1, ignorando erros
        texto = unicodedata.normalize('NFKD', texto).encode('latin-1', 'ignore').decode('latin-1')
    except:
        # Fallback para ASCII puro se latin-1 falhar (raro)
        texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
        
    return texto


# --- FUNÇÃO PDF (Folha de Frequência) ---
def criar_pdf_frequencia(df_monitor, nome_monitor, mes, ano, preceptora):
    """
    Cria um PDF de folha de frequência baseado no template .docx
    usando os dados filtrados do DataFrame.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Define a fonte. 'Arial' é mais seguro para servidores que 'Helvetica'
    try:
        pdf.set_font("Arial", 'B', 12)
    except Exception:
        pdf.set_font("Helvetica", 'B', 12)


    # --- CABEÇALHO (do docx) ---
    # (MODIFICADO) Limpa o texto do cabeçalho
    pdf.cell(0, 5, limpar_texto("UNIVERSIDADE FEDERAL DO PIAUÍ - UFPI"), ln=True, align='C') 
    pdf.cell(0, 5, limpar_texto("PROJETO PET SAÚDE/I&SD - INFORMAÇÃO E SAÚDE DIGITAL"), ln=True, align='C') 
    pdf.ln(5)
    pdf.cell(0, 7, limpar_texto("FOLHA DE FREQUÊNCIA - MONITORES"), ln=True, align='C') 
    pdf.ln(5)

    # --- METADADOS (do docx) ---
    if 'Arial' in pdf.font_family:
        pdf.set_font("Arial", size=10)
    else:
        pdf.set_font("Helvetica", size=10)
        
    # (MODIFICADO) Limpa o texto dos metadados
    pdf.cell(0, 5, limpar_texto(f"MÊS DE REFERÊNCIA: {meses_ptbr[mes-1].upper()} / {ano}"), ln=True) 
    pdf.cell(0, 5, limpar_texto("Grupo Tutorial: Grupo 1 - Letramento para Usuários dos Serviços Digitais do SUS"), ln=True) #
    pdf.cell(0, 5, limpar_texto("Local de Atuação: CAPS AD - Teresina / PI"), ln=True) #
    pdf.cell(0, 5, limpar_texto(f"Preceptora: {preceptora}"), ln=True) #
    pdf.cell(0, 5, limpar_texto(f"Monitor: {nome_monitor}"), ln=True) # (Adicionado para clareza)
    pdf.ln(5)

    # --- TABELA ---
    if 'Arial' in pdf.font_family:
        pdf.set_font("Arial", 'B', 8) # (MANTIDO) Fonte tamanho 8
    else:
        pdf.set_font("Helvetica", 'B', 8) # (MANTIDO) Fonte tamanho 8
    
    # Larguras das colunas (total 190mm)
    w_data = 25
    w_ent = 25
    w_sai = 25
    w_ati = 85  # Coluna principal
    w_ass = 30
    
    # Cabeçalho da Tabela
    # (MODIFICADO) Limpa o texto do cabeçalho da tabela
    pdf.cell(w_data, 7, limpar_texto("Data"), border=1, align='C')
    pdf.cell(w_ent, 7, limpar_texto("Horário de Entrada"), border=1, align='C')
    pdf.cell(w_sai, 7, limpar_texto("Horário de Saída"), border=1, align='C')
    pdf.cell(w_ati, 7, limpar_texto("Atividades Desenvolvidas"), border=1, align='C')
    # pdf.cell(w_ass, 7, limpar_texto("Assinatura do Monitor"), border=1, align='C') #
    pdf.ln()

    # Conteúdo da Tabela
    if 'Arial' in pdf.font_family:
        pdf.set_font("Arial", size=8) # (MANTIDO) Fonte tamanho 8
    else:
        pdf.set_font("Helvetica", size=8) # (MANTIDO) Fonte tamanho 8
        
    # Garante que os dados estão em ordem de data
    df_monitor = df_monitor.sort_values(by='Data da atividade')
    
    # Define uma altura de linha base
    altura_linha_base = 5 # (MANTIDO) Altura 5
    
    for _, row in df_monitor.iterrows():
        # (MODIFICADO) Limpa os dados da tabela
        data = limpar_texto(row['Data da atividade'].strftime('%d/%m/%Y'))
        entrada_str = str(row.get('Horário de Início', '')).strip()
        try:
            # Converte a string de hora (ex: "14:00") em objeto datetime
            entrada_dt = datetime.strptime(entrada_str, "%H:%M")
            # Soma 4 horas
            saida_dt = entrada_dt + timedelta(hours=4)
            # Formata de volta para string "HH:MM"
            saida = saida_dt.strftime("%H:%M")
        except ValueError:
            # Caso o campo venha vazio ou inválido
            entrada_str = ""
            saida = ""
            
        entrada = limpar_texto(entrada_str)
        saida = limpar_texto(saida)
        
        atividade_texto = limpar_texto(row.get('ATIVIDADE(S) REALIZADA(S)', '')).upper()
        if pd.isna(atividade_texto):
            atividade_texto = ''
        
        # (REMOVIDO) A função limpar_texto() já faz isso
        
        # (MANTIDO) Lógica de formatação da tabela
        
        y_inicial = pdf.get_y()
        
        pdf.cell(w_data, altura_linha_base, data, border=0, align='C')
        pdf.cell(w_ent, altura_linha_base, entrada, border=0, align='C')
        pdf.cell(w_sai, altura_linha_base, saida, border=0, align='C')

        x_ati = pdf.get_x()
        
        pdf.multi_cell(w_ati, altura_linha_base, atividade_texto, border=1, align='L')

        y_final_ati = pdf.get_y()
        
        h_real = y_final_ati - y_inicial
        
        # x_ass = x_ati + w_ati
        # pdf.set_xy(x_ass, y_inicial)
        # pdf.cell(w_ass, h_real, "", border=1) 
        
        pdf.rect(pdf.l_margin, y_inicial, w_data, h_real)
        pdf.rect(pdf.l_margin + w_data, y_inicial, w_ent, h_real)
        pdf.rect(pdf.l_margin + w_data + w_ent, y_inicial, w_sai, h_real)

        pdf.set_y(y_final_ati)


    # --- RODAPÉ (do docx) ---
    pdf.ln(10)
    if 'Arial' in pdf.font_family:
        pdf.set_font("Arial", size=10)
    else:
        pdf.set_font("Helvetica", size=10)
        
    # (MODIFICADO) Limpa o texto do rodapé
    pdf.cell(0, 5, limpar_texto("Observações:"), ln=True) #
    pdf.cell(0, 5, "", border='B', ln=True) # Linha em branco para observações
    pdf.ln(15)
    pdf.cell(0, 5, limpar_texto("ASSINATURA DO MONITOR: _________________________________________ "), align='L')
    pdf.ln(15)
    pdf.cell(0, 5, limpar_texto("VISTO DO PRECEPTOR: _________________________________________ DATA: ____ / ____ / ______"), align='L') #
    
    # (MANTIDO) Retorna 'bytes' (sem o .encode('latin1') que causava erro)
    return pdf.output()



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
        hoje = date.today()
        data_min_default = hoje.replace(day=1)  # primeiro dia do mês atual
        data_max_default = hoje  # dia atual

        # Defina o intervalo padrão, mas permita escolher qualquer data
        data_selecionada = st.sidebar.date_input(
            "Selecione o Período:",
            value=(data_min_default, data_max_default),
            format="DD/MM/YYYY"
        )

        # Garante que temos um intervalo válido
        if isinstance(data_selecionada, tuple) and len(data_selecionada) == 2:
            data_inicio, data_fim = data_selecionada
        else:
            data_inicio, data_fim = data_min_default, data_max_default

        st.sidebar.write(
            f"📅 Período selecionado: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}"
        )

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
