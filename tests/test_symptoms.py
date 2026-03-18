from src.safety.symptoms import extract_symptoms


class TestExtractSymptoms:
    def test_single_match(self, lexicon):
        result = extract_symptoms("patient has chest pain", lexicon)
        assert "chest_pain" in result

    def test_multiple_matches(self, lexicon):
        result = extract_symptoms("chest pain with shortness of breath", lexicon)
        assert "chest_pain" in result
        assert "shortness_of_breath" in result

    def test_no_match(self, lexicon):
        result = extract_symptoms("patient has a headache", lexicon)
        assert "chest_pain" not in result
        assert "shortness_of_breath" not in result

    def test_empty_string(self, lexicon):
        result = extract_symptoms("", lexicon)
        assert result == set()

    def test_none_input(self, lexicon):
        result = extract_symptoms(None, lexicon)
        assert result == set()

    def test_case_insensitivity(self, lexicon):
        result = extract_symptoms("CHEST PAIN and DYSPNEA", lexicon)
        assert "chest_pain" in result
        assert "shortness_of_breath" in result

    def test_synonym_dyspnea(self, lexicon):
        result = extract_symptoms("dyspnea on exertion", lexicon)
        assert "shortness_of_breath" in result

    def test_synonym_sob(self, lexicon):
        result = extract_symptoms("patient reports sob", lexicon)
        assert "shortness_of_breath" in result

    def test_abbreviation_cp(self, lexicon):
        result = extract_symptoms("presenting with cp", lexicon)
        assert "chest_pain" in result

    def test_real_clinical_text_seizure(self, lexicon):
        result = extract_symptoms("Seizure Like Activity", lexicon)
        assert "seizure" in result

    def test_real_clinical_text_motor_weakness(self, lexicon):
        result = extract_symptoms("Rt. side motor weakness", lexicon)
        assert "motor_weakness" in result

    def test_whitespace_only(self, lexicon):
        result = extract_symptoms("   ", lexicon)
        assert result == set()
