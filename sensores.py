"""
GreenVolt - Camada de Sensoriamento (IoT)
=========================================

Este modulo simula os sensores fisicos do eletroposto. Cada classe representa
um dispositivo real do projeto e entrega o mesmo tipo de grandeza que o
hardware entregaria ao controlador RISC-V:

    Piranometro / string box  -> irradiancia solar (W/m2)
    Medidor bidirecional      -> estado e tarifa da rede concessionaria
    Leitor OCPP do carregador -> chegada de veiculos e demanda de recarga

Todos os valores sao deterministicos (seed fixa), para que a demonstracao do
video e os dados do repositorio sejam exatamente reproduziveis.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Parametros da planta simulada
# --------------------------------------------------------------------------
POTENCIA_PICO_KWP = 60.0      # potencia instalada do arranjo fotovoltaico
EFICIENCIA_INVERSOR = 0.96    # rendimento do inversor hibrido GoodWe
IRRADIANCIA_STC = 1000.0      # condicao padrao de ensaio (W/m2)

NASCER_DO_SOL = 6.0           # hora decimal
POR_DO_SOL = 18.5             # hora decimal


@dataclass
class LeituraSolar:
    """Pacote de telemetria publicado pelo sensor de geracao."""
    irradiancia_wm2: float
    temperatura_modulo_c: float
    potencia_kw: float


class SensorSolar:
    """Piranometro + medicao de saida do inversor.

    A irradiancia segue uma curva senoidal entre o nascer e o por do sol,
    modulada por um fator de nebulosidade que caminha aleatoriamente
    (random walk) para reproduzir a passagem de nuvens.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._nebulosidade = 1.0

    def _atualizar_nuvens(self) -> None:
        # Caminhada aleatoria suave, limitada entre 35% e 100% de ceu limpo.
        self._nebulosidade += self._rng.uniform(-0.035, 0.035)
        self._nebulosidade = max(0.35, min(1.0, self._nebulosidade))

    def ler(self, hora: float) -> LeituraSolar:
        self._atualizar_nuvens()

        if hora < NASCER_DO_SOL or hora > POR_DO_SOL:
            return LeituraSolar(0.0, 22.0, 0.0)

        fase = (hora - NASCER_DO_SOL) / (POR_DO_SOL - NASCER_DO_SOL)
        irradiancia = IRRADIANCIA_STC * math.sin(math.pi * fase) * self._nebulosidade
        irradiancia = max(0.0, irradiancia)

        # Modulos aquecem e perdem rendimento: -0,4 %/degC acima de 25 degC.
        temperatura = 22.0 + irradiancia * 0.025
        perda_termica = max(0.0, (temperatura - 25.0) * 0.004)

        potencia = (
            POTENCIA_PICO_KWP
            * (irradiancia / IRRADIANCIA_STC)
            * (1 - perda_termica)
            * EFICIENCIA_INVERSOR
        )
        return LeituraSolar(round(irradiancia, 1), round(temperatura, 1), round(max(0.0, potencia), 2))


@dataclass
class LeituraRede:
    """Estado da conexao com a concessionaria."""
    disponivel: bool
    tarifa_rs_kwh: float
    horario_ponta: bool


class SensorRede:
    """Medidor bidirecional no ponto de entrega.

    Reproduz a tarifa branca (ponta entre 18h e 21h) e uma interrupcao
    programada de rede das 13h05 as 13h35, usada na demonstracao para provar
    que o eletroposto continua operando em modo ilhado com o banco de baterias.
    """

    TARIFA_FORA_PONTA = 0.75
    TARIFA_PONTA = 1.25
    FALHA_INICIO = 13.0833   # 13h05
    FALHA_FIM = 13.5833      # 13h35

    def ler(self, hora: float) -> LeituraRede:
        ponta = 18.0 <= hora < 21.0
        disponivel = not (self.FALHA_INICIO <= hora < self.FALHA_FIM)
        tarifa = self.TARIFA_PONTA if ponta else self.TARIFA_FORA_PONTA
        return LeituraRede(disponivel, tarifa, ponta)


@dataclass
class Veiculo:
    """Veiculo eletrico conectado a um ponto de recarga."""
    placa: str
    capacidade_kwh: float
    soc_inicial: float          # 0.0 a 1.0
    soc: float
    meta_soc: float
    potencia_max_kw: float      # limite do proprio carregador de bordo
    hora_chegada: float
    energia_recebida_kwh: float = 0.0

    def demanda_kw(self) -> float:
        """Potencia que o veiculo pediria se nao houvesse restricao."""
        if self.soc >= self.meta_soc:
            return 0.0
        # Acima de 80% de SoC a curva de recarga cai (protecao da bateria).
        fator = 1.0 if self.soc < 0.8 else 0.4
        return self.potencia_max_kw * fator

    def carregar(self, potencia_kw: float, passo_h: float) -> float:
        """Aplica energia ao veiculo e devolve o quanto foi efetivamente aceito."""
        energia = potencia_kw * passo_h
        espaco = max(0.0, (self.meta_soc - self.soc) * self.capacidade_kwh)
        energia = min(energia, espaco)
        self.soc += energia / self.capacidade_kwh
        self.energia_recebida_kwh += energia
        return energia


class GeradorDeChegadas:
    """Leitor OCPP dos carregadores: sorteia a chegada de veiculos.

    A probabilidade de chegada acompanha o perfil tipico de um eletroposto
    urbano, com picos no inicio da manha, no almoco e no fim da tarde.
    """

    FROTA = [
        ("BYD Dolphin", 44.9, 7.0),
        ("Renault Kwid E-Tech", 26.8, 7.0),
        ("Volvo EX30", 69.0, 50.0),
        ("Fiat 500e", 42.0, 22.0),
        ("Nissan Leaf", 40.0, 46.0),
        ("Toyota bZ4X", 71.4, 50.0),
    ]

    PERFIL_HORARIO = {
        6: 0.4, 7: 0.9, 8: 1.4, 9: 1.1, 10: 0.8, 11: 0.9,
        12: 1.3, 13: 1.2, 14: 0.7, 15: 0.6, 16: 0.8, 17: 1.2,
        18: 1.5, 19: 1.3, 20: 0.8, 21: 0.4, 22: 0.2,
    }

    def __init__(self, seed: int = 7) -> None:
        self._rng = random.Random(seed)
        self._contador = 0

    def sortear(self, hora: float, passo_h: float) -> Veiculo | None:
        intensidade = self.PERFIL_HORARIO.get(int(hora), 0.05)  # chegadas/hora
        if self._rng.random() > intensidade * passo_h:
            return None

        modelo, capacidade, potencia = self._rng.choice(self.FROTA)
        self._contador += 1
        soc_inicial = self._rng.uniform(0.12, 0.45)
        return Veiculo(
            placa=f"{modelo} #{self._contador:02d}",
            capacidade_kwh=capacidade,
            soc_inicial=soc_inicial,
            soc=soc_inicial,
            meta_soc=self._rng.choice([0.80, 0.80, 0.90]),
            potencia_max_kw=potencia,
            hora_chegada=hora,
        )
