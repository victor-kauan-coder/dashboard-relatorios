import streamlit as st

st.title("Teste Simples de Secrets")
st.write("Esta página está a testar se a funcionalidade de 'Secrets' está a funcionar.")

# Tentamos ler um secret muito simples chamado "senha_teste"
if "senha_teste" in st.secrets:
    st.success("✅ SUCESSO! O Secret 'senha_teste' foi encontrado!")
    
    valor_do_secret = st.secrets["senha_teste"]
    
    st.write("O valor encontrado foi:")
    st.code(valor_do_secret, language=None)
    
    if valor_do_secret == "funcionou123":
        st.success("✅ E o valor está correto! A funcionalidade de Secrets está a funcionar perfeitamente.")
    else:
        st.error("❌ O valor do secret está incorreto. Verifique se copiou e colou bem.")

else:
    st.error("❌ FALHA CRÍTICA! O Secret 'senha_teste' não foi encontrado.")
    st.warning("Verifique se guardou o Secret corretamente no painel do Streamlit Cloud.")