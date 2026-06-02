# TV Fiscal WebMonitor — Hotfix Editorial Header/Logo V18

## Objetivo
Corrige o cabeçalho dos relatórios editoriais premium para evitar que o texto de risco apareça visualmente no mesmo bloco da logomarca.

## Ajuste aplicado
Arquivo alterado:

```text
backend/app/services/editorial_report_generator.py
```

Alterações:

- A logomarca passou a ficar em um bloco branco exclusivo no canto direito do cabeçalho.
- O indicador de risco foi movido para um bloco próprio, separado da logo.
- O cabeçalho mantém a identidade premium com azul escuro, vermelho institucional e melhor alinhamento.
- Aplicável aos relatórios:
  - Sintético Executivo Premium;
  - Analítico Expandido Premium.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois, gerar novamente os relatórios pela tela:

```text
http://localhost:3000/editorial
```

Botões:

- Sintético executivo
- Analítico expandido
