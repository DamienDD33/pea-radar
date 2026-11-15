#!/usr/bin/env python3
"""
PEA Radar — mise à jour quotidienne des cours.

Télécharge environ 2 ans de cours de clôture quotidiens (plus les dividendes
versés) pour chaque actif listé dans data/tickers.json, depuis Yahoo Finance
via la bibliothèque yfinance (sans clé d'API), puis écrit data/prices.json,
le fichier lu par l'application (index.html).

Pour les actions, il récupère aussi quelques fondamentaux : consensus des
analystes sur le BPA de l'année prochaine et ses révisions, free cash flow
sur 12 mois et capitalisation (pour le rendement FCF).

Robustesse :
- chaque actif est retenté 3 fois en cas d'échec ;
- si un actif échoue, ses données de la veille sont conservées (marquées « stale ») ;
- si AUCUN actif n'a pu être téléchargé, le script s'arrête en erreur sans
  écraser le fichier existant (GitHub vous prévient alors par e-mail).
"""

import json
import math
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
TICKERS_FILE = ROOT / "data" / "tickers.json"
OUT_FILE = ROOT / "data" / "prices.json"

HISTORY_DAYS = 2 * 365 + 30   # 2 ans + une marge pour les moyennes mobiles et les jours fériés
RETRIES = 3
PAUSE_BETWEEN = 0.6           # secondes entre deux actifs, pour ménager Yahoo
MIN_POINTS = 30               # en dessous, la série est jugée inexploitable


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def fetch_history(symbol: str, start: str):
    """Historique quotidien non ajusté (Close = cours réel) avec les dividendes."""
    last_error = None
    for attempt in range(1, RETRIES + 1):
        try:
            df = yf.Ticker(symbol).history(
                start=start, interval="1d", auto_adjust=False, actions=True
            )
            if df is not None and not df.empty and "Close" in df.columns:
                return df
            last_error = "réponse vide"
        except Exception as exc:  # yfinance lève des exceptions variées
            last_error = repr(exc)
        time.sleep(2 * attempt)
    print(f"  ✗ {symbol} : échec après {RETRIES} tentatives ({last_error})")
    return None


def to_series(df: pd.DataFrame):
    """Convertit le DataFrame yfinance en listes compactes pour le JSON."""
    df = df[df["Close"].notna() & (df["Close"] > 0)].copy()
    df.index = pd.to_datetime(df.index)
    df["date"] = df.index.strftime("%Y-%m-%d")
    # Yahoo renvoie parfois deux lignes pour la même séance : on garde la dernière
    df = df.drop_duplicates(subset="date", keep="last").sort_values("date")

    dates = df["date"].tolist()
    closes = [round(float(v), 4) for v in df["Close"]]

    # Dividendes versés sur les 12 derniers mois (pour le rendement)
    div12m = 0.0
    if "Dividends" in df.columns and len(df):
        cutoff = df.index[-1] - pd.Timedelta(days=365)
        div12m = float(df.loc[df.index > cutoff, "Dividends"].fillna(0).sum())

    return dates, closes, round(div12m, 4)


# ---------------------------------------------------------------------------
# Fondamentaux : révisions du consensus de BPA et rendement du free cash flow
# ---------------------------------------------------------------------------
_FX_CACHE = {}


def fx_rate(src, dst):
    """Taux de change src→dst (ex. USD→EUR) ; 1.0 si même devise, None si introuvable."""
    if not src or not dst or src == dst:
        return 1.0
    key = f"{src}{dst}"
    if key not in _FX_CACHE:
        try:
            h = yf.Ticker(f"{key}=X").history(period="5d")
            _FX_CACHE[key] = float(h["Close"].dropna().iloc[-1]) if not h.empty else None
        except Exception:
            _FX_CACHE[key] = None
    return _FX_CACHE[key]


def cell(df, row, column):
    """Lecture tolérante d'une cellule (les noms de colonnes de Yahoo varient en casse)."""
    if df is None or getattr(df, "empty", True) or row not in df.index:
        return None
    cols = {str(c).lower(): c for c in df.columns}
    c = cols.get(column.lower())
    if c is None:
        return None
    try:
        v = float(df.at[row, c])
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def rel_change(new, old):
    """Variation relative robuste aux bases négatives."""
    if new is None or old is None or old == 0:
        return None
    return (new - old) / abs(old)


def fetch_fundamentals(symbol: str):
    """
    Renvoie un dict compact (ou None) :
      eps1y      consensus de BPA de l'année prochaine (+1y)
      epsChg30   variation de ce consensus sur 30 jours
      epsChg90   variation sur 90 jours
      revUp30 / revDown30   nombre de révisions à la hausse / à la baisse sur 30 jours
      fcf, mcap, fcfYield   free cash flow 12 mois (converti dans la devise de cotation),
                            capitalisation et rendement FCF
    """
    t = yf.Ticker(symbol)
    try:
        info = t.info or {}
    except Exception as exc:
        print(f"    (fondamentaux indisponibles pour {symbol} : {exc!r})")
        return None

    if info.get("quoteType") in ("ETF", "MUTUALFUND"):
        return None   # pas de BPA ni de FCF pour un fonds

    fund = {"asOf": datetime.now(timezone.utc).date().isoformat()}

    # Rendement du free cash flow
    fcf, mcap = info.get("freeCashflow"), info.get("marketCap")
    if fcf is not None and mcap:
        rate = fx_rate(info.get("financialCurrency") or info.get("currency"), info.get("currency"))
        if rate:
            fcf_conv = float(fcf) * rate
            fund.update(fcf=round(fcf_conv), mcap=round(float(mcap)), fcfYield=round(fcf_conv / float(mcap), 5))

    # Révisions du consensus de BPA de l'année prochaine
    try:
        trend = t.eps_trend
    except Exception:
        trend = None
    current = cell(trend, "+1y", "current")
    if current is not None:
        fund["eps1y"] = round(current, 4)
        for days in (30, 90):
            chg = rel_change(current, cell(trend, "+1y", f"{days}daysAgo"))
            if chg is not None:
                fund[f"epsChg{days}"] = round(chg, 5)
    try:
        revisions = t.eps_revisions
    except Exception:
        revisions = None
    up, down = cell(revisions, "+1y", "upLast30days"), cell(revisions, "+1y", "downLast30days")
    if up is not None and down is not None:
        fund.update(revUp30=int(up), revDown30=int(down))

    return fund if len(fund) > 1 else None


def main() -> int:
    tickers = load_json(TICKERS_FILE)
    if not tickers:
        print(f"Fichier introuvable ou invalide : {TICKERS_FILE}")
        return 1
    tickers = {k: v for k, v in tickers.items() if not k.startswith("_")}

    previous = load_json(OUT_FILE) or {}
    previous_assets = previous.get("assets", {})

    start = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).date().isoformat()
    print(f"Téléchargement de {len(tickers)} actifs depuis le {start}…")

    assets, failed, ok, fund_ok = {}, [], 0, 0
    for app_ticker, symbol in tickers.items():
        df = fetch_history(symbol, start)
        entry = None
        if df is not None:
            dates, closes, div12m = to_series(df)
            if len(closes) >= MIN_POINTS:
                entry = {
                    "symbol": symbol,
                    "dates": dates,
                    "close": closes,
                    "div12m": div12m,
                    "stale": False,
                }
                ok += 1
                print(f"  ✓ {symbol:<10} {len(closes):>4} séances, dernier cours {closes[-1]} ({dates[-1]})")
            else:
                print(f"  ✗ {symbol} : seulement {len(closes)} séances")

        if entry is None:
            failed.append(app_ticker)
            if app_ticker in previous_assets:
                entry = dict(previous_assets[app_ticker], stale=True)
                print(f"    → données précédentes conservées pour {app_ticker}")
        else:
            # Fondamentaux (révisions de BPA, free cash flow) : jamais bloquants
            fund = fetch_fundamentals(symbol)
            if fund:
                entry["fund"] = fund
                fund_ok += 1
            elif (previous_assets.get(app_ticker) or {}).get("fund"):
                entry["fund"] = previous_assets[app_ticker]["fund"]   # garde ceux de la veille (date asOf conservée)
                print(f"    → fondamentaux précédents conservés pour {app_ticker}")

        if entry is not None:
            assets[app_ticker] = entry
        time.sleep(PAUSE_BETWEEN)

    if ok == 0:
        print("Aucun actif téléchargé : le fichier existant n'est pas modifié.")
        return 1

    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "Yahoo Finance (via yfinance)",
        "failed": failed,
        "assets": assets,
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"\n{ok}/{len(tickers)} actifs à jour, {len(failed)} en échec {failed if failed else ''}")
    print(f"Fondamentaux récupérés pour {fund_ok} actifs (les ETF n'en ont pas)")
    print(f"Fichier écrit : {OUT_FILE.relative_to(ROOT)} ({size_kb:.0f} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
