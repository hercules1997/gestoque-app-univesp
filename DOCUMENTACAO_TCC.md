# Gestoque — Documentação Técnica

**Sistema web de apoio à decisão para gestão inteligente de estoque em pequenas empresas**

> Documento de apoio ao Trabalho de Conclusão de Curso. Descreve a arquitetura, as tecnologias, o modelo de previsão de demanda, a metodologia de validação e os resultados obtidos. Todas as fórmulas e números deste documento correspondem exatamente ao código-fonte entregue.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Arquitetura do sistema](#2-arquitetura-do-sistema)
3. [Tecnologias utilizadas](#3-tecnologias-utilizadas)
4. [Estrutura do código-fonte](#4-estrutura-do-código-fonte)
5. [Modelo de dados](#5-modelo-de-dados)
6. [Perfis de usuário e permissões](#6-perfis-de-usuário-e-permissões)
7. [Funcionalidades](#7-funcionalidades)
8. [Modelo de previsão de demanda](#8-modelo-de-previsão-de-demanda)
9. [Regras de decisão de reposição](#9-regras-de-decisão-de-reposição)
10. [Validação do modelo e resultados](#10-validação-do-modelo-e-resultados)
11. [API REST](#11-api-rest)
12. [Segurança](#12-segurança)
13. [Como executar o projeto](#13-como-executar-o-projeto)
14. [Limitações e trabalhos futuros](#14-limitações-e-trabalhos-futuros)

---

## 1. Visão geral

### 1.1 Problema

Pequenas empresas costumam controlar o estoque de forma manual (planilhas ou caderno) e decidir as compras pela intuição. Isso gera dois tipos de prejuízo:

- **Ruptura**: o produto acaba e a venda é perdida;
- **Excesso**: o capital fica parado em mercadoria que gira pouco.

### 1.2 Objetivo

Desenvolver um sistema web que **registre o estoque**, **preveja a demanda futura** de cada produto a partir do histórico de vendas e **recomende quanto e quando comprar**, apresentando essas informações em um painel voltado à tomada de decisão.

### 1.3 Escopo implementado

| Módulo | Descrição |
|---|---|
| Autenticação | Login com dois perfis: Administrador e Operador |
| Dashboard | Indicadores (KPIs), recomendação prioritária, gráfico previsto x real, saúde do estoque, alertas |
| Produtos | Cadastro, consulta, busca e exclusão |
| Movimentações | Registro de entradas e saídas com atualização automática do saldo |
| Previsão e compras | Previsão de demanda para 7, 15, 30 ou 60 dias e sugestão de compra por produto |
| Alertas por fornecedor | Produtos no ponto de pedido agrupados por fornecedor, com custo estimado do pedido |
| Importação e exportação | Importação de produtos via CSV e exportação do estoque em CSV |

---

## 2. Arquitetura do sistema

O sistema segue uma arquitetura **cliente-servidor em três camadas**: interface (frontend), regras de negócio (backend) e persistência (banco de dados). As camadas se comunicam por uma **API REST** que troca dados em JSON.

```
┌──────────────────────────────┐
│  NAVEGADOR (Frontend)        │   React 19 + TypeScript
│  - Telas do painel           │   Tailwind CSS + shadcn/ui
│  - Gráficos e tabelas        │   TanStack Query (cache)
└──────────────┬───────────────┘
               │ HTTP / JSON  (rotas /api/...)
               │ sessão via cookie httpOnly
┌──────────────▼───────────────┐
│  SERVIDOR (Backend)          │   Python 3.11 + FastAPI
│  - Autenticação e permissões │   Pydantic v2 (validação)
│  - Regras de estoque         │
│  - MODELO DE PREVISÃO        │   ← núcleo do trabalho
│  - Recomendações e alertas   │
└──────────────┬───────────────┘
               │ driver assíncrono (Motor)
┌──────────────▼───────────────┐
│  BANCO DE DADOS              │   MongoDB 7
│  users · sessions ·          │
│  products · movements        │
└──────────────────────────────┘
```

**Decisão de projeto importante:** toda a lógica de previsão e de recomendação roda **no servidor**. O navegador apenas exibe os resultados. Isso garante que todos os usuários vejam os mesmos números e que a regra de negócio não possa ser alterada pelo cliente.

---

## 3. Tecnologias utilizadas

| Camada | Tecnologia | Versão | Por que foi escolhida |
|---|---|---|---|
| Frontend | React | 19.2 | Biblioteca de interfaces baseada em componentes, amplamente adotada no mercado |
| Frontend | TypeScript | 7.0 | Tipagem estática: erros de tipo são detectados antes da execução |
| Frontend | Vite | 8.1 | Servidor de desenvolvimento e build rápidos |
| Frontend | Tailwind CSS | 4.3 | Estilização utilitária, com consistência visual |
| Frontend | shadcn/ui (Base UI) | — | Componentes acessíveis (diálogos, selects, tabelas) |
| Frontend | TanStack Query | 5.101 | Cache e sincronização dos dados vindos da API |
| Backend | Python | 3.11 | Linguagem de referência em ciência de dados e estatística |
| Backend | FastAPI | 0.141 | Framework web assíncrono, com validação automática e documentação da API |
| Backend | Pydantic | v2 | Validação dos dados de entrada e saída |
| Backend | Motor | 3.7 | Driver assíncrono do MongoDB para Python |
| Banco | MongoDB | 7.0 | Banco orientado a documentos, flexível para o modelo de dados |

**Linguagens:** Python (backend e modelo de previsão), TypeScript/TSX (frontend), CSS (estilos) e HTML (página base).

---

## 4. Estrutura do código-fonte

```
app/
├── backend/
│   ├── server.py               # Inicialização da aplicação FastAPI e registro das rotas
│   ├── seed.py                 # Gera os dados de demonstração (usuários, produtos, histórico)
│   ├── requirements.txt        # Dependências Python
│   ├── lib/
│   │   ├── db.py               # Conexão com o MongoDB e criação dos índices
│   │   └── dates.py            # Utilitário de data do servidor
│   ├── models/
│   │   └── inventory.py        # Modelos de dados (Pydantic): Produto, Movimentação, Previsão...
│   └── routers/
│       └── inventory.py        # ★ Rotas da API, MODELO DE PREVISÃO e regras de reposição
├── frontend/
│   ├── index.html
│   └── src/
│       ├── App.tsx             # Rotas do frontend e sistema de notificações
│       ├── index.css           # Tema visual (cores, fontes, layout)
│       ├── lib/api.ts          # Camada de comunicação com a API
│       └── pages/Home.tsx      # ★ Todas as telas do painel
└── DOCUMENTACAO_TCC.md         # Este documento
```

Os arquivos marcados com ★ concentram a lógica central do trabalho.

---

## 5. Modelo de dados

O banco possui quatro coleções. Os identificadores são UUIDs (texto), e não o `ObjectId` padrão do MongoDB, para facilitar a troca de dados em JSON.

### 5.1 `products` — Produtos

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | texto (UUID) | Identificador único |
| `sku` | texto | Código do produto (único, em maiúsculas) |
| `name` | texto | Nome comercial |
| `category` | texto | Categoria (ex.: Eletrônicos) |
| `unit_cost` | número | Custo unitário de compra (R$) |
| `sale_price` | número | Preço de venda (R$) |
| `stock` | inteiro | Saldo atual em estoque |
| `min_stock` | inteiro | Estoque mínimo (estoque de segurança) |
| `reorder_point` | inteiro | Ponto de pedido: ao atingi-lo, o produto deve ser reposto |
| `supplier` | texto | Fornecedor |

### 5.2 `movements` — Movimentações

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | texto (UUID) | Identificador |
| `product_id` / `product_sku` / `product_name` | texto | Produto movimentado |
| `type` | `entrada` · `saida` · `ajuste` | Tipo de movimento |
| `quantity` | inteiro (> 0) | Quantidade |
| `reason` | texto | Motivo (ex.: venda, compra do fornecedor) |
| `user_name` / `user_role` | texto | Quem registrou |
| `created_at` | data/hora (UTC) | Momento do registro |

As **saídas** formam a série histórica de demanda usada pelo modelo de previsão.

### 5.3 `users` e `sessions`

- `users`: nome, e-mail, perfil (`admin` ou `operator`) e o hash da senha.
- `sessions`: token de sessão aleatório, usuário e data de expiração. Um **índice TTL** do MongoDB apaga automaticamente as sessões expiradas.

---

## 6. Perfis de usuário e permissões

| Ação | Administrador | Operador |
|---|:---:|:---:|
| Ver dashboard, previsões e alertas | ✅ | ✅ |
| Consultar produtos e exportar CSV | ✅ | ✅ |
| Registrar entradas e saídas | ✅ | ✅ |
| Cadastrar produtos | ✅ | ❌ |
| Excluir produtos | ✅ | ❌ |
| Importar produtos via CSV | ✅ | ❌ |
| Ver a tela de usuários e permissões | ✅ | ❌ |

As permissões são verificadas **no servidor**: um operador que tente cadastrar ou importar produtos diretamente pela API recebe o erro **403 (Proibido)**. A interface também oculta esses botões para o operador, mas a proteção real está no backend.

---

## 7. Funcionalidades

### 7.1 Dashboard — Central de decisão
- **KPIs:** valor total em estoque (Σ estoque × custo), itens em nível crítico, produtos com risco de falta em 7 dias e giro médio diário.
- **Recomendação prioritária:** o produto mais urgente, com a quantidade e o investimento sugeridos.
- **Gráfico "Previsto x real":** compara, nos últimos 7 dias completos, a venda real com o que o modelo havia previsto (ver seção 10).
- **Alertas de reposição**, **saúde do estoque** (distribuição em Saudável, Baixo, Crítico e Excesso) e **movimentações recentes**.
- **Avisos por fornecedor:** produtos no ponto de pedido agrupados por fornecedor, com custo do pedido. O botão "Ver produtos a repor" abre a lista já filtrada.

### 7.2 Notificações
- O **sino** no topo mostra quantos produtos estão no ponto de pedido.
- Ao registrar uma **saída** que leva o estoque ao ponto de pedido (ou abaixo dele), o sistema exibe um aviso com o nome do fornecedor a ser contatado.

### 7.3 Produtos, Movimentações, Previsões e Importação
Telas de cadastro, registro de movimentos, tabela de sugestões de compra (com horizonte de 7, 15, 30 ou 60 dias) e importação e exportação de planilhas CSV.

---

## 8. Modelo de previsão de demanda

### 8.1 Classificação do modelo

O sistema usa um **modelo estatístico de previsão de séries temporais**: uma **Média Móvel Ponderada (WMA, *Weighted Moving Average*) com fator de tendência limitado**.

> **Nota sobre o termo "Machine Learning":** o modelo implementado é estatístico e determinístico. Ele não passa por uma etapa de treinamento com ajuste de parâmetros, como uma rede neural ou uma regressão. A escolha foi intencional, pelos seguintes motivos:
> 1. pequenas empresas têm **pouco histórico de dados**, o que torna modelos complexos instáveis e sujeitos a superajuste (*overfitting*);
> 2. o modelo é **explicável**: o gestor consegue entender por que o sistema sugeriu comprar X unidades;
> 3. ele serve de **linha de base** (*baseline*) para comparar modelos de aprendizado de máquina no futuro (ver seção 14).
>
> No texto do TCC, recomenda-se descrevê-lo como "técnicas estatísticas de previsão de demanda" ou "modelo preditivo estatístico", que é a descrição tecnicamente precisa.

### 8.2 Passo 1: montar a série diária de demanda

Para cada produto, o sistema soma as quantidades de **saída** por dia nos últimos **N = 28 dias**. Os dias sem venda entram como **zero**. O resultado é uma série ordenada do dia mais antigo (d₁) ao mais recente (d₂₈):

```
D = [d₁, d₂, ..., d₂₈]
```

### 8.3 Passo 2: média móvel ponderada

Cada dia recebe um peso linear: o dia mais antigo pesa 1 e o mais recente pesa 28. Assim, o comportamento recente influencia mais a previsão.

```
          Σ (i · dᵢ)        i = 1..28
WMA  =  ─────────────
            Σ i              Σ i = 1 + 2 + ... + 28 = 406
```

### 8.4 Passo 3: fator de tendência

O fator compara a média dos **últimos 7 dias** (μ₇) com a média dos **21 dias anteriores** (μ₂₁):

```
T = 1 + 0,2 · (μ₇ − μ₂₁) / μ₂₁          limitado ao intervalo [0,8 ; 1,25]
```

- Se as vendas recentes crescem, T > 1 e a previsão sobe.
- O coeficiente **0,2** suaviza a reação: um aumento de 50% nas vendas recentes eleva a previsão em 10%.
- Os **limites [0,8 ; 1,25]** impedem que uma única semana atípica (uma promoção, por exemplo) distorça a previsão.
- Casos especiais: se μ₂₁ = 0 e μ₇ > 0, usa-se T = 1,25; se não houve nenhuma venda em 28 dias, a previsão é 0.

### 8.5 Passo 4: previsão final

```
Demanda diária prevista  ŷ = WMA · T
Demanda no horizonte  H  = ⌈ ŷ · H ⌉        H ∈ {7, 15, 30, 60} dias
```

### 8.6 Parâmetros do modelo

| Parâmetro | Valor | Constante no código |
|---|---|---|
| Janela histórica | 28 dias | `WINDOW_DAYS` |
| Janela da tendência recente | 7 dias | `TREND_RECENT_DAYS` |
| Sensibilidade da tendência | 0,2 | `TREND_SENSITIVITY` |
| Limites do fator de tendência | 0,8 a 1,25 | `TREND_MIN`, `TREND_MAX` |

Implementação: função `wma_trend_forecast` em `backend/routers/inventory.py`.

### 8.7 Exemplo resolvido (dados reais do sistema)

Produto **Fone Bluetooth Pulse (ELEC-001)**, com estoque de 6 un., estoque mínimo de 10, ponto de pedido de 14, custo de R$ 48,90 e fornecedor Tech Distribuidora.

**Série dos últimos 28 dias (do mais antigo ao mais recente):**
```
0 2 1 2 0 2 2 3 0 0 0 2 1 1 1 0 4 0 1 0 0 1 1 1 2 2 0 0
```

| Etapa | Cálculo | Resultado |
|---|---|---|
| Soma ponderada Σ(i·dᵢ) | — | 389 |
| WMA | 389 / 406 | 0,9581 un./dia |
| μ₇ (últimos 7 dias) | 7 / 7 | 1,0000 |
| μ₂₁ (21 dias anteriores) | 22 / 21 | 1,0476 |
| Fator de tendência T | 1 + 0,2 · (1,0000 − 1,0476) / 1,0476 | 0,9909 |
| **Demanda diária ŷ** | 0,9581 × 0,9909 | **0,95 un./dia** |
| Demanda prevista em 7 dias | ⌈0,95 × 7⌉ | 7 un. |
| Demanda prevista em 30 dias | ⌈0,95 × 30⌉ | 29 un. |

---

## 9. Regras de decisão de reposição

A partir da demanda prevista ŷ, o sistema aplica as regras abaixo para cada produto.

| Indicador | Fórmula | Exemplo (ELEC-001) |
|---|---|---|
| **Cobertura** (dias até acabar) | ⌊ estoque / ŷ ⌋ | ⌊6 / 0,95⌋ = **6 dias** |
| **Estoque-alvo** | ⌈ ŷ · 14 ⌉ + estoque mínimo | ⌈13,3⌉ + 10 = **24 un.** |
| **Sugestão de compra** | máx(0, estoque-alvo − estoque) | 24 − 6 = **18 un.** |
| **Custo estimado** | sugestão × custo unitário | 18 × 48,90 = **R$ 880,20** |

O **estoque-alvo** cobre 14 dias de demanda prevista mais o estoque de segurança (estoque mínimo).

**Prioridade da compra:**
- **Urgente:** estoque zerado ou cobertura menor que 7 dias. *(ELEC-001: cobertura de 6 dias, portanto Urgente.)*
- **Normal:** há sugestão de compra, mas sem urgência.
- **Baixa:** não há necessidade de compra.

**Status do estoque** (usado no dashboard):
- **Crítico:** estoque = 0;
- **Baixo:** estoque ≤ estoque mínimo;
- **Excesso:** estoque > 4 × estoque mínimo;
- **Saudável:** nos demais casos.

**Alertas por fornecedor:** entram no alerta os produtos com **estoque ≤ ponto de pedido**. A quantidade sugerida no alerta é o maior valor entre a sugestão do modelo e (ponto de pedido − estoque + estoque mínimo), garantindo ao menos 1 unidade. Os fornecedores são ordenados pelo número de itens urgentes.

---

## 10. Validação do modelo e resultados

### 10.1 Metodologia: backtest com janela deslizante (*walk-forward*)

Para medir a qualidade da previsão sem "olhar o futuro", o modelo foi avaliado da seguinte forma:

1. para cada dia **t** do período de teste, o modelo calcula a previsão usando **apenas os 28 dias anteriores a t**;
2. a previsão é comparada com a venda real ocorrida;
3. o processo se repete, deslizando a janela dia a dia.

O mesmo procedimento alimenta o gráfico **"Previsto x real"** do dashboard, que mostra a validação do modelo diretamente na interface.

### 10.2 Métricas

- **MAE** (Erro Absoluto Médio): média de |real − previsto|, em unidades.
- **WAPE** (Erro Percentual Absoluto Ponderado): Σ|real − previsto| / Σ real. É preferível ao MAPE porque não "explode" nos dias de venda zero.
- **Viés:** Σ(previsto − real) / Σ real. Um valor negativo indica que o modelo subestima a demanda, o que aumenta o risco de ruptura.

### 10.3 Modelos comparados

| Modelo | Descrição |
|---|---|
| **WMA + tendência** | Modelo do sistema |
| WMA sem tendência | Ablação: o mesmo modelo sem o fator T |
| Média simples (28 dias) | *Baseline* clássico |
| Ingênuo | Prevê que amanhã será igual a hoje |

### 10.4 Resultados

**Base de teste:** 6 produtos × 30 dias de teste, com janelas deslizantes de 7 dias (o horizonte usado para as compras).

| Modelo | WAPE (todos) | Viés (todos) | WAPE (produtos com tendência) | Viés (com tendência) |
|---|:---:|:---:|:---:|:---:|
| **WMA + tendência (sistema)** | **22,9%** | **−5,2%** | 32,4% | +2,3% |
| WMA sem tendência | 21,6% | −7,4% | 30,6% | −0,8% |
| Média simples 28 dias | 21,4% | −8,7% | 28,6% | −2,9% |
| Ingênuo (ontem) | 66,8% | −1,7% | 89,9% | +1,9% |

Na previsão dia a dia (180 previsões), o erro absoluto médio (MAE) foi de 0,92 un. para o WMA com tendência, 0,88 un. para a média simples e 1,19 un. para o modelo ingênuo.

### 10.5 Discussão

1. **Os modelos baseados em média são cerca de 3 vezes mais precisos que o modelo ingênuo** (WAPE de aproximadamente 22% contra 67%). Isso justifica usar um modelo estatístico em vez de "repetir o que vendeu ontem".
2. **O fator de tendência reduz a subestimação:** o viés passa de −8,7% (média simples) para −5,2%. Na gestão de estoque, subestimar a demanda é o erro mais caro, porque causa ruptura e perda de venda. O modelo do sistema é o menos enviesado entre os modelos de média.
3. **Em compensação, o fator de tendência aumenta um pouco a variação do erro** (WAPE cerca de 1,5 p.p. maior). Com baixo volume de vendas (0,4 a 2,8 un./dia), o ruído aleatório domina, e a diferença entre os três modelos de média fica dentro da margem de variação. Trata-se de uma **troca entre viés e variância**, e não de uma superioridade absoluta.
4. **Os parâmetros não foram ajustados para "vencer" o teste.** Como os dados são sintéticos, calibrar o modelo neles seria superajuste. Os parâmetros foram fixados *a priori* com base em critérios de negócio.
5. O erro **diário** é naturalmente alto (WAPE de aproximadamente 65%), porque vender 0, 1 ou 2 unidades num dia é quase aleatório. No horizonte **semanal**, que é o relevante para a decisão de compra, o erro cai para cerca de 22%.

### 10.6 Dados de demonstração

Os dados foram gerados pelo script `backend/seed.py`, com **semente aleatória fixa (42)**, de modo que os resultados são **reproduzíveis**:
- 60 dias de vendas diárias para 6 produtos de 4 categorias;
- venda diária ~ Normal(λ, √λ), arredondada para inteiro ≥ 0, sendo λ a taxa base do produto;
- fins de semana com +35% de movimento;
- tendência de alta no Fone Bluetooth (+60% ao longo do período) e de queda na Jaqueta (−50%, fim de estação);
- compras do fornecedor a cada 21 dias.

> **Atenção:** os resultados validam o **funcionamento correto** do modelo, mas não substituem uma validação com dados reais de uma empresa (ver seção 14).

Para reproduzir a validação, gere os dados com `python seed.py` e repita o procedimento da seção 10.1 usando as funções `daily_outgoing`, `series_ending` e `wma_trend_forecast`.

---

## 11. API REST

Todas as rotas usam o prefixo `/api` e exigem sessão ativa, exceto o login. A documentação interativa gerada pelo FastAPI fica em `/docs` quando o backend roda localmente.

| Método | Rota | Perfil | Descrição |
|---|---|---|---|
| POST | `/api/auth/login` | público | Autentica o usuário e cria a sessão (cookie) |
| GET | `/api/auth/me` | logado | Dados do usuário atual |
| POST | `/api/auth/logout` | logado | Encerra a sessão |
| GET | `/api/dashboard` | logado | KPIs, distribuição, série previsto x real, alertas |
| GET | `/api/products` | logado | Lista os produtos |
| POST | `/api/products` | admin | Cadastra um produto (409 se o SKU já existir) |
| DELETE | `/api/products/{id}` | admin | Exclui um produto |
| GET | `/api/movements` | logado | Histórico de movimentações |
| POST | `/api/movements` | logado | Registra uma entrada, saída ou ajuste (422 se a saída deixar o estoque negativo) |
| GET | `/api/forecast?days=7` | logado | Previsão e sugestões (days ∈ {7, 15, 30, 60}) |
| GET | `/api/alerts/suppliers` | logado | Produtos no ponto de pedido, agrupados por fornecedor |
| POST | `/api/import/products` | admin | Importa ou atualiza produtos em lote |

**Códigos de resposta usados:** 200 (sucesso), 204 (sem conteúdo), 401 (não autenticado), 403 (sem permissão), 404 (não encontrado), 409 (conflito), 422 (dados inválidos).

---

## 12. Segurança

- **Sessões em cookie `httpOnly`:** o token não fica acessível ao JavaScript do navegador, o que reduz o risco de roubo por XSS. As sessões expiram em 7 dias.
- **Autorização no servidor:** cada rota verifica o perfil do usuário (seção 6).
- **Validação de entrada:** todos os dados recebidos passam pelos modelos Pydantic. Dados inválidos são rejeitados com erro 422 antes de chegar à regra de negócio.
- **Integridade do estoque:** o sistema não permite saídas que deixem o estoque negativo.
- **Limitação conhecida:** as senhas são armazenadas com hash **SHA-256 sem *salt***, o que é suficiente para uma demonstração, mas não para produção. Para uso real, o recomendado é **bcrypt** ou **Argon2** (ver seção 14).

---

## 13. Como executar o projeto

### 13.1 Pré-requisitos
- Python 3.11 ou superior
- Node.js 20 ou superior e Yarn
- MongoDB 7 rodando localmente (porta 27017)

### 13.2 Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> Se a instalação falhar no pacote `emergentintegrations`, remova essa linha do `requirements.txt`. Ele pertence à plataforma de desenvolvimento e **não é usado** por este sistema.

Crie o arquivo `backend/.env`:
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="stokos"
CORS_ORIGINS="*"
```

Gere os dados de demonstração e inicie o servidor:
```bash
python seed.py
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### 13.3 Frontend

```bash
cd frontend
yarn install
yarn dev                                 # abre em http://localhost:3000
```

O frontend redireciona as chamadas `/api` para o backend na porta 8001 (configurado em `vite.config.ts`).

> Os pacotes `@emergentbase/overlay` e `@emergentbase/visual-edits` são ferramentas da plataforma de desenvolvimento e não fazem parte da lógica do sistema. Se não instalarem, remova-os do `package.json` e retire o plugin `visualEdits` do `vite.config.ts`.

### 13.4 Acesso de demonstração

| Perfil | Nome | E-mail | Senha |
|---|---|---|---|
| Administrador | Rafael Luiz | `admin@gestoque.com` | `Admin123!` |
| Operador | Rafael Lima | `operador@gestoque.com` | `Operador123!` |

> Executar `python seed.py` novamente **restaura os saldos de estoque** dos 6 produtos de demonstração e **recria o histórico de vendas**. As movimentações registradas manualmente são preservadas.

---

## 14. Limitações e trabalhos futuros

### 14.1 Limitações
1. **Dados sintéticos:** o modelo foi validado com dados simulados. Falta uma validação com o histórico real de uma empresa.
2. **Modelo estatístico, não treinado:** não há aprendizado de parâmetros a partir dos dados (seção 8.1).
3. **Sazonalidade não modelada:** o efeito de fim de semana e as datas sazonais (Natal, Black Friday) não entram explicitamente no modelo.
4. **Prazo de entrega do fornecedor (*lead time*) não considerado:** o estoque-alvo usa 14 dias fixos para todos os produtos.
5. **Importação apenas em CSV:** arquivos Excel (.xlsx) precisam ser salvos como CSV antes de importar.
6. **Tela de usuários ilustrativa:** os perfis existem e funcionam, mas o cadastro de novos usuários pela interface não foi implementado.
7. **Senhas com SHA-256 sem *salt*** (seção 12).

### 14.2 Trabalhos futuros
1. **Modelos de Machine Learning comparados ao baseline atual:** suavização exponencial de Holt-Winters (tendência e sazonalidade), regressão com variáveis de calendário e modelos de *gradient boosting* (por exemplo, LightGBM), usando o backtest da seção 10 como protocolo de comparação.
2. **Ajuste automático de parâmetros** (janela, sensibilidade da tendência) por validação cruzada temporal, quando houver dados reais suficientes.
3. **Estoque de segurança estatístico:** ES = z · σ · √L, considerando a variabilidade da demanda (σ), o nível de serviço desejado (z) e o *lead time* (L) de cada fornecedor.
4. **Cadastro de fornecedores** com prazo de entrega e geração automática de pedidos de compra.
5. **Envio real de alertas** por e-mail ou WhatsApp ao atingir o ponto de pedido.
6. **Senhas com bcrypt ou Argon2** e cadastro de usuários pela interface.
