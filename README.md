# DocSynthFab

Experimental synthetic document generation toolkit for OCR and Document AI dataset prototyping.

## What is DocSynthFab?

DocSynthFab is an experimental synthetic document dataset generator.

It creates document-like page images together with structured labels, annotation JSON files, segmentation masks, ground truth files, train/validation/test splits, reports, and export-ready dataset formats.

The current `v0.1.0-alpha` release focuses on generation correctness, annotation consistency, QC validation, exports, and acceptance testing. Real-world model performance benchmarking is planned for a later milestone.

## Use Cases

DocSynthFab is intended for experiments in:

- OCR.
- Document AI.
- Layout analysis.
- Text and table detection.
- Segmentation.
- Synthetic dataset prototyping.
- Annotation pipeline testing.

## Output Structure

A generated dataset contains folders similar to:

~~~text
out/demo/
  images/
  masks/
  ann/
  gt/
  splits/
  reports/
  exports/
~~~

The `out/` folder is a generated output directory. It is shown here only as an example and is intentionally ignored by Git.

## Installation

Clone the repository:

~~~bash
git clone https://github.com/EndEgl/DocSynthFab.git
cd DocSynthFab
~~~

Create and activate a virtual environment:

~~~bash
python -m venv .venv
~~~

On Windows PowerShell:

~~~powershell
.\.venv\Scripts\Activate.ps1
~~~

On Linux/macOS:

~~~bash
source .venv/bin/activate
~~~

Upgrade pip and install dependencies:

~~~bash
python -m pip install --upgrade pip
pip install -r requirements.txt
~~~

Install DocSynthFab in editable mode:

~~~bash
pip install -e .
~~~

## Quickstart

Generate a small demo dataset:

~~~bash
python -m docsynthfab.cli --config configs/default.yaml --out out/demo --pages 5 --workers 1 --seed 123
~~~

## Web GUI

DocSynthFab includes an optional NiceGUI-based Web GUI:

~~~bash
pip install -r requirements-web.txt
python -m docsynthfab.gui.web.app
~~~

## Optional LaTeX Renderer

Optional Docker-based LaTeX rendering support is located under:

~~~text
docker/latex-renderer/
~~~

## Testing

Install development dependencies before running tests:

~~~bash
pip install -r requirements-dev.txt
~~~

Run unit tests:

~~~bash
pytest test/unit -q
~~~

Run integration tests:

~~~bash
pytest test/integration -q
~~~

Run E2E acceptance tests:

~~~bash
pytest test/e2e -q -m "e2e and slow and not diversity"
~~~

Optional diversity E2E test on Linux/macOS:

~~~bash
DOCSYNTHFAB_RUN_DIVERSITY_E2E=1 pytest test/e2e -q -m "diversity"
~~~

Optional diversity E2E test on Windows PowerShell:

~~~powershell
$env:DOCSYNTHFAB_RUN_DIVERSITY_E2E = "1"
pytest test\e2e -q -m "diversity"
Remove-Item Env:\DOCSYNTHFAB_RUN_DIVERSITY_E2E
~~~

## Project Status

DocSynthFab is an early experimental release.

It is not yet a production benchmark suite. It currently focuses on synthetic document generation infrastructure and dataset package correctness.

## License

DocSynthFab is licensed under the Apache License 2.0.

See [LICENSE](LICENSE) for the full license text. Additional attribution and third-party component information is available in [NOTICE.md](NOTICE.md).

Bundled fonts, Python dependencies, Docker base images, system packages, LaTeX distributions, and TeX packages remain under their own respective licenses.

## Maintainer

Maintained by [EndEgl](https://github.com/EndEgl).

