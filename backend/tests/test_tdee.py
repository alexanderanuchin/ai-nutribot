from apps.nutrition.services import tdee

def test_tdee_basic():
    tgt = tdee("m", 80, 180, None, "moderate", "maintain")
    assert 2000 <= tgt.calories <= 3500
    assert tgt.protein_g > 0
