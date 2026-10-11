# Site 1stgeniusAI (estático, NÃO publicado)
Páginas: `index.html`, `guias.html`, `sobre.html`, `contato.html`, `404.html`. CSS único `assets/style.css`, Inter variável local (`assets/fonts`), sem JavaScript, sem rastreadores, sem formulário.
Marca: cópias de `artifacts/brand/marca/svg` (horizontal-transparente no topo/rodapé, emblema no herói e na og.png, símbolo no favicon). Especificação: `docs/brand/MARCA-ATUAL.md`.

Regerar (a partir de `lab-claude-piloto`):
- `python3 scripts/brand/build-site.py` — páginas, CSS, sitemap, robots, manifest, _headers, firebase.json; copia marca, fonte e PDFs que faltarem (não sobrescreve PDFs já em `guias/`).
- `... --imagens` — og.png 1200×630, favicon-32, apple-touch-icon 180, icon-192/512, emblema-880.png (Chrome via `scripts/brand/render.mjs`).
- `... --verificar` — links/src locais e âncoras, 1 h1, títulos/descrições únicos, JSON-LD, contraste WCAG.
Depois de trocar os PDFs em `guias/`, rode de novo para atualizar nº de páginas e KB nos botões.

Antes de publicar (dono): escolher domínio e trocar a constante `BASE` no gerador (canonical, og:image, JSON-LD, sitemap, robots); escolher hospedagem. Firebase: `firebase deploy --only hosting` aqui (`cleanUrls`). Cloudflare Pages: apontar para esta pasta, sem build (`_headers`). Prévia local: `python3 -m http.server 8080` aqui dentro.
