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
arquivo_dashboard = "dashboard.html"

os.makedirs(pasta_plots, exist_ok=True)

# ==================================================
# FUNÇÕES AUXILIARES
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
portfolio['ticker'] = portfolio['ticker'].apply(normalizar_ticker)

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
.card {{
  background:white;
  padding:20px;
  margin:20px auto;
  width:90%;
  border-radius:8px;
  box-shadow:0 2px 5px rgba(0,0,0,.1);
}}
.ok {{ color: #2e7d32; font-weight:bold; }}
.buy {{ color: #1565c0; font-weight:bold; }}
.sell {{ color: #c62828; font-weight:bold; }}
.warn {{ color: #f57c00; font-weight:bold; }}
img {{ max-width:100%; }}
</style>
</head>
<body>
<h1>📊 Dashboard do Portfólio</h1>
<p style="text-align:center;">Atualizado em: {date.today()}</p>
"""

# ==================================================
# PROCESSA CADA ATIVO
# ==================================================
for _, row in portfolio.iterrows():
    ticker = row['ticker']

    df = yf.download(
        ticker,
        start="2010-01-01",
        auto_adjust=True,
        progress=False
    )

    if df.empty:
        html += f"""
        <div class="card">
          <h2>{ticker}</h2>
          <p class="warn">❌ Dados não encontrados</p>
        </div>
        """
        continue

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[['Close']].dropna()

    # Verificação mínima antes das médias
    if len(df) < long_window + 5:
        html += f"""
        <div class="card">
          <h2>{ticker}</h2>
          <p class="warn">⚠️ Histórico insuficiente para cálculo das médias</p>
        </div>
        """
        continue

    # Médias móveis
    df['MM20'] = df['Close'].rolling(short_window).mean()
    df['MM50'] = df['Close'].rolling(long_window).mean()

    # Remove linhas sem médias
    df = df.dropna()

    # Verificação FINAL antes de acessar iloc[-2]
    if len(df) < 2:
        html += f"""
        <div class="card">
          <h2>{ticker}</h2>
          <p class="warn">⚠️ Dados insuficientes após cálculo das médias</p>
        </div>
        """
        continue

    ontem = df.iloc[-2]
    hoje = df.iloc[-1]

    if ontem['MM20'] <= ontem['MM50'] and hoje['MM20'] > hoje['MM50']:
        status = "🟢 COMPRA"
        classe = "buy"
    elif ontem['MM20'] >= ontem['MM50'] and hoje['MM20'] < hoje['MM50']:
        status = "🔴 VENDA"
        classe = "sell"
    else:
        status = "⚪ NENHUMA AÇÃO"
        classe = "ok"

    # ======================
    # PLOT
    # ======================
    plt.figure(figsize=(10, 4))
    plt.plot(df.index, df['Close'], label='Preço')
    plt.plot(df.index, df['MM20'], label='MM20')
    plt.plot(df.index, df['MM50'], label='MM50')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    nome_plot = f"{ticker}.png"
    caminho_plot = os.path.join(pasta_plots, nome_plot)
    plt.savefig(caminho_plot, dpi=150)
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
# FINAL HTML
# ==================================================
html += "</body></html>"

with open(arquivo_dashboard, "w", encoding="utf-8") as f:
    f.write(html)

print("Dashboard gerado com sucesso.")
