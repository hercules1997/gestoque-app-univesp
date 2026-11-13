# StokOS ML — Especificação viva

## O que faz
Painel em português para pequenas empresas acompanharem produtos, entradas e saídas, alertas de estoque e recomendações de reposição. O dashboard exibe KPIs, saúde do estoque, histórico recente e previsão de demanda.

## Dados
- `users`: contas demo com perfil `admin` ou `operator`, senha armazenada como hash SHA-256.
- `products`: SKU, nome, categoria, custos/preços, estoque, mínimo, ponto de pedido e fornecedor.
- `movements`: produto, entrada/saída/ajuste, quantidade, motivo, usuário e data.
- `sessions`: cookie httpOnly de sessão.

## Lógica de previsão
Ver `DOCUMENTACAO_TCC.md` §8–10 (fonte de verdade para o TCC). Resumo: série DIÁRIA de saídas dos últimos 28 dias (zeros nos dias sem venda) → WMA com pesos 1..28 (recente pesa mais) × fator de tendência T = 1 + 0,2·(μ7−μ21)/μ21 limitado a [0,8; 1,25]. Estoque-alvo = ⌈ŷ·14⌉ + mínimo; sugestão = alvo − estoque; Urgente se estoque 0 ou cobertura < 7 dias. O gráfico do dashboard é um backtest walk-forward dos últimos 7 dias completos (previsão feita só com dados anteriores a cada dia). Seed: 60 dias de vendas sintéticas, random.Random(42), reexecutar o seed restaura os saldos e recria o histórico.

## Fluxos
Login demo → dashboard → produtos → cadastrar/remover (admin) ou movimentar → previsão → importar/exportar CSV. O operador consulta e registra movimentações, sem excluir produtos ou importar dados.

## Alertas de compra por fornecedor
- `GET /api/alerts/suppliers` (qualquer usuário logado): produtos com `stock <= reorder_point`, agrupados por fornecedor, ordenados por nº de urgentes. Cada item traz quantidade sugerida (maior entre a sugestão do modelo e `reorder_point - stock + min_stock`), custo estimado e prioridade (Urgente se `stock <= min_stock` ou se o modelo prevê ruptura em menos de 7 dias).
- Dashboard: card "Avisos por fornecedor"; o botão "Ver produtos a repor" abre Produtos filtrado por aquele fornecedor + ponto de reposição (com banner "Limpar filtro").
- Sino do cabeçalho: contador de produtos no ponto de reposição; ao clicar, rola até o card.
- Ao registrar uma saída que faz o produto cruzar o ponto de reposição, aparece um toast de aviso citando o fornecedor.
- Os botões "Registrar movimento" (dashboard) e "Movimentar" (produtos) abrem a tela Movimentações já com o produto escolhido.
- Seed: Tech Distribuidora (ELEC-001), Armazém Central (ALIM-008), Auto Center Brasil (AUTO-220) estão no ponto de reposição.

## Integrações
Nenhuma externa. CSV é processado no navegador e enviado ao backend para importação. Exportações são CSV geradas no navegador.
## Alertas de compra por fornecedor
- `GET /api/alerts/suppliers` (requer login): produtos com `stock <= reorder_point`, agrupados por fornecedor. Cada item traz a quantidade sugerida (o maior valor entre a reposição prevista e `reorder_point - stock + min_stock`), o custo estimado e a prioridade (Urgente se `stock <= min_stock` ou se a previsão marcar urgente). Grupos ordenados por número de urgentes.
- Dashboard: cartão "Avisos por fornecedor"; o botão "Ver produtos a repor" abre Produtos filtrado por fornecedor + ponto de reposição (faixa "Limpar filtro").
- O sino do topo mostra o total de produtos no ponto de reposição e leva ao cartão de alertas.
- Ao registrar uma saída que faz o estoque cruzar o ponto de pedido, aparece um aviso (toast) com o nome do fornecedor.
- A tabela de Produtos mostra a coluna Fornecedor e "Ponto de pedido" com a etiqueta REPOR.
- "Registrar movimento" (dashboard) e "Movimentar" (produtos) abrem a tela de Movimentações já com o produto escolhido.

## Nomes demo
- Admin: Rafael Luiz · Operador: Rafael Lima. O nome no menu e na saudação vem do usuário logado.
