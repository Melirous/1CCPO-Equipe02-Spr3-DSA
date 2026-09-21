"""
GreenVolt - Testes de integracao do controlador
===============================================

Cada cenario abaixo verifica uma das regras de despacho descritas no README e
implementadas tanto em controlador.py quanto em firmware/decisao_riscv.s.
E o roteiro usado na demonstracao do video.

Uso:
    python src/teste_integracao.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controlador import BancoDeBaterias, ControladorGreenVolt  # noqa: E402

PASSO_H = 1 / 60


def cenario(nome, pv, pedidos, soc, rede_ok, ponta, esperado):
    bateria = BancoDeBaterias(soc_inicial=soc)
    ctrl = ControladorGreenVolt(bateria)
    prioridade = {cp: 0.3 + i * 0.1 for i, cp in enumerate(pedidos)}
    d = ctrl.decidir(pv, pedidos, prioridade, rede_ok, ponta, PASSO_H)

    ok = d.modo == esperado
    marca = "OK  " if ok else "FALHA"
    print(f"[{marca}] {nome}")
    print(f"         demanda {sum(pedidos.values()):>6.1f} kW | FV {pv:>6.1f} kW"
          f" | solar {d.fonte_solar_kw:>6.1f} | bateria {d.fonte_bateria_kw:>6.1f}"
          f" | rede {d.fonte_rede_kw:>6.1f} | modo {d.modo}")
    return ok


def main() -> None:
    print("=" * 74)
    print("  GREENVOLT | VALIDACAO DAS REGRAS DE DESPACHO")
    print("=" * 74)

    resultados = [
        cenario("Sol cobre toda a demanda -> nao aciona a rede",
                pv=45.0, pedidos={"CP01": 22.0, "CP02": 15.0}, soc=0.60,
                rede_ok=True, ponta=False, esperado="100% SOLAR"),

        cenario("Sol insuficiente fora de ponta -> complementa com a rede",
                pv=12.0, pedidos={"CP01": 22.0, "CP02": 20.0}, soc=0.60,
                rede_ok=True, ponta=False, esperado="HIBRIDO"),

        cenario("Horario de ponta -> bateria assume o complemento",
                pv=5.0, pedidos={"CP01": 22.0}, soc=0.80,
                rede_ok=True, ponta=True, esperado="SOLAR+BANCO"),

        cenario("Queda de rede -> opera ilhado pelo banco",
                pv=8.0, pedidos={"CP01": 22.0, "CP02": 10.0}, soc=0.75,
                rede_ok=False, ponta=False, esperado="ILHADO"),

        cenario("Demanda acima do contrato e banco na reserva -> modo economia",
                pv=4.0, pedidos={"CP01": 22.0, "CP02": 50.0, "CP03": 50.0}, soc=0.20,
                rede_ok=True, ponta=False, esperado="ECONOMIA"),

        cenario("Sem veiculos -> excedente solar carrega o banco",
                pv=30.0, pedidos={"CP01": 0.0}, soc=0.50,
                rede_ok=True, ponta=False, esperado="OCIOSO"),
    ]

    # Verificacoes adicionais de conservacao de energia e limite contratado
    bateria = BancoDeBaterias(soc_inicial=0.20)
    ctrl = ControladorGreenVolt(bateria)
    pedidos = {"CP01": 22.0, "CP02": 50.0, "CP03": 50.0}
    d = ctrl.decidir(4.0, pedidos, {c: 0.3 for c in pedidos}, True, False, PASSO_H)

    limite_ok = d.fonte_rede_kw <= ctrl.demanda_contratada_kw + 1e-6
    print(f"[{'OK  ' if limite_ok else 'FALHA'}] Rede nunca ultrapassa a demanda contratada"
          f" ({d.fonte_rede_kw:.1f} kW <= {ctrl.demanda_contratada_kw:.1f} kW)")

    soma = sum(d.alocacao.values())
    balanco_ok = abs(soma - d.potencia_entregue_kw) < 1e-3
    print(f"[{'OK  ' if balanco_ok else 'FALHA'}] Balanco de potencia fecha"
          f" (rateio {soma:.2f} kW = entregue {d.potencia_entregue_kw:.2f} kW)")

    resultados += [limite_ok, balanco_ok]

    print("=" * 74)
    print(f"  {sum(resultados)}/{len(resultados)} verificacoes aprovadas")
    print("=" * 74)
    sys.exit(0 if all(resultados) else 1)


if __name__ == "__main__":
    main()
