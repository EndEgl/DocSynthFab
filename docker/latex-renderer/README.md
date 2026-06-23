# DocSynthFab LaTeX Renderer

Small HTTP service that renders LaTeX math expressions into transparent PNG images for DocSynthFab synthetic document generation.

The main DocSynthFab generator is text/table-only by default. LaTeX generation is intentionally separated into this renderer so that LaTeX dependencies stay isolated inside Docker.

## Endpoints

### Health check

```bash
curl http://127.0.0.1:8080/health


