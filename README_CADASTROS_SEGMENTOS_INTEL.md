# TV Fiscal WebMonitor — Cadastros Operacionais e Intel por Segmento

Esta versão adiciona a camada operacional para transformar o WebMonitor em uma ferramenta de checking individual e inteligência competitiva por segmento.

## Novidades

### Backend

Novas entidades/tabelas:

- `segments`
- `advertisers`
- `advertiser_aliases`
- `portals`
- `project_portals`
- `project_advertisers`

Novo router:

```text
/registry
```

Principais endpoints:

```text
GET  /registry/segments
POST /registry/segments
GET  /registry/advertisers
POST /registry/advertisers
POST /registry/advertisers/{advertiser_id}/aliases
GET  /registry/portals
POST /registry/portals
GET  /registry/projects/{project_id}/config
POST /registry/projects/{project_id}/portals
POST /registry/projects/{project_id}/advertisers
POST /registry/bootstrap-defaults
```

As rotas POST exigem `X-Admin-Token`, reaproveitando o token administrativo já usado no Scheduler.

### Frontend

Nova tela:

```text
http://localhost:3000/admin/cadastros
```

Permite cadastrar:

- segmentos de mercado;
- anunciantes/clientes;
- aliases de reconhecimento;
- portais/fontes;
- vínculos entre projeto, portais e anunciantes.

### Evidências

A tela `/evidencias` agora também permite filtrar por:

- segmento cadastrado;
- anunciante cadastrado;
- finalidade operacional;
- status de checking;
- tipo de conteúdo;
- score;
- evidência preservada.

### Intel

O painel `/intel` recebeu filtros de:

- segmento;
- anunciante cadastrado.

Com isso, passa a ser possível preparar análises como:

- segmento Saúde;
- Unimed x Hapvida;
- Telecom: Claro x Vivo x TIM;
- Varejo: Casas Bahia x Magalu;
- Bancos: Caixa x Banco do Brasil.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/admin/cadastros
```

Use o mesmo token administrativo do Scheduler.

## Primeira configuração sugerida

1. Entrar em `/admin/cadastros`.
2. Informar o token administrativo.
3. Clicar em **Criar padrões comerciais**.
4. Cadastrar/ajustar segmentos reais.
5. Cadastrar clientes e concorrentes com aliases.
6. Vincular anunciantes e portais ao projeto ativo.
7. Abrir `/evidencias` e `/intel` para filtrar por segmento/anunciante.

