# 1CCPO-Equipe02-Spr3-DSA

# Sprint 3 — Sistema de Gerenciamento de Estação de Recarga

## Integrantes
- João Victor Canello Ferian - RM573295
- Lucas Klein - RM570029
- Gustavo Melo dos Santos - RM573562
- João Pedro Costenari Silva - RM572260


---

# 1. Estrutura utilizada

Para representar cada sessão de recarga foi utilizada uma **classe chamada `Sessao`**.

A utilização de uma classe permite reunir, em um único objeto, todas as informações relacionadas a uma sessão de recarga.

A estrutura utilizada é:

```python
class Sessao:
    def __init__(self, id_sessao, veiculo, energia, tempo, custo,
                 carregador="AC", data="Nao informada",
                 horario="Nao informado", status="Concluida"):

        self.id = id_sessao
        self.veiculo = veiculo
        self.energia = energia
        self.tempo = tempo
        self.custo = custo
        self.carregador = carregador
        self.data = data
        self.horario = horario
        self.status = status
```

Cada objeto `Sessao` possui os seguintes atributos:

| Atributo     | Descrição                     |
| ------------ | ----------------------------- |
| `id`         | Identificação única da sessão |
| `veiculo`    | Identificação do veículo      |
| `energia`    | Energia consumida em kWh      |
| `tempo`      | Tempo de recarga em minutos   |
| `custo`      | Valor da sessão em reais      |
| `carregador` | Tipo de carregador utilizado  |
| `data`       | Data da recarga               |
| `horario`    | Horário da recarga            |
| `status`     | Situação da sessão            |

As sessões são armazenadas em uma lista:

```python
sessoes = []
```

Quando uma nova sessão é cadastrada, ela é adicionada à lista:

```python
sessoes.append(nova_sessao)
```

Dessa forma, o sistema consegue trabalhar com várias sessões simultaneamente.

---

# 2. Funcionamento geral

O programa possui um menu que permanece funcionando até que o usuário escolha a opção de encerramento.

O menu principal possui as seguintes opções:

```text
=============================================
       ESTACAO DE RECARGA
=============================================

1 - Nova sessao de recarga
2 - Listar sessoes
3 - Buscar sessao
4 - Ordenar sessoes
5 - Estatisticas
6 - Carregar dados de exemplo
7 - Analise de complexidade
8 - Encerrar
```

## Cadastro de sessões

A opção **1** permite cadastrar uma nova sessão.

O programa solicita informações como:

* ID;
* veículo;
* energia consumida;
* tempo de recarga;
* custo;
* tipo de carregador;
* data;
* horário;
* status.

Também são realizadas validações para evitar problemas nos dados.

Por exemplo, o sistema impede:

* IDs duplicados;
* energia negativa;
* tempo negativo;
* custo negativo;
* entradas numéricas inválidas.

---

## Listagem

A opção **2** apresenta todas as sessões cadastradas.

O programa também informa a quantidade total de sessões armazenadas.

---

## Busca

A opção **3** permite informar o ID de uma sessão e localizar seus dados.

Para realizar essa operação foi implementado manualmente o algoritmo de **Busca Sequencial**.

---

## Ordenação

A opção **4** permite ordenar as sessões.

O usuário pode escolher entre:

```text
1 - ID
2 - Energia consumida
3 - Custo
4 - Tempo de recarga
```

A ordenação é realizada utilizando o algoritmo **Bubble Sort**, implementado manualmente.
---

## Estatísticas

A opção **5** calcula informações utilizando as sessões armazenadas.

São apresentados:

* quantidade total de sessões;
* energia total fornecida;
* faturamento total;
* custo médio das sessões;
* maior consumo;
* menor consumo.

Exemplo:

```text
========== ESTATISTICAS ==========

Sessoes realizadas: 5
Energia fornecida: 165.40 kWh
Faturamento: R$ 205.50
Ticket medio: R$ 41.10
Maior consumo: 57.30 kWh
Menor consumo: 8.70 kWh
```

---

# 3. Algoritmo de busca utilizado

O algoritmo utilizado para localizar uma sessão é a **Busca Sequencial**.

A implementação foi feita manualmente:

```python
def busca_sequencial(sessoes, id_procurado):
    for i in range(len(sessoes)):
        if sessoes[i].id == id_procurado:
            return i

    return -1
```

A Busca Sequencial percorre os elementos da lista um por um.

Por exemplo, considerando:

```text
ID: 1
ID: 2
ID: 3
ID: 4
ID: 5
```

Se o usuário procurar o ID `4`, o algoritmo verifica:

```text
1 → não encontrado
2 → não encontrado
3 → não encontrado
4 → encontrado
```

Quando encontra o ID procurado, o algoritmo retorna a posição correspondente.

Caso percorra toda a lista e não encontre o ID, retorna:

```python
-1
```

Isso permite que o programa informe ao usuário que a sessão não foi encontrada.

---

# 4. Algoritmo de ordenação utilizado

Para ordenar as sessões foi utilizado o **Bubble Sort**.

O algoritmo também foi implementado manualmente.

A estrutura principal é:

```python
def bubble_sort(sessoes, criterio):
    n = len(sessoes)

    for i in range(n):
        trocou = False

        for j in range(n - 1 - i):

            if criterio == "id":
                deve_trocar = sessoes[j].id > sessoes[j + 1].id

            elif criterio == "energia":
                deve_trocar = sessoes[j].energia > sessoes[j + 1].energia

            elif criterio == "custo":
                deve_trocar = sessoes[j].custo > sessoes[j + 1].custo

            else:
                deve_trocar = sessoes[j].tempo > sessoes[j + 1].tempo

            if deve_trocar:
                sessoes[j], sessoes[j + 1] = (
                    sessoes[j + 1],
                    sessoes[j]
                )

                trocou = True

        if not trocou:
            break
```

O Bubble Sort compara elementos que estão lado a lado.

Quando o elemento da esquerda é maior que o elemento da direita, os dois são trocados.

Por exemplo:

```text
[5, 2, 4, 1]
```

Na primeira passagem, o algoritmo realiza comparações entre os elementos vizinhos até que os maiores valores sejam deslocados para o final.

Ao repetir o processo, a lista fica ordenada:

```text
[1, 2, 4, 5]
```

No projeto, o algoritmo pode comparar diferentes atributos da classe `Sessao`, permitindo ordenar por:

* ID;
* energia;
* custo;
* tempo.

---

# 5. Análise Big-O dos dois algoritmos

## Busca Sequencial — O(n)

A Busca Sequencial possui complexidade de **O(n)** no pior caso.

Isso ocorre porque, para uma lista contendo `n` sessões, o algoritmo pode precisar verificar todas as posições.

O trecho responsável pelo crescimento é:

```python
for i in range(len(sessoes)):
```

Se houver:

```text
10 sessões → até 10 verificações
100 sessões → até 100 verificações
1.000 sessões → até 1.000 verificações
```

---

## Bubble Sort — O(n²)

O Bubble Sort possui complexidade de **O(n²)** no pior caso.

Isso acontece porque o algoritmo utiliza dois laços para realizar as comparações:

```python
for i in range(n):
    for j in range(n - 1 - i):
```

O primeiro laço controla as passagens pela lista, enquanto o segundo realiza as comparações entre os elementos.

---

## Comparação das complexidades

| Algoritmo        | Complexidade no pior caso | Crescimento |
| ---------------- | ------------------------: | ----------- |
| Busca Sequencial |                  **O(n)** | Linear      |
| Bubble Sort      |                 **O(n²)** | Quadrático  |

A diferença pode ser observada conforme o número de sessões aumenta.

Na Busca Sequencial, se o número de sessões dobrar, o número máximo de verificações também cresce aproximadamente na mesma proporção.

No Bubble Sort, o crescimento é mais rápido porque existem comparações realizadas dentro de laços aninhados.
