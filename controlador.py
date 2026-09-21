"""
GreenVolt - Controlador de Despacho Energetico
==============================================

Nucleo logico do projeto. E a versao em Python da rotina que roda no
microcontrolador RISC-V (ver firmware/decisao_riscv.s). A cada ciclo de
controle ele recebe a telemetria dos sensores e decide, em ordem de
prioridade:

    1. Atender a demanda com energia fotovoltaica.
    2. Completar com o banco de baterias (obrigatorio se a rede caiu ou se
       estamos em horario de ponta).
    3. Completar com a rede, respeitando a demanda contratada.
    4. Se ainda faltar potencia, entrar em MODO ECONOMIA e ratear a energia
       disponivel entre os veiculos, priorizando quem tem menor SoC.

O excedente fotovoltaico carrega a bateria; o que sobra e registrado como
curtailment (energia que seria desperdicada sem armazenamento).
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEMANDA_CONTRATADA_KW = 45.0     # limite do ponto de entrega da concessionaria
SOC_MINIMO_BATERIA = 0.20        # reserva tecnica do banco
SOC_RESERVA_ILHAMENTO = 0.10     # so pode ser usado com a rede fora


class BancoDeBaterias:
    """BESS de apoio: armazena excedente solar e sustenta o modo ilhado."""

    def __init__(self, capacidade_kwh: float = 100.0, potencia_kw: float = 30.0,
                 soc_inicial: float = 0.55, eficiencia: float = 0.94) -> None:
        self.capacidade_kwh = capacidade_kwh
        self.potencia_kw = potencia_kw
        self.soc = soc_inicial
        self.eficiencia = eficiencia
        self.ciclos_kwh = 0.0

    @property
    def energia_kwh(self) -> float:
        return self.soc * self.capacidade_kwh

    def descarregar(self, potencia_pedida_kw: float, passo_h: float,
                    piso_soc: float) -> float:
        """Entrega potencia ate o limite do inversor e do SoC de reserva."""
        disponivel_kwh = max(0.0, (self.soc - piso_soc) * self.capacidade_kwh)
        potencia = min(potencia_pedida_kw, self.potencia_kw, disponivel_kwh / passo_h)
        potencia = max(0.0, potencia)
        self.soc -= (potencia * passo_h) / self.capacidade_kwh
        self.ciclos_kwh += potencia * passo_h
        return potencia

    def carregar(self, potencia_ofertada_kw: float, passo_h: float) -> float:
        """Absorve excedente solar ate encher. Devolve a potencia aceita."""
        espaco_kwh = max(0.0, (1.0 - self.soc) * self.capacidade_kwh)
        potencia = min(potencia_ofertada_kw, self.potencia_kw, espaco_kwh / (passo_h * self.eficiencia))
        potencia = max(0.0, potencia)
        self.soc += (potencia * passo_h * self.eficiencia) / self.capacidade_kwh
        return potencia


@dataclass
class Carregador:
    """Ponto de recarga controlado via OCPP."""
    id: str
    tipo: str
    potencia_max_kw: float
    veiculo: object | None = None

    def ocupado(self) -> bool:
        return self.veiculo is not None


@dataclass
class Decisao:
    """Saida de um ciclo de controle - e isto que vai para a telemetria."""
    modo: str
    potencia_entregue_kw: float = 0.0
    fonte_solar_kw: float = 0.0
    fonte_bateria_kw: float = 0.0
    fonte_rede_kw: float = 0.0
    solar_para_bateria_kw: float = 0.0
    solar_desperdicado_kw: float = 0.0
    alocacao: dict = field(default_factory=dict)


class ControladorGreenVolt:
    """Maquina de decisao do eletroposto."""

    def __init__(self, bateria: BancoDeBaterias,
                 demanda_contratada_kw: float = DEMANDA_CONTRATADA_KW) -> None:
        self.bateria = bateria
        self.demanda_contratada_kw = demanda_contratada_kw

    # -- utilitario ---------------------------------------------------------
    @staticmethod
    def _ratear(pedidos: dict[str, float], disponivel_kw: float,
                prioridade: dict[str, float]) -> dict[str, float]:
        """Distribui a potencia disponivel: quem tem menor SoC e servido antes."""
        alocacao = {cp: 0.0 for cp in pedidos}
        restante = disponivel_kw
        for cp in sorted(pedidos, key=lambda c: prioridade.get(c, 1.0)):
            entrega = min(pedidos[cp], restante)
            alocacao[cp] = round(entrega, 3)
            restante -= entrega
            if restante <= 1e-6:
                break
        return alocacao

    # -- ciclo de controle --------------------------------------------------
    def decidir(self, pv_kw: float, pedidos: dict[str, float],
                prioridade: dict[str, float], rede_disponivel: bool,
                horario_ponta: bool, passo_h: float) -> Decisao:

        demanda_kw = sum(pedidos.values())

        # Sem carros conectados: todo o sol vai para a bateria.
        if demanda_kw <= 1e-6:
            para_bateria = self.bateria.carregar(pv_kw, passo_h)
            return Decisao(
                modo="OCIOSO" if rede_disponivel else "ILHADO",
                solar_para_bateria_kw=round(para_bateria, 2),
                solar_desperdicado_kw=round(max(0.0, pv_kw - para_bateria), 2),
                alocacao={cp: 0.0 for cp in pedidos},
            )

        # 1) Energia solar direta -------------------------------------------
        solar_para_carga = min(pv_kw, demanda_kw)
        falta = demanda_kw - solar_para_carga

        # 2) Banco de baterias ----------------------------------------------
        bateria_kw = 0.0
        if falta > 1e-6:
            piso = SOC_RESERVA_ILHAMENTO if not rede_disponivel else SOC_MINIMO_BATERIA
            # Com a rede disponivel fora de ponta, a bateria so entra para
            # evitar ultrapassar a demanda contratada.
            if not rede_disponivel or horario_ponta:
                bateria_kw = self.bateria.descarregar(falta, passo_h, piso)
            elif falta > self.demanda_contratada_kw:
                bateria_kw = self.bateria.descarregar(falta - self.demanda_contratada_kw,
                                                      passo_h, piso)
            falta -= bateria_kw

        # 3) Rede concessionaria --------------------------------------------
        rede_kw = 0.0
        if falta > 1e-6 and rede_disponivel:
            rede_kw = min(falta, self.demanda_contratada_kw)
            falta -= rede_kw

        entregue = solar_para_carga + bateria_kw + rede_kw

        # 4) Modo de operacao e rateio --------------------------------------
        if not rede_disponivel:
            modo = "ILHADO"
        elif falta > 1e-6:
            modo = "ECONOMIA"
        elif rede_kw <= 1e-6 and bateria_kw > 1e-6:
            modo = "SOLAR+BANCO"
        elif rede_kw <= 1e-6:
            modo = "100% SOLAR"
        else:
            modo = "HIBRIDO"

        alocacao = self._ratear(pedidos, entregue, prioridade)

        # 5) Excedente solar -> bateria -> curtailment -----------------------
        excedente = max(0.0, pv_kw - solar_para_carga)
        para_bateria = self.bateria.carregar(excedente, passo_h) if excedente > 1e-6 else 0.0

        return Decisao(
            modo=modo,
            potencia_entregue_kw=round(entregue, 3),
            fonte_solar_kw=round(solar_para_carga, 3),
            fonte_bateria_kw=round(bateria_kw, 3),
            fonte_rede_kw=round(rede_kw, 3),
            solar_para_bateria_kw=round(para_bateria, 3),
            solar_desperdicado_kw=round(max(0.0, excedente - para_bateria), 3),
            alocacao=alocacao,
        )
