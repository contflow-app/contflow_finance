
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt

# Configurações da página
st.set_page_config(page_title="ContFlow Finance", layout="wide")

# Conexão com banco de dados
conn = sqlite3.connect('dados_financeiros.db')
c = conn.cursor()

# Tabelas
c.execute('''CREATE TABLE IF NOT EXISTS lancamentos (
                Data TEXT, 
                Valor REAL, 
                Identificador TEXT,
                Descricao TEXT, 
                Tipo TEXT, 
                Categoria TEXT, 
                Subcategoria TEXT
            )''')
conn.commit()

# Upload do extrato
st.title("ContFlow Finance - Upload de Extrato")
uploaded_file = st.file_uploader("Selecione o arquivo CSV", type=["csv"])

if uploaded_file:
    extrato_df = pd.read_csv(uploaded_file)

    # Ajuste nos nomes das colunas
    extrato_df.columns = ['Data', 'Valor', 'Identificador', 'Descricao']

    st.write("Visualização dos dados:")
    st.dataframe(extrato_df)

    # Importar plano de contas
    plano = pd.read_csv("plano_de_contas_contflow.csv")

    def classificar(descricao):
        descricao = str(descricao).upper()
        for _, row in plano.iterrows():
            if row['Subcategoria'].upper() in descricao:
                return row['Tipo'], row['Categoria'], row['Subcategoria']
        return None, None, None

    # Classificação automática
    extrato_df[['Tipo', 'Categoria', 'Subcategoria']] = extrato_df['Descrição'].apply(lambda d: pd.Series(classificar(d)))

    # Remover duplicados
    c.execute("SELECT Data, Valor, Descricao FROM lancamentos")
    registros_existentes = c.fetchall()
    extrato_df = extrato_df[~extrato_df[['Data', 'Valor', 'Descrição']].apply(tuple, 1).isin(registros_existentes)]

    # Salvar no banco
    extrato_df.to_sql("lancamentos", conn, if_exists="append", index=False)

    st.success("Importação concluída! Lançamentos novos adicionados.")

# Relatório DRE
st.title("Relatório DRE")
df = pd.read_sql_query("SELECT * FROM lancamentos", conn)
if not df.empty:
    st.dataframe(df)
    
    # Gráficos
    fig, ax = plt.subplots()
    df.groupby('Categoria')['Valor'].sum().plot(kind='pie', autopct='%1.1f%%', ax=ax)
    st.pyplot(fig)

conn.close()
