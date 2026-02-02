import matplotlib
matplotlib.use("Agg")  # backend estável (Windows + GitHub)

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import date

# ==================================================
# CONFIGURAÇÃO
# ==================================================
arquivo_portfolio = "portfolio.xlsx"
short_window = 20
long_window = 50
pasta_plots = "plots"
arquivo_dashboard = "index.html"

os.makedirs(pasta_plots, exist_ok=True)

# ==================================================
# FUNÇÃO AUXILIAR
# ==================================================
def normalizar_ticker(ticker):
    ticker = str(ticker).strip().upper()
    if not ticker.endswith(".SA"):
        ticker += ".SA"
    return ticker

# ==================================================
# LEITURA DO PORTFÓLIO
# ==================================================
portfolio = pd.read_excel(arquivo_portfolio)
portfolio["ticker"] = portfolio["ticker"].apply(normalizar_ticker)

# ==================================================
# RESUMO EXECUTIVO
# ==================================================
resumo = []

# ==================================================
# INÍCIO HTML
# ==================================================
html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Dashboard do Portfólio</title>
<style>
body {{ font-family: Arial; background:#f4f6f8; }}
h1 {{ text-align:center; }}
h2 {{ text-align:center; }}
.card {{
  background:white;
  padding:20px;
  margin:20px auto;
  width:92%;
  border-radius:8px;
  box-shadow:0 2px 6px rgba(0,0,0,.12);
}}
.buy {{ color:#1b5e20; font-weight:bold; }}
.sell {{ color:#b71c1c; font-weight:bold; }}
.ok {{ color:#333; }}
table {{ border-collapse:collapse; width:90%; margin:20px auto; }}
th, td {{ padding:8px; border:1px solid #ccc; text-align:center; }}
th {{ background:#e0e0e0; }}
img {{ max-width:100%; }}
</style>
</head>
<body>
<h1>📊 Dashboard do Portfólio</h1>
<p style="text-align:center;">Atualizado em: {date.today()}</p>
"""

# ==================================================
# PROCESSA ATIVOS
# ==================================================
for _, row in portfolio.iterrows():
    ticker = row["ticker"]

    df = yf.download(
        ticker,
        start="2018-01-01",
        auto_adjust=True,
        progress=False
    )

    if df.empty:
        continue

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Close"]].dropna()

    if len(df) < long_window + 10:
        continue

    # Médias móveis
    df["MM20"] = df["Close"].rolling(short_window).mean()
    df["MM50"] = df["Close"].rolling(long_window).mean()
    df.dropna(inplace=True)

    if len(df) < 2:
        continue

    # ======================
    # DETECÇÃO DE CRUZAMENTOS (HISTÓRICO)
    # ======================
    buy_x, buy_y = [], []
    sell_x, sell_y = [], []

    for i in range(1, len(df)):
        if df["MM20"].iloc[i-1] <= df["MM50"].iloc[i-1] and df["MM20"].iloc[i] > df["MM50"].iloc[i]:
            buy_x.append(df.index[i])
            buy_y.append(df["Close"].iloc[i])

        if df["MM20"].iloc[i-1] >= df["MM50"].iloc[i-1] and df["MM20"].iloc[i] < df["MM50"].iloc[i]:
            sell_x.append(df.index[i])
            sell_y.append(df["Close"].iloc[i])

    # ======================
    # SINAL ATUAL
    # ======================
    ontem = df.iloc[-2]
    hoje = df.iloc[-1]

    if ontem["MM20"] <= ontem["MM50"] and hoje["MM20"] > hoje["MM50"]:
        status = "🟢 COMPRA"
        classe = "buy"
    elif ontem["MM20"] >= ontem["MM50"] and hoje["MM20"] < hoje["MM50"]:
        status = "🔴 VENDA"
        classe = "sell"
    else:
        status = "⚪ NENHUMA AÇÃO"
        classe = "ok"

    # ======================
    # ADICIONA AO RESUMO
    # ======================
    resumo.append({
        "ticker": ticker,
        "preco": round(hoje["Close"], 2),
        "status": status,
        "classe": classe,
        "tendencia": "Alta" if hoje["MM20"] > hoje["MM50"] else "Baixa"
    })

    # ======================
    # PLOT COM MARCADORES
    # ======================
    plt.figure(figsize=(12, 5))
    plt.plot(df.index, df["Close"], label="Preço", linewidth=2)
    plt.plot(df.index, df["MM20"], label="MM20", linestyle="--")
    plt.plot(df.index, df["MM50"], label="MM50", linestyle="--")

    plt.scatter(buy_x, buy_y, marker="^", color="green", s=120, label="Compra", zorder=5)
    plt.scatter(sell_x, sell_y, marker="v", color="red", s=120, label="Venda", zorder=5)

    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    nome_plot = f"{ticker}.png"
    plt.savefig(os.path.join(pasta_plots, nome_plot), dpi=160)
    plt.close()

    # ======================
    # HTML DO ATIVO
    # ======================
    html += f"""
    <div class="card">
      <h2>{ticker}</h2>
      <p>Preço atual: <strong>{hoje['Close']:.2f}</strong></p>
      <p class="{classe}">Sinal: {status}</p>
      <img src="{pasta_plots}/{nome_plot}">
    </div>
    """

# ==================================================
# RESUMO EXECUTIVO (TOPO)
# ==================================================
ordem_status = {"🔴 VENDA": 0, "🟢 COMPRA": 1, "⚪ NENHUMA AÇÃO": 2}
resumo.sort(key=lambda x: ordem_status.get(x["status"], 99))

tabela_resumo = """
<h2>📌 Resumo Executivo</h2>
<table>
<tr>
  <th>Ticker</th>
  <th>Preço</th>
  <th>Sinal</th>
  <th>Tendência</th>
</tr>
"""

for r in resumo:
    tabela_resumo += f"""
    <tr>
      <td>{r['ticker']}</td>
      <td>{r['preco']}</td>
      <td class="{r['classe']}">{r['status']}</td>
      <td>{r['tendencia']}</td>
    </tr>
    """

tabela_resumo += "</table>"

html = html.replace("</h1>", "</h1>" + tabela_resumo)

# ==================================================
# FINAL HTML
# ==================================================
html += "</body></html>"

with open(arquivo_dashboard, "w", encoding="utf-8") as f:
    f.write(html)

print("Dashboard gerado com sucesso.")
