# DocSynthFab Font Manifest

DocSynthFab includes a minimal Noto-based font pack for multilingual synthetic document rendering.

These fonts are included only as part of the DocSynthFab software package. They are not sold or distributed as a standalone font package.

## Purpose

The bundled fonts are used to render multilingual synthetic document pages for OCR, layout analysis, segmentation, and Document AI experiments.

The default font pack is designed to cover the script groups used by the bundled word banks:

* Latin
* Cyrillic
* Greek
* Arabic
* Hebrew
* Devanagari
* CJK / Han / Japanese-oriented text
* Hangul / Korean
* Thai
* Symbols
* Monospace text

## Directory structure

Expected structure:

```text
assets/fonts/
  latin/
    NotoSans-Regular.ttf

  cyrillic/
    NotoSans-Regular.ttf

  greek/
    NotoSans-Regular.ttf

  arabic/
    NotoSansArabic-Regular.ttf

  hebrew/
    NotoSansHebrew-Regular.ttf

  devanagari/
    NotoSansDevanagari-Regular.ttf

  cjk/
  cjk/
    NotoSansSC-Regular.ttf
    NotoSansJP-Regular.ttf

  hangul/
    NotoSansKR-Regular.ttf

  thai/
    NotoSansThai-Regular.ttf

  symbols/
    NotoSansSymbols-Regular.ttf

  mono/
    NotoSansMono-Regular.ttf

  LICENSES/
    NotoSans-OFL.txt
    NotoSansArabic-OFL.txt
    NotoSansDevanagari-OFL.txt
    NotoSansHebrew-OFL.txt
    NotoSansSC-OFL.txt
    NotoSansJP-OFL.txt
    NotoSansKR-OFL.txt
    NotoSansMono-OFL.txt
    NotoSansSymbols-OFL.txt
    NotoSansThai-OFL.txt

  FONT_MANIFEST.json
  README_FONT_MANIFEST.md
```

If your Chinese, Japanese, or Korean font files are stored as `.otf` instead of `.ttf`, update the corresponding paths in `FONT_MANIFEST.json`.

For Chinese text, `NotoSansSC-Regular.ttf` should be preferred for `zh`, `han`, and Simplified Chinese word banks. `NotoSansJP-Regular.ttf` should be used for Japanese-oriented `ja` and `kana_han` word banks.

## License summary

The bundled fonts are distributed under their respective open font licenses, primarily the SIL Open Font License 1.1.

The license files are stored under:

```text
assets/fonts/LICENSES/
```

The manifest file is stored at:

```text
assets/fonts/FONT_MANIFEST.json
```

The bundled fonts may be used as part of the DocSynthFab software package, subject to their license terms. The fonts are not distributed or sold as a standalone font package.

## Important license notes

Under the SIL Open Font License 1.1:

* The fonts may be used, studied, copied, embedded, modified, redistributed, and bundled with software, subject to the license terms.
* The fonts must not be sold by themselves.
* If modified versions are distributed, they must remain under the same font license.
* Reserved Font Name restrictions must be respected for modified versions.
* Documents, images, PDFs, and datasets generated using the fonts are not required to be licensed under the font license.

This is only a project-level summary. The full legal terms are in the license files under `assets/fonts/LICENSES/`.

## Manifest fields

Each entry in `FONT_MANIFEST.json` contains:

```text
script_group
script_or_role_keys
path
font_name
source
license
license_file
copyright
modified
notes
```

These fields help users understand which font is used for which script group, where the font is stored, and which license file applies.

## DocSynthFab configuration

The default configuration should map scripts to font folders similar to:

```yaml
render:
  text:
    fonts_dir: "assets/fonts"

    font_script_dirs:
      latin: latin
      en: latin
      tr: latin
      de: latin
      es: latin
      fr: latin

      cyrillic: cyrillic
      ru: cyrillic

      greek: greek
      el: greek

      arabic: arabic
      ar: arabic

      hebrew: hebrew
      he: hebrew

      devanagari: devanagari
      hi: devanagari

      han: cjk
      zh: cjk
      cjk: cjk
      ja: cjk
      kana_han: cjk


      hangul: hangul
      ko: hangul

      thai: thai
      th: thai

      symbols: symbols
      mono: mono
```
The `cjk` folder may contain multiple CJK fonts. Font selection should prefer `NotoSansSC-Regular.ttf` for `zh` / Simplified Chinese and `NotoSansJP-Regular.ttf` for `ja` / Japanese.


## Font coverage check

After placing fonts and licenses, run the font coverage test:

```powershell
pytest test\unit\render\test_font_coverage.py -q
```

Then run a small smoke test:

```powershell
python -m docsynthfab.cli --config configs/default.yaml --out out/font_wordbank_smoke --pages 5 --workers 1 --seed 123
```

If a font file is missing or a script is not covered, update the font folder or the `FONT_MANIFEST.json` path before publishing the repository.

## Public v1 note

DocSynthFab public v1 focuses on generic multilingual synthetic document dataset generation.

It does not bundle invoice, receipt, contract, or business-specific templates. Users may create their own custom region templates if needed.



