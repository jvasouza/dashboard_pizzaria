import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata
from datetime import date, timedelta
import calendar
import locale
import plotly.io as pio
from PIL import Image
from pathlib import Path


def estilizar_fig(fig):
    fig.update_layout(
        paper_bgcolor="#fefaf2",
        plot_bgcolor="#fefaf2",
        font=dict(color="#5f100e"),
        legend=dict(bgcolor="#fefaf2")
    )
    fig.update_xaxes(gridcolor="#eadfcb", zerolinecolor="#eadfcb")
    fig.update_yaxes(gridcolor="#eadfcb", zerolinecolor="#eadfcb")
    return fig

TONS_TERROSOS = [
    "#5F100E",  # marrom escuro
    "#8C3B2E",  # marrom médio
    "#CD853F",  # areia
    "#B85C38",  # bege
    "#DEB887",  # caramelo claro
    "#F5DEB3",  # trigo
]

pio.templates["bene_tema"] = dict(
    layout=dict(
        colorway=TONS_TERROSOS,
        plot_bgcolor="#fefaf2",
        paper_bgcolor="#fefaf2",
        font=dict(color="#5f100e"),
        xaxis=dict(gridcolor="#eadfcb", zerolinecolor="#eadfcb"),
        yaxis=dict(gridcolor="#eadfcb", zerolinecolor="#eadfcb"),
        legend=dict(bgcolor="#fefaf2")
    )
)
pio.templates.default = "bene_tema"
st.set_page_config(page_title="Dashboard - Armazém Benevenuto", layout="wide")
st.title("Dashboard - Armazém Benevenuto")

from PIL import Image

# ===== TEMA + LOGO NA SIDEBAR (um único CSS) =====
st.markdown("""
<style>
/* ===== GERAL ===== */
.stApp { background-color:#fefaf2; color:#5f100e; }

/* ===== TÍTULOS ===== */
h1, h2, h3, h4, h5, h6 { color:#5f100e !important; font-weight:700; }

/* ===== SIDEBAR ===== */
[data-testid="stSidebar"] {
    background-color:#5f100e !important;
    color:#fefaf2 !important;
    padding-top:0 !important;
    margin-top:0 !important;
}
/* (opcional) esconder botão de recolher */
section[data-testid="stSidebar"] div[role="button"] { display:none !important; }

/* textos da sidebar */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span { color:#fefaf2 !important; }

/* botões da sidebar */
[data-testid="stSidebar"] .stButton>button {
    background-color:#fefaf2 !important;
    color:#5f100e !important;
    border-radius:10px !important;
    border:none !important;
    font-weight:700 !important;
    padding:0.5rem 0.75rem !important;
}
[data-testid="stSidebar"] .stButton>button:hover { background-color:#f4e9d4 !important; }
[data-testid="stSidebar"] .stButton>button * { color:#5f100e !important; }

/* inputs */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] .stDateInput input {
    color:#5f100e !important;
    background-color:#fefaf2 !important;
    border-radius:10px !important;
}

/* métricas */
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] { color:#5f100e !important; }

/* divisores */
hr { border-top:2px solid #5f100e !important; }

/* ===== REMOVE QUALQUER LOGO renderizada anteriormente ===== */
.sidebar-logo-box, .sidebar-sep { display:none !important; }
</style>
""", unsafe_allow_html=True)

DATA = Path(__file__).parent / "data"

arq_itens = DATA / "Historico_Itens_Vendidos.xlsx"
arq_pedidos = DATA / "Todos os pedidos.xlsx"
arq_contas = DATA / "Lista-contas-receber.xlsx"
arq_custo_bebidas = DATA / "custo bebidas.xlsx"
arq_custo_pizzas = DATA / "custo_pizzas.xlsx"

ANCHOR_DAY = 12
CYCLE_START_OFFSET = 1

def ciclo_12_12_bounds(y, m, anchor_day=ANCHOR_DAY, start_offset=CYCLE_START_OFFSET):
    start_day = min(anchor_day + start_offset, calendar.monthrange(y, m)[1])
    start = date(y, m, start_day)
    end_y, end_m = (y + 1, 1) if m == 12 else (y, m + 1)
    end_day = min(anchor_day, calendar.monthrange(end_y, end_m)[1])
    end = date(end_y, end_m, end_day)
    return start, end

def listar_ciclos_mensais(series_dt):
    if series_dt.empty:
        return []
    dt_min = pd.to_datetime(series_dt.min()).date()
    dt_max = pd.to_datetime(series_dt.max()).date()
    ciclos = []
    y, m = dt_min.year, dt_min.month
    y_end, m_end = (dt_max.year + (1 if dt_max.month == 12 else 0),
                    1 if dt_max.month == 12 else dt_max.month + 1)
    while (y < y_end) or (y == y_end and m <= m_end):
        ini, fim = ciclo_12_12_bounds(y, m)
        if not (fim < dt_min or ini > dt_max):
            nome_mes = date(y, m, 1).strftime("%B").capitalize()
            nome_mes = nome_mes.replace("January","Janeiro").replace("February","Fevereiro").replace("March","Março").replace("April","Abril").replace("May","Maio").replace("June","Junho").replace("July","Julho").replace("August","Agosto").replace("September","Setembro").replace("October","Outubro").replace("November","Novembro").replace("December","Dezembro")

            ciclos.append((nome_mes, ini, fim))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return ciclos

def filtro_periodo_global(series_dt):
    st.sidebar.header("📅 Selecione o Período")
    dmin = pd.to_datetime(series_dt.min()).date()
    dmax = pd.to_datetime(series_dt.max()).date()
    ciclos = listar_ciclos_mensais(series_dt)

    data_ini = st.session_state.get("data_ini", dmin)
    data_fim = st.session_state.get("data_fim", dmax)
    if "data_ini" not in st.session_state: st.session_state["data_ini"] = dmin
    if "data_fim" not in st.session_state: st.session_state["data_fim"] = dmax
    if "ini_input" not in st.session_state: st.session_state["ini_input"] = st.session_state["data_ini"]
    if "fim_input" not in st.session_state: st.session_state["fim_input"] = st.session_state["data_fim"]

    cols = st.sidebar.columns(2)
    for i, (nome_mes, ini, fim) in enumerate(ciclos):
        col = cols[i % 2]
        uid = ini.strftime("%Y%m")  # chave única por ano+mês
        if col.button(nome_mes, key=f"mes_{uid}"):
            st.session_state["data_ini"] = ini
            st.session_state["data_fim"] = fim
            st.session_state["ini_input"] = ini      # <- ver item 2
            st.session_state["fim_input"] = fim      # <- ver item 2
            st.rerun()

    if st.sidebar.button("Período todo", key="all"):
        st.session_state["data_ini"] = dmin
        st.session_state["data_fim"] = dmax
        st.session_state["ini_input"] = dmin
        st.session_state["fim_input"] = dmax
        st.rerun()

    c1, c2 = st.sidebar.columns(2)
    dini = c1.date_input("Início", value=st.session_state["ini_input"],
                         min_value=dmin, max_value=dmax, key="ini_input")
    dfim = c2.date_input("Fim", value=st.session_state["fim_input"],
                         min_value=dmin, max_value=dmax, key="fim_input")
    

    if dini < dmin: dini = dmin
    if dfim > dmax: dfim = dmax
    if dini > dfim: dini, dfim = dmin, dmax

    st.session_state["data_ini"] = dini
    st.session_state["data_fim"] = dfim

    st.session_state["data_ini"], st.session_state["data_fim"] = dini, dfim
    st.sidebar.caption(f"Filtrando: {dini.strftime('%d/%m/%Y')} → {dfim.strftime('%d/%m/%Y')}")
    return dini, dfim

def carregar_primeira_aba_xlsx(arquivo, caminho):
    if arquivo:
        xls = pd.ExcelFile(arquivo)
        return pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    if caminho:
        xls = pd.ExcelFile(caminho)
        return pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    return None

def carregou(df):
    return df is not None and len(df) > 0

def br_money(x):
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def sem_acentos_upper(s):
    if pd.isna(s):
        return s
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.split())

def padroniza_pizza_nome_tamanho(nome):
    nome = sem_acentos_upper(nome)
    if nome.startswith("PIZZA "):
        nome = nome[6:].strip()
    tam = None
    if nome.endswith(" GRANDE"):
        nome = nome[:-7].strip()
        tam = "G"
    elif nome.endswith(" MEDIA"):
        nome = nome[:-6].strip()
        tam = "M"
    elif nome.endswith(" PEQUENA"):
        nome = nome[:-8].strip()
        tam = "P"
    elif nome.endswith(" BROTO"):
        nome = nome[:-6].strip()
        tam = "P"
    if tam:
        return f"{nome} {tam}"
    return nome

# ==========================================================
# NOVA FUNÇÃO – renomeia colunas e formata valores
# ==========================================================
def nomes_legiveis(df):
    mapa = {
        "data": "Data",
        "valor_liq": "Valor",
        "forma_pagamento": "Forma de Pagamento",
        "dow": "Dia da Semana",
        "pedidos": "Pedidos",
        "receita": "Receita (R$)",
        "cliente": "Cliente",
        "gasto": "Valor (R$)",
        "cod_pedido": "Código do Pedido",
        "total_pedido": "Total do Pedido (R$)",
        "tipo_norm": "Tipo de Pedido",
        "total": "Total (R$)",
        "total_recebido": "Total Recebido (R$)",
        "categoria": "Categoria",
        "produto": "Produto",
        "qtd": "Qtd",
        "cmv": "CMV (R$)",
        "margem": "Margem (R$)",
        "margem_%": "Margem (%)"
    }
    df_formatado = df.rename(columns={c: mapa.get(c, c) for c in df.columns}).copy()
    for col in df_formatado.columns:
        if any(p in col for p in ["(R$)", "Valor", "Receita", "CMV", "Margem"]) and pd.api.types.is_numeric_dtype(df_formatado[col]):
            df_formatado[col] = df_formatado[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    return df_formatado

# ==========================================================
# INÍCIO DASHBOARD
# ==========================================================

df_periodo_base = carregar_primeira_aba_xlsx(arq_contas, None)
if carregou(df_periodo_base) and "Crédito" in df_periodo_base.columns:
    df_periodo_base["Crédito"] = pd.to_datetime(df_periodo_base["Crédito"], errors="coerce")
    data_ini, data_fim = filtro_periodo_global(df_periodo_base["Crédito"])
else:
    data_ini, data_fim = None, None

tab1, tab2, tab3 = st.tabs(["Faturamento", "Pedidos", "CMV"])

try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_TIME, "Portuguese_Brazil.1252")
    except:
        locale.setlocale(locale.LC_TIME, "")
# ==========================================================
# ABA FATURAMENTO
# ==========================================================
with tab1:
    df = carregar_primeira_aba_xlsx(arq_contas, None)
    if not carregou(df):
        st.info("Carregue a planilha de Contas a Receber para visualizar a aba Faturamento.")
    else:
        df = df.copy()
        df.columns = df.columns.str.strip()
        df = df.rename(columns={"Cód. Pedido":"cod_pedido","Valor Líq.":"valor_liq","Forma Pagamento":"forma_pagamento","Crédito":"data","Total Pedido":"total_pedido"})
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        df = df.dropna(subset=["data","valor_liq","cod_pedido"]).copy()
        df["valor_liq"] = pd.to_numeric(df["valor_liq"], errors="coerce").fillna(0)

        def normaliza_pagto(x):
            s = str(x).strip().upper()
            if s in {"PIX", "PIX MANUAL", "A CONFIRMAR", "VALE REFEICAO", "VALE REFEIÇÃO"}:
                return "PIX"
            return s

        df["forma_pagamento"] = df["forma_pagamento"].apply(normaliza_pagto)
        mask = (df["data"] >= pd.to_datetime(data_ini)) & (df["data"] <= pd.to_datetime(data_fim))
        dff = df.loc[mask].copy()

        fat_total = float(dff["valor_liq"].sum())
        n_pedidos = int(dff["cod_pedido"].nunique())
        ticket_medio = fat_total / n_pedidos if n_pedidos else 0
        dias_periodo = max(1, (pd.to_datetime(data_fim) - pd.to_datetime(data_ini)).days + 1)
        fat_medio_dia = fat_total / dias_periodo

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Faturamento Total (R$)", br_money(fat_total))
        k2.metric("Total de Pedidos", f"{n_pedidos}")
        k3.metric("Ticket Médio (R$)", br_money(ticket_medio))
        k4.metric("Faturamento Médio/Dia (R$)", br_money(fat_medio_dia))

        st.divider()

        st.subheader("Evolução do Faturamento Diário")
        dff["dia"] = dff["data"].dt.date
        fat_dia = dff.groupby("dia", as_index=False)["valor_liq"].sum().sort_values("dia")
        fig_fat = px.line(fat_dia, x="dia", y="valor_liq", markers=True, labels={"dia":"Data","valor_liq":"Receita (R$)"}, color_discrete_sequence=TONS_TERROSOS)
        fig_fat = estilizar_fig(fig_fat)
        fig_fat.update_xaxes(tickformat="%d/%m/%Y")
        st.plotly_chart(fig_fat, use_container_width=True, key="fat_linha_dia")
    

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Receita por Forma de Pagamento")
            fat_pagto = dff.groupby("forma_pagamento", as_index=False)["valor_liq"].sum().sort_values("valor_liq", ascending=False)
            fig_pagto = px.pie(fat_pagto, names="forma_pagamento", values="valor_liq", hole=0.3)
            fig_pagto = estilizar_fig(fig_pagto)
            fig_pagto.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_pagto, use_container_width=True, key="fat_pizza_pagto")
            st.dataframe(nomes_legiveis(fat_pagto.reset_index(drop=True)), use_container_width=True, hide_index=True)
        with col_b:
            st.subheader("Faturamento por Dia da Semana")
            mapper = {0:"Seg",1:"Ter",2:"Qua",3:"Qui",4:"Sex",5:"Sáb",6:"Dom"}
            dff["dow"] = dff["data"].dt.weekday.map(mapper)
            dff = dff[dff["dow"] != "Ter"]   # ← ignora terças
            
            ordem = ["Seg","Qua","Qui","Sex","Sáb","Dom"]
            fat_dow = dff.groupby("dow", as_index=False)["valor_liq"].sum()
            fat_dow["dow"] = pd.Categorical(fat_dow["dow"], categories=ordem, ordered=True)
            fat_dow = fat_dow.sort_values("dow")
           
            fig_dow = px.bar(fat_dow, x="dow", y="valor_liq", labels={"dow":"Dia da Semana","valor_liq":"Receita (R$)"})
            fig_dow = estilizar_fig(fig_dow)
            st.plotly_chart(fig_dow, use_container_width=True, key="fat_barras_dow")
            st.dataframe(nomes_legiveis(fat_dow.reset_index(drop=True)), use_container_width=True, hide_index=True)

# ==========================================================
# ABA PEDIDOS
# ==========================================================
with tab2:
    dfp = carregar_primeira_aba_xlsx(arq_pedidos, None)
    if not carregou(dfp):
        st.info("Carregue a planilha de Pedidos para visualizar a aba Pedidos.")
    else:
        dfp = dfp.copy()
        dfp.columns = dfp.columns.str.strip()
        rename_map = {"Código":"codigo","Data Abertura":"data","Status":"status","Cliente":"cliente","Tipo":"tipo","Origem":"origem","Total":"total","Total Recebido":"total_recebido","Forma de Pagto":"forma_pagto"}
        dfp = dfp.rename(columns=rename_map)
        dfp["data"] = pd.to_datetime(dfp["data"], errors="coerce")
        maskp = (dfp["data"] >= pd.to_datetime(data_ini)) & (dfp["data"] <= pd.to_datetime(data_fim))
        dpp = dfp.loc[maskp].copy()

        pedidos_total = int(dpp["codigo"].nunique())
        receita_periodo = float(dpp["total_recebido"].sum())
        ticket_medio = receita_periodo / pedidos_total if pedidos_total else 0
        clientes_unicos = int(dpp["cliente"].nunique())

        k1, k2, k3 = st.columns(3)
        k1.metric("Pedidos no período", f"{pedidos_total}")
        k2.metric("Ticket Médio (R$)", br_money(ticket_medio))
        k3.metric("Clientes únicos", f"{clientes_unicos}")

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Nº de Pedidos por Tipo")
            pedidos_tipo = dpp.groupby("tipo", as_index=False)["codigo"].nunique().rename(columns={"codigo":"pedidos"})
            fig_pt = px.bar(pedidos_tipo, x="tipo", y="pedidos", labels={"tipo":"Tipo","pedidos":"Pedidos"})
            fig_pt = estilizar_fig(fig_pt)
            st.plotly_chart(fig_pt, use_container_width=True, key="ped_barras_tipo")
            st.dataframe(nomes_legiveis(pedidos_tipo.reset_index(drop=True)), use_container_width=True, hide_index=True)
        with c2:
            st.subheader("Receita por Tipo")
            receita_tipo = dpp.groupby("tipo", as_index=False)["total_recebido"].sum().rename(columns={"total_recebido":"receita"})
            fig_rt = px.pie(receita_tipo, names="tipo", values="receita", hole=0.3)
            fig_rt = estilizar_fig(fig_rt)
            fig_rt.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_rt, use_container_width=True, key="ped_pizza_tipo")
            st.dataframe(nomes_legiveis(receita_tipo.reset_index(drop=True)), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Top 10 Clientes por Nº de Pedidos")
        top_cli = (dpp.groupby("cliente", as_index=False)
                    .agg(pedidos=("codigo","nunique"), gasto=("total_recebido","sum"))
                    .sort_values(["pedidos","gasto"], ascending=[False, False])
                    .head(10)
                    .reset_index(drop=True))
        st.dataframe(nomes_legiveis(top_cli), use_container_width=True, hide_index=True)

with tab3:
    itens = carregar_primeira_aba_xlsx(arq_itens, None)
    c_pizzas = carregar_primeira_aba_xlsx(arq_custo_pizzas, None)
    c_bebidas = carregar_primeira_aba_xlsx(arq_custo_bebidas, None)

    if not (carregou(itens) and carregou(c_pizzas) and carregou(c_bebidas)):
        st.info("Carregue as planilhas: Itens Vendidos, Custo Pizzas e Custo Bebidas para visualizar a aba CMV.")
    else:
        itens = itens.copy()
        itens.columns = itens.columns.str.strip()
        itens = itens.rename(columns={"Data/Hora Item":"data_item","Qtd.":"qtd","Valor Un. Item":"valor_un","Valor. Tot. Item":"valor_tot","Nome Prod":"nome_prod","Cat. Prod.":"cat_prod"})
        itens["data_item"] = pd.to_datetime(itens["data_item"], errors="coerce")
        itens = itens.dropna(subset=["data_item","nome_prod","cat_prod","qtd","valor_tot"]).copy()
        itens["qtd"] = pd.to_numeric(itens["qtd"], errors="coerce").fillna(0)
        itens["valor_tot"] = pd.to_numeric(itens["valor_tot"], errors="coerce").fillna(0)
        itens["cat_norm"] = itens["cat_prod"].astype(str).str.upper().str.strip()

        c_pizzas = c_pizzas.copy()
        c_pizzas.columns = c_pizzas.columns.str.strip()
        c_pizzas = c_pizzas.rename(columns={"produto":"produto","custo":"custo","preço_venda":"preco_venda"})
        c_pizzas["produto_key"] = c_pizzas["produto"].apply(sem_acentos_upper)

        c_bebidas = c_bebidas.copy()
        c_bebidas.columns = c_bebidas.columns.str.strip()
        c_bebidas = c_bebidas.rename(columns={"produto":"produto","custo":"custo","preco_venda":"preco_venda"})
        c_bebidas["produto_key"] = c_bebidas["produto"].apply(sem_acentos_upper)



        maski = (itens["data_item"] >= pd.to_datetime(data_ini)) & (itens["data_item"] <= pd.to_datetime(data_fim))

        iv = itens.loc[maski].copy()

        iv_pizza = iv[iv["cat_norm"] == "PIZZAS"].copy()
        iv_pizza["produto_key"] = iv_pizza["nome_prod"].apply(padroniza_pizza_nome_tamanho).apply(sem_acentos_upper)
        pizza_merged = iv_pizza.merge(c_pizzas[["produto_key","custo","preco_venda","produto"]], on="produto_key", how="left")
        pizza_merged["cmv"] = pizza_merged["custo"].fillna(0) * pizza_merged["qtd"]
        pizza_merged["receita"] = pizza_merged["valor_tot"]
        pizza_merged["margem"] = pizza_merged["receita"] - pizza_merged["cmv"]

        iv_beb = iv[iv["cat_norm"] == "BEBIDAS"].copy()
        iv_beb["produto_key"] = iv_beb["nome_prod"].apply(sem_acentos_upper)
        beb_merged = iv_beb.merge(c_bebidas[["produto_key","custo","preco_venda","produto"]], on="produto_key", how="left")
        beb_merged["cmv"] = beb_merged["custo"].fillna(0) * beb_merged["qtd"]
        beb_merged["receita"] = beb_merged["valor_tot"]
        beb_merged["margem"] = beb_merged["receita"] - beb_merged["cmv"]

        cmv_total = float(pizza_merged["cmv"].sum() + beb_merged["cmv"].sum())
        receita_total = float(pizza_merged["receita"].sum() + beb_merged["receita"].sum())
        margem_total = receita_total - cmv_total
        cmv_pct = (cmv_total / receita_total * 100) if receita_total else 0
        margem_pct = (margem_total / receita_total * 100) if receita_total else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Receita Considerada (R$)", br_money(receita_total))
        k2.metric("CMV (R$)", br_money(cmv_total))
        k3.metric("CMV (%)", f"{cmv_pct:,.1f}%")
        k4.metric("Margem Bruta (R$)", br_money(margem_total))

        st.caption(f"Margem Bruta (%): {margem_pct:,.1f}%")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("CMV por Categoria")
            cat_df = pd.DataFrame({
                "categoria": ["PIZZAS","BEBIDAS"],
                "receita": [pizza_merged["receita"].sum(), beb_merged["receita"].sum()],
                "cmv": [pizza_merged["cmv"].sum(), beb_merged["cmv"].sum()]
            })
            cat_df["margem"] = cat_df["receita"] - cat_df["cmv"]
            cat_df["cmv_%"] = (cat_df["cmv"] / cat_df["receita"] * 100).round(1).fillna(0)
            fig_cat = px.bar(cat_df, x="categoria", y="cmv", text_auto=".2s", labels={"categoria":"Categoria","cmv":"CMV (R$)"})
            fig_cat = estilizar_fig(fig_cat)
            st.plotly_chart(fig_cat, use_container_width=True, key="cmv_bar_cat")
            st.dataframe(cat_df.round(2).reset_index(drop=True), use_container_width=True, hide_index=True)
        with col2:
            st.subheader("Receita por Categoria")
            fig_rec = px.pie(cat_df, names="categoria", values="receita", hole=0.3)
            fig_rec = estilizar_fig(fig_rec)
            fig_rec.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_rec, use_container_width=True, key="cmv_pie_cat")

        st.divider()

        st.subheader("Ranking de Produtos – Melhores Margens")
        pizzas_rank = pizza_merged.groupby("produto_key", as_index=False).agg(
            produto=("produto","first"),
            receita=("receita","sum"),
            cmv=("cmv","sum"),
            margem=("margem","sum"),
            qtd=("qtd","sum")
        )
        bebidas_rank = beb_merged.groupby("produto_key", as_index=False).agg(
            produto=("produto","first"),
            receita=("receita","sum"),
            cmv=("cmv","sum"),
            margem=("margem","sum"),
            qtd=("qtd","sum")
        )
        produtos_rank = pd.concat([pizzas_rank.assign(categoria="PIZZAS"), bebidas_rank.assign(categoria="BEBIDAS")], ignore_index=True)
        produtos_rank["margem_%"] = (produtos_rank["margem"] / produtos_rank["receita"] * 100).round(1)
        melhores = produtos_rank.sort_values(["margem_%","margem"], ascending=[False, False]).head(10).reset_index(drop=True)
        st.dataframe(melhores[["categoria","produto","qtd","receita","cmv","margem","margem_%"]].round(2), use_container_width=True, hide_index=True)

        st.subheader("Ranking de Produtos – Piores Margens")
        piores = produtos_rank.sort_values(["margem_%","margem"], ascending=[True, True]).head(10).reset_index(drop=True)
        st.dataframe(piores[["categoria","produto","qtd","receita","cmv","margem","margem_%"]].round(2), use_container_width=True, hide_index=True)

        st.divider()

        nao_mapeados_pizza = int(pizza_merged["custo"].isna().sum())
        nao_mapeados_beb = int(beb_merged["custo"].isna().sum())
        st.caption(f"Itens sem custo mapeado – PIZZAS: {nao_mapeados_pizza} | BEBIDAS: {nao_mapeados_beb}")
