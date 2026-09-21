class Sessao:
    def __init__(self, id_sessao, veiculo, energia, tempo, custo,
                 carregador="AC", data="Nao informada", horario="Nao informado",
                 status="Concluida"):
        self.id = id_sessao
        self.veiculo = veiculo
        self.energia = energia
        self.tempo = tempo
        self.custo = custo
        self.carregador = carregador
        self.data = data
        self.horario = horario
        self.status = status

    def exibir(self):
        print(f"ID: {self.id}")
        print(f"Veiculo: {self.veiculo}")
        print(f"Energia: {self.energia:.2f} kWh")
        print(f"Tempo: {self.tempo:.2f} minutos")
        print(f"Custo: R$ {self.custo:.2f}")
        print(f"Carregador: {self.carregador}")
        print(f"Data: {self.data}")
        print(f"Horario: {self.horario}")
        print(f"Status: {self.status}")

sessoes = []

def ler_inteiro(mensagem, minimo=None):
    while True:
        try:
            valor = int(input(mensagem))
            if minimo is not None and valor < minimo:
                print(f"Digite um valor maior ou igual a {minimo}.")
                continue
            return valor
        except ValueError:
            print("Entrada invalida. Digite um numero inteiro.")


def ler_float(mensagem, minimo=None):
    while True:
        try:
            valor = float(input(mensagem).replace(",", "."))
            if minimo is not None and valor < minimo:
                print(f"Digite um valor maior ou igual a {minimo}.")
                continue
            return valor
        except ValueError:
            print("Entrada invalida. Digite um numero.")


def ler_texto(mensagem, padrao=None):
    while True:
        valor = input(mensagem).strip()
        if valor:
            return valor
        if padrao is not None:
            return padrao
        print("Este campo nao pode ficar vazio.")


def id_existe(sessoes, id_sessao):
    for sessao in sessoes:
        if sessao.id == id_sessao:
            return True
    return False


def cadastrar_sessao(sessoes):
    print("\n========== NOVA SESSAO ==========")

    while True:
        id_sessao = ler_inteiro("ID da sessao: ", 1)
        if id_existe(sessoes, id_sessao):
            print("Esse ID ja esta cadastrado. Escolha outro.")
        else:
            break

    veiculo = ler_texto("Identificacao do veiculo: ")
    energia = ler_float("Energia consumida (kWh): ", 0)
    tempo = ler_float("Tempo de recarga (minutos): ", 0)
    custo = ler_float("Custo da sessao (R$): ", 0)
    carregador = ler_texto("Tipo de carregador [AC/DC]: ", "AC")
    data = ler_texto("Data [opcional]: ", "Nao informada")
    horario = ler_texto("Horario [opcional]: ", "Nao informado")
    status = ler_texto("Status [Concluida/Em andamento/Cancelada]: ", "Concluida")

    nova_sessao = Sessao(
        id_sessao, veiculo, energia, tempo, custo,
        carregador, data, horario, status
    )
    sessoes.append(nova_sessao)

    print("\nSessao cadastrada com sucesso!")


def listar_sessoes(sessoes):
    print("\n========== SESSOES ==========")

    if len(sessoes) == 0:
        print("Nenhuma sessao cadastrada.")
        return

    print(f"Total de sessoes: {len(sessoes)}\n")

    for sessao in sessoes:
        print("-" * 40)
        sessao.exibir()

    print("-" * 40)


def busca_sequencial(sessoes, id_procurado):
    for i in range(len(sessoes)):
        if sessoes[i].id == id_procurado:
            return i
    return -1


def buscar_sessao(sessoes):
    print("\n========== BUSCAR SESSAO ==========")

    if len(sessoes) == 0:
        print("Nenhuma sessao cadastrada.")
        return

    id_procurado = ler_inteiro("Digite o ID da sessao: ", 1)
    indice = busca_sequencial(sessoes, id_procurado)

    if indice == -1:
        print("Sessao nao encontrada.")
    else:
        print("\nSessao encontrada:")
        print("-" * 40)
        sessoes[indice].exibir()
        print("-" * 40)


def bubble_sort(sessoes, criterio):
    n = len(sessoes)

    for i in range(n):
        trocou = False

        for j in range(n - 1 - i):
            a = sessoes[j]
            b = sessoes[j + 1]

            if criterio == "id":
                deve_trocar = a.id > b.id
            elif criterio == "energia":
                deve_trocar = a.energia > b.energia
            elif criterio == "custo":
                deve_trocar = a.custo > b.custo
            else:
                deve_trocar = a.tempo > b.tempo

            if deve_trocar:
                sessoes[j], sessoes[j + 1] = sessoes[j + 1], sessoes[j]
                trocou = True

        if not trocou:
            break


def ordenar_sessoes(sessoes):
    print("\n========== ORDENAR SESSOES ==========")

    if len(sessoes) == 0:
        print("Nenhuma sessao cadastrada.")
        return

    print("1 - ID")
    print("2 - Energia consumida")
    print("3 - Custo")
    print("4 - Tempo de recarga")

    opcao = ler_inteiro("Escolha o criterio: ", 1)

    if opcao == 1:
        criterio = "id"
    elif opcao == 2:
        criterio = "energia"
    elif opcao == 3:
        criterio = "custo"
    elif opcao == 4:
        criterio = "tempo"
    else:
        print("Opcao invalida.")
        return

    bubble_sort(sessoes, criterio)
    print("Sessoes ordenadas com Bubble Sort.")

    listar_sessoes(sessoes)


def mostrar_estatisticas(sessoes):
    print("\n========== ESTATISTICAS ==========")

    quantidade = len(sessoes)

    if quantidade == 0:
        print("Nenhuma sessao cadastrada.")
        return

    energia_total = 0
    faturamento_total = 0
    maior_consumo = sessoes[0].energia
    menor_consumo = sessoes[0].energia

    for sessao in sessoes:
        energia_total += sessao.energia
        faturamento_total += sessao.custo

        if sessao.energia > maior_consumo:
            maior_consumo = sessao.energia

        if sessao.energia < menor_consumo:
            menor_consumo = sessao.energia

    custo_medio = faturamento_total / quantidade

    print(f"Sessoes realizadas: {quantidade}")
    print(f"Energia fornecida: {energia_total:.2f} kWh")
    print(f"Faturamento: R$ {faturamento_total:.2f}")
    print(f"Ticket medio: R$ {custo_medio:.2f}")
    print(f"Maior consumo: {maior_consumo:.2f} kWh")
    print(f"Menor consumo: {menor_consumo:.2f} kWh")


def carregar_dados_exemplo(sessoes):
    exemplos = [
        Sessao(1, "EV-001", 32.50, 75, 39.90, "AC", "21/09/2026", "08:30"),
        Sessao(2, "EV-002", 48.20, 95, 58.40, "DC", "21/09/2026", "10:15"),
        Sessao(3, "EV-003", 18.70, 42, 24.90, "AC", "21/09/2026", "12:00"),
        Sessao(4, "EV-004", 57.30, 110, 69.90, "DC", "21/09/2026", "14:20"),
        Sessao(5, "EV-005", 8.70, 25, 12.40, "AC", "21/09/2026", "16:10"),
    ]

    for exemplo in exemplos:
        if not id_existe(sessoes, exemplo.id):
            sessoes.append(exemplo)

    print("Dados de exemplo carregados.")


def mostrar_complexidade():
    print("\n========== ANALISE DE COMPLEXIDADE ==========")
    print("1. Busca Sequencial")
    print("   - Percorre a lista ate encontrar o ID ou chegar ao fim.")
    print("   - Pior caso: O(n).")
    print("   - O crescimento e linear em relacao ao numero de sessoes.")
    print()
    print("2. Bubble Sort")
    print("   - Utiliza dois lacos para comparar elementos adjacentes.")
    print("   - Pior caso: O(n^2).")
    print("   - O numero de comparacoes cresce quadraticamente.")
    print()
    print("A analise considera o codigo efetivamente utilizado no projeto.")


def menu():
    while True:
        print("\n" + "=" * 45)
        print("       ESTACAO DE RECARGA")
        print("=" * 45)
        print("1 - Nova sessao de recarga")
        print("2 - Listar sessoes")
        print("3 - Buscar sessao")
        print("4 - Ordenar sessoes")
        print("5 - Estatisticas")
        print("6 - Carregar dados de exemplo")
        print("7 - Analise de complexidade")
        print("8 - Encerrar")
        print("=" * 45)

        opcao = ler_inteiro("Escolha: ")

        if opcao == 1:
            cadastrar_sessao(sessoes)
        elif opcao == 2:
            listar_sessoes(sessoes)
        elif opcao == 3:
            buscar_sessao(sessoes)
        elif opcao == 4:
            ordenar_sessoes(sessoes)
        elif opcao == 5:
            mostrar_estatisticas(sessoes)
        elif opcao == 6:
            carregar_dados_exemplo(sessoes)
        elif opcao == 7:
            mostrar_complexidade()
        elif opcao == 8:
            print("Programa encerrado.")
            break
        else:
            print("Opcao invalida. Escolha uma opcao do menu.")

menu()
