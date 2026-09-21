# =============================================================================
# GreenVolt - Rotina de despacho energetico
# Arquitetura alvo: RV32IM (microcontrolador RISC-V do quadro de comando)
# =============================================================================
#
# Esta e a versao embarcada da funcao ControladorGreenVolt.decidir(), escrita
# em Assembly para rodar no laco de controle de 1 Hz do eletroposto. Toda a
# aritmetica usa potencia em WATTS (inteiros), o que elimina ponto flutuante:
# o mesmo ciclo de decisao cabe em poucas dezenas de instrucoes, sem FPU e
# sem alocacao dinamica. E exatamente esse ponto que liga o projeto ao
# conteudo de arquitetura de computadores: menos ciclos de CPU por decisao
# significa menos energia gasta pelo proprio sistema de controle.
#
# Entradas (registradores de argumento, convencao RISC-V):
#   a0 = potencia fotovoltaica disponivel        [W]
#   a1 = demanda total dos pontos de recarga     [W]
#   a2 = estado de carga do banco                [por mil: 0..1000]
#   a3 = rede disponivel                         [0 = falha, 1 = normal]
#   a4 = horario de ponta                        [0 = fora, 1 = ponta]
#   a5 = ponteiro para a struct de saida
#
# Struct de saida (4 palavras de 32 bits):
#   offset 0  -> potencia vinda do sol     [W]
#   offset 4  -> potencia vinda da bateria [W]
#   offset 8  -> potencia vinda da rede    [W]
#   offset 12 -> modo de operacao          [codigo]
#
# Retorno:
#   a0 = codigo do modo de operacao
# =============================================================================

        .section .rodata
        .equ DEMANDA_CONTRATADA, 45000   # limite do ponto de entrega        [W]
        .equ BATERIA_POT_MAX,    30000   # limite do inversor do banco       [W]
        .equ SOC_MINIMO,           200   # reserva tecnica (20,0 %)
        .equ SOC_ILHAMENTO,        100   # reserva usada so com a rede fora

        .equ MODO_OCIOSO,            0
        .equ MODO_SOLAR,             1   # 100 % fotovoltaico
        .equ MODO_HIBRIDO,           2   # solar + rede
        .equ MODO_ECONOMIA,          3   # rateio de potencia entre os pontos
        .equ MODO_ILHADO,            4   # opera sem a rede

        .section .text
        .globl greenvolt_despacho
        .align 2

# -----------------------------------------------------------------------------
# greenvolt_despacho
# -----------------------------------------------------------------------------
greenvolt_despacho:
        addi    sp, sp, -16
        sw      s0, 12(sp)
        sw      s1,  8(sp)
        sw      s2,  4(sp)
        sw      s3,  0(sp)

        li      s0, 0                   # s0 = contribuicao solar   [W]
        li      s1, 0                   # s1 = contribuicao bateria [W]
        li      s2, 0                   # s2 = contribuicao rede    [W]
        mv      s3, a1                  # s3 = deficit a cobrir     [W]

        # -- Sem demanda: planta ociosa, excedente vai para o banco -----------
        beqz    a1, planta_ociosa

# -----------------------------------------------------------------------------
# Prioridade 1 - energia fotovoltaica direta
# solar = min(pv, demanda)
# -----------------------------------------------------------------------------
prioridade_solar:
        blt     a0, a1, solar_parcial
        mv      s0, a1                  # o sol cobre tudo
        li      s3, 0
        j       verifica_deficit
solar_parcial:
        mv      s0, a0                  # o sol cobre parte
        sub     s3, a1, a0

verifica_deficit:
        beqz    s3, fecha_sem_rede      # deficit zero -> 100 % solar

# -----------------------------------------------------------------------------
# Prioridade 2 - banco de baterias
# O banco entra quando a rede caiu, no horario de ponta, ou para impedir que
# a demanda ultrapasse a potencia contratada.
# -----------------------------------------------------------------------------
prioridade_bateria:
        beqz    a3, usa_bateria         # rede fora -> obrigatorio
        bnez    a4, usa_bateria         # horario de ponta -> preferencial

        li      t0, DEMANDA_CONTRATADA
        ble     s3, t0, prioridade_rede # deficit cabe no contrato -> poupa banco
        sub     t1, s3, t0              # so o excedente do contrato vem do banco
        mv      t2, t1
        j       limita_bateria

usa_bateria:
        mv      t2, s3                  # tenta cobrir todo o deficit

limita_bateria:
        # Escolhe o piso de SoC conforme a rede esteja disponivel ou nao
        li      t3, SOC_MINIMO
        bnez    a3, checa_soc
        li      t3, SOC_ILHAMENTO
checa_soc:
        ble     a2, t3, prioridade_rede # banco na reserva -> nao descarrega

        li      t4, BATERIA_POT_MAX     # satura no limite do inversor
        ble     t2, t4, aplica_bateria
        mv      t2, t4
aplica_bateria:
        mv      s1, t2
        sub     s3, s3, t2              # abate do deficit

# -----------------------------------------------------------------------------
# Prioridade 3 - rede concessionaria, limitada a demanda contratada
# -----------------------------------------------------------------------------
prioridade_rede:
        beqz    s3, fecha_operacao
        beqz    a3, fecha_operacao      # rede indisponivel: nada a fazer aqui

        li      t0, DEMANDA_CONTRATADA
        mv      t1, s3
        ble     t1, t0, aplica_rede
        mv      t1, t0                  # trunca no contrato
aplica_rede:
        mv      s2, t1
        sub     s3, s3, t1

# -----------------------------------------------------------------------------
# Classificacao do modo de operacao
# -----------------------------------------------------------------------------
fecha_operacao:
        beqz    a3, modo_ilhado         # rede fora tem precedencia
        bnez    s3, modo_economia       # sobrou deficit -> racionamento
        beqz    s2, modo_solar          # nao usou rede -> 100 % solar
        li      t0, MODO_HIBRIDO
        j       escreve_saida

fecha_sem_rede:
        beqz    a3, modo_ilhado
modo_solar:
        li      t0, MODO_SOLAR
        j       escreve_saida
modo_economia:
        li      t0, MODO_ECONOMIA
        j       escreve_saida
modo_ilhado:
        li      t0, MODO_ILHADO
        j       escreve_saida
planta_ociosa:
        li      t0, MODO_OCIOSO
        beqz    a3, modo_ilhado

# -----------------------------------------------------------------------------
# Publica o resultado na struct e retorna
# -----------------------------------------------------------------------------
escreve_saida:
        sw      s0,  0(a5)              # solar
        sw      s1,  4(a5)              # bateria
        sw      s2,  8(a5)              # rede
        sw      t0, 12(a5)              # modo
        mv      a0, t0

        lw      s3,  0(sp)
        lw      s2,  4(sp)
        lw      s1,  8(sp)
        lw      s0, 12(sp)
        addi    sp, sp, 16
        ret

# -----------------------------------------------------------------------------
# rateia_potencia
# Distribui a potencia disponivel entre os pontos de recarga. A lista de
# pedidos ja chega ordenada por SoC crescente (o veiculo mais descarregado
# recebe primeiro), montada pela camada OCPP.
#
#   a0 = ponteiro para o vetor de pedidos     [W]
#   a1 = ponteiro para o vetor de saida       [W]
#   a2 = numero de pontos
#   a3 = potencia total disponivel            [W]
# -----------------------------------------------------------------------------
        .globl rateia_potencia
        .align 2
rateia_potencia:
        li      t0, 0                   # indice
laco_rateio:
        bge     t0, a2, fim_rateio
        slli    t1, t0, 2               # deslocamento = indice * 4 bytes
        add     t2, a0, t1
        lw      t3, 0(t2)               # pedido do ponto atual

        ble     t3, a3, entrega_total
        mv      t3, a3                  # entrega so o que resta
entrega_total:
        add     t4, a1, t1
        sw      t3, 0(t4)
        sub     a3, a3, t3              # atualiza o saldo disponivel

        addi    t0, t0, 1
        bnez    a3, laco_rateio         # saldo zerado encerra o laco

        # Zera os pontos que nao foram atendidos neste ciclo
zera_restantes:
        bge     t0, a2, fim_rateio
        slli    t1, t0, 2
        add     t4, a1, t1
        sw      zero, 0(t4)
        addi    t0, t0, 1
        j       zera_restantes

fim_rateio:
        li      a0, 0
        ret
