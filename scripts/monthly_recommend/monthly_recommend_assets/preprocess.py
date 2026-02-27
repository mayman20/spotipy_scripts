# preprocess.py
"""
Build a lightweight recommender from top_monthly_songs.csv (no lyrics).

Input CSV must have at least: song, artist
Optional columns used if present: album, release_date

Outputs:
  - df_cleaned.pkl  (DataFrame with song/artist and a 'document' column)
  - tfidf_matrix.pkl
  - cosine_sim.pkl

Usage:
  pip install pandas scikit-learn joblib
  python3 preprocess.py --in top_monthly_songs.csv
"""

import argparse
import logging
import re

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------- logging ----------
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("preprocess.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def clean_text(s: str) -> str:
    s = str(s or "")
    s = s.lower()
    s = re.sub(r"[^a-z\s]", " ", s)  # keep letters/spaces only
    s = re.sub(r"\s+", " ", s).strip()
    return s

def build_document(row: pd.Series) -> str:
    parts = []
    for col in ("song", "artist", "album", "release_date"):
        if col in row and pd.notna(row[col]):
            parts.append(str(row[col]))
    return clean_text(" ".join(parts))

def main():
    parser = argparse.ArgumentParser(description="Preprocess top songs (no lyrics).")
    parser.add_argument("--in", dest="inp", default="top_monthly_songs.csv", help="Input CSV path")
    parser.add_argument("--max-features", type=int, default=4000, help="TF-IDF max features")
    args = parser.parse_args()

    logging.info("🚀 Loading dataset: %s", args.inp)
    df = pd.read_csv(args.inp)

    # Minimal required columns
    for col in ("song", "artist"):
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' is missing from CSV.")

    # Drop exact duplicates of (song, artist)
    before = len(df)
    df = df.drop_duplicates(subset=["song", "artist"]).reset_index(drop=True)
    if len(df) != before:
        logging.info("ℹ️ Dropped %d duplicate rows", before - len(df))

    # Build simple text "document" from available metadata
    logging.info("🧹 Building metadata documents...")
    if "album" not in df.columns:
        df["album"] = ""
    if "release_date" not in df.columns:
        df["release_date"] = ""
    df["document"] = df.apply(build_document, axis=1)

    if df["document"].str.len().sum() == 0:
        # fallback to just song+artist
        logging.warning("Documents are empty after cleaning; falling back to song+artist only.")
        df["document"] = (df["song"].fillna("") + " " + df["artist"].fillna("")).map(clean_text)

    # TF-IDF on metadata text
    logging.info("🔠 Vectorizing with TF-IDF (max_features=%d)…", args.max_features)
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=args.max_features,
        ngram_range=(1, 2),
        strip_accents="unicode"
    )
    tfidf_matrix = vectorizer.fit_transform(df["document"])
    logging.info("✅ TF-IDF matrix shape: %s", tfidf_matrix.shape)

    # Cosine similarity
    logging.info("📐 Computing cosine similarity…")
    cosine_sim = cosine_similarity(tfidf_matrix, dense_output=False)  # sparse out to save RAM
    # some tools prefer dense array; convert if you like:
    cosine_sim = cosine_sim.toarray().astype(np.float32)

    # Save artifacts
    logging.info("💾 Saving artifacts…")
    joblib.dump(df[["artist", "song", "document"]], "df_cleaned.pkl")
    joblib.dump(tfidf_matrix, "tfidf_matrix.pkl")
    joblib.dump(cosine_sim, "cosine_sim.pkl")

    logging.info("✅ Done. Wrote df_cleaned.pkl, tfidf_matrix.pkl, cosine_sim.pkl")

if __name__ == "__main__":
    main()
