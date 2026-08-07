# Corrigir seção de deploy do Streamlit no README

## Tipo
[x] Bug fix

## Status
[x] implementado

## Resumo
`README.md`, seção "Streamlit — Dashboard em Produção" (linhas ~84-229),
descreve deploy manual via AWS Lightsail com Nginx + systemd (passo a passo
completo: certbot, `nginx -t`, `systemctl enable/start`) — mecanismo que não
reflete como o deploy funciona hoje.

## Contexto
Achado durante inventário de `docs/` (2026-08-07): a spec
[[004-reescrever-readme]] reescreveu README.md para refletir a arquitetura
real, mas tratou especificamente Airflow/Postgres, credenciais, CI/CD e
Metodologia Ágil — não essa seção. A seção de deploy do Streamlit ficou de
fora da varredura daquela spec e continuou descrevendo o mecanismo antigo
(Nginx + systemd configurados manualmente no host), que contradiz
`CLAUDE.md` (fonte de verdade): o deploy real é via imagem Docker publicada
no GHCR (`build-and-push.yml`) + `deploy-streamlit-weather.sh` no
repositório `infra`, que faz `git pull`, rebuild sem cache e recreate do
container.

Os arquivos `streamlit/deploy/nginx-weather.conf` e
`streamlit/deploy/weather-streamlit.service` existem de fato no repositório
— não é um caso de link quebrado — mas não são o mecanismo de deploy ativo
hoje.

## Requirements (EARS)

### Funcionais
- THE system SHALL corrigir a seção de deploy do Streamlit no `README.md`
  para refletir o mecanismo real: build de imagem via `build-and-push.yml`
  (GHCR) + deploy/pull gerenciado pelo repositório `infra` — sem detalhar
  mecanismo físico do `infra` (mesma fronteira já aplicada nas specs
  [[001-atualizar-docs-arquitetura]], [[003-estrutura-steering-memory]] e
  [[004-reescrever-readme]]).
- THE system SHALL remover ou condensar o passo a passo manual de
  Nginx/certbot/systemd, já que não reflete como o deploy funciona hoje —
  mesmo tratamento dado à seção Airflow/Postgres pela spec
  [[004-reescrever-readme]].
- THE system SHALL preservar a menção de que
  `streamlit/deploy/nginx-weather.conf` e
  `streamlit/deploy/weather-streamlit.service` existem no repositório (são
  reais), mas deixar claro que não são o mecanismo de deploy ativo hoje.

### Não-funcionais
- A correção SHALL ser verificada contra `CLAUDE.md` (seção "Deploy") antes
  de ser considerada completa.
- Nenhum path de servidor específico da VPS, IP, ou domínio interno SHALL
  ser introduzido além do que já é público (o domínio do dashboard).

## Design

### Decisões de arquitetura
| Decisão | Alternativa considerada | Motivo |
|---|---|---|
| Condensar a seção Nginx/certbot/systemd para uma nota breve, preservando a existência dos arquivos `streamlit/deploy/*` sem o passo a passo operacional completo | Remover toda a seção "Deploy na AWS" | Os arquivos `nginx-weather.conf`/`weather-streamlit.service` continuam no repo por motivo histórico (mesmo raciocínio aplicado a `airflow/`/`postgresql/` na spec 004) — apagar a menção completamente esconderia por que esses arquivos ainda existem no repositório |
| Descrever o deploy real só como "imagem GHCR consumida pelo `infra`", sem detalhar o script/mecanismo físico | Documentar o passo a passo do `deploy-streamlit-weather.sh` no README | Mantém a mesma fronteira entre repositórios já estabelecida nas specs 001/003/004: detalhes físicos de deploy pertencem ao repositório `infra`, não a este |

### Componentes afetados
- `README.md` — seção "Streamlit — Dashboard em Produção": tabela de
  arquitetura (linha do deploy), bloco de estrutura de diretórios, e a
  subseção "Deploy na AWS (Maquina Linux) — passo a passo" (Nginx/certbot/
  systemd)

## Casos de borda
- Se algum leitor externo do README depender do passo a passo Nginx/certbot/
  systemd para replicar o deploy fora do fluxo `infra` (ex: fork do
  projeto) — aceito como risco residual; o README de um projeto público
  documenta o mecanismo real de deploy do mantenedor, não um guia genérico
  de self-hosting. Quem quiser configurar Nginx/systemd manualmente ainda
  tem os arquivos `streamlit/deploy/*` disponíveis como referência.

## Fora do escopo
- Qualquer mudança em `streamlit/deploy/nginx-weather.conf`,
  `streamlit/deploy/weather-streamlit.service`, `deploy/`, ou
  `docker-compose*.yml` — só a documentação no README muda; os arquivos
  continuam no repo.
- Detalhar o mecanismo físico do repositório `infra`
  (`deploy-streamlit-weather.sh`, paths de servidor) — fora da fronteira já
  estabelecida pelas specs 001/003/004.
- Qualquer outra seção do README não relacionada a deploy do Streamlit —
  já corrigidas pela spec 004.

## Referências de código
- `README.md` — arquivo corrigido por esta spec
- `CLAUDE.md` (seção "Deploy") — fonte de verdade do mecanismo real
- `.github/workflows/build-and-push.yml` — build/push real da imagem
- `streamlit/deploy/nginx-weather.conf`,
  `streamlit/deploy/weather-streamlit.service` — arquivos reais, preservados
  no repo, mencionados de forma condensada

## Ver também
- [[004-reescrever-readme]] — reescreveu o README para refletir a
  arquitetura real, mas não cobriu esta seção especificamente; esta spec
  fecha essa lacuna.
- [[001-atualizar-docs-arquitetura]] — estabeleceu a fronteira de não
  documentar detalhes físicos do `infra` neste repositório.
