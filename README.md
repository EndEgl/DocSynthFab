# <PROJECT_NAME>
**Open-source synthetic data generator for Document AI**

<PROJECT_NAME> is a CPU-friendly synthetic data generator for building richly annotated document datasets for Document AI workflows.

It is designed for teams and researchers who need scalable, controllable, and diverse synthetic document data without locking themselves into a single narrow task. Instead of targeting only OCR or only layout analysis, the project supports broader Document AI use cases through structured page generation, annotation export, masks, and dataset splits. The current pipeline produces page-level metadata, block and line annotations, bounding boxes, text masks, math masks, and train/val/test split files. It also supports multiple page families and layout patterns such as notes, academic pages, books, single-column, double-column, and mixed-column layouts. :contentReference[oaicite:0]{index=0} :contentReference[oaicite:1]{index=1} :contentReference[oaicite:2]{index=2} :contentReference[oaicite:3]{index=3} :contentReference[oaicite:4]{index=4}

## Why this project exists

High-quality labeled document data is expensive to collect, slow to annotate, and often too narrow for real-world experimentation.

<PROJECT_NAME> exists to make synthetic document dataset generation more accessible and more flexible. It can be used for:
- research and experimentation
- internal dataset generation
- prototyping Document AI systems
- stress-testing training pipelines
- generating large volumes of labeled samples on demand

The generator is built to scale by count as well: the pipeline can generate large numbered datasets and export predefined split files for training, validation, and testing. :contentReference[oaicite:5]{index=5} :contentReference[oaicite:6]{index=6} :contentReference[oaicite:7]{index=7}

## What it generates

The project generates synthetic document pages together with structured supervision outputs.

### Core outputs
- rendered page images
- text masks
- math masks
- JSON annotations
- ground-truth page text exports
- train / val / test split files

### Annotation richness
Depending on the generated sample, annotations can include:
- page metadata
- page family and layout type
- block-level annotations
- line-level annotations
- bounding boxes
- line order
- script metadata
- equation presence
- text and math mask coverage
- augmentation trace metadata

Example metadata in the current outputs includes fields such as `page_family`, `layout_type`, `noise_level`, `density_level`, `scale_profile`, `has_equation`, `mask_text_nonzero`, `mask_math_nonzero`, block definitions, and line-level text/script annotations. :contentReference[oaicite:8]{index=8} :contentReference[oaicite:9]{index=9} :contentReference[oaicite:10]{index=10}

## Supported generation characteristics

<PROJECT_NAME> is intended as a **multi-purpose Document AI data generator**, not a single-task tool.

Current sample outputs show support for:
- single-column layouts
- double-column layouts
- mixed-column layouts
- notes-style pages
- academic-style pages
- book-like pages
- multilingual / mixed-script text content
- text-heavy pages
- equation-aware pages
- augmentation and degradation traces

This gives users room to adapt the data to OCR, layout analysis, text segmentation, math-aware parsing, or broader document understanding experiments without reducing the project to only one benchmark task. :contentReference[oaicite:11]{index=11} :contentReference[oaicite:12]{index=12} :contentReference[oaicite:13]{index=13} :contentReference[oaicite:14]{index=14}

## Key strengths

### 1. Multi-purpose positioning
The project is intentionally not restricted to a single narrow use case. It is better understood as a synthetic data generator for Document AI rather than an OCR-only tool.

### 2. Rich annotations
The output is not limited to plain rendered images. The pipeline also emits masks, structured JSON annotations, metadata, and dataset split files. :contentReference[oaicite:15]{index=15}

### 3. Scalable generation
The generator is designed to produce datasets at user-defined scale, making it useful for both small experiments and large synthetic corpora.

### 4. CPU-friendly workflow
The project is designed to be usable without requiring a GPU-first environment, making synthetic dataset generation more accessible for laptops, standard workstations, and lightweight experimentation flows.

### 5. Useful for both research and practical workflows
The project can support academic exploration, open-source experimentation, and internal commercial data generation pipelines.

## Who this is for

<PROJECT_NAME> is built for:
- ML engineers working on Document AI
- computer vision practitioners
- OCR and parsing researchers
- product teams needing synthetic training data
- builders who want controllable labeled data generation without depending entirely on manually collected corpora

## Example use cases

- Generate synthetic pages for Document AI model pretraining
- Build labeled datasets for layout-aware vision systems
- Produce text and math masks for segmentation experiments
- Create controllable benchmark-like corpora for internal evaluation
- Stress-test annotation, ingestion, or training pipelines
- Prototype multilingual or mixed-layout document models

## Output structure

A typical dataset run can include folders and files such as:

```text
output/
  images/
  masks/
  ann/
  gt/
  splits/
    train.txt
    val.txt
    test.txt
  gt_pages.jsonl
  qc_summary.json
  errors.jsonl
  failed_pages.log
  run.log