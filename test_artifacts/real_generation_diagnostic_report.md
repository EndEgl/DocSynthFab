# Real Generation Diagnostic Report

- Run ID: `33c731954f50`
- Final state: `done`
- Out root: `C:\Users\AG Zaferi\Desktop\LLM_tabanlı_projeler\DocSynthFab\test_artifacts\real_generation_diagnostic_out`

## GUI overrides
```json
{
  "augment.enable": true,
  "content.block_mix": {
    "latex": 0.0,
    "table": 0.0,
    "text": 100.0
  },
  "content.sentences": {
    "max_sentences": 4,
    "min_sentences": 2,
    "separator": " "
  },
  "content.source_mode": "content_bank",
  "content.text_mode": "words",
  "content.words": {
    "max_words": 5,
    "min_words": 3,
    "separator": " "
  },
  "dist.density_dist": {
    "dense": 0.51,
    "mixed": 0.16,
    "normal": 0.26,
    "sparse": 0.07
  },
  "dist.noise_level_dist": {
    "clean": 0.3,
    "heavy": 0.25,
    "medium": 0.45
  },
  "diversity_preset": "balanced_document_ai_diverse",
  "layout.layout_type_dist": {
    "academic": 0.12,
    "double_col": 0.24,
    "mixed_cols": 0.28,
    "report_like": 0.08,
    "single_col": 0.28
  },
  "layout.line_gap": {
    "distribution": "gaussian",
    "exponential_lambda": 2.5,
    "max_scale": 1.525,
    "mean_ratio": 0.45,
    "min_scale": 0.7375,
    "randomness_percent": 75.0,
    "std_ratio": 0.245
  },
  "layout.line_gap_random_scale": 2.25,
  "layout.occupancy.enable": true,
  "layout.occupancy.max_place_attempts": 62,
  "layout.occupancy.min_gap_px": 7,
  "layout.occupancy.spread_percent": 78.0,
  "layout.occupancy.whitespace_strategy": "spread",
  "render.latex.enable": false,
  "render.non_text.table_shape": {
    "max_cols": 4,
    "max_rows": 5,
    "min_cols": 2,
    "min_rows": 2
  },
  "render.text.font_size.distribution": "gaussian",
  "render.text.font_size.max_px": 18,
  "render.text.font_size.mean_ratio": 0.55,
  "render.text.font_size.min_px": 10,
  "render.text.font_size.std_ratio": 0.18,
  "render.text.scripts_dist": {
    "ar": 0.06,
    "de": 0.06,
    "el": 0.05,
    "he": 0.04,
    "hi": 0.05,
    "ja": 0.05,
    "ko": 0.04,
    "latin": 0.3,
    "ru": 0.08,
    "symbols": 0.05,
    "th": 0.03,
    "tr": 0.14,
    "zh": 0.05
  }
}
```

## Effective selected config
```json
{
  "content": {
    "block_mix": {
      "latex": 0.0,
      "table": 0.0,
      "text": 100.0
    },
    "generate_json_if_missing": true,
    "regenerate_json_on_start": true,
    "sentences": {
      "max_sentences": 4,
      "min_sentences": 2,
      "separator": " "
    },
    "source": {
      "generated_json": "data/content/content_bank.json",
      "label_registry_csv": "data/content/label_registry.csv",
      "sentences_csv": "data/content/sentences.csv",
      "word_banks_dir": "data/content/word_banks",
      "words_csv": "data/content/words.csv"
    },
    "source_mode": "content_bank",
    "text_mode": "words",
    "text_order": "random",
    "word_bank_policy": {
      "alphabet_mix": {
        "arabic_ar": 6,
        "cyrillic_ru": 8,
        "devanagari_hi": 3,
        "greek_el": 4,
        "han_zh": 4,
        "hangul_ko": 2,
        "hebrew_he": 3,
        "kana_ja": 3,
        "latin_de": 10,
        "latin_en": 20,
        "latin_es": 8,
        "latin_fr": 8,
        "latin_tr": 20,
        "thai_th": 1
      },
      "enable": true,
      "primary": "alphabet"
    },
    "words": {
      "max_words": 5,
      "min_words": 3,
      "separator": " "
    }
  },
  "dist": {
    "density_dist": {
      "dense": 0.51,
      "mixed": 0.16,
      "normal": 0.26,
      "sparse": 0.07
    },
    "noise_level_dist": {
      "clean": 0.3,
      "heavy": 0.25,
      "medium": 0.45
    },
    "scale_dist": {
      "dpi200": 0.22,
      "dpi300": 0.7,
      "hires_crop": 0.02,
      "lowres_capture": 0.06
    }
  },
  "font_size": {
    "distribution": "gaussian",
    "max_px": 18,
    "mean_ratio": 0.55,
    "min_px": 10,
    "std_ratio": 0.18
  },
  "layout_occupancy": {
    "enable": true,
    "max_place_attempts": 62,
    "min_gap_px": 7,
    "spread_percent": 78.0,
    "target_fill_ratio": {
      "dense": [
        0.26,
        0.42
      ],
      "mixed": [
        0.12,
        0.34
      ],
      "normal": [
        0.14,
        0.26
      ],
      "sparse": [
        0.06,
        0.14
      ]
    },
    "whitespace_strategy": "spread"
  },
  "run": {
    "export_targets": [
      "native"
    ],
    "fail_fast": false,
    "jsonl_flush_batch_size": 50,
    "max_fail_ratio": 0.05,
    "max_pending_min": 8,
    "max_pending_mult": 2.0,
    "pages": 3,
    "seed": 12345,
    "splits": {
      "test": 0.1,
      "train": 0.8,
      "val": 0.1
    },
    "worker": {
      "disable_augment_on_try": 3,
      "fallback_dpi": 300,
      "jitter_seed_step": 10000019,
      "max_tries": 5
    },
    "workers": 1
  },
  "table_shape": {
    "max_cols": 4,
    "max_rows": 5,
    "min_cols": 2,
    "min_rows": 2
  }
}
```

## Output report
```json
{
  "ann_count": 3,
  "block_type_counts": {
    "list": 4,
    "paragraph": 13,
    "title": 3
  },
  "files": [
    "errors.jsonl",
    "failed_pages.log",
    "gt_pages.jsonl",
    "qc_summary.json",
    "run.log",
    "ann\\000000.json",
    "ann\\000001.json",
    "ann\\000002.json",
    "exports\\export_summary.json",
    "exports\\native\\dataset_card.md",
    "exports\\native\\label_schema.json",
    "exports\\native\\README.md",
    "exports\\native\\run_manifest.json",
    "exports\\native\\ann\\000000.json",
    "exports\\native\\ann\\000001.json",
    "exports\\native\\ann\\000002.json",
    "exports\\native\\gt\\000000.json",
    "exports\\native\\gt\\000001.json",
    "exports\\native\\gt\\000002.json",
    "exports\\native\\images\\000000.png",
    "exports\\native\\images\\000001.png",
    "exports\\native\\images\\000002.png",
    "exports\\native\\masks\\000000_mask_math.png",
    "exports\\native\\masks\\000000_mask_text.png",
    "exports\\native\\masks\\000001_mask_math.png",
    "exports\\native\\masks\\000001_mask_text.png",
    "exports\\native\\masks\\000002_mask_math.png",
    "exports\\native\\masks\\000002_mask_text.png",
    "exports\\native\\splits\\test.txt",
    "exports\\native\\splits\\train.txt",
    "exports\\native\\splits\\val.txt",
    "gt\\000000.json",
    "gt\\000001.json",
    "gt\\000002.json",
    "images\\000000.png",
    "images\\000001.png",
    "images\\000002.png",
    "masks\\000000_mask_math.png",
    "masks\\000000_mask_text.png",
    "masks\\000001_mask_math.png",
    "masks\\000001_mask_text.png",
    "masks\\000002_mask_math.png",
    "masks\\000002_mask_text.png",
    "reports\\dataset_card.md",
    "reports\\diversity_report.md",
    "reports\\diversity_summary.csv",
    "reports\\diversity_summary.json",
    "reports\\features.csv",
    "reports\\features.jsonl",
    "reports\\label_schema.json",
    "reports\\label_schema.md",
    "reports\\run_manifest.json",
    "splits\\test.txt",
    "splits\\train.txt",
    "splits\\val.txt"
  ],
  "gt_count": 3,
  "line_type_counts": {
    "text": 158
  },
  "meta_density_counts": {
    "normal": 1,
    "sparse": 2
  },
  "out_root": "C:\\Users\\AG Zaferi\\Desktop\\LLM_tabanlı_projeler\\DocSynthFab\\test_artifacts\\real_generation_diagnostic_out",
  "page_gap_reports": [
    {
      "bbox_count": 41,
      "file": "000000.json",
      "y_gap_count": 40,
      "y_gap_max": 342.0,
      "y_gap_mean": 37.575,
      "y_gap_min": 7.0
    },
    {
      "bbox_count": 12,
      "file": "000001.json",
      "y_gap_count": 11,
      "y_gap_max": 681.0,
      "y_gap_mean": 146.9090909090909,
      "y_gap_min": 12.0
    },
    {
      "bbox_count": 105,
      "file": "000002.json",
      "y_gap_count": 60,
      "y_gap_max": 40.0,
      "y_gap_mean": 8.166666666666666,
      "y_gap_min": 0.0
    }
  ],
  "sample_texts": [
    "fecha Abschnitt Anfrage fuel  sigorta ปฏิทิน बैठक συνάντηση calidad país σύνολο 列Stadt Ausrüstung çalışan جرد entrega numéro ค่าจริง",
    "spacing Bestand وقود delivery başarı مدينة email material उत्पाद Absatz terminal proje task margin رسالة export toll başarı équipement आदेश περιγραφή καύσιμο लाइसेंस máscara مجموعة_بياناتدرجة_حرارة निर्यात 수량 E-Mail problème inventaire",
    "Zertifikat sözleşme gráfico  yük section supplier 間隔 analysis налог コンテナfilter gestionnaire Ausrüstungfecha şema 验证 summary paragrafcümle μήκος símbolo Karton مراجعة  risque column Team şehir permit image пошлина temperature section 設備 travailleur sütun  इकाई 日期 E-Mail алфавит 箱",
    "quality imza מלאי_זמין boşluk mesafe  compte export ζήτημα Datum field 기록sayfa belge peaje εξοπλισμός 箱子 iskonto answer currency תרשים  correo विश्लेषण formül",
    "ширина ワーカー unicode champ срок Frist Gewicht 总计चित्र avertissement 记录 φάκελος pays belge facture açıklama ενότητα import risk alan order equipment статус saklama предупреждение",
    "E-Mail 検証 importación терминал  carburant Datei sütunBreite Antwortsatz Lieferungeposta ürün مرشح ürün  מקטע machine rastgele rangée партия Bestellung عنوان height έγκριση_άδειας dilErlaubnis kayıt sigorta",
    "izin εξαγωγή exportación preciosignature schedule storage מסוףaratoplam 段落 altbilgi tarea üstbilgi alphabet 运输 itinéraire script  lote ответ مادة geçişbordure مخزون üstbilgi  label встреча random code_barres بريد",
    "temperature договор Kunde  Breite numara özet páginaкатегория メモ Dateivolume alphabet Zahlung paletдиаграмма décision формула rastgele note  alfabe оборудование dışa_aktarım sertifika товар 合計 запас 总计 ödeme task carga",
    "risk משפט errorwidth Validierung скидка response douane  海关 包裹 seguro tax  schéma durum distance margin  خطأ formula ряд  equipment subtotal gemi stockage peaje  height Einheit 编码 note inspection contract Zahlung class denetim",
    "(∩∩∂×] °0≤3∉∂±→8∑∞∇7↔∩64≈3∪6 2∏≈631∉4∞∏≠2∑°4∩7126∪≥5∑↔9∏  ≈÷87√3≥∞√∉7∞←26∑×∩6≈° ×2→√√4192≠5×÷∈3∈→∩ lorem ←∇≤8°0←√396×≠∪×725≥1∞≥ ∞∈24↔∩≤9∏∂0±↔0∇∞7×5",
    "хранение Entscheidung Palette склад Versand container number количество 연락처 batch número mot barcode material Kategorie program başlık original طلب запрос quality جدول_زمني celda sembol quality",
    "çalışan invoice categoría respuesta entrega temperatura sıcaklık עובד लाइसेंस제목 Datensatzsammlung qualité страница rastgele footer Problemfatura talep Status class unicode 公式 kenar storage ссылка",
    "ग्राहक वितरण talep נהג وصف calendrier топливо unicode address Datensatzsammlung veri_seti Frage lengthgroundtruth answer formule 句子 単語 класс yorum метка respuesta graphique جواب حقيقة_مرجعية κωδικοποίηση subtotal",
    "شهادة hesap город record календарь 税费 row pallet paragraphe permiso equipment  şema Volumen 마감 symbol مجموعة_بيانات वर्कर sipariş 決定 marge validación Länge ülke 原件 πόλη Länge clase 设备 บาร์โค้ด altbilgi program invoice",
    "موافقة volume Paket حزمةvehicle город cevap warehouse топливо département клиент footer כותרת_תחתונה Schiff word Abteilung शेष column commande özet  длина filtre weight Schiff  单元格 Analyse रिकॉर्ड 허가 cargo",
    "分析 เรือ جملة çalışan request  label problema sütun терминал подвал 参考 สินค้าเรือ figura πόληcategoría סך_הכול Zufall تحليلstock departman gestionnaire कैलेंडर Ordner correo Abbildung يونيكود altbilgi палета adres téléphone абзац Nachrichtcolumna soru precio ValidierungZufall signature alan",
    "валюта stockage température Sprache 问题 телефон 警告 numéro cantidad קופסה  Stadt pregunta grafik ülke customs Satz comment certificate örnek税费 заметка anotaciónformat договор certificate driver revision sorun граница",
    "height lisans section Format fuel projet image analiz subtotalemail mesafe Titel koli Frist uyarı yönetici",
    "cargo inventario mensaje водитель 余白  телефон summary задача 语言 peso маска ancho invoice 高度 длина paquet उपकरण program batch   邮件 konteyner satır  供应商 עובד_תהליך toll  account Stempel seed تذييل problema   koli spacing ответ unicode   Diagramm Währung şoför karar Import",
    "para Analyse footer 合同 paket уравнение בעיה kaşe decision 予定 עובד_תהליך plazo mise_en_page réunion karar  genişlik папка demande Maut warning 邮件 палета Entscheidungdocumento liman quality barcode",
    "رأس catégorie advertencia jeu_données   city para kalite ביאור  库存 número مرجع расписание title расписание tablo gestionnaire formato   Abstand جدول_زمني अनुरोध 차량 task  tâche Warnung volumen veri Abstand  en-tête 간격 gerente партия Qualität   sample balance Format douane",
    "bordure δείγμα file şoför  ülke παραγγελία gerçek_veri Original template language table response Dokument konteyner total compte etiqueta yerleşim 部署 Datensatzsammlung approval Kodierung equation",
    "hacim reunión proje header gümrük quantity importación командаFeld विभाग copia Lagerungfuel quantity figureAntwortsatz combustible ekipman статус original comment גופן phone  sözleşme figure Tabelle запись inventory Kalender görev",
    "machine отгрузка stock segurotable font fuel soru Formel 设备 वर्कर  worker numéro statut table ライセンス Warnung 标题 nota código बीज inspection मुद्रा تصريح warehouse Schiff project",
    "palette denetim Zeitplan maske 通行费  Import route sertifika قالب 支払い toll Frist takvim  截止期 toplantı birim sample Annotation   απόφαση تقرير validación Abbildung gemi\tинтервал Stapel column μήνυμα sous-total",
    "Bestand экспорт Schrift saklama formule tabla Fußzeile auditoría оригинал 正解値 επαφή 소계 qualité word calidad 标注ссылка entrepôt 成功 عميل 検証 cargo footer paragraphe Filter horario תשלום discount volume",
    "диаграмма партия формат चालान 通行费 Lizenz ağırlıkanalysis terminal 경로 מועד_סופי error sembol 句子 revision dataset figure температура kategori 计划 Formel 付款 status सामग्री équipement मात्रा 客户 مخطط seed макет έγκριση пошлина строка filtre предложение fila  وزن οδηγός alphabet задача",
    "inspection 类别名 paiement  qualité yükseklik route  yerleşim sorun dil birim vehicle format hacim Kopie bordure margin Zoll фильтр schedule  soru numara error record bölüm veri_seti price 여백 masque sıcaklık עמוד document",
    "маршрут informe code_barres   iletişim kategori field Filter  project Reihe encoding   标注 soru peso   Maut контейнер sorun คำตอบ ανάλυση 운전자 table satır Projekt request אחסון   péage iletişim idioma Maut",
    "Saldo muestra מקטע Fußzeile 보험 route border ग्राउंड_ट्रुथ colonne order price fournisseur yük título שורה_טבלה cliente  response not 参照  поле_страницы Währung απόφαση signature 기록 Zoll cell تنسيق hata"
  ]
}
```
