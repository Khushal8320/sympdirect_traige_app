
# triage_utils.py

# Import from this file in BOTH training and inference.


import re
import numpy as np
import pandas as pd

from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from gensim.models import Word2Vec
from sklearn.base import BaseEstimator, TransformerMixin

# ── NLP setup ────────────────────────────────────────────────
ls = WordNetLemmatizer()
stop_words = set(stopwords.words("english"))
for neg in ["not", "no", "nor", "without"]:
    stop_words.discard(neg)


def clean_text_func(text):
    text = re.sub('[^a-zA-Z]', ' ', str(text))
    text = text.lower().split()
    text = [ls.lemmatize(w) for w in text if w not in stop_words]
    return " ".join(text)


# ── Custom transformer ───────────────────────────────────────
class Word2VecTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, vector_size=100, window=5, min_count=1, workers=4):
        self.vector_size = vector_size
        self.window = window
        self.min_count = min_count
        self.workers = workers
        self.model = None

    def fit(self, X, y=None):
        texts = pd.Series(X.squeeze()).astype(str).fillna("")
        tokenized = [word_tokenize(t.lower()) for t in texts]
        self.model = Word2Vec(
            sentences=tokenized,
            vector_size=self.vector_size,
            window=self.window,
            min_count=self.min_count,
            workers=self.workers,
        )
        return self

    def transform(self, X):
        texts = pd.Series(X.squeeze()).astype(str).fillna("")
        tokenized = [word_tokenize(t.lower()) for t in texts]
        vectors = []
        for tokens in tokenized:
            vecs = [self.model.wv[w] for w in tokens if w in self.model.wv]
            vectors.append(
                np.mean(vecs, axis=0) if vecs else np.zeros(self.vector_size)
            )
        return np.array(vectors)


# ── Rule functions ───────────────────────────────────────────
def obstetric_rule_override(row):
    text     = str(row.get("Chief_complain_clean", "")).lower()
    pregnant = row.get("pregnant", 0) == 1
    sbp      = row.get("SBP", None)
    rr       = row.get("RR", None)
    hr       = row.get("HR", None)

    has_bleeding     = any(k in text for k in ["vaginal bleeding", "bleeding", "heavy bleeding"])
    has_headache     = any(k in text for k in ["severe headache", "headache"])
    has_blur         = any(k in text for k in ["blurred vision", "vision blur", "vision_blur"])
    has_abd_pain     = any(k in text for k in ["abdominal pain", "abd pain", "epigastric pain"])
    has_no_fetal_mvt = any(k in text for k in ["no fetal movement", "reduced fetal movement", "decreased fetal movement"])
    has_labor        = any(k in text for k in ["contractions", "labor", "labour"])
    has_prolapse     = any(k in text for k in ["cord prolapse", "prolapsed cord", "presenting fetal parts"])

    if pregnant:
        if has_prolapse:                                                        return 1
        if sbp is not None and pd.notna(sbp) and sbp < 80:                     return 1
        if rr  is not None and pd.notna(rr)  and rr  > 30:                     return 1
        if hr  is not None and pd.notna(hr)  and hr  > 130:                    return 1
        if has_no_fetal_mvt:                                                    return 2
        if has_headache and has_blur:                                           return 2
        if has_headache and sbp is not None and pd.notna(sbp) and sbp >= 140:  return 2
        if has_abd_pain:                                                        return 2
        if has_bleeding:                                                        return 2
        if has_labor:                                                           return 2
    return None


def clinical_rule_override(row):
    text_raw = row.get("Chief_complain_clean", "")
    text = "" if pd.isna(text_raw) else str(text_raw).lower()

    sbp  = row.get("SBP",      np.nan)
    hr   = row.get("HR",       np.nan)
    rr   = row.get("RR",       np.nan)
    pain = row.get("NRS_pain", np.nan)

    altered_mental   = any(k in text for k in ["mental change", "altered mental", "confused", "unresponsive"])
    seizure          = any(k in text for k in ["seizure", "convulsion", "fits"])
    severe_resp      = any(k in text for k in ["cannot breathe", "not breathing", "severe shortness of breath", "respiratory distress"])
    chest_pain       = any(k in text for k in ["chest pain", "crushing chest pain", "heavy chest pain"])
    shortness_breath = any(k in text for k in ["shortness of breath", "sob", "breathing difficulty"])
    major_bleeding   = any(k in text for k in ["massive bleeding", "heavy bleeding", "profuse bleeding"])

    if altered_mental:                              return 1
    if seizure:                                     return 1
    if severe_resp:                                 return 1
    if major_bleeding:                              return 1
    if pd.notna(sbp)  and sbp < 80:                return 1
    if pd.notna(hr)   and hr  > 130:               return 1
    if pd.notna(rr)   and rr  > 30:                return 1
    if chest_pain:                                  return 2
    if shortness_breath:                            return 2
    if pd.notna(pain) and pain >= 8:               return 2
    if pd.notna(sbp)  and 80 <= sbp < 90:          return 2
    if pd.notna(hr)   and 110 <= hr  <= 130:       return 2
    if pd.notna(rr)   and 24  <= rr  <= 30:        return 2
    return None


def combined_rule_override(row):
    preds = [p for p in [obstetric_rule_override(row), clinical_rule_override(row)] if p is not None]
    return min(preds) if preds else None


def predict_with_all_rules(model, patient_df, threshold_class_1=0.30, threshold_class_2=0.40):
    classes        = model.named_steps["clf"].classes_
    class_to_index = {cls: idx for idx, cls in enumerate(classes)}
    idx1, idx2     = class_to_index[1], class_to_index[2]

    default_preds = model.predict(patient_df)
    probs         = model.predict_proba(patient_df)

    tuned_preds, preg_preds, clinical_preds = [], [], []
    combined_preds, final_preds, final_source = [], [], []

    for i, (_, row) in enumerate(patient_df.iterrows()):
        p = probs[i]
        if   p[idx1] >= threshold_class_1: tuned_pred = 1
        elif p[idx2] >= threshold_class_2: tuned_pred = 2
        else:                              tuned_pred = classes[np.argmax(p)]
        tuned_preds.append(tuned_pred)

        preg_pred = obstetric_rule_override(row)
        clin_pred = clinical_rule_override(row)
        comb_pred = combined_rule_override(row)

        preg_preds.append(preg_pred)
        clinical_preds.append(clin_pred)
        combined_preds.append(comb_pred)

        if comb_pred is not None:
            final_preds.append(comb_pred);  final_source.append("rule_override")
        else:
            final_preds.append(tuned_pred); final_source.append("model_tuned")

    result_df = patient_df.copy()
    result_df["Pregnancy_Rule_CTAS"] = preg_preds
    result_df["Clinical_Rule_CTAS"]  = clinical_preds
    result_df["Combined_Rule_CTAS"]  = combined_preds
    result_df["Model_Default_CTAS"]  = default_preds
    result_df["Model_Tuned_CTAS"]    = tuned_preds
    result_df["Final_CTAS"]          = final_preds
    result_df["Final_Source"]        = final_source

    for i, cls in enumerate(classes):
        result_df[f"Prob_Class_{cls}"] = np.round(probs[:, i], 4)

    return result_df
