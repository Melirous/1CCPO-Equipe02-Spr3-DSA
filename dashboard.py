"""
GreenVolt - Geracao de graficos e painel supervisorio
=====================================================

Le os arquivos de dados produzidos por src/simulador.py e gera:

    docs/grafico_despacho.png        -> geracao x demanda x fontes (24 h)
    docs/grafico_bateria.png         -> SoC do banco e eventos de automacao
    docs/grafico_fontes.png          -> composicao da energia entregue
    dados/eventos_automacao.csv      -> log dos comandos emitidos pelo controlador
    docs/dashboard.html              -> painel supervisorio (arquivo unico)

Uso:
    python src/dashboard.py
"""

from __future__ import annotations

import base64
import csv
import io
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MultipleLocator  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_DADOS = os.path.join(BASE, "dados")
DIR_DOCS = os.path.join(BASE, "docs")

# Paleta do painel
C_FUNDO = "#0E1A1F"
C_PAINEL = "#152329"
C_SOLAR = "#F2A20C"
C_BATERIA = "#3FC5A0"
C_REDE = "#5B8FD9"
C_DEMANDA = "#E8EDEE"
C_ALERTA = "#E2574C"
C_TEXTO = "#AFC0C6"


def carregar():
    with open(os.path.join(DIR_DADOS, "telemetria_24h.csv"), encoding="utf-8") as f:
        tele = list(csv.DictReader(f))
    with open(os.path.join(DIR_DADOS, "sessoes_recarga.csv"), encoding="utf-8") as f:
        sessoes = list(csv.DictReader(f))
    with open(os.path.join(DIR_DADOS, "resumo_diario.json"), encoding="utf-8") as f:
        resumo = json.load(f)
    return tele, sessoes, resumo


def estilo(ax, titulo: str, ylabel: str) -> None:
    ax.set_facecolor(C_PAINEL)
    ax.set_title(titulo, color="#FFFFFF", fontsize=13, pad=14, loc="left")
    ax.set_ylabel(ylabel, color=C_TEXTO, fontsize=10)
    ax.tick_params(colors=C_TEXTO, labelsize=9)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("bottom", "left"):
        ax.spines[lado].set_color("#2C3E45")
    ax.grid(color="#22343B", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_locator(MultipleLocator(2))
    ax.set_xlim(0, 24)


def salvar(fig, nome: str) -> str:
    caminho = os.path.join(DIR_DOCS, nome)
    fig.savefig(caminho, dpi=150, facecolor=C_FUNDO, bbox_inches="tight")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, facecolor=C_FUNDO, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def grafico_despacho(t) -> str:
    horas = [i / 60 for i in range(len(t))]
    solar = [float(r["solar_kw"]) for r in t]
    bat = [float(r["bateria_kw"]) for r in t]
    rede = [float(r["rede_kw"]) for r in t]
    pv = [float(r["pv_kw"]) for r in t]
    dem = [float(r["demanda_kw"]) for r in t]

    fig, ax = plt.subplots(figsize=(11, 4.6))
    fig.patch.set_facecolor(C_FUNDO)
    ax.stackplot(horas, solar, bat, rede,
                 colors=[C_SOLAR, C_BATERIA, C_REDE], alpha=0.9,
                 labels=["Solar direta", "Banco de baterias", "Rede"])
    ax.plot(horas, pv, color="#FFD980", lw=1.2, ls="--", label="Geracao FV disponivel")
    ax.plot(horas, dem, color=C_DEMANDA, lw=1.4, label="Demanda dos veiculos")
    ax.axvspan(13.083, 13.583, color=C_ALERTA, alpha=0.18)
    ax.text(13.33, max(dem) * 0.96, "rede fora", color=C_ALERTA, fontsize=8.5, ha="center")
    ax.axvspan(18, 21, color=C_REDE, alpha=0.08)
    ax.text(19.5, max(dem) * 0.96, "horario de ponta", color=C_REDE, fontsize=8.5, ha="center")
    estilo(ax, "Despacho energetico por fonte ao longo do dia", "Potencia (kW)")
    ax.set_xlabel("Hora do dia", color=C_TEXTO, fontsize=10)
    leg = ax.legend(loc="upper left", frameon=False, fontsize=9, ncol=2)
    for txt in leg.get_texts():
        txt.set_color(C_TEXTO)
    return salvar(fig, "grafico_despacho.png")


def grafico_bateria(t) -> str:
    horas = [i / 60 for i in range(len(t))]
    soc = [float(r["soc_bateria_%"]) for r in t]
    carga = [float(r["solar_p_bateria_kw"]) for r in t]
    perda = [float(r["curtailment_kw"]) for r in t]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 5.4), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    fig.patch.set_facecolor(C_FUNDO)

    ax1.plot(horas, soc, color=C_BATERIA, lw=2)
    ax1.fill_between(horas, soc, color=C_BATERIA, alpha=0.15)
    ax1.axhline(20, color=C_ALERTA, ls=":", lw=1)
    ax1.text(0.2, 22, "reserva tecnica 20%", color=C_ALERTA, fontsize=8.5)
    ax1.axvspan(13.083, 13.583, color=C_ALERTA, alpha=0.18)
    ax1.set_ylim(0, 105)
    estilo(ax1, "Estado de carga do banco de baterias", "SoC (%)")

    ax2.fill_between(horas, carga, color=C_SOLAR, alpha=0.85, label="Excedente armazenado")
    ax2.fill_between(horas, perda, color="#6B4F1D", alpha=0.9, label="Excedente perdido")
    estilo(ax2, "Aproveitamento do excedente fotovoltaico", "kW")
    ax2.set_xlabel("Hora do dia", color=C_TEXTO, fontsize=10)
    leg = ax2.legend(loc="upper left", frameon=False, fontsize=9)
    for txt in leg.get_texts():
        txt.set_color(C_TEXTO)
    return salvar(fig, "grafico_bateria.png")


def grafico_fontes(resumo) -> str:
    valores = [resumo["energia_solar_direta_kwh"], resumo["energia_bateria_kwh"],
               resumo["energia_rede_kwh"]]
    rotulos = ["Solar direta", "Baterias\n(excedente solar)", "Rede"]
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    fig.patch.set_facecolor(C_FUNDO)
    barras = ax.bar(rotulos, valores, color=[C_SOLAR, C_BATERIA, C_REDE], width=0.55)
    for b, v in zip(barras, valores):
        ax.text(b.get_x() + b.get_width() / 2, v + 5, f"{v:.0f} kWh",
                ha="center", color="#FFFFFF", fontsize=10)
    ax.set_facecolor(C_PAINEL)
    ax.set_title("Origem da energia entregue", color="#FFFFFF", fontsize=13, pad=14, loc="left")
    ax.set_ylabel("kWh", color=C_TEXTO)
    ax.tick_params(colors=C_TEXTO, labelsize=9)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("bottom", "left"):
        ax.spines[lado].set_color("#2C3E45")
    ax.grid(axis="y", color="#22343B", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(valores) * 1.2)
    return salvar(fig, "grafico_fontes.png")


def extrair_eventos(t) -> list[dict]:
    """Converte as transicoes de modo do controlador em um log de comandos."""
    acoes = {
        "100% SOLAR": "Chaveia carga para 100% fotovoltaico; rede em standby",
        "SOLAR+BANCO": "Complementa a geracao solar com o banco de baterias",
        "HIBRIDO": "Complementa a geracao solar com energia da rede",
        "ECONOMIA": "Limita potencia dos pontos e prioriza veiculo de menor SoC",
        "ILHADO": "Abre o disjuntor de rede e opera pelo banco de baterias",
        "OCIOSO": "Sem veiculos conectados; excedente direcionado ao banco",
    }
    eventos, anterior = [], None
    for r in t:
        if r["modo"] != anterior:
            comando = acoes[r["modo"]]
            if float(r["pv_kw"]) < 0.1:
                if r["modo"] == "HIBRIDO":
                    comando = "Sem geracao solar: atende a demanda pela rede"
                elif r["modo"] == "SOLAR+BANCO":
                    comando = "Sem geracao solar: atende a demanda pelo banco de baterias"
                elif r["modo"] == "OCIOSO":
                    comando = "Sem veiculos conectados; banco em repouso"
            eventos.append({
                "hora": r["hora"],
                "modo": r["modo"],
                "comando": comando,
                "pv_kw": r["pv_kw"],
                "soc_%": r["soc_bateria_%"],
            })
            anterior = r["modo"]
    return eventos


def construir_html(resumo, sessoes, eventos, imgs) -> str:
    kpis = [
        ("Participacao renovavel", f"{resumo['participacao_renovavel_%']:.1f}", "%",
         f"{resumo['energia_solar_direta_kwh'] + resumo['energia_bateria_kwh']:.0f} kWh de origem solar"),
        ("Energia entregue", f"{resumo['energia_entregue_kwh']:.0f}", "kWh",
         f"{resumo['sessoes_concluidas']} sessoes concluidas"),
        ("Economia no dia", f"{resumo['economia_rs']:.0f}", "R$",
         f"contra R$ {resumo['custo_sem_greenvolt_rs']:.0f} so com a rede"),
        ("CO2 evitado", f"{resumo['co2_evitado_kg']:.1f}", "kg",
         "fator do SIN 0,0385 kgCO2/kWh"),
    ]
    kpi_html = "".join(
        f"""<div class="kpi"><p class="kpi-nome">{n}</p>
            <p class="kpi-valor">{v}<span>{u}</span></p>
            <p class="kpi-nota">{nota}</p></div>"""
        for n, v, u, nota in kpis
    )

    ev_html = "".join(
        f"""<tr><td class="mono">{e['hora']}</td>
            <td><span class="tag tag-{e['modo'].split()[0].lower().replace('%','').replace('+','')}">{e['modo']}</span></td>
            <td>{e['comando']}</td>
            <td class="mono num">{e['pv_kw']}</td>
            <td class="mono num">{e['soc_%']}</td></tr>"""
        for e in eventos
    )

    ses_html = "".join(
        f"""<tr><td class="mono">{s['ponto']}</td><td>{s['veiculo']}</td>
            <td class="mono">{s['chegada']}</td><td class="mono">{s['saida']}</td>
            <td class="mono num">{s['duracao_min']}</td>
            <td class="mono num">{s['soc_inicial_%']} &rarr; {s['soc_final_%']}</td>
            <td class="mono num">{s['energia_kwh']}</td></tr>"""
        for s in sessoes
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>GreenVolt - Painel Supervisorio</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600&family=Chivo+Mono:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  :root {{
    box-sizing: border-box;
    padding-top: env(safe-area-inset-top, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
    --fundo: {C_FUNDO};
    --painel: {C_PAINEL};
    --borda: #22343B;
    --solar: {C_SOLAR};
    --bateria: {C_BATERIA};
    --rede: {C_REDE};
    --alerta: {C_ALERTA};
    --texto: {C_TEXTO};
    --claro: #F3F7F8;
  }}
  *, *::before, *::after {{ box-sizing: inherit; }}
  body {{
    margin: 0; background: var(--fundo); color: var(--texto);
    font-family: Archivo, "Segoe UI", system-ui, sans-serif;
    font-size: 15px; line-height: 1.6;
  }}
  .wrap {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 72px; }}
  header {{ border-bottom: 1px solid var(--borda); padding-bottom: 20px; margin-bottom: 32px; }}
  h1 {{
    font-family: "Chivo Mono", ui-monospace, monospace; font-weight: 600;
    font-size: clamp(26px, 4vw, 38px); color: var(--claro); margin: 0 0 6px;
    letter-spacing: -0.02em;
  }}
  h1 b {{ color: var(--solar); font-weight: 600; }}
  header p {{ margin: 0; max-width: 62ch; }}
  .estado {{
    display: inline-flex; align-items: center; gap: 8px; margin-top: 14px;
    border: 1px solid var(--bateria); border-radius: 999px; padding: 4px 14px;
    color: var(--bateria); font-family: "Chivo Mono", monospace; font-size: 13px;
  }}
  .ponto {{ width: 8px; height: 8px; border-radius: 50%; background: var(--bateria); }}
  .kpis {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(215px, 1fr)); margin-bottom: 38px; }}
  .kpi {{ background: var(--painel); border: 1px solid var(--borda); border-left: 3px solid var(--solar); padding: 18px 20px; }}
  .kpi-nome {{ margin: 0; font-size: 13px; }}
  .kpi-valor {{
    font-family: "Chivo Mono", monospace; font-size: 40px; font-weight: 600;
    color: var(--claro); margin: 4px 0 2px; line-height: 1;
  }}
  .kpi-valor span {{ font-size: 15px; color: var(--texto); margin-left: 6px; font-weight: 400; }}
  .kpi-nota {{ margin: 0; font-size: 12.5px; opacity: .78; }}
  section {{ margin-bottom: 42px; }}
  h2 {{
    font-size: 15px; font-weight: 600; color: var(--claro); margin: 0 0 14px;
    padding-left: 10px; border-left: 3px solid var(--bateria);
  }}
  figure {{ margin: 0; background: var(--painel); border: 1px solid var(--borda); padding: 10px; }}
  figure img {{ display: block; width: 100%; max-width: 100%; height: auto; }}
  figcaption {{ font-size: 12.5px; padding: 10px 6px 4px; }}
  .duas {{ display: grid; gap: 18px; grid-template-columns: 1fr; }}
  @media (min-width: 880px) {{ .duas {{ grid-template-columns: 1.15fr .85fr; align-items: start; }} }}
  .tabela {{ overflow-x: auto; border: 1px solid var(--borda); background: var(--painel); }}
  table {{ border-collapse: collapse; width: 100%; min-width: 620px; font-size: 13.5px; }}
  th {{
    text-align: left; font-weight: 500; color: var(--claro); font-size: 12.5px;
    padding: 11px 14px; border-bottom: 1px solid var(--borda); white-space: nowrap;
  }}
  td {{ padding: 9px 14px; border-bottom: 1px solid #1B2C33; }}
  tr:last-child td {{ border-bottom: none; }}
  .mono {{ font-family: "Chivo Mono", monospace; font-size: 12.5px; }}
  .num {{ text-align: right; }}
  .tag {{ font-family: "Chivo Mono", monospace; font-size: 11.5px; padding: 2px 8px; border: 1px solid; white-space: nowrap; }}
  .tag-100 {{ color: var(--solar); border-color: var(--solar); }}
  .tag-solarbanco {{ color: var(--bateria); border-color: var(--bateria); }}
  .tag-hibrido {{ color: var(--rede); border-color: var(--rede); }}
  .tag-economia {{ color: #E5C76B; border-color: #E5C76B; }}
  .tag-ilhado {{ color: var(--alerta); border-color: var(--alerta); }}
  .tag-ocioso {{ color: var(--texto); border-color: var(--borda); }}
  footer {{ border-top: 1px solid var(--borda); padding-top: 18px; font-size: 12.5px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>GreenVolt <b>/</b> painel supervisorio</h1>
    <p>Ciclo de 24 horas do eletroposto, com 60 kWp de geracao fotovoltaica, banco de 100 kWh e tres pontos de recarga. Dados gerados por <span class="mono">src/simulador.py</span> a partir da telemetria dos sensores.</p>
    <div class="estado"><span class="ponto"></span>ciclo encerrado &middot; {len(eventos)} comandos automaticos emitidos</div>
  </header>

  <div class="kpis">{kpi_html}</div>

  <section>
    <h2>Despacho por fonte</h2>
    <figure>
      <img src="data:image/png;base64,{imgs['despacho']}" alt="Grafico de despacho energetico por fonte ao longo de 24 horas">
      <figcaption>A area amarela mostra a carga atendida diretamente pelo sol. A faixa vermelha marca a queda de rede das 13h05 as 13h35, quando o banco de baterias assumiu sozinho o atendimento.</figcaption>
    </figure>
  </section>

  <section class="duas">
    <figure>
      <img src="data:image/png;base64,{imgs['bateria']}" alt="Grafico do estado de carga da bateria e do aproveitamento do excedente solar">
      <figcaption>O banco carrega com o excedente do meio-dia e sustenta o horario de ponta.</figcaption>
    </figure>
    <figure>
      <img src="data:image/png;base64,{imgs['fontes']}" alt="Grafico de barras com a origem da energia entregue">
      <figcaption>Composicao final da energia entregue aos veiculos.</figcaption>
    </figure>
  </section>

  <section>
    <h2>Comandos automaticos do controlador</h2>
    <div class="tabela">
      <table>
        <thead><tr><th>Hora</th><th>Modo</th><th>Acao executada</th><th class="num">FV (kW)</th><th class="num">SoC (%)</th></tr></thead>
        <tbody>{ev_html}</tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Sessoes de recarga registradas</h2>
    <div class="tabela">
      <table>
        <thead><tr><th>Ponto</th><th>Veiculo</th><th>Entrada</th><th>Saida</th><th class="num">Min</th><th class="num">SoC (%)</th><th class="num">kWh</th></tr></thead>
        <tbody>{ses_html}</tbody>
      </table>
    </div>
  </section>

  <footer>
    GreenVolt &middot; Sprint 3 &middot; Joao Victor Canello Ferian, Gustavo Melo dos Santos e Joao Pedro Costenari Silva
  </footer>
</div>
</body>
</html>"""


def main() -> None:
    os.makedirs(DIR_DOCS, exist_ok=True)
    tele, sessoes, resumo = carregar()

    imgs = {
        "despacho": grafico_despacho(tele),
        "bateria": grafico_bateria(tele),
        "fontes": grafico_fontes(resumo),
    }

    eventos = extrair_eventos(tele)
    with open(os.path.join(DIR_DADOS, "eventos_automacao.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(eventos[0].keys()))
        w.writeheader()
        w.writerows(eventos)

    html = construir_html(resumo, sessoes, eventos, imgs)
    destino = os.path.join(DIR_DOCS, "dashboard.html")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Painel gerado em {destino}")
    print(f"Comandos automaticos registrados: {len(eventos)}")


if __name__ == "__main__":
    main()
