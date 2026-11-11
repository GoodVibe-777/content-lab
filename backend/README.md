# Content Lab API

Primeira etapa da migração do notebook Colab para uma API Python modular.

## O que existe nesta etapa

- API FastAPI com health check.
- Content Brain migrado com a identidade editorial NOXIS LAB.
- Gemini como provedor principal e Groq como fallback.
- Media Hunter com busca de vídeos no Pixabay, três consultas por cena e até quatro opções ranqueadas.
- Validação do JSON e da continuidade temporal das cenas.
- Chaves e configurações carregadas por variáveis de ambiente.

## Rodar localmente

Na pasta `backend`:

1. Crie um ambiente virtual.
2. Instale as dependências: `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env` e preencha as chaves localmente.
4. Inicie: `uvicorn app.main:app --reload`.

A API ficará disponível em `http://127.0.0.1:8000`. A documentação interativa fica em `/docs`.

## Endpoints

- `GET /api/health`
- `GET /api/content/styles`
- `POST /api/content/generate`
- `POST /api/media/search`
- `POST /api/projects` e `GET /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/media/search`
- `PUT /api/projects/{project_id}/media/scenes/{scene_number}/selection`

Exemplo de corpo para geração:

```json
{
  "tema": "Como a produtividade virou medida de valor humano",
  "duracao": 45,
  "plataforma": "Instagram Reels",
  "estilo": "critica_social"
}
```

## Persistência inicial

Os projetos são salvos como arquivos JSON em `APP_DATA_DIR/projects` (padrão: `./data/projects`). Essa persistência local é adequada para desenvolvimento e prototipagem; antes de produção com múltiplos servidores, deve ser substituída por banco de dados e armazenamento compartilhado.

## Segurança

Nunca envie chaves reais para o GitHub. O arquivo `.env` é ignorado pelo Git; use variáveis de ambiente ou secrets no ambiente de hospedagem.

## Próximas etapas

1. Testes automatizados do Content Brain e da validação de cenas.
2. Persistência de projetos e status.
3. Persistência da seleção manual de candidatos de mídia.
4. Voice Studio.
5. Video Engine com FFmpeg e renderização retomável.
6. Conectar as estações do estúdio à API.
