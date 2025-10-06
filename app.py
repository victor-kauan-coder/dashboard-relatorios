# app.py (Temporário para Diagnóstico)
import streamlit as st

st.set_page_config(page_title="Diagnóstico de Secrets", layout="centered")
st.title("Página de Diagnóstico de Secrets")

# 1. Verifica se a seção principal [gcp_service_account] existe nos Secrets
if "gcp_service_account" in st.secrets:
    st.success("✅ A seção [gcp_service_account] foi encontrada nos Secrets!")
    
    # Pega o dicionário de credenciais
    creds_dict = st.secrets["gcp_service_account"]
    
    # 2. Verifica se a 'private_key' existe dentro da seção
    if "private_key" in creds_dict:
        st.success("✅ A 'private_key' foi encontrada dentro da seção!")
        
        private_key = creds_dict["private_key"]
        
        # 3. Exibe informações sobre a chave para diagnóstico
        st.write("---")
        st.subheader("Análise da Chave Privada:")
        st.write(f"**Tipo da Chave no Python:** `{type(private_key)}`")
        st.write(f"**Comprimento total do texto:** `{len(private_key)}` caracteres")
        
        st.write("**Começa com:**")
        st.code(private_key[:35], language=None)
        
        st.write("**Termina com:**")
        st.code(private_key[-35:], language=None)
        
        # Verificando a presença e o tipo das quebras de linha
        if "\\n" in private_key:
            st.warning("⚠️ Alerta: A chave contém os caracteres '\\' e 'n' literais em vez de quebras de linha reais.")
        elif "\n" in private_key:
            st.success("✅ A chave parece conter quebras de linha (\\n) corretamente.")
        else:
            st.error("❌ Erro: Nenhuma quebra de linha (\\n) foi encontrada na chave.")

    else:
        st.error("❌ ERRO: A seção [gcp_service_account] foi encontrada, mas a 'private_key' não está dentro dela.")
        st.write("Verifique se você escreveu 'private_key' corretamente no seu TOML.")

else:
    st.error("❌ ERRO CRÍTICO: A seção [gcp_service_account] não foi encontrada!")
    st.write("Verifique se o cabeçalho no seu arquivo de Secrets está exatamente como `[gcp_service_account]`.")