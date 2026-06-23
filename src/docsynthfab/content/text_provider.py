# src/docsynthfab/content/text_provider.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
#
# Text provider with optional word-bank policy.
# It does not validate language correctness. It only uses metadata to choose
# from configured banks/profiles.

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
        policy_cfg = self.cfg.get("word_bank_policy", {}) or {}

        self.charset = str(chars_cfg.get("charset", DEFAULT_CHARSET))
        self.char_min_len = int(chars_cfg.get("min_len", 3))
        self.char_max_len = int(chars_cfg.get("max_len", 18))

        self.word_min = int(words_cfg.get("min_words", 1))
        self.word_max = int(words_cfg.get("max_words", 8))
        self.word_join = str(words_cfg.get("join_with", words_cfg.get("separator", " ")))


        self.sent_min = int(sent_cfg.get("min_sentences", 1))
        self.sent_max = int(sent_cfg.get("max_sentences", 2))
        self.sent_sep = str(sent_cfg.get("separator", " "))

        self.filter_lang = str(filter_cfg.get("language_label", "")).strip().lower()
        self.filter_script = str(filter_cfg.get("script_label", "")).strip().lower()
        self.filter_alphabet = str(filter_cfg.get("alphabet_profile", "")).strip().lower()

        self.word_bank_policy_enabled = bool(policy_cfg.get("enable", False))
        self.word_bank_policy_primary = str(policy_cfg.get("primary", "alphabet")).strip().lower()
        
        self.language_mix = self._norm_weight_map(policy_cfg.get("language_mix", {}) or {})
        self.script_mix = self._norm_weight_map(policy_cfg.get("script_mix", {}) or {})
        self.alphabet_mix = self._norm_weight_map(policy_cfg.get("alphabet_mix", {}) or {})

        self.word_bank_mix_strategy = str(
            policy_cfg.get("mix_strategy", "")
        ).strip().lower()

        self.group_multilingual = bool(
            policy_cfg.get("group_multilingual", False)
        )

        try:
            self.min_alphabets_per_group = int(
                policy_cfg.get("min_alphabets_per_group", 0)
            )
        except Exception:
            self.min_alphabets_per_group = 0


        self.sentence_language_mode = str(
            policy_cfg.get("sentence_language_mode", "dominant")
        ).strip().lower()

        try:
            self.sentence_language_switch_prob = float(
                policy_cfg.get("sentence_language_switch_prob", 0.05)
            )
        except Exception:
            self.sentence_language_switch_prob = 0.05

        self.sentence_language_switch_prob = max(
            0.0,
            min(1.0, self.sentence_language_switch_prob),
        )

        try:
            self.table_cell_sentence_prob = float(
                policy_cfg.get("table_cell_sentence_prob", 0.15)
            )
        except Exception:
            self.table_cell_sentence_prob = 0.15

        self.table_cell_sentence_prob = max(
            0.0,
            min(1.0, self.table_cell_sentence_prob),
        )

        self.table_cell_sentence_min_words = int(
            policy_cfg.get("table_cell_sentence_min_words", 2)
        )
        self.table_cell_sentence_max_words = int(
            policy_cfg.get("table_cell_sentence_max_words", 6)
        )


    @classmethod
    def from_json(
        cls,
        json_path: str | Path,
        content_cfg: Dict[str, Any],
        rng: random.Random,
    ) -> "TextProvider":
        obj = json.loads(Path(json_path).read_text(encoding="utf-8"))
        return cls(obj, content_cfg, rng)

    def _norm_weight_map(self, value: Any) -> Dict[str, float]:
        if not isinstance(value, dict):
            return {}

        out: Dict[str, float] = {}
        total = 0.0

        for k, v in value.items():
            key = str(k).strip().lower()
            if not key:
                continue
            try:
                w = max(0.0, float(v))
            except Exception:
                w = 0.0

            if w > 0:
                out[key] = w
                total += w

        if total <= 0:
            return {}

        return {k: v / total for k, v in out.items()}

    def _weighted_pick_key(self, weights: Dict[str, float]) -> str:
        if not weights:
            return ""

        keys = list(weights.keys())
        vals = list(weights.values())
        return str(self.rng.choices(keys, weights=vals, k=1)[0]).strip().lower()

    def _filter_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not items:
            return items

        filtered = [item for item in items if self._matches_filter(item)]
        if not filtered:
            filtered = items

        if self.word_bank_policy_enabled:
            policy_filtered = self._apply_word_bank_policy(filtered)
            if policy_filtered:
                return policy_filtered

        return filtered

    def _apply_word_bank_policy(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not items:
            return []

        choices: list[tuple[str, str, Dict[str, float]]] = []

        if self.word_bank_policy_primary == "language":
            choices = [
                ("lang", self._weighted_pick_key(self.language_mix), self.language_mix),
                ("script", self._weighted_pick_key(self.script_mix), self.script_mix),
                ("alphabet_profile", self._weighted_pick_key(self.alphabet_mix), self.alphabet_mix),
            ]
        elif self.word_bank_policy_primary == "script":
            choices = [
                ("script", self._weighted_pick_key(self.script_mix), self.script_mix),
                ("alphabet_profile", self._weighted_pick_key(self.alphabet_mix), self.alphabet_mix),
                ("lang", self._weighted_pick_key(self.language_mix), self.language_mix),
            ]
        else:
            choices = [
                ("alphabet_profile", self._weighted_pick_key(self.alphabet_mix), self.alphabet_mix),
                ("lang", self._weighted_pick_key(self.language_mix), self.language_mix),
                ("script", self._weighted_pick_key(self.script_mix), self.script_mix),
            ]

        current = items

        for field, selected, _weights in choices:
            if not selected:
                continue

            subset = [
                item for item in current
                if str(item.get(field, "")).strip().lower() == selected
            ]

            if subset:
                current = subset

        return current

    def _base_filtered_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not items:
            return items

        filtered = [item for item in items if self._matches_filter(item)]
        if filtered:
            return filtered

        return items

    def _items_by_field(
        self,
        items: List[Dict[str, Any]],
        field: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {}

        for item in items:
            key = str(item.get(field, "")).strip().lower()
            if not key:
                continue
            out.setdefault(key, []).append(item)

        return out

    def _weighted_sample_keys_without_replacement(
        self,
        keys: List[str],
        weights: Dict[str, float],
        k: int,
    ) -> List[str]:
        pool = list(keys)
        picked: List[str] = []

        while pool and len(picked) < k:
            vals = [max(0.0, float(weights.get(key, 0.0))) for key in pool]

            if not any(vals):
                vals = [1.0 for _ in pool]

            chosen = self.rng.choices(pool, weights=vals, k=1)[0]
            picked.append(chosen)
            pool.remove(chosen)

        return picked

    def _choose_item_from_pool(self, pool: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not pool:
            return {}

        weights = [max(0.0, float(item.get("weight", 1.0))) for item in pool]

        if not any(weights):
            weights = [1.0 for _ in pool]

        return self.rng.choices(pool, weights=weights, k=1)[0]

    def _words_multilingual_group(self, n: int) -> str:
        base_pool = self._base_filtered_items(self.words)

        if not base_pool:
            return self._chars()

        by_alpha = self._items_by_field(base_pool, "alphabet_profile")

        active_alphas = [
            key
            for key, items in by_alpha.items()
            if items and float(self.alphabet_mix.get(key, 0.0)) > 0.0
        ]

        if len(active_alphas) < 2:
            return self.word_join.join(self._next_word() for _ in range(n)).strip()

        k = min(
            max(1, int(self.min_alphabets_per_group or 1)),
            n,
            len(active_alphas),
        )

        active_weights = {
            key: float(self.alphabet_mix.get(key, 1.0))
            for key in active_alphas
        }

        chosen_alphas = self._weighted_sample_keys_without_replacement(
            active_alphas,
            active_weights,
            k,
        )

        words: List[str] = []

        # First pass: force diversity by taking one word from each selected alphabet.
        for alpha in chosen_alphas:
            item = self._choose_item_from_pool(by_alpha.get(alpha, []))
            text = str(item.get("text", "")).strip()
            if text:
                words.append(text)

        # Fill remaining words with weighted alphabet choices.
        while len(words) < n:
            alpha = self._weighted_pick_key(active_weights)

            if alpha and alpha in by_alpha:
                item = self._choose_item_from_pool(by_alpha.get(alpha, []))
            else:
                item = self._choose_item_from_pool(base_pool)

            text = str(item.get("text", "")).strip()
            if text:
                words.append(text)

        self.rng.shuffle(words)
        return self.word_join.join(words).strip()

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
        if not any(weights):
            weights = [1.0 for _ in pool]

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

    def _dominant_alphabet(self) -> str:
        if self.alphabet_mix:
            return str(self._weighted_pick_key(self.alphabet_mix) or "").strip().lower()
        return ""

    def _word_from_alphabet(self, alpha: str) -> str:
        alpha = str(alpha or "").strip().lower()
        base_pool = self._base_filtered_items(self.words)

        if alpha:
            pool = [
                item
                for item in base_pool
                if str(item.get("alphabet_profile", "")).strip().lower() == alpha
            ]
            if pool:
                item = self._choose_item_from_pool(pool)
                return str(item.get("text", "")).strip()

        return self._next_word().strip()

    def _words_dominant_group(self, n: int) -> str:
        alpha = self._dominant_alphabet()
        words: List[str] = []

        for idx in range(max(1, int(n))):
            use_alpha = alpha

            if idx > 0 and self.rng.random() < self.sentence_language_switch_prob:
                use_alpha = self._dominant_alphabet() or alpha

            text = self._word_from_alphabet(use_alpha)
            if text:
                words.append(text)

        if not words:
            fallback = self._next_word().strip()
            if fallback:
                words.append(fallback)

        return self.word_join.join(words).strip()

    def _short_sentence_from_words(self, min_words: int, max_words: int) -> str:
        lo = max(1, int(min_words))
        hi = max(lo, int(max_words))
        return self._words_dominant_group(self.rng.randint(lo, hi)).strip()

    def _table_cell_text(self) -> str:
        if self.rng.random() < self.table_cell_sentence_prob:
            text = self._short_sentence_from_words(
                self.table_cell_sentence_min_words,
                self.table_cell_sentence_max_words,
            )
        else:
            text = self._short_sentence_from_words(1, 3)

        return text.strip() or self._next_word().strip() or self._chars()


    def _words(self) -> str:
        max_words = max(self.word_min, self.word_max)
        n = self.rng.randint(self.word_min, max_words)

        if (
            self.word_bank_policy_enabled
            and self.sentence_language_mode in {"dominant", "single"}
        ):
            return self._words_dominant_group(n)

        if (
            self.word_bank_policy_enabled
            and self.group_multilingual
        ):
            return self._words_multilingual_group(n)

        return self.word_join.join(self._next_word() for _ in range(n)).strip()


    def _sentences(self) -> str:
        max_sentences = max(self.sent_min, self.sent_max)
        n = self.rng.randint(self.sent_min, max_sentences)

        return self.sent_sep.join(self._next_sentence() for _ in range(n)).strip()

    def next_text(self, *, line_type: str = "text") -> str:
        if line_type == "math":
            return ""

        if line_type == "table_cell":
            return self._table_cell_text()

        mode = self._pick_mode()

        if mode == "chars":
            return self._chars()

        if mode == "words":
            # Preserve the public/default TextProvider behavior for tests and GUI
            # controls. Only renderer-requested paragraph/body lines are expanded.
            if line_type in {"paragraph", "body"}:
                lo = max(8, int(self.word_min))
                hi = max(lo, int(self.word_max), 18)
                return self._short_sentence_from_words(lo, hi)

            return self._words()

        return self._sentences()