# src/ai1_gen/content/text_provider.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_CHARSET = "abcçdefgğhıijklmnoöprsştuüvyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


class TextProvider:
    def __init__(
        self,
        bank: Dict[str, Any],
        content_cfg: Dict[str, Any],
        rng: random.Random,
    ) -> None:
        self.bank = bank or {}
        self.cfg = content_cfg or {}
        self.rng = rng

        self.words: List[Dict[str, Any]] = list(self.bank.get("words", []))
        self.sentences: List[Dict[str, Any]] = list(self.bank.get("sentences", []))

        self.text_mode = str(self.cfg.get("text_mode", "mixed")).strip().lower()
        self.text_order = str(self.cfg.get("text_order", "random")).strip().lower()
        self.source_mode = str(self.cfg.get("source_mode", "content_bank")).strip().lower()

        if self.source_mode == "random_chars":
            self.words = []
            self.sentences = []
            self.text_mode = "chars"

        self.word_idx = 0
        self.sentence_idx = 0

        chars_cfg = self.cfg.get("chars", {}) or {}
        words_cfg = self.cfg.get("words", {}) or {}
        sent_cfg = self.cfg.get("sentences", {}) or {}
        filter_cfg = self.cfg.get("filter", {}) or {}

        self.charset = str(chars_cfg.get("charset", DEFAULT_CHARSET))
        self.char_min_len = int(chars_cfg.get("min_len", 3))
        self.char_max_len = int(chars_cfg.get("max_len", 18))

        self.word_min = int(words_cfg.get("min_words", 1))
        self.word_max = int(words_cfg.get("max_words", 8))
        self.word_join = str(words_cfg.get("join_with", " "))

        self.sent_min = int(sent_cfg.get("min_sentences", 1))
        self.sent_max = int(sent_cfg.get("max_sentences", 2))
        self.sent_sep = str(sent_cfg.get("separator", " "))

        self.filter_lang = str(filter_cfg.get("language_label", "")).strip().lower()
        self.filter_script = str(filter_cfg.get("script_label", "")).strip().lower()
        self.filter_alphabet = str(filter_cfg.get("alphabet_profile", "")).strip().lower()

    @classmethod
    def from_json(
        cls,
        json_path: str | Path,
        content_cfg: Dict[str, Any],
        rng: random.Random,
    ) -> "TextProvider":
        obj = json.loads(Path(json_path).read_text(encoding="utf-8"))
        return cls(obj, content_cfg, rng)

    def _filter_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not items:
            return items

        filtered = [item for item in items if self._matches_filter(item)]
        return filtered if filtered else items

    def _matches_filter(self, item: Dict[str, Any]) -> bool:
        if self.filter_alphabet:
            if str(item.get("alphabet_profile", "")).strip().lower() != self.filter_alphabet:
                return False

        if self.filter_lang:
            if str(item.get("lang", "")).strip().lower() != self.filter_lang:
                return False

        if self.filter_script:
            if str(item.get("script", "")).strip().lower() != self.filter_script:
                return False

        return True

    def _pick_mode(self) -> str:
        if self.text_mode != "mixed":
            return self.text_mode

        probs = self.cfg.get("mixed_probs", {}) or {}

        chars_p = float(probs.get("chars", 0.10))
        words_p = float(probs.get("words", 0.45))
        sent_p = float(probs.get("sentences", 0.45))

        total = max(1e-9, chars_p + words_p + sent_p)
        r = self.rng.random() * total

        if r < chars_p:
            return "chars"

        if r < chars_p + words_p:
            return "words"

        return "sentences"

    def _choose_item(self, pool: List[Dict[str, Any]], index_attr: str) -> Dict[str, Any]:
        if self.text_order == "sequential":
            idx = getattr(self, index_attr)
            item = pool[idx % len(pool)]
            setattr(self, index_attr, idx + 1)
            return item

        weights = [max(0.0, float(item.get("weight", 1.0))) for item in pool]
        return self.rng.choices(pool, weights=weights, k=1)[0]

    def _next_word(self) -> str:
        pool = self._filter_items(self.words)

        if not pool:
            return self._chars()

        item = self._choose_item(pool, "word_idx")
        return str(item.get("text", "")).strip()

    def _next_sentence(self) -> str:
        pool = self._filter_items(self.sentences)

        if not pool:
            return self._words()

        item = self._choose_item(pool, "sentence_idx")
        return str(item.get("text", "")).strip()

    def _chars(self) -> str:
        max_len = max(self.char_min_len, self.char_max_len)
        n = self.rng.randint(self.char_min_len, max_len)

        return "".join(self.rng.choice(self.charset) for _ in range(n))

    def _words(self) -> str:
        max_words = max(self.word_min, self.word_max)
        n = self.rng.randint(self.word_min, max_words)

        return self.word_join.join(self._next_word() for _ in range(n)).strip()

    def _sentences(self) -> str:
        max_sentences = max(self.sent_min, self.sent_max)
        n = self.rng.randint(self.sent_min, max_sentences)

        return self.sent_sep.join(self._next_sentence() for _ in range(n)).strip()

    def next_text(self, *, line_type: str = "text") -> str:
        if line_type == "math":
            return ""

        mode = self._pick_mode()

        if mode == "chars":
            return self._chars()

        if mode == "words":
            return self._words()

        return self._sentences()