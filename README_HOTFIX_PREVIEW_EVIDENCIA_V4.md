# Hotfix V4 — Preview de Evidência no Modal

## Correção

A tela `/evidencias` já abria os detalhes e os links preservados, mas o preview automático do modal podia não renderizar a imagem em alguns casos.

Este hotfix altera `frontend/src/components/EvidenceConsole.tsx` para usar um componente de preview com fallback em camadas:

1. `screenshot_banner_url`
2. `image_url`
3. `screenshot_page_url`
4. `evidence_html_url` via iframe, quando não houver imagem direta

Também foram adicionados botões separados para:

- Abrir evidência preservada
- Abrir banner preservado
- Abrir página preservada
- Imagem original
- Página original

## Aplicação

```bash
docker compose up -d --build --force-recreate frontend
```

Se quiser reconstruir tudo:

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Teste recomendado

1. Acesse `http://localhost:3000/evidencias`.
2. Filtre por `Checking publicitário` ou `Auditável`.
3. Clique em `Detalhar` em uma peça auditável.
4. Confirme que a imagem aparece no próprio modal.
5. Teste os botões de abertura em nova aba.
