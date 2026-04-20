"""
Downloads and caches real Instagram account data for PAS model training.

Source: fcakyon/instafake-dataset (GitHub)
  - fake-v1.0/fakeAccountData.json     — 888 fake Instagram accounts
  - fake-v1.0/realAccountData.json     — 888 real Instagram accounts
  - automated-v1.0/automatedAccountData.json
  - automated-v1.0/nonautomatedAccountData.json

Fields per record:
  userFollowerCount, userFollowingCount, userBiographyLength,
  userMediaCount, userHasProfilPic, userIsPrivate,
  usernameDigitCount, usernameLength, isFake

These map directly to PAS proxy signals from Kozlov et al. (RAID 2020):
  - follower count    → social graph size (GPAS signal)
  - following count   → aggressive-follow ratio (BPAS signal)
  - profile pic       → account completion proxy (GPAS signal)
  - media count       → activity level (distinguishes GPAS from EPAS)
  - bio length        → identity completeness

Reference: https://github.com/fcakyon/instafake-dataset
"""
import json
import logging
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = Path("storage/data")

_BASE = "https://raw.githubusercontent.com/fcakyon/instafake-dataset/master/data"
_URLS = {
    "fake":      f"{_BASE}/fake-v1.0/fakeAccountData.json",
    "real":      f"{_BASE}/fake-v1.0/realAccountData.json",
    "automated": f"{_BASE}/automated-v1.0/automatedAccountData.json",
    "nonauto":   f"{_BASE}/automated-v1.0/nonautomatedAccountData.json",
}


def _fetch_json(url: str) -> list[dict]:
    response = urllib.request.urlopen(url, timeout=20)
    return json.loads(response.read())


def _fetch_all() -> pd.DataFrame:
    frames = []
    for label, url in _URLS.items():
        try:
            records = _fetch_json(url)
            df = pd.DataFrame(records)
            logger.info("Downloaded %d records from %s (%s)", len(df), label, url)
            frames.append(df)
        except Exception as exc:
            logger.warning("Could not download %s: %s", url, exc)

    if not frames:
        raise RuntimeError("All instafake download URLs failed")

    return pd.concat(frames, ignore_index=True)


def _map_to_pas_features(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Map Instagram account signals to PAS training features.

    PAS label assignment:
      BPAS — isFake == 1 (fake/automated account — likely bot/spam)
      EPAS — real account but near-zero activity (new or empty account)
      GPAS — real account with meaningful activity

    This mirrors Kozlov et al. (RAID 2020) which defines:
      GPAS = accounts with positive post-clearing OSN signals
      BPAS = accounts that later show abuse behavior
      EPAS = accounts with insufficient signals to classify
    """
    rng = np.random.default_rng(42)
    n = len(raw)

    df = pd.DataFrame()

    def _col(name: str, default: float = 0.0) -> pd.Series:
        """Safe column access with fillna."""
        return raw[name].fillna(default) if name in raw.columns else pd.Series(default, index=raw.index)

    # Direct mappings
    df["num_friends"]      = _col("userFollowerCount").clip(0, 10000).astype(float)
    df["num_following"]    = _col("userFollowingCount").clip(0, 15000).astype(float)
    df["posts_count"]      = _col("userMediaCount").clip(0, 2000).astype(float)
    df["phone_present"]    = _col("userHasProfilPic").round().astype(int)
    df["bio_length"]       = _col("userBiographyLength").clip(0, 200).astype(float)
    df["is_private"]       = _col("userIsPrivate").round().astype(int)
    df["username_length"]  = _col("usernameLength", 10).clip(1, 50).astype(float)
    df["username_numeric_ratio"] = (
        _col("usernameDigitCount") / _col("usernameLength", 10).clip(1, 50)
    ).clip(0, 1).fillna(0).astype(float)

    # Derived: aggressive follow ratio — key BPAS signal
    follow_ratio = (_col("userFollowingCount") + 1) / (_col("userFollowerCount") + 1)
    df["friend_requests_sent"] = follow_ratio.clip(0, 20).mul(15).clip(0, 300).astype(float)

    # Reports received — inferred from fake label + Poisson noise
    is_fake = _col("isFake").round().astype(int) == 1
    lam = np.where(is_fake, 3.5, 0.1)
    df["reports_received"] = rng.poisson(lam=lam, size=n).astype(float)

    # PAS label assignment
    is_empty = (~is_fake) & (_col("userMediaCount") < 2) & (_col("userFollowerCount") < 10)
    labels = np.full(n, "GPAS")
    labels[is_fake.values]  = "BPAS"
    labels[is_empty.values] = "EPAS"
    df["pas_label"] = labels

    return df


def load_real_pas_data(force_refresh: bool = False) -> pd.DataFrame | None:
    """
    Return real PAS training data (download + cache).
    Returns None on failure — caller falls back to synthetic data.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / "instafake_pas.parquet"

    if cache_path.exists() and not force_refresh:
        logger.info("Loading cached instafake PAS data from %s", cache_path)
        try:
            return pd.read_parquet(cache_path)
        except Exception:
            pass  # corrupt cache — re-download

    try:
        raw = _fetch_all()
        mapped = _map_to_pas_features(raw)
        mapped.to_parquet(cache_path, index=False)

        dist = mapped["pas_label"].value_counts().to_dict()
        logger.info(
            "Cached %d real OSN records — GPAS=%d  BPAS=%d  EPAS=%d",
            len(mapped),
            dist.get("GPAS", 0),
            dist.get("BPAS", 0),
            dist.get("EPAS", 0),
        )
        return mapped
    except Exception as exc:
        logger.warning("Real data load failed (%s) — synthetic fallback will be used", exc)
        return None


def get_feature_columns() -> list[str]:
    """Feature columns produced by _map_to_pas_features."""
    return [
        "num_friends",
        "num_following",
        "posts_count",
        "phone_present",
        "bio_length",
        "is_private",
        "username_length",
        "username_numeric_ratio",
        "friend_requests_sent",
        "reports_received",
    ]
