from pathlib import Path
import pandas as pd
import numpy as np
import re

PATH_HIST = r"C:\Users\jvand\Downloads\Historico_Itens_Vendidos de 01-04-25 à 13-10-25.xlsx"
PATH_CUSTO_PIZZAS = r"C:\Users\jvand\Desktop\Adoro Pizza\custo_pizzas.xlsx"
PATH_CUSTO_BEBIDAS = r"C:\Users\jvand\Desktop\Adoro Pizza\custo bebidas.xlsx"
PATH_SAIDA = r"C:\Users\jvand\Desktop\Adoro Pizza\diag_sem_custo.xlsx"

def normalize_sizes(text):
    s = text.str.replace(r"\bGrande\b", "G", regex=True)
    s = s.str.replace(r"\bM[eé]dia\b", "M", regex=True)
    s = s.str.replace(r"\bPequena\b", "P", regex=True)
    return s

def normalize_key_general(s):
    t = s.astype(str)
    t = t.str.replace(r"^\s*Pizza\s+", "", regex=True)
    t = normalize_sizes(t)
    t = t.str.replace(r"\bBENEVENUTO\b", "CAPRICCIOSA", flags=re.IGNORECASE, regex=True)
    t = t.str.replace(r"\s{2,}", " ", regex=True).str.strip()
    return t

def clean_nome_prod_hist(nome_series, cat_series):
    s = nome_series.astype(str)
    s = s.str.replace(r"^\s*Pizza\s+", "", regex=True)
    s = s.str.replace(r"^\s*Batata Frita\s+", "", regex=True)
    s = s.str.replace(r"^\s*Carnes\s+", "", regex=True)
    s = normalize_sizes(s)
    s = s.str.replace(r"\bBENEVENUTO\b", "CAPRICCIOSA", flags=re.IGNORECASE, regex=True)
    mask_sucos = cat_series.astype(str).str.upper().eq("SUCOS")
    sabores = r"(LARANJA|ABACAXI|MARACUJ[ÁA])"
    s2 = s.copy()
    s2.loc[mask_sucos] = s2.loc[mask_sucos].str.replace(rf"(\bSUCO)\s+{sabores}\s+", r"\1 ", flags=re.IGNORECASE, regex=True)
    s2 = s2.str.replace(r"\s{2,}", " ", regex=True).str.strip()
    return s2

df_hist = pd.read_excel(PATH_HIST)
df_custo_pizzas = pd.read_excel(PATH_CUSTO_PIZZAS)
df_custo_bebidas = pd.read_excel(PATH_CUSTO_BEBIDAS)

mask_excluido = df_hist["Nome Prod"].astype(str).str.startswith("* Excluído *", na=False)
df = df_hist.loc[~mask_excluido].copy()

df["Nome Prod LIMPO"] = clean_nome_prod_hist(df["Nome Prod"], df["Cat. Prod."])

for col in ["Valor. Tot. Item", "Qtd."]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df["Valor_Base"] = df["Valor. Tot. Item"].fillna(0) * df["Qtd."].fillna(0)

df_custo_pizzas["_KEY"] = normalize_key_general(df_custo_pizzas["produto"])
df_custo_bebidas["_KEY"] = normalize_key_general(df_custo_bebidas["produto"])

lookup_pizza = df_custo_pizzas.set_index("_KEY")["custo"]
lookup_bebida = df_custo_bebidas.set_index("_KEY")["custo"]


df["Custo Unitário (pizza)"] = df["Nome Prod LIMPO"].map(lookup_pizza)
df["Custo Unitário (bebida)"] = df["Nome Prod LIMPO"].map(lookup_bebida)
df["Custo Unitário"] = df["Custo Unitário (pizza)"].combine_first(df["Custo Unitário (bebida)"])

CUSTO_UNITARIO_RODIZIO = 19.0
df.loc[df["Cat. Prod."].astype(str).str.upper().str.contains("RODÍZIO"), "Custo Unitário"] = CUSTO_UNITARIO_RODIZIO

mask_complemento = df["Cat. Prod."].astype(str).str.upper().eq("COMPLEMENTO")
df["CMV_Item"] = np.where(
    mask_complemento,
    0.5 * df["Valor_Base"],
    df["Custo Unitário"] * df["Qtd."].fillna(0)
)

mask_sem_custo = df["Custo Unitário"].isna() & ~mask_complemento
diag_sem_custo = (
    df.loc[mask_sem_custo, ["Nome Prod", "Nome Prod LIMPO", "Cat. Prod.", "Qtd.", "Valor. Tot. Item", "Valor_Base"]]
    .assign(ocorrencias=1)
    .groupby(["Nome Prod", "Nome Prod LIMPO", "Cat. Prod."])
    .agg(qtd_total=("Qtd.", "sum"),
         valor_total=("Valor_Base", "sum"),
         ocorrencias=("ocorrencias", "sum"))
    .reset_index()
    .sort_values(["Cat. Prod.", "ocorrencias", "valor_total"], ascending=[True, False, False])
)

resumo_cat = (
    df.groupby(df["Cat. Prod."].astype(str))
      .agg(linhas=("Nome Prod", "count"),
           qtd_total=("Qtd.", "sum"),
           valor_base=("Valor_Base", "sum"),
           cmv=("CMV_Item", "sum"))
      .reset_index()
      .sort_values("valor_base", ascending=False)
)

cmv_total = float(df["CMV_Item"].sum(skipna=True))

print("=" * 80)
print("CMV TOTAL (com regra de 50% para COMPLEMENTO): R$ {:,.2f}".format(cmv_total).replace(",", "X").replace(".", ",").replace("X", "."))
print("=" * 80)
print("\nResumo por Categoria:")
print(resumo_cat.to_string(index=False))
if len(diag_sem_custo) > 0:
    print("\nATENÇÃO: Itens sem custo mapeado exportados para:", PATH_SAIDA)
    diag_sem_custo.to_excel(PATH_SAIDA, index=False)
    print(diag_sem_custo.head(50).to_string(index=False))
    if len(diag_sem_custo) > 50:
        print(f"... (+{len(diag_sem_custo)-50} linhas)")
else:
    print("\nNão há itens pendentes de mapeamento de custo. ✅")
print("\nAmostra de 15 linhas pós-limpeza:")
print(df[["Nome Prod", "Nome Prod LIMPO", "Cat. Prod.", "Qtd.", "Valor. Tot. Item", "Valor_Base", "Custo Unitário", "CMV_Item"]].head(15).to_string(index=False))