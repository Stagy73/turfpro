
import pandas as pd
import numpy as np

def eval_formula(df, formula_str):
    f_py = formula_str.replace('?', ' if ').replace(':', ' else ').replace('""', '0')

    def calc(row):
        ctx = row.to_dict()
        ctx.update({'log': np.log, 'sqrt': np.sqrt, 'max': max, 'min': min, 'abs': abs})
        try:
            return float(eval(f_py, {"__builtins__": {}}, ctx))
        except:
            return 0.0

    return df.apply(calc, axis=1)


def run_app():
    import streamlit as st
    st.title("🚀 Algo Builder PRO")
    st.success("Architecture modulaire prête.")
