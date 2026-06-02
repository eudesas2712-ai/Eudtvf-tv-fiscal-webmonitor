# Hotfix V9 — Intel Comparativo: presença unilateral

Este hotfix ajusta a nomenclatura executiva do Intel Comparativo.

## Correção principal

Quando apenas um anunciante possui evidências/investimento e o outro está zerado, a matriz não deve classificar o confronto como **domínio competitivo**.

Agora o sistema classifica esse caso como:

```text
presença unilateral
```

## Onde reflete

- Tela `/intel/comparativo`;
- PDF comparativo;
- PPTX comparativo;
- Insights automáticos;
- Matriz de confronto direto.

## Nova regra

```text
0 x 0 => sem dados
valor x 0 => presença unilateral
valor x valor com equilíbrio >= 85 => equilibrado
valor x valor com equilíbrio >= 60 => vantagem competitiva
valor x valor com equilíbrio < 60 => domínio competitivo
```

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois gere novamente o relatório em `/intel/comparativo`.
