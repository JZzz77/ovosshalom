import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Ovos Shalom Admin v2.1", layout="wide", page_icon="🥚")

# Design CSS personalizado
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; background-color: #2E8B57; color: white !important; font-weight: bold; height: 3.5em; border: none; }
    [data-testid="stMetricValue"] { color: #2E8B57 !important; font-weight: bold; }
    div[data-testid="stMetric"] { background-color: rgba(46, 139, 87, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #2E8B57; }
    div[data-testid="stExpander"] { border: none; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. SISTEMA DE LOGIN
def check_password():
    def password_entered():
        if st.session_state["password_input"] == "SHALOM2024":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.title("🔐 Acesso Administrativo - Ovos Shalom")
        st.text_input("Senha:", type="password", on_change=password_entered, key="password_input")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ Senha Incorreta! Tente novamente.")
        return False
    return True

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)

    def load_data():
        try:
            df = conn.read(worksheet="Vendas", ttl=0)
            if not df.empty:
                df['Data_Formatada'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
            return df
        except:
            return pd.DataFrame()

    # --- BANCO DE DADOS DINÂMICO (Produtos Shalom) ---
    if "menu_df" not in st.session_state:
        dados_iniciais = [
            {"Produto": "Ovos Brancos (30 un)", "Preço Venda": 18.0, "Custo Unit": 12.0, "Categoria": "Ovos"},
            {"Produto": "Ovos Caipira (12 un)", "Preço Venda": 12.0, "Custo Unit": 8.0, "Categoria": "Ovos"},
            {"Produto": "Queijo Frescal (Un)", "Preço Venda": 25.0, "Custo Unit": 18.0, "Categoria": "Laticínios"},
            {"Produto": "Doce de Leite 500g", "Preço Venda": 15.0, "Custo Unit": 9.5, "Categoria": "Doces"},
            {"Produto": "Ovos de Codorna (Pote)", "Preço Venda": 10.0, "Custo Unit": 6.0, "Categoria": "Ovos"},
            {"Produto": "Goiabada Cascão", "Preço Venda": 12.0, "Custo Unit": 7.0, "Categoria": "Doces"}
        ]
        st.session_state["menu_df"] = pd.DataFrame(dados_iniciais)

    # --- SIDEBAR: METAS E CUSTOS ---
    st.sidebar.header("🎯 Metas e Custos Fixos")
    meta_mensal = st.sidebar.number_input("Meta de Faturamento (R$)", value=3000.0)
    custos_fixos = st.sidebar.number_input("Custos (Combustível/MEI)", value=200.0)
    
    st.sidebar.info("Dica: Edite os preços de custo na aba 'Cardápio' para ter o lucro real exato.")

    # --- ABAS ---
    tab1, tab2, tab3 = st.tabs(["📝 PDV & Produtos", "📈 Dashboard", "📜 Histórico"])

    with tab1:
        # EXPANDER 1: O PDV
        with st.expander("✨ Registrar Novo Pedido", expanded=True):
            hora_padrao = datetime.now() - timedelta(hours=3)
            
            c1, c2 = st.columns(2)
            data_sel = c1.date_input("Data da Venda", value=hora_padrao.date())
            hora_sel = c2.time_input("Hora", value=hora_padrao.time())
            
            canal = st.radio("Forma de Venda", ["Entrega Direta", "Feira / Ponto"], horizontal=True)
            
            lista_produtos = st.session_state["menu_df"]["Produto"].tolist()
            produtos_selecionados = st.multiselect("Itens Vendidos:", lista_produtos)

            if produtos_selecionados:
                v_venda_total = 0
                custo_total = 0
                
                for p in produtos_selecionados:
                    prod_info = st.session_state["menu_df"][st.session_state["menu_df"]["Produto"] == p].iloc[0]
                    v_venda_total += prod_info["Preço Venda"]
                    custo_total += prod_info["Custo Unit"]
                
                st.metric("Valor Total do Pedido", f"R$ {v_venda_total:.2f}")

                if st.button("🚀 FINALIZAR VENDA"):
                    lucro = v_venda_total - custo_total
                    nome_pedido = " + ".join(produtos_selecionados)
                    
                    novo = pd.DataFrame([{
                        "Data": data_sel.strftime("%d/%m/%Y"), 
                        "Hora": hora_sel.strftime("%H:%M"), 
                        "Produto": nome_pedido, 
                        "Canal": canal, 
                        "Valor_Bruto": v_venda_total, 
                        "Lucro_Liquido": round(lucro, 2)
                    }])
                    
                    # Salva no Google Sheets
                    conn.update(worksheet="Vendas", data=pd.concat([load_data().drop(columns=['Data_Formatada'], errors='ignore'), novo], ignore_index=True))
                    st.success(f"Venda registrada! Lucro: R$ {lucro:.2f}")
                    st.balloons()

        # EXPANDER 2: EDITOR DE PRODUTOS
        with st.expander("📦 Gerenciar Produtos e Preços", expanded=False):
            st.write("Atualize seus preços de venda e custos de compra aqui.")
            menu_editado = st.data_editor(st.session_state["menu_df"], num_rows="dynamic", use_container_width=True)
            st.session_state["menu_df"] = menu_editado

    with tab2:
        df = load_data()
        if not df.empty:
            hoje = datetime.now().date()
            inicio_mes = hoje.replace(day=1)
            
            c_f1, c_f2 = st.columns(2)
            d_ini = c_f1.date_input("Início", inicio_mes)
            d_fim = c_f2.date_input("Fim", hoje)
            
            mask = (df['Data_Formatada'].dt.date >= d_ini) & (df['Data_Formatada'].dt.date <= d_fim)
            df_f = df[mask].sort_values('Data_Formatada')

            m1, m2, m3 = st.columns(3)
            faturamento_total = df_f['Valor_Bruto'].sum()
            lucro_op = df_f['Lucro_Liquido'].sum()
            falta_pagar = custos_fixos - lucro_op

            m1.metric("Faturamento Total", f"R$ {faturamento_total:.2f}")
            m2.metric("Lucro Bruto", f"R$ {lucro_op:.2f}")
            
            if falta_pagar > 0:
                m3.metric("Falta p/ Cobrir Custos", f"R$ {falta_pagar:.2f}", delta_color="inverse")
            else:
                m3.metric("Lucro Líquido Real", f"R$ {abs(falta_pagar):.2f}", delta="Custos Pagos!")

            st.divider()

            # Gráfico de Evolução
            st.subheader("📈 Progresso das Vendas")
            df_f['Acumulado'] = df_f['Valor_Bruto'].cumsum()
            fig_meta = go.Figure()
            fig_meta.add_trace(go.Scatter(x=df_f['Data_Formatada'], y=df_f['Acumulado'], mode='lines+markers', name='Vendas', line=dict(color='#2E8B57', width=4)))
            fig_meta.add_hline(y=meta_mensal, line_dash="dash", line_color="red", annotation_text="Meta Mensal")
            fig_meta.update_layout(height=400)
            st.plotly_chart(fig_meta, use_container_width=True)

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                # Como o pedido pode ter múltiplos itens, fazemos um split simples para o ranking
                all_prods = df_f['Produto'].str.split(' \+ ').explode()
                rank = all_prods.value_counts().reset_index()
                rank.columns = ['Produto', 'Qtd']
                st.plotly_chart(px.bar(rank.sort_values('Qtd'), x='Qtd', y='Produto', orientation='h', title="Produtos Mais Vendidos", color_discrete_sequence=['#2E8B57']), use_container_width=True)
            with col_g2:
                st.plotly_chart(px.pie(df_f, names='Canal', title="Vendas por Canal", hole=0.4, color_discrete_sequence=['#2E8B57', '#DAA520']), use_container_width=True)

    with tab3:
        st.subheader("Gerenciar Histórico de Vendas")
        df_h = load_data()
        if not df_h.empty:
            df_h['Deletar'] = False
            cols = ['Deletar', 'Data', 'Hora', 'Produto', 'Canal', 'Valor_Bruto', 'Lucro_Liquido']
            edited_df = st.data_editor(df_h[cols].iloc[::-1], hide_index=True, use_container_width=True)
            
            if st.button("🗑️ EXCLUIR VENDAS SELECIONADAS"):
                indices_manter = edited_df[edited_df['Deletar'] == False].index
                df_final_del = df_h.loc[indices_manter].drop(columns=['Data_Formatada', 'Deletar'], errors='ignore')
                conn.update(worksheet="Vendas", data=df_final_del)
                st.success("Histórico atualizado!")
                st.rerun()
