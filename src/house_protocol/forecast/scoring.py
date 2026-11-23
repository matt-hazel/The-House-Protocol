# scoring how good the forecasts were resolved


import pandas as pd

CALIBRATION_EDGES = [0.0, 0.05, 0.10, 0.20, 0.35, 0.50, 1.0]



def _resolved(ledger: pd.DataFrame, kind: str) -> pd.DataFrame:
    # forecasts of one kind whose outcome is known, outcome as a float
    
    done = ledger.loc[(ledger["kind"] == kind) & ledger["outcome"].notna()].copy()
    done["outcome"] = done["outcome"].astype(float)
    
    
    return done



def score(ledger: pd.DataFrame, kind: str) -> pd.DataFrame:
    # one row per track and model: brier score and skill against clima.
    
    done = _resolved(ledger, kind)
    done["error"] = (done["probability"] - done["outcome"]) ** 2
    
    
    reference = done.loc[
        done["model"] == "climatology", ["track", "issued_on", "probability"]
    ].rename(columns={"probability": "reference"})
    
    
    #judge every model on same dates its climatology reference was issued
    
    done = done.merge(reference, on=["track", "issued_on"])
    done["reference_error"] = (done["reference"] - done["outcome"]) ** 2
    
    
    card = done.groupby(["track", "model"]).agg(
        n=("error", "size"),
        horizon=("horizon_days", "first"),
        brier=("error","mean"),
        reference_brier=("reference_error", "mean"),
        mean_p = ("probability", "mean"),
        hit_rate = ("outcome", "mean"),
    )
    
    card["skill"] = 1 - card["brier"] / card["reference_brier"]
    card["eff_n"] = card["n"] / card["horizon"]
    
    
    return card.drop(columns=["horizon", "reference_brier"])


def calibration(ledger: pd.DataFrame, kind: str, track: str, model: str) -> pd.DataFrame:
    # per probability pin how many forecasts, the aver forecast, and how oftern
    
    done = _resolved(ledger, kind)
    done = done.loc[(done["track"] == track) & (done["model"] == model)]
    
    bins = pd.cut(done["probability"], CALIBRATION_EDGES, include_lowest=True)
    
    
    return done.groupby(bins, observed=True).agg(
        n = ("outcome", "size"),
        mean_p = ("probability", "mean"),
        hit_rate = ("outcome", "mean"),
    )
    