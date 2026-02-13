
import pandas as pd
import re

def parse_classement(val):
    if val is None:
        return 0
    try:
        if pd.isna(val):
            return 0
    except:
        pass
    s = str(val).strip().upper()
    if s in ("", "D", "NR", "NP", "DAI", "DB", "AR", "T", "RET", "DIS", "SOL", "NONE", "NAN", "0", "0.0"):
        return 0
    m = re.search(r'\d+', s)
    return int(m.group()) if m else 0
