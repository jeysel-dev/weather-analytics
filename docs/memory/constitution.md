# Constitution — Regras Não-Negociáveis

Regras que não mudam por feature ou por sessão. Violação exige parar e
reportar, não corrigir sozinho.

## Segredos e credenciais

1. Nunca aceitar, solicitar ou expor credencial, chave de API, ou segredo em
   texto no chat ou em arquivo versionado — usar variável de ambiente, nunca
   hardcode.

## Git

2. Commits são sempre locais — nunca `git push` automático. Aguardar
   autorização explícita do usuário antes de publicar qualquer commit no
   remoto.

## Validação de correções

3. Uma correção só é considerada concluída após validação funcional real
   (rodar o teste, comando ou fluxo afetado e confirmar o resultado) — nunca
   presumir sucesso só por ter editado o código.

## Documentação e specs

4. Toda spec deste repositório segue o padrão SDD em
   `docs/specs/NNN-nome/spec.md`, com requirements no formato EARS
   (`WHEN`/`IF` [condição], `THE system SHALL` [comportamento]) — ver
   `docs/specs/_template.md`.
