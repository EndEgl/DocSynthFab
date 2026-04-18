import pytest
import numpy as np
from ai1_gen.augment.apply_augment import _sync_meta_from_annotation_and_masks


@pytest.mark.fast
def test_meta_sync_erasure_logic():
    ann = {"meta": {}, "lines": [{"line_type": "math"}], "blocks": []}
    mt = np.zeros((100, 100), dtype=np.uint8)
    mm = np.zeros((100, 100), dtype=np.uint8) # Matematik maskesi tamamen boş!

    _sync_meta_from_annotation_and_masks(ann, mt, mm)
    
    # Line 'math' olsa bile maske boşsa has_equation False olmalı
    assert ann["meta"]["has_equation"] is False
    assert ann["meta"]["mask_math_nonzero"] == 0