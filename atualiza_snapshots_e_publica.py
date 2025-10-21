import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

REPO_DIR = Path(r"C:\Users\jvand\Desktop\Dashboard")
DATA_DIR = REPO_DIR / "data"
DOWNLOADS = Path(r"C:\Users\jvand\Downloads")
CUSTOS_DIR = Path(r"C:\Users\jvand\Desktop\Adoro Pizza")

ARQ_CUSTO_BEBIDAS_ORIG = CUSTOS_DIR / "custo bebidas.xlsx"
ARQ_CUSTO_PIZZAS_ORIG  = CUSTOS_DIR / "custo_pizzas.xlsx"
ARQ_CUSTOS_FIXOS_ORIG = CUSTOS_DIR / "custos fixos.xlsx"


DEST_HIST     = DATA_DIR / "Historico_Itens_Vendidos.xlsx"
DEST_PEDIDOS  = DATA_DIR / "Todos os pedidos.xlsx"
DEST_RECEBER  = DATA_DIR / "Lista-contas-receber.xlsx"
DEST_BEBIDAS  = DATA_DIR / "custo bebidas.xlsx"
DEST_PIZZAS   = DATA_DIR / "custo_pizzas.xlsx"
DEST_CUSTOS_FIXOS = DATA_DIR / "custos fixos.xlsx"


RX_ITENS = re.compile(r"^Historico_Itens_Vendidos de (\d{2}-\d{2}-\d{2}) à (\d{2}-\d{2}-\d{2})\.xlsx$", re.IGNORECASE)
RX_PEDIDOS = re.compile(r"^Todos os pedidos\s+Data de Abertura\s*\[(\d{2}-\d{2}-\d{4})\s*\d{4}\s*-\s*(\d{2}-\d{2}-\d{4})\s*\d{4}\]\.xlsx$", re.IGNORECASE)
RX_RECEBER = re.compile(r"^Lista-contas-receber-(\d{2}-\d{2}-\d{2})-a-(\d{2}-\d{2}-\d{2})\.xlsx$", re.IGNORECASE)

def parse_date_end_itens(name):
    m = RX_ITENS.match(name)
    if not m: return None
    dd, mm, aa = m.group(2).split("-")
    return datetime.strptime(f"{dd}-{mm}-20{aa}", "%d-%m-%Y")

def parse_date_end_pedidos(name):
    m = RX_PEDIDOS.match(name)
    if not m: return None
    return datetime.strptime(m.group(2), "%d-%m-%Y")

def parse_date_end_receber(name):
    m = RX_RECEBER.match(name)
    if not m: return None
    dd, mm, aa = m.group(2).split("-")
    return datetime.strptime(f"{dd}-{mm}-20{aa}", "%d-%m-%Y")

def escolher_mais_recente(pasta, parser, prefixo):
    candidatos = []
    for p in pasta.glob("*.xlsx"):
        if prefixo.lower() in p.name.lower():
            dt = parser(p.name) or datetime.fromtimestamp(p.stat().st_mtime)
            candidatos.append((dt, p))
    if not candidatos: return None
    candidatos.sort(key=lambda x: x[0], reverse=True)
    return candidatos[0][1]

def copiar(src, dst, label):
    if not src or not src.exists():
        print(f"[AVISO] {label} não encontrado")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"[OK] {label} atualizado")
    return True

def git_commit_push(repo_dir, msg):
    def run(*args, check=True, capture=False):
        return subprocess.run(
            ["git", "-C", str(repo_dir), *args],
            check=check,
            text=True,
            capture_output=capture
        )

    # puxa do remoto antes de tudo
    run("fetch", "origin")
    try:
        run("pull", "--rebase", "origin", "main")
        print("[OK] Pull --rebase concluído.")
    except subprocess.CalledProcessError as e:
        print("[ERRO] Falha no pull --rebase. Saída:")
        print(e.stderr or e.stdout)
        raise

    # adiciona e commita
    run("add", ".")
    res = run("commit", "-m", msg, capture=True, check=False)
    if "nothing to commit" in (res.stdout or "").lower():
        print("[INFO] Nenhuma alteração nova.")

    # tenta o push
    try:
        run("push", "-u", "origin", "main")
        print("[OK] Push concluído.")
    except subprocess.CalledProcessError as e:
        print("[ERRO] Push falhou. Mensagem do Git:")
        print(e.stderr or e.stdout)
        print("Dica: verifique se há commits remotos novos ou tente 'git push --force' (com cautela).")
        raise


def main():
    print("== Atualizando arquivos e publicando ==")
    itens   = escolher_mais_recente(DOWNLOADS, parse_date_end_itens,   "Historico_Itens_Vendidos")
    pedidos = escolher_mais_recente(DOWNLOADS, parse_date_end_pedidos, "Todos os pedidos")
    receber = escolher_mais_recente(DOWNLOADS, parse_date_end_receber, "Lista-contas-receber")

    copiar(itens,   DEST_HIST,    "Histórico de Itens Vendidos")
    copiar(pedidos, DEST_PEDIDOS, "Todos os Pedidos")
    copiar(receber, DEST_RECEBER, "Lista de Contas a Receber")
    copiar(ARQ_CUSTO_BEBIDAS_ORIG, DEST_BEBIDAS, "Custo Bebidas")
    copiar(ARQ_CUSTO_PIZZAS_ORIG,  DEST_PIZZAS,  "Custo Pizzas")
    copiar(ARQ_CUSTOS_FIXOS_ORIG, DEST_CUSTOS_FIXOS, "Custos Fixos")


    msg = f"Atualização automática - {datetime.now():%Y-%m-%d %H:%M}"
    git_commit_push(REPO_DIR, msg)
    print("== Finalizado ==")

if __name__ == "__main__":
    main()
