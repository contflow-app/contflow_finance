
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
                Descricao TEXT, 
                Tipo TEXT, 
                Categoria TEXT, 
                Subcategoria TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS regras_classificacao (
                Descricao TEXT PRIMARY KEY, 
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

    # Remover a coluna Identificador, pois não será usada
    extrato_df.drop(columns=['Identificador'], inplace=True)

    # Converter o valor para float, removendo vírgulas se houver
    extrato_df['Valor'] = extrato_df['Valor'].astype(float)

    st.write("Visualização dos dados:")
    st.dataframe(extrato_df)

    # Importar plano de contas
    plano = pd.read_csv("plano_de_contas_contflow.csv")

    def classificar(descricao):
        descricao = str(descricao).upper()
        # Verificar se já existe uma regra salva
        regra = c.execute("SELECT Tipo, Categoria, Subcategoria FROM regras_classificacao WHERE Descricao = ?", (descricao,)).fetchone()
        if regra:
            return regra
        # Caso não exista, buscar no plano de contas
        for _, row in plano.iterrows():
            if row['Subcategoria'].upper() in descricao:
                return row['Tipo'], row['Categoria'], row['Subcategoria']
        return "Não Classificado", "Não Classificado", "Não Classificado"

    # Classificação automática
    extrato_df[['Tipo', 'Categoria', 'Subcategoria']] = extrato_df['Descricao'].apply(lambda d: pd.Series(classificar(d)))

    # Remover duplicados
    c.execute("SELECT Data, Valor, Descricao FROM lancamentos")
    registros_existentes = c.fetchall()
    extrato_df = extrato_df[~extrato_df[['Data', 'Valor', 'Descricao']].apply(tuple, 1).isin(registros_existentes)]

    # Salvar no banco
    extrato_df.to_sql("lancamentos", conn, if_exists="append", index=False)

    st.success("Importação concluída! Lançamentos novos adicionados.")

# Interface para Classificação Manual
st.title("Classificação Manual")
nao_classificados = pd.read_sql_query("SELECT rowid, * FROM lancamentos WHERE Categoria = 'Não Classificado'", conn)

if not nao_classificados.empty:
    for idx, row in nao_classificados.iterrows():
        st.write(f"Data: {row['Data']}, Valor: {row['Valor']}, Descrição: {row['Descricao']}")
        tipo = st.selectbox(f"Selecione o Tipo para {row['Descricao']}", ["Entrada", "Saída"], key=f"tipo_{row['rowid']}")
        categoria = st.text_input(f"Categoria para {row['Descricao']}", key=f"categoria_{row['rowid']}")
        subcategoria = st.text_input(f"Subcategoria para {row['Descricao']}", key=f"subcategoria_{row['rowid']}")
        
        if st.button(f"Salvar {row['Descricao']}", key=f"salvar_{row['rowid']}"):
            c.execute("""
                UPDATE lancamentos 
                SET Tipo = ?, Categoria = ?, Subcategoria = ? 
                WHERE rowid = ?
            """, (tipo, categoria, subcategoria, row['rowid']))
            conn.commit()

            # Salvar regra de aprendizado
            c.execute("""
                INSERT OR REPLACE INTO regras_classificacao (Descricao, Tipo, Categoria, Subcategoria) 
                VALUES (?, ?, ?, ?)
            """, (row['Descricao'].upper(), tipo, categoria, subcategoria))
            conn.commit()

            st.success(f"Lançamento {row['Descricao']} atualizado e regra salva com sucesso!")
else:
    st.info("Não há lançamentos para classificar manualmente.")

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
