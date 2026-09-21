"""
GreenVolt - Simulador de operacao (24 horas)
============================================

Executa um dia completo de operacao do eletroposto com passo de 1 minuto,
integrando sensores + controlador + carregadores, e grava:

    dados/telemetria_24h.csv    -> uma linha por minuto de operacao
    dados/sessoes_recarga.csv   -> uma linha por sessao de recarga concluida
    dados/resumo_diario.json    -> indicadores consolidados do dia

Uso:
    python src/simulador.py
"""

from __future__ import annotations

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controlador import BancoDeBaterias, Carregador, ControladorGreenVolt  # noqa: E402
from sensores import GeradorDeChegadas, SensorRede, SensorSolar  # noqa: E402

PASSO_MIN = 1
PASSO_H = PASSO_MIN / 60.0
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_DADOS = os.path.join(BASE, "dados")

# Fatores usados nos indicadores (parametrizaveis)
FATOR_CO2_REDE_KG_KWH = 0.0385   # fator medio do Sistema Interligado Nacional
TARIFA_INJECAO_RS_KWH = 0.42     # credito de energia injetada / evitada


def hhmm(hora: float) -> str:
    h = int(hora)
    m = int(round((hora - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    return f"{h:02d}:{m:02d}"


def executar(verboso: bool = True) -> dict:
    solar = SensorSolar(seed=42)
    rede = SensorRede()
    chegadas = GeradorDeChegadas(seed=7)
    bateria = BancoDeBaterias(capacidade_kwh=100.0, potencia_kw=30.0, soc_inicial=0.55)
    controlador = ControladorGreenVolt(bateria)

    carregadores = [
        Carregador("CP01", "AC 22 kW", 22.0),
        Carregador("CP02", "DC 50 kW", 50.0),
        Carregador("CP03", "DC 50 kW", 50.0),
    ]

    telemetria: list[dict] = []
    sessoes: list[dict] = []
    fila: list = []

    acc = {
        "solar_gerada": 0.0, "solar_carga": 0.0, "solar_bateria": 0.0,
        "solar_desperdicada": 0.0, "bateria_carga": 0.0, "rede_carga": 0.0,
        "entregue": 0.0, "custo_rs": 0.0, "custo_sem_sistema_rs": 0.0,
        "min_economia": 0, "min_ilhado": 0, "min_100_solar": 0,
    }

    os.makedirs(DIR_DADOS, exist_ok=True)

    for passo in range(int(24 * 60 / PASSO_MIN)):
        hora = passo * PASSO_H

        leitura_solar = solar.ler(hora)
        leitura_rede = rede.ler(hora)

        # --- chegada de veiculos e conexao aos carregadores ----------------
        novo = chegadas.sortear(hora, PASSO_H)
        if novo:
            fila.append(novo)
        for cp in carregadores:
            if not cp.ocupado() and fila:
                cp.veiculo = fila.pop(0)

        # --- demanda instantanea de cada ponto -----------------------------
        pedidos, prioridade = {}, {}
        for cp in carregadores:
            if cp.ocupado():
                pedidos[cp.id] = min(cp.veiculo.demanda_kw(), cp.potencia_max_kw)
                prioridade[cp.id] = cp.veiculo.soc   # menor SoC = atendido antes
            else:
                pedidos[cp.id] = 0.0
                prioridade[cp.id] = 9.9

        # --- ciclo de decisao ----------------------------------------------
        d = controlador.decidir(
            pv_kw=leitura_solar.potencia_kw,
            pedidos=pedidos,
            prioridade=prioridade,
            rede_disponivel=leitura_rede.disponivel,
            horario_ponta=leitura_rede.horario_ponta,
            passo_h=PASSO_H,
        )

        # --- aplica a energia nos veiculos e fecha sessoes -----------------
        for cp in carregadores:
            if not cp.ocupado():
                continue
            entregue = d.alocacao.get(cp.id, 0.0)
            cp.veiculo.carregar(entregue, PASSO_H)
            if cp.veiculo.soc >= cp.veiculo.meta_soc - 1e-4:
                v = cp.veiculo
                sessoes.append({
                    "ponto": cp.id,
                    "tipo": cp.tipo,
                    "veiculo": v.placa,
                    "chegada": hhmm(v.hora_chegada),
                    "saida": hhmm(hora),
                    "duracao_min": round((hora - v.hora_chegada) * 60),
                    "soc_inicial_%": round(v.soc_inicial * 100, 1),
                    "soc_final_%": round(v.soc * 100, 1),
                    "energia_kwh": round(v.energia_recebida_kwh, 2),
                })
                cp.veiculo = None

        # --- acumuladores e indicadores -------------------------------------
        acc["solar_gerada"] += leitura_solar.potencia_kw * PASSO_H
        acc["solar_carga"] += d.fonte_solar_kw * PASSO_H
        acc["solar_bateria"] += d.solar_para_bateria_kw * PASSO_H
        acc["solar_desperdicada"] += d.solar_desperdicado_kw * PASSO_H
        acc["bateria_carga"] += d.fonte_bateria_kw * PASSO_H
        acc["rede_carga"] += d.fonte_rede_kw * PASSO_H
        acc["entregue"] += d.potencia_entregue_kw * PASSO_H
        acc["custo_rs"] += d.fonte_rede_kw * PASSO_H * leitura_rede.tarifa_rs_kwh
        acc["custo_sem_sistema_rs"] += d.potencia_entregue_kw * PASSO_H * leitura_rede.tarifa_rs_kwh
        if d.modo == "ECONOMIA":
            acc["min_economia"] += 1
        if d.modo == "ILHADO":
            acc["min_ilhado"] += 1
        if d.modo in ("100% SOLAR", "SOLAR+BANCO"):
            acc["min_100_solar"] += 1

        telemetria.append({
            "hora": hhmm(hora),
            "irradiancia_wm2": leitura_solar.irradiancia_wm2,
            "pv_kw": leitura_solar.potencia_kw,
            "demanda_kw": round(sum(pedidos.values()), 2),
            "entregue_kw": d.potencia_entregue_kw,
            "solar_kw": d.fonte_solar_kw,
            "bateria_kw": d.fonte_bateria_kw,
            "rede_kw": d.fonte_rede_kw,
            "solar_p_bateria_kw": d.solar_para_bateria_kw,
            "curtailment_kw": d.solar_desperdicado_kw,
            "soc_bateria_%": round(bateria.soc * 100, 1),
            "rede_ok": int(leitura_rede.disponivel),
            "tarifa_rs_kwh": leitura_rede.tarifa_rs_kwh,
            "modo": d.modo,
            "cp01_kw": d.alocacao.get("CP01", 0.0),
            "cp02_kw": d.alocacao.get("CP02", 0.0),
            "cp03_kw": d.alocacao.get("CP03", 0.0),
        })

    # ---------------------------------------------------------------- saida
    with open(os.path.join(DIR_DADOS, "telemetria_24h.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(telemetria[0].keys()))
        w.writeheader()
        w.writerows(telemetria)

    if sessoes:
        with open(os.path.join(DIR_DADOS, "sessoes_recarga.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(sessoes[0].keys()))
            w.writeheader()
            w.writerows(sessoes)

    entregue = acc["entregue"]
    renovavel = acc["solar_carga"] + acc["bateria_carga"]
    resumo = {
        "energia_entregue_kwh": round(entregue, 2),
        "energia_solar_gerada_kwh": round(acc["solar_gerada"], 2),
        "energia_solar_direta_kwh": round(acc["solar_carga"], 2),
        "energia_bateria_kwh": round(acc["bateria_carga"], 2),
        "energia_rede_kwh": round(acc["rede_carga"], 2),
        "solar_armazenada_kwh": round(acc["solar_bateria"], 2),
        "curtailment_kwh": round(acc["solar_desperdicada"], 2),
        "participacao_renovavel_%": round(100 * renovavel / entregue, 1) if entregue else 0.0,
        "sessoes_concluidas": len(sessoes),
        "energia_media_por_sessao_kwh": round(
            sum(s["energia_kwh"] for s in sessoes) / len(sessoes), 2) if sessoes else 0.0,
        "duracao_media_sessao_min": round(
            sum(s["duracao_min"] for s in sessoes) / len(sessoes)) if sessoes else 0,
        "custo_energia_rs": round(acc["custo_rs"], 2),
        "custo_sem_greenvolt_rs": round(acc["custo_sem_sistema_rs"], 2),
        "economia_rs": round(acc["custo_sem_sistema_rs"] - acc["custo_rs"], 2),
        "co2_evitado_kg": round(renovavel * FATOR_CO2_REDE_KG_KWH, 2),
        "minutos_modo_economia": acc["min_economia"],
        "minutos_modo_ilhado": acc["min_ilhado"],
        "minutos_sem_rede_com_sol": acc["min_100_solar"],
        "soc_final_bateria_%": round(bateria.soc * 100, 1),
        "energia_ciclada_bateria_kwh": round(bateria.ciclos_kwh, 2),
    }

    with open(os.path.join(DIR_DADOS, "resumo_diario.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)

    if verboso:
        imprimir_relatorio(resumo, sessoes)

    return resumo


def imprimir_relatorio(r: dict, sessoes: list[dict]) -> None:
    linha = "=" * 62
    print(linha)
    print("  GREENVOLT | RELATORIO OPERACIONAL - CICLO DE 24 HORAS")
    print(linha)
    print(f"  Energia entregue aos veiculos ....... {r['energia_entregue_kwh']:>8.2f} kWh")
    print(f"    - fotovoltaica direta ............. {r['energia_solar_direta_kwh']:>8.2f} kWh")
    print(f"    - banco de baterias ............... {r['energia_bateria_kwh']:>8.2f} kWh")
    print(f"    - rede concessionaria ............. {r['energia_rede_kwh']:>8.2f} kWh")
    print(f"  Participacao renovavel .............. {r['participacao_renovavel_%']:>8.1f} %")
    print("-" * 62)
    print(f"  Geracao fotovoltaica total .......... {r['energia_solar_gerada_kwh']:>8.2f} kWh")
    print(f"  Excedente armazenado na bateria ..... {r['solar_armazenada_kwh']:>8.2f} kWh")
    print(f"  Excedente nao aproveitado ........... {r['curtailment_kwh']:>8.2f} kWh")
    print(f"  SoC final do banco .................. {r['soc_final_bateria_%']:>8.1f} %")
    print("-" * 62)
    print(f"  Sessoes de recarga concluidas ....... {r['sessoes_concluidas']:>8d}")
    print(f"  Energia media por sessao ............ {r['energia_media_por_sessao_kwh']:>8.2f} kWh")
    print(f"  Duracao media por sessao ............ {r['duracao_media_sessao_min']:>8d} min")
    print("-" * 62)
    print(f"  Custo com o GreenVolt ............... R$ {r['custo_energia_rs']:>7.2f}")
    print(f"  Custo so com a rede ................. R$ {r['custo_sem_greenvolt_rs']:>7.2f}")
    print(f"  Economia no dia ..................... R$ {r['economia_rs']:>7.2f}")
    print(f"  CO2 evitado ......................... {r['co2_evitado_kg']:>8.2f} kg")
    print("-" * 62)
    print(f"  Minutos sem consumir da rede ....... {r['minutos_sem_rede_com_sol']:>8d}")
    print(f"  Minutos em modo economia ............ {r['minutos_modo_economia']:>8d}")
    print(f"  Minutos em modo ilhado (rede fora) .. {r['minutos_modo_ilhado']:>8d}")
    print(linha)
    print("  ULTIMAS SESSOES REGISTRADAS")
    print(f"  {'PONTO':<6}{'VEICULO':<24}{'ENTRADA':<9}{'SAIDA':<9}{'kWh':>7}")
    for s in sessoes[-6:]:
        print(f"  {s['ponto']:<6}{s['veiculo']:<24}{s['chegada']:<9}{s['saida']:<9}{s['energia_kwh']:>7.2f}")
    print(linha)


if __name__ == "__main__":
    executar()
