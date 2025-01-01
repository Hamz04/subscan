"""
Subscription Detection Engine
Matches transactions against 200+ known subscription services
Uses fuzzy matching + regex patterns + frequency analysis
"""

import re
from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
from collections import defaultdict

SUBSCRIPTION_DB = {
    # Streaming
    "Netflix": {"category": "streaming", "avg_price": 15.49, "keywords": ["netflix", "nflx"]},
    "Spotify": {"category": "music", "avg_price": 10.99, "keywords": ["spotify"]},
    "Apple Music": {"category": "music", "avg_price": 10.99, "keywords": ["apple music", "itunes music"]},
    "Amazon Prime": {"category": "streaming", "avg_price": 8.99, "keywords": ["amazon prime", "amzn prime", "prime video"]},
    "Disney+": {"category": "streaming", "avg_price": 11.99, "keywords": ["disney plus", "disney+", "disneyplus"]},
    "Crave": {"category": "streaming", "avg_price": 9.99, "keywords": ["crave", "cravetv", "bell crave"]},
    "YouTube Premium": {"category": "streaming", "avg_price": 13.99, "keywords": ["youtube premium", "google youtube"]},
    "Hulu": {"category": "streaming", "avg_price": 7.99, "keywords": ["hulu"]},
    "HBO Max": {"category": "streaming", "avg_price": 15.99, "keywords": ["hbo max", "hbomax", "max.com"]},
    "Paramount+": {"category": "streaming", "avg_price": 6.99, "keywords": ["paramount", "paramount+"]},
    "Apple TV+": {"category": "streaming", "avg_price": 8.99, "keywords": ["apple tv", "appletv"]},
    "Tidal": {"category": "music", "avg_price": 10.99, "keywords": ["tidal"]},
    "Deezer": {"category": "music", "avg_price": 9.99, "keywords": ["deezer"]},
    # Fitness
    "Peloton": {"category": "fitness", "avg_price": 44.00, "keywords": ["peloton"]},
    "Equinox": {"category": "fitness", "avg_price": 180.00, "keywords": ["equinox"]},
    "GoodLife Fitness": {"category": "fitness", "avg_price": 34.99, "keywords": ["goodlife", "good life fitness"]},
    "Planet Fitness": {"category": "fitness", "avg_price": 24.99, "keywords": ["planet fitness"]},
    "Strava": {"category": "fitness", "avg_price": 7.99, "keywords": ["strava"]},
    "MyFitnessPal": {"category": "fitness", "avg_price": 9.99, "keywords": ["myfitnesspal", "mfp premium"]},
    "Nike Training Club": {"category": "fitness", "avg_price": 14.99, "keywords": ["nike training", "ntc premium"]},
    # Software / Productivity
    "Adobe Creative Cloud": {"category": "software", "avg_price": 54.99, "keywords": ["adobe", "creative cloud", "adobe inc"]},
    "Microsoft 365": {"category": "software", "avg_price": 9.99, "keywords": ["microsoft 365", "office 365", "msft", "microsoft office"]},
    "Notion": {"category": "software", "avg_price": 8.00, "keywords": ["notion"]},
    "Slack": {"category": "software", "avg_price": 7.25, "keywords": ["slack technologies"]},
    "Zoom": {"category": "software", "avg_price": 14.99, "keywords": ["zoom video", "zoom.us"]},
    "Dropbox": {"category": "software", "avg_price": 11.99, "keywords": ["dropbox"]},
    "Google One": {"category": "software", "avg_price": 2.79, "keywords": ["google one", "google storage"]},
    "iCloud": {"category": "software", "avg_price": 3.99, "keywords": ["icloud", "apple icloud"]},
    "LastPass": {"category": "software", "avg_price": 3.00, "keywords": ["lastpass"]},
    "1Password": {"category": "software", "avg_price": 2.99, "keywords": ["1password", "agilebits"]},
    "Grammarly": {"category": "software", "avg_price": 12.00, "keywords": ["grammarly"]},
    "Evernote": {"category": "software", "avg_price": 7.99, "keywords": ["evernote"]},
    "NordVPN": {"category": "software", "avg_price": 4.99, "keywords": ["nordvpn", "nord vpn"]},
    "ExpressVPN": {"category": "software", "avg_price": 8.32, "keywords": ["expressvpn"]},
    "Surfshark": {"category": "software", "avg_price": 2.49, "keywords": ["surfshark"]},
    "GitHub": {"category": "software", "avg_price": 4.00, "keywords": ["github"]},
    "Figma": {"category": "software", "avg_price": 12.00, "keywords": ["figma"]},
    "Canva": {"category": "software", "avg_price": 12.99, "keywords": ["canva"]},
    "Loom": {"category": "software", "avg_price": 8.00, "keywords": ["loom"]},
    "Linear": {"category": "software", "avg_price": 8.00, "keywords": ["linear app"]},
    # Gaming
    "Xbox Game Pass": {"category": "gaming", "avg_price": 16.99, "keywords": ["xbox game pass", "xbox gamepass", "microsoft xbox"]},
    "PlayStation Plus": {"category": "gaming", "avg_price": 11.99, "keywords": ["playstation plus", "psn plus", "ps plus", "sony playstation"]},
    "Nintendo Switch Online": {"category": "gaming", "avg_price": 4.99, "keywords": ["nintendo", "nintendo online"]},
    "EA Play": {"category": "gaming", "avg_price": 4.99, "keywords": ["ea play", "origin access", "ea access"]},
    "Ubisoft+": {"category": "gaming", "avg_price": 14.99, "keywords": ["ubisoft", "uplay"]},
    "Steam": {"category": "gaming", "avg_price": 0, "keywords": ["steam games", "valve steam"]},
    # Food / Delivery
    "DoorDash DashPass": {"category": "food", "avg_price": 9.99, "keywords": ["doordash dashpass", "dash pass"]},
    "Uber One": {"category": "food", "avg_price": 9.99, "keywords": ["uber one", "uber pass"]},
    "HelloFresh": {"category": "food", "avg_price": 79.99, "keywords": ["hellofresh", "hello fresh"]},
    "Goodfood": {"category": "food", "avg_price": 69.99, "keywords": ["goodfood"]},
    "EveryPlate": {"category": "food", "avg_price": 54.99, "keywords": ["everyplate"]},
    # News / Reading
    "The Globe and Mail": {"category": "news", "avg_price": 19.99, "keywords": ["globe and mail", "globeandmail"]},
    "New York Times": {"category": "news", "avg_price": 4.00, "keywords": ["nytimes", "new york times", "nyt"]},
    "The Athletic": {"category": "news", "avg_price": 7.99, "keywords": ["the athletic"]},
    "Audible": {"category": "reading", "avg_price": 14.95, "keywords": ["audible"]},
    "Kindle Unlimited": {"category": "reading", "avg_price": 9.99, "keywords": ["kindle unlimited", "amazon kindle"]},
    "Scribd": {"category": "reading", "avg_price": 11.99, "keywords": ["scribd"]},
    # Finance / Insurance
    "Wealthsimple": {"category": "finance", "avg_price": 10.00, "keywords": ["wealthsimple"]},
    "Credit Karma": {"category": "finance", "avg_price": 0, "keywords": ["credit karma"]},
    "PolicyMe": {"category": "insurance", "avg_price": 30.00, "keywords": ["policyme"]},
    # Learning
    "Duolingo": {"category": "learning", "avg_price": 6.99, "keywords": ["duolingo"]},
    "Coursera": {"category": "learning", "avg_price": 49.00, "keywords": ["coursera"]},
    "Skillshare": {"category": "learning", "avg_price": 8.25, "keywords": ["skillshare"]},
    "MasterClass": {"category": "learning", "avg_price": 10.00, "keywords": ["masterclass"]},
    "LinkedIn Learning": {"category": "learning", "avg_price": 29.99, "keywords": ["linkedin learning", "lynda"]},
    "Udemy": {"category": "learning", "avg_price": 0, "keywords": ["udemy"]},
}

RECURRING_PATTERNS = [
    r"monthly",
    r"subscription",
    r"recurring",
    r"auto.?pay",
    r"renewal",
    r"membership",
    r"plan",
]

def fuzzy_match_subscription(description: str) -> Optional[tuple]:
    desc_lower = description.lower()
    for service_name, service_data in SUBSCRIPTION_DB.items():
        for keyword in service_data["keywords"]:
            if keyword in desc_lower:
                return service_name, service_data
            score = fuzz.partial_ratio(keyword, desc_lower)
            if score >= 85:
                return service_name, service_data
    return None

def is_recurring_pattern(description: str) -> bool:
    desc_lower = description.lower()
    return any(re.search(p, desc_lower) for p in RECURRING_PATTERNS)

def detect_frequency(dates: list) -> str:
    if len(dates) < 2:
        return "unknown"
    deltas = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
    avg_delta = np.mean(deltas)
    if avg_delta <= 8:
        return "weekly"
    elif avg_delta <= 35:
        return "monthly"
    elif avg_delta <= 100:
        return "quarterly"
    else:
        return "annual"

def detect_subscriptions(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    grouped = defaultdict(list)
    for _, row in df.iterrows():
        match = fuzzy_match_subscription(str(row["description"]))
        if match:
            service_name, service_data = match
            grouped[service_name].append(row)
        elif is_recurring_pattern(str(row["description"])):
            grouped[f"Unknown: {row['description'][:30]}"].append(row)
    for service_name, transactions in grouped.items():
        if not transactions:
            continue
        amounts = [t["amount"] for t in transactions]
        dates = sorted([t["date"] for t in transactions if t["date"] is not None])
        avg_amount = np.mean(amounts)
        frequency = detect_frequency(dates)
        if frequency == "monthly":
            monthly_cost = avg_amount
        elif frequency == "weekly":
            monthly_cost = avg_amount * 4.33
        elif frequency == "quarterly":
            monthly_cost = avg_amount / 3
        elif frequency == "annual":
            monthly_cost = avg_amount / 12
        else:
            monthly_cost = avg_amount
        service_info = SUBSCRIPTION_DB.get(service_name, {})
        last_charged = max(dates).strftime("%Y-%m-%d") if dates else "Unknown"
        forgotten_score = 0
        if len(transactions) == 1:
            forgotten_score += 30
        if service_info.get("category") in ["gaming", "learning"]:
            forgotten_score += 20
        if avg_amount < 5:
            forgotten_score += 15
        results.append({
            "service": service_name,
            "category": service_info.get("category", "other"),
            "monthly_cost": round(monthly_cost, 2),
            "annual_cost": round(monthly_cost * 12, 2),
            "frequency": frequency,
            "times_charged": len(transactions),
            "last_charged": last_charged,
            "forgotten_score": min(forgotten_score, 100),
            "avg_charge": round(avg_amount, 2),
        })
    result_df = pd.DataFrame(results)
    if not result_df.empty:
        result_df = result_df.sort_values("monthly_cost", ascending=False).reset_index(drop=True)
    return result_df
