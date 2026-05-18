# Docker Components License Notice

This project includes a Docker-based LaTeX rendering environment.

## Dockerfile

The Dockerfile in this project is part of this project’s own source code and is licensed under the Apache License 2.0, unless stated otherwise.

## Base Image

This Docker environment uses:

* Debian `bookworm-slim`

Debian and its packages are distributed under various open source licenses. See the official Debian package license information for exact details.

## System Packages

The Docker image installs the following system packages via `apt`:

* python3
* python3-pip
* texlive-latex-base
* texlive-latex-recommended
* texlive-fonts-recommended

Each package is licensed under its respective license.

## Python Dependencies

The Docker environment installs Python dependencies listed in:

* `docker/latex/requirements.txt`

These include:

* fastapi
* uvicorn
* pypdfium2
* Pillow

Each Python package is licensed under its respective license.

## Important Notice

This Docker environment bundles third-party software.
Third-party components are not covered by this project’s Apache License 2.0 and remain subject to their own license terms.
