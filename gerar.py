import streamlit_authenticator as stauth

# Novo formato para as versões mais recentes da biblioteca
senhas_criptografadas = stauth.Hasher.hash_list(['123456'])

print(senhas_criptografadas)