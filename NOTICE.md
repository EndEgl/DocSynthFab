# NOTICE

DocSynthFab

Copyright 2026 Ender Emre Hayırlıoğlu.

DocSynthFab is licensed under the Apache License, Version 2.0. See the `LICENSE` file for the full license text.

This NOTICE file provides attribution and third-party component information for the DocSynthFab project.

## Third-Party Components

This project may include, bundle, reference, or depend on third-party components. These components remain under their own respective licenses.

Third-party components may include, but are not limited to:

- Python packages.
- Fonts and font metadata.
- Docker base images.
- System packages used inside Docker images.
- LaTeX distributions.
- TeX packages.
- Optional GUI, rendering, and image-processing dependencies.

## Fonts

DocSynthFab may include bundled font files for multilingual synthetic document generation.

Bundled font files remain under their own respective font licenses. Font-specific license information may be available under:

- `assets/fonts/LICENSES/`
- `assets/fonts/README_FONT_MANIFEST.md`
- `assets/fonts/FONT_MANIFEST.json`
- `THIRD_PARTY_LICENSES/fonts/`

The fonts are included only as part of the DocSynthFab software package. They are not sold or distributed as a standalone font package.

Generated documents, images, PDFs, and datasets are generally treated as user-generated outputs. Users remain responsible for ensuring that their own use, redistribution, and deployment comply with all applicable third-party licenses.

## Python Dependencies

Runtime, development, optional web, and optional renderer dependencies are listed in files such as:

- `requirements.txt`
- `requirements-dev.txt`
- `requirements-web.txt`
- Docker-specific requirements files, when present.

Python dependencies remain under their own respective licenses.

## Docker and LaTeX Rendering

DocSynthFab may use optional Docker-based LaTeX rendering for math-heavy synthetic document generation.

Docker base images, system packages, LaTeX distributions, TeX packages, fonts, and renderer dependencies remain under their own respective licenses.

Additional third-party license notes may be placed under `THIRD_PARTY_LICENSES/`.

## Important Notice

DocSynthFab's own source code is licensed under the Apache License 2.0.

Third-party components are not relicensed by this project. They remain subject to their own license terms.

The contents of this NOTICE file are for attribution and informational purposes only and do not modify the Apache License 2.0 terms that apply to DocSynthFab source code.
