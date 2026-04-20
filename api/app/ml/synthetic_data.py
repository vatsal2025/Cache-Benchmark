"""
Synthetic account feature generation for PAS model training.
Distributions match documented parameters in ml/data/synthetic_config.yaml.
"""
import numpy as np
import pandas as pd
from typing import Literal


LABEL_MAP = {"GPAS": 0, "BPAS": 1, "EPAS": 2}
LABEL_REVERSE = {0: "GPAS", 1: "BPAS", 2: "EPAS"}

FEATURE_NAMES = [
    "num_friends",
    "email_domain_category",  # 0=gmail/yahoo, 1=corporate, 2=suspicious
    "phone_present",
    "device_type",            # 0=mobile, 1=desktop, 2=tablet
    "account_age_days",
    "time_on_platform_mins",
    "login_frequency",
    "num_subscriptions",
    "friend_requests_sent",
    "reports_received",
    "content_posted",
]

# Features available by N-day delay (minimum days needed)
FEATURE_AVAILABILITY = {
    "num_friends": 0,
    "email_domain_category": 0,
    "phone_present": 0,
    "device_type": 0,
    "account_age_days": 0,
    "time_on_platform_mins": 1,
    "login_frequency": 3,
    "num_subscriptions": 7,
    "friend_requests_sent": 3,
    "reports_received": 5,
    "content_posted": 1,
}


def generate_account(label: str, rng: np.random.Generator) -> dict:
    if label == "GPAS":
        return {
            "num_friends": int(rng.poisson(150)),
            "email_domain_category": int(rng.choice([0, 1], p=[0.6, 0.4])),
            "phone_present": int(rng.binomial(1, 0.85)),
            "device_type": int(rng.choice([0, 1, 2], p=[0.5, 0.4, 0.1])),
            "account_age_days": int(rng.exponential(365)),
            "time_on_platform_mins": float(rng.lognormal(4.5, 0.8)),
            "login_frequency": float(rng.poisson(3)),
            "num_subscriptions": int(rng.poisson(5)),
            "friend_requests_sent": int(rng.poisson(2)),
            "reports_received": int(rng.poisson(0.1)),
            "content_posted": int(rng.poisson(10)),
        }
    elif label == "BPAS":
        return {
            "num_friends": int(rng.poisson(5)),
            "email_domain_category": int(rng.choice([0, 1, 2], p=[0.3, 0.1, 0.6])),
            "phone_present": int(rng.binomial(1, 0.3)),
            "device_type": int(rng.choice([0, 1, 2], p=[0.2, 0.7, 0.1])),
            "account_age_days": int(rng.exponential(30)),
            "time_on_platform_mins": float(rng.lognormal(1.5, 1.2)),
            "login_frequency": float(rng.poisson(0.5)),
            "num_subscriptions": int(rng.poisson(0)),
            "friend_requests_sent": int(rng.poisson(50)),
            "reports_received": int(rng.poisson(3)),
            "content_posted": int(rng.poisson(100)),
        }
    else:  # EPAS
        return {
            "num_friends": int(rng.poisson(30)),
            "email_domain_category": int(rng.choice([0, 1, 2], p=[0.5, 0.3, 0.2])),
            "phone_present": int(rng.binomial(1, 0.5)),
            "device_type": int(rng.choice([0, 1, 2], p=[0.4, 0.5, 0.1])),
            "account_age_days": int(rng.exponential(90)),
            "time_on_platform_mins": float(rng.lognormal(2.0, 1.5)),
            "login_frequency": float(rng.poisson(0.2)),
            "num_subscriptions": int(rng.poisson(1)),
            "friend_requests_sent": int(rng.poisson(5)),
            "reports_received": int(rng.poisson(0.3)),
            "content_posted": int(rng.poisson(1)),
        }


def generate_dataset(n_total: int = 50000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_gpas = int(n_total * 0.60)
    n_bpas = int(n_total * 0.20)
    n_epas = n_total - n_gpas - n_bpas

    records = []
    for label, n in [("GPAS", n_gpas), ("BPAS", n_bpas), ("EPAS", n_epas)]:
        for _ in range(n):
            row = generate_account(label, rng)
            row["label"] = LABEL_MAP[label]
            records.append(row)

    df = pd.DataFrame(records)
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


def get_available_features(n_day_delay: int) -> list[str]:
    return [f for f, min_days in FEATURE_AVAILABILITY.items() if min_days <= n_day_delay]


def account_to_features(account: dict, n_day_delay: int = 7) -> list[float]:
    available = get_available_features(n_day_delay)
    return [float(account.get(f, 0)) for f in available]
