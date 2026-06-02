# Hotfix V5 — Selects e datas visíveis

Correção visual para os campos de filtro do Intel, Intel Comparativo, Evidências e Cadastros.

## Ajuste aplicado

Alguns navegadores estavam herdando `color-scheme: dark` do CSS global, fazendo com que o valor selecionado em campos `select` e `input[type=date]` ficasse invisível até o clique.

Agora os campos operacionais claros usam explicitamente:

- texto `#111827`;
- fundo branco;
- `-webkit-text-fill-color`;
- `colorScheme: light`;
- foco com contorno vermelho suave.

## Telas impactadas

- `/intel`
- `/intel/comparativo`
- `/evidencias`
- `/admin/cadastros`

## Aplicação

```bash
docker compose up -d --build --force-recreate frontend
```

Se quiser reconstruir tudo:

```bash
docker compose up -d --build --force-recreate backend frontend
```
