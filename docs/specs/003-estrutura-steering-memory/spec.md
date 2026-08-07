# Estrutura docs/steering/ e docs/memory/

## Tipo
[x] Melhoria

## Status
[x] implementado (relocação de arquivo + `constitution.md` criados; reescrita
de conteúdo do arquivo movido continua pendente — ver [[001-atualizar-docs-arquitetura]])

## Resumo
Cria `docs/steering/` e `docs/memory/` neste repositório, espelhando a
convenção do projeto de referência (`Aluguel_Pinheira`), e reconcilia isso com
a decisão anterior da spec 001 de manter `docs/architecture.md` na raiz.

## Contexto
A spec [[001-atualizar-docs-arquitetura]] (`## Design → Decisões de
arquitetura`) havia decidido manter `docs/architecture.md` na raiz de `docs/`,
tratando a criação de `docs/steering/` como fora do escopo daquela spec. Esta
spec 003 reverte especificamente essa decisão de **posicionamento** — não
invalida o resto da 001: o requirement funcional de reescrever o conteúdo do
arquivo (hoje ainda desatualizado, descrevendo Airflow/Postgres/Airbyte como
caminho ativo) continua válido e pendente, só muda o destino final do arquivo
reescrito.

## Requirements (EARS)

### Funcionais
- THE system SHALL mover `docs/architecture.md` para
  `docs/steering/weather-analytics.md`, preservando histórico git (`git mv`)
  e sem reescrever o conteúdo — a reescrita continua sendo requirement da spec
  001, ainda não aplicado.
- THE system SHALL criar `docs/memory/constitution.md` com as regras
  não-negociáveis já em uso nesta sessão: nunca aceitar/expor credencial em
  texto no chat, commits sempre locais sem `git push` automático, validação
  funcional real antes de aceitar uma correção como concluída, e o formato de
  spec EARS em `docs/specs/`.
- THE system SHALL atualizar a spec 001 para refletir o novo path
  (`docs/steering/weather-analytics.md`) nos requirements funcionais que
  citavam `docs/architecture.md`, e marcar a decisão de arquitetura original
  (manter o arquivo na raiz) como superada, com nota apontando para esta spec.

### Não-funcionais
- A relocação SHALL preservar 100% do conteúdo do arquivo movido — nenhuma
  edição de texto nesta spec, só mudança de path.
- Nenhum arquivo criado em `docs/steering/` ou `docs/memory/` (nesta spec ou
  em specs futuras que os populem) SHALL descrever detalhes físicos de como o
  repositório `infra` implementa a infraestrutura — paths de servidor (ex.
  `/home/ubuntu/...`), IPs, domínios internos, conteúdo real de crontab, ou
  nomes de arquivo específicos da VPS. Esses arquivos documentam o que este
  projeto (`weather-analytics`) precisa/espera logicamente — nomes de env var,
  datasets, arquitetura de dados, convenções de código — não como o `infra`
  entrega isso fisicamente. Regra de fronteira entre repositórios, não
  preferência de estilo.

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Criar `docs/steering/`/`docs/memory/` agora, revertendo a decisão de posicionamento da spec 001 | Manter `docs/architecture.md` na raiz (decisão original da 001) e adiar `docs/steering/` para quando houvesse mais conteúdo para justificar a pasta | Melhor estabelecer a convenção de diretório antes de mais specs/arquivos passarem a referenciar o path antigo — quanto mais tempo passa, mais referências quebradas se acumulam |
| `docs/steering/` e `docs/memory/` neste repo descrevem só o lado lógico (o que este projeto precisa), nunca a implementação física do `infra` | Espelhar o nível de detalhe do projeto de referência, que inclui IPs/paths de servidor em `tech.md` | O projeto de referência não tem essa fronteira entre repositórios do mesmo jeito; aqui, `infra` é um repositório de infraestrutura compartilhada por múltiplos projetos (não só `weather-analytics`) — documentar detalhes físicos de servidor aqui criaria uma segunda fonte (desatualizável) para informação que já vive no repo `infra` |

### Componentes afetados
- `docs/steering/weather-analytics.md` — novo path (era `docs/architecture.md`), conteúdo não alterado nesta spec
- `docs/memory/constitution.md` — novo
- `docs/specs/001-atualizar-docs-arquitetura/spec.md` — path atualizado, decisão de arquitetura marcada como superada

## Casos de borda
- Referências a `docs/architecture.md` em outros arquivos do repositório
  (README, CLAUDE.md, outras specs) ficam quebradas após o `git mv` — ver
  levantamento em separado; não corrigidas nesta spec sem revisão humana
  primeiro.

## Fora do escopo
- Reescrever o conteúdo de `docs/steering/weather-analytics.md` — continua
  sendo requirement da spec 001, ainda não aplicado.
- Criar outros arquivos de steering equivalentes a `product.md`/`tech.md`/
  `structure.md` do projeto de referência — não solicitado nesta spec.
- Documentar qualquer detalhe físico de implementação do repositório `infra`
  — ver regra de fronteira acima (requirement não-funcional).

## Referências de código
`docs/steering/weather-analytics.md` (novo path), `docs/memory/constitution.md`,
`docs/specs/001-atualizar-docs-arquitetura/spec.md`.

## Ver também
- [[001-atualizar-docs-arquitetura]] — supera a decisão de manter
  `docs/architecture.md` na raiz; requirement de reescrita de conteúdo
  continua válido lá, só o path mudou.
