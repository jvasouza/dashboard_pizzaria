import re
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata
from datetime import date, timedelta
import calendar
import locale
import plotly.io as pio
from PIL import Image
import numpy as np


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
    "#5F100E",  
    "#A9210E", 
    "#CD853F",  
    "#D9C77C",  
    "#DEB887",  
    "#F5DEB3"
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


""", unsafe_allow_html=True)


DATA = Path(__file__).parent / "data"

arq_itens = DATA / "Historico_Itens_Vendidos.xlsx"
arq_pedidos = DATA / "Todos os pedidos.xlsx"
arq_contas = DATA / "Lista-contas-receber.xlsx"
arq_custo_bebidas = DATA / "custo bebidas.xlsx"
arq_custo_pizzas = DATA / "custo_pizzas.xlsx"
arq_custos_fixos = DATA / "custos fixos.xlsx"
arq_pre = DATA / "recebimentos_ate_25.04.xlsx"



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
    ano = 2025
    inicio_ano = date(ano, 1, 1)
    fim_ano = date(ano, 12, 31)
    dt_min = max(dt_min, inicio_ano)
    dt_max = min(dt_max, fim_ano)

    nomes_pt = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    ciclos = []
    for m in range(1, 12 + 1):
        offset = 0 if m == 4 else CYCLE_START_OFFSET   # Abril sem offset
        ini, fim = ciclo_12_12_bounds(ano, m, anchor_day=ANCHOR_DAY, start_offset=offset)

        # Exige interseção com duração > 0 dia:
        if (fim > dt_min) and (ini <= dt_max):
            nome_mes = nomes_pt[m-1]
            ciclos.append((nome_mes, ini, fim))
    return ciclos


def set_locale_ptbr():
    for loc in ("pt_BR.UTF-8", "pt_BR.utf8", "pt_BR", "Portuguese_Brazil.1252"):
        try:
            locale.setlocale(locale.LC_TIME, loc)
            return loc
        except locale.Error:
            continue
    # último recurso: sem tradução (evita quebrar o app)
    locale.setlocale(locale.LC_TIME, "C")
    return "C"

_ = set_locale_ptbr()

def renomeia_benevenuto_para_capricciosa(nome_padronizado):
    s = sem_acentos_upper(nome_padronizado)
    m = re.match(r"^(BENEVENUTO)(?:\s+(G|M|P))?$", s)
    if m:
        tam = f" {m.group(2)}" if m.group(2) else ""
        return f"CAPRICCIOSA{tam}"
    return s

def normaliza_bebida_nome(nome):

    s = sem_acentos_upper(nome)
    if s.startswith("SUCO "):
        if " 400ML" in s:
            return "SUCO 400ML"
        if " JARRA" in s:
            return "SUCO JARRA"
        
    return s


def filtro_periodo_global(series_dt):
    st.sidebar.header("📅 Selecione o Período")
    dmin = pd.to_datetime(series_dt.min()).date()
    dmax = pd.to_datetime(series_dt.max()).date()
    ciclos = listar_ciclos_mensais(series_dt)

    data_ini = st.session_state.get("data_ini", dmin)
    data_fim = st.session_state.get("data_fim", dmax)
    if data_ini < dmin: data_ini = dmin
    if data_ini > dmax: data_ini = dmin
    if data_fim > dmax: data_fim = dmax
    if data_fim < dmin: data_fim = dmax

    cols = st.sidebar.columns(2)
    for i, (nome_mes, ini, fim) in enumerate(ciclos):
        col = cols[i % 2]
        if col.button(f"{nome_mes}", key=f"mes_{nome_mes}_2025"):
            st.session_state["data_ini"] = ini
            st.session_state["data_fim"] = fim
            data_ini, data_fim = ini, fim
            st.rerun()

    if st.sidebar.button("Período todo", key="all_2025"):
        st.session_state["data_ini"] = dmin
        st.session_state["data_fim"] = dmax
        st.rerun()

    c1, c2 = st.sidebar.columns(2)
    dini = c1.date_input("Início", value=data_ini, min_value=dmin, max_value=dmax, key="ini_input")
    dfim = c2.date_input("Fim", value=data_fim, min_value=dmin, max_value=dmax, key="fim_input")

    if dini < dmin: dini = dmin
    if dfim > dmax: dfim = dmax
    if dini > dfim: dini, dfim = dmin, dmax

    st.session_state["data_ini"], st.session_state["data_fim"] = dini, dfim
    st.sidebar.caption(f"Filtrando: {dini.strftime('%d/%m/%Y')} → {dfim.strftime('%d/%m/%Y')}")
    return dini, dfim


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
        nome = nome[:-7].strip(); tam = "G"
    elif nome.endswith(" MEDIA"):
        nome = nome[:-6].strip(); tam = "M"
    elif nome.endswith(" PEQUENA"):
        nome = nome[:-8].strip(); tam = "P"
    if tam:
        nome = f"{nome} {tam}"
    nome = renomeia_benevenuto_para_capricciosa(nome)
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
        if ("R$" in col or "(R$)" in col or "Valor" in col or "Receita" in col or "CMV" in col or "Margem" in col):
            if "%" not in col and pd.api.types.is_numeric_dtype(df_formatado[col]):
                df_formatado[col] = df_formatado[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    return df_formatado

# ==========================================================
# INÍCIO DASHBOARD
# ==========================================================

df_periodo_base = (arq_contas, None)
arq_pre_range = DATA / "recebimentos_ate_25.04.xlsx"
df_pre_range = (None, arq_pre_range)

series_list = []

if carregou(df_periodo_base) and "Crédito" in df_periodo_base.columns:
    series_list.append(pd.to_datetime(df_periodo_base["Crédito"], errors="coerce"))

if carregou(df_pre_range):
    cols = df_pre_range.columns.str.strip()
    if "data" in cols: 
        series_list.append(pd.to_datetime(df_pre_range["data"], errors="coerce"))
    elif "Data" in cols: 
        series_list.append(pd.to_datetime(df_pre_range["Data"], errors="coerce"))
    elif "Crédito" in cols: 
        series_list.append(pd.to_datetime(df_pre_range["Crédito"], errors="coerce"))
    elif "Credito" in cols:
        series_list.append(pd.to_datetime(df_pre_range["Credito"], errors="coerce"))

if series_list:
    base_series = pd.concat(series_list, ignore_index=True).dropna()
    if not base_series.empty:
        data_ini, data_fim = filtro_periodo_global(base_series)
    else:
        data_ini, data_fim = None, None
else:
    data_ini, data_fim = None, None


tab1, tab2, tab3 = st.tabs(["Faturamento", "Pedidos", "CMV"])


# ==========================================================
# ABA FATURAMENTO
# ==========================================================
with tab1:
    df = (arq_contas, None)
    if not carregou(df):
        st.info("Carregue a planilha de Contas a Receber para visualizar a aba Faturamento.")
    else:
        df = df.copy()
        df.columns = df.columns.str.strip()
        arq_pre = DATA / "recebimentos_ate_25.04.xlsx"
        df = df.rename(columns={"Cód. Pedido":"cod_pedido","Valor Líq.":"valor_liq","Forma Pagamento":"forma_pagamento","Crédito":"data","Total Pedido":"total_pedido"})
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        df["valor_liq"] = pd.to_numeric(df["valor_liq"], errors="coerce")
        df_pre = (None, arq_pre)
        if carregou(df_pre):
            dfx = df_pre.copy()
            dfx.columns = dfx.columns.str.strip()
            dfx = dfx.rename(columns={"Data": "data"})
            dfx["data"] = pd.to_datetime(dfx["data"], errors="coerce")

            cols_pagto = [c for c in dfx.columns if c not in {"data", "TOTAL", "TOTAL_RECALCULADO"}]

            dfx_long = dfx.melt(id_vars=["data"], value_vars=cols_pagto,
                                var_name="forma_pagamento", value_name="valor_liq")
            dfx_long["valor_liq"] = pd.to_numeric(dfx_long["valor_liq"], errors="coerce").fillna(0)
            dfx_long = dfx_long[dfx_long["valor_liq"] > 0].copy()

            dfx_long["cod_pedido"] = (
                "PRE-" + dfx_long.index.astype(str).str.zfill(4) + "-" +
                dfx_long["data"].dt.strftime("%Y%m%d")
            )
            dfx_long["total_pedido"] = np.nan

            df = pd.concat([df, dfx_long[["cod_pedido", "valor_liq", "forma_pagamento", "data", "total_pedido"]]], ignore_index=True)

        def normaliza_pagto(x):
            s = str(x).strip().upper()
            if s in {"PIX", "PIX MANUAL", "A CONFIRMAR", "VALE REFEICAO", "VALE REFEIÇÃO"}:
                return "PIX"
            return s

        df["forma_pagamento"] = df["forma_pagamento"].apply(normaliza_pagto)
        mask = (df["data"] >= pd.to_datetime(data_ini)) & (df["data"] <= pd.to_datetime(data_fim))
        dff = df.loc[mask].copy()
        dff = dff[~dff["data"].dt.weekday.isin([0, 1])]


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
        fat_dia = (
            dff.groupby("dia", as_index=False)["valor_liq"]
            .sum()
            .sort_values("dia")
        )

        mapper = {0:"Seg",1:"Ter",2:"Qua",3:"Qui",4:"Sex",5:"Sáb",6:"Dom"}
        fat_dia["dow"] = pd.to_datetime(fat_dia["dia"]).dt.weekday.map(mapper)

        fig_fat = px.line(
            fat_dia,
            x="dia", y="valor_liq",
            markers=True,
            labels={"dia":"Data","valor_liq":"Receita (R$)"},
            color_discrete_sequence=TONS_TERROSOS
        )
        fig_fat = estilizar_fig(fig_fat)
        fig_fat.update_xaxes(type="date", tickformat="%d/%m/%Y", ticklabelmode="period", tickangle=-45)
        fig_fat.update_traces(
            hovertemplate="Data: %{x|%d/%m/%Y}<br>Dia da semana: %{customdata[0]}<br>Receita: R$ %{y:.2f}",
            customdata=fat_dia[["dow"]].to_numpy()
        )
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
            ordem = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
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
    dfp = (arq_pedidos, None)
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

        st.divider()

        st.subheader("Evolução do Nº de Pedidos por Dia")

        dpp["dia"] = dpp["data"].dt.date
        pedidos_por_dia = (
            dpp.groupby("dia", as_index=False)["codigo"]
            .nunique()
            .rename(columns={"codigo": "pedidos"})
            .sort_values("dia")
        )

        mapper = {0:"Seg",1:"Ter",2:"Qua",3:"Qui",4:"Sex",5:"Sáb",6:"Dom"}
        pedidos_por_dia["dow"] = pd.to_datetime(pedidos_por_dia["dia"]).dt.weekday.map(mapper)

        fig_ped_dia = px.line(
            pedidos_por_dia,
            x="dia", y="pedidos",
            markers=True,
            labels={"dia":"Data", "pedidos":"Pedidos"},
            color_discrete_sequence=TONS_TERROSOS
        )
        fig_ped_dia = estilizar_fig(fig_ped_dia)
        fig_ped_dia.update_xaxes(tickformat="%d/%m/%Y")
        fig_ped_dia.update_traces(
            hovertemplate="Data: %{x|%d/%m/%Y}<br>Dia da semana: %{customdata[0]}<br>Pedidos: %{y}",
            customdata=pedidos_por_dia[["dow"]].to_numpy()
        )
        st.plotly_chart(fig_ped_dia, use_container_width=True, key="ped_linha_dia")


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

        dpp_top = dpp[~dpp["cliente"].astype(str).str.strip().str.lower().eq("não informado")]

        top_cli = (dpp_top.groupby("cliente", as_index=False)
                    .agg(pedidos=("codigo","nunique"), gasto=("total_recebido","sum"))
                    .sort_values(["pedidos","gasto"], ascending=[False, False])
                    .head(10)
                    .reset_index(drop=True))

        st.dataframe(nomes_legiveis(top_cli), use_container_width=True, hide_index=True)



# ==========================================================
# ABA CMV
# ==========================================================    



with tab3:
    itens = (arq_itens, None)
    c_pizzas = (arq_custo_pizzas, None)
    c_bebidas = (arq_custo_bebidas, None)

    if not (carregou(itens) and carregou(c_pizzas) and carregou(c_bebidas)):
        st.info("Carregue as planilhas: Itens Vendidos, Custo Pizzas e Custo Bebidas para visualizar a aba CMV.")
    else:
        itens = itens.copy()
        itens.columns = itens.columns.str.strip()
        itens = itens.rename(columns={"Data/Hora Item":"data_item","Qtd.":"qtd","Valor. Tot. Item":"valor_tot","Nome Prod":"nome_prod","Cat. Prod.":"cat_prod"})
        itens["nome_prod_norm"] = itens["nome_prod"].astype(str).str.strip()
        itens = itens[~itens["nome_prod_norm"].str.startswith("* Excluído *", na=False)].copy()
        itens["data_item"] = pd.to_datetime(itens["data_item"], errors="coerce")
        itens["qtd"] = pd.to_numeric(itens["qtd"], errors="coerce").fillna(0)
        itens["valor_tot"] = pd.to_numeric(itens["valor_tot"], errors="coerce").fillna(0)
        itens = itens.dropna(subset=["data_item"]).copy()

        def normalize_sizes(text):
            s = text.str.replace(r"\bGrande\b","G",regex=True)
            s = s.str.replace(r"\bM[eé]dia\b","M",regex=True)
            s = s.str.replace(r"\bPequena\b","P",regex=True)
            return s

        def normalize_key_general(s):
            t = s.astype(str)
            t = t.str.replace(r"^\s*Pizza\s+","",regex=True)
            t = normalize_sizes(t)
            t = t.str.replace(r"\bBENEVENUTO\b","CAPRICCIOSA",flags=re.IGNORECASE,regex=True)
            t = t.str.replace(r"\s{2,}"," ",regex=True).str.strip()
            return t

        def clean_nome_prod_hist(nome_series, cat_series):
            s = nome_series.astype(str)
            s = s.str.replace(r"^\s*Pizza\s+","",regex=True)
            s = normalize_sizes(s)
            s = s.str.replace(r"\bBENEVENUTO\b","CAPRICCIOSA",flags=re.IGNORECASE,regex=True)
            mask_sucos = cat_series.astype(str).str.upper().eq("SUCOS")
            sabores = r"(LARANJA|ABACAXI|MARACUJ[ÁA])"
            s2 = s.copy()
            s2.loc[mask_sucos] = s2.loc[mask_sucos].str.replace(rf"(\bSUCO)\s+{sabores}\s+",r"\1 ",flags=re.IGNORECASE,regex=True)
            s2 = s2.str.replace(r"^carnes\s+","",regex=True, flags=re.IGNORECASE)
            s2 = s2.str.replace(r"^(?:batata frita\s+){2}", "BATATA FRITA ", flags=re.IGNORECASE, regex=True)
            mask_rodizio = s2.str.contains(r"rod[ií]zio", flags=re.IGNORECASE, regex=True)
            s2.loc[mask_rodizio] = "RODÍZIO DE PIZZA"
            s2 = s2.str.replace(r"\s{2,}"," ",regex=True).str.strip()
            return s2
        mask_periodo = True
        if data_ini is not None and data_fim is not None:
            mask_periodo = (itens["data_item"] >= pd.to_datetime(data_ini)) & (itens["data_item"] <= pd.to_datetime(data_fim))
        iv = itens.loc[mask_periodo].copy()

        iv["cat_norm"] = iv["cat_prod"].astype(str).str.upper().str.strip()
        iv["nome_limpo"] = clean_nome_prod_hist(iv["nome_prod"], iv["cat_prod"])
        iv["valor_base"] = iv["valor_tot"] * iv["qtd"]

        c_pizzas = c_pizzas.copy()
        c_bebidas = c_bebidas.copy()
        c_pizzas.columns = c_pizzas.columns.str.strip()
        c_bebidas.columns = c_bebidas.columns.str.strip()
        c_pizzas["_KEY"] = normalize_key_general(c_pizzas["produto"])
        c_bebidas["_KEY"] = normalize_key_general(c_bebidas["produto"])
        lookup_pizza = c_pizzas.set_index("_KEY")["custo"]
        lookup_bebida = c_bebidas.set_index("_KEY")["custo"]

        iv["custo_pizza"] = iv["nome_limpo"].map(lookup_pizza)
        iv["custo_bebida"] = iv["nome_limpo"].map(lookup_bebida)
        iv["custo_unit"] = iv["custo_pizza"].combine_first(iv["custo_bebida"])

        mask_complemento = iv["cat_norm"].eq("COMPLEMENTO")
        iv["cmv_item"] = np.where(mask_complemento, 0.5 * iv["valor_base"], iv["custo_unit"] * iv["qtd"])

        cmv_total = float(iv["cmv_item"].sum(skipna=True))
        pre_receita_total = 0.0
        if arq_pre.exists():
            dfx = pd.read_excel(arq_pre)
            dfx.columns = dfx.columns.str.strip()
            if "Data" in dfx.columns and "data" not in dfx.columns:
                dfx = dfx.rename(columns={"Data":"data"})
            dfx["data"] = pd.to_datetime(dfx["data"], errors="coerce")
            cols_pagto = [c for c in dfx.columns if c not in {"data","TOTAL","TOTAL_RECALCULADO"}]
            dfx_long = dfx.melt(id_vars=["data"], value_vars=cols_pagto, var_name="forma_pagamento", value_name="valor_liq")
            dfx_long["valor_liq"] = pd.to_numeric(dfx_long["valor_liq"], errors="coerce").fillna(0)
            mask_pre = (dfx_long["data"] >= pd.to_datetime(data_ini)) & (dfx_long["data"] <= pd.to_datetime(data_fim))
            pre_receita_total = float(dfx_long.loc[mask_pre, "valor_liq"].sum())
            cmv_extra_pre = 0.30 * pre_receita_total
            cmv_total = cmv_total + cmv_extra_pre

        st.metric("CMV Total (R$)", br_money(cmv_total))


        def meses_ciclo_ancora(ini, fim):
            ini = pd.to_datetime(ini).date()
            fim = pd.to_datetime(fim).date()
            y, m = ini.year, ini.month
            cini, cfim = ciclo_12_12_bounds(y, m)
            while cfim <= ini:
                y, m = (y + 1, 1) if m == 12 else (y, m + 1)
                cini, cfim = ciclo_12_12_bounds(y, m)
            meses = []
            while cini < fim:
                if not (cfim <= ini or cini >= fim):
                    meses.append((cini.year, cini.month))
                y, m = (y + 1, 1) if m == 12 else (y, m + 1)
                cini, cfim = ciclo_12_12_bounds(y, m)
            return set(meses)

        def custos_fixos_periodo(df_custos, data_ini, data_fim):
            dfc = df_custos.copy()
            dfc.columns = dfc.columns.str.strip()
            dfc = dfc.rename(columns={"DATA":"data","DESCRIÇÃO":"descricao","VALOR":"valor"})
            dfc["data"] = pd.to_datetime(dfc["data"], errors="coerce")
            dfc["valor"] = pd.to_numeric(dfc["valor"], errors="coerce")
            dfc = dfc.dropna(subset=["data","valor"])
            dfc["ano"] = dfc["data"].dt.year
            dfc["mes"] = dfc["data"].dt.month
            ini = pd.to_datetime(data_ini)
            fim = pd.to_datetime(data_fim)
            meses = meses_ciclo_ancora(ini, fim)
            aloc = dfc[dfc.apply(lambda r: (int(r["ano"]), int(r["mes"])) in meses, axis=1)].copy()
            if aloc.empty:
                return 0.0, pd.DataFrame()
            aloc["Mês"] = aloc["data"].dt.to_period("M").astype(str)
            aloc = aloc[["Mês","descricao","valor"]].rename(columns={"descricao":"Descrição","valor":"Valor (R$)"})
            total = float(aloc["Valor (R$)"].sum())
            return total, aloc

        df_contas_custos = (arq_contas, None)
        receita_total = 0.0
        if carregou(df_contas_custos):
            dfc2 = df_contas_custos.copy()
            dfc2.columns = dfc2.columns.str.strip()
            dfc2 = dfc2.rename(columns={"Cód. Pedido":"cod_pedido","Valor Líq.":"valor_liq","Forma Pagamento":"forma_pagamento","Crédito":"data"})
            dfc2["data"] = pd.to_datetime(dfc2["data"], errors="coerce")
            dfc2 = dfc2.dropna(subset=["data","valor_liq","cod_pedido"]).copy()
            def normaliza_pagto2(x):
                s = str(x).strip().upper()
                if s in {"PIX", "PIX MANUAL", "A CONFIRMAR", "VALE REFEICAO", "VALE REFEIÇÃO"}:
                    return "PIX"
                return s
            dfc2["forma_pagamento"] = dfc2["forma_pagamento"].apply(normaliza_pagto2)
            mask_receita = (dfc2["data"] >= pd.to_datetime(data_ini)) & (dfc2["data"] <= pd.to_datetime(data_fim))
            dfr = dfc2.loc[mask_receita].copy()
            dfr = dfr[~dfr["data"].dt.weekday.isin([0, 1])]
            receita_total = float(dfr["valor_liq"].sum())
            receita_total = receita_total + pre_receita_total

        df_cfix = (None, arq_custos_fixos)

        dias_periodo = (pd.to_datetime(data_fim) - pd.to_datetime(data_ini)).days + 1
        total_cfix, tabela_cfix = 0.0, pd.DataFrame()
        if dias_periodo >= 30 and carregou(df_cfix):
            total_cfix, tabela_cfix = custos_fixos_periodo(df_cfix, data_ini, data_fim)

        margem_bruta = receita_total - cmv_total
        margem_bruta_pct = (margem_bruta / receita_total * 100) if receita_total else 0.0
        margem_liquida = receita_total - cmv_total - total_cfix
        margem_liquida_pct = (margem_liquida / receita_total * 100) if receita_total else 0.0

        kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
        kpi1.metric("Receita (R$)", br_money(receita_total))
        kpi2.metric("CMV (R$)", br_money(cmv_total))
        kpi3.metric("Margem Bruta (R$)", br_money(margem_bruta))
        kpi4.metric("Margem Bruta (%)", f"{margem_bruta_pct:.1f}%")
        kpi5.metric("Custos Fixos (R$)", br_money(total_cfix))
        kpi6.metric("Margem Líquida (R$)", br_money(margem_liquida))

        st.subheader("Custos Fixos no Período")
        if dias_periodo < 30:
            st.info("Período menor que 30 dias: custos fixos e margem líquida ignorados.")
        else:
            if not tabela_cfix.empty:
                st.dataframe(nomes_legiveis(tabela_cfix.reset_index(drop=True)), use_container_width=True, hide_index=True)
            else:
                st.info("Sem custos fixos para o período selecionado ou arquivo ausente.")


        tabela = iv.groupby(["nome_limpo"],as_index=False).agg(
            categoria=("cat_norm","first"),
            qtd=("qtd","sum"),
            receita=("valor_tot","sum"),
            cmv=("cmv_item","sum")
        )
        tabela["margem"] = tabela["receita"] - tabela["cmv"]
        tabela["margem_%"] = (tabela["margem"] / tabela["receita"] * 100).round(1)
        tabela = tabela.rename(columns={"nome_limpo":"produto"}).sort_values("cmv", ascending=False).reset_index(drop=True)

        st.dataframe(nomes_legiveis(tabela), use_container_width=True, hide_index=True)

        mask_sem_custo = iv["custo_unit"].isna() & ~mask_complemento
        diag_sem_custo = (iv.loc[mask_sem_custo, ["nome_prod","nome_limpo","cat_prod","qtd","valor_tot","valor_base"]]
                            .assign(ocorrencias=1)
                            .groupby(["nome_prod","nome_limpo","cat_prod"])
                            .agg(qtd_total=("qtd","sum"), valor_total=("valor_base","sum"), ocorrencias=("ocorrencias","sum"))
                            .reset_index()
                            .sort_values(["ocorrencias","valor_total"], ascending=[False, False]))
        if not diag_sem_custo.empty:
            st.divider()
            