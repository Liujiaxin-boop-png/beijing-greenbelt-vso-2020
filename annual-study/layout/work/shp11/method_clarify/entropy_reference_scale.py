"""Change the entropy reference from 1 km to 500 m on the final GIS boundary.

The three-scale pooled extrema, indicator direction, original 500 m
assessment panel, and intersection-area regional averaging stay fixed.
Reference observations (cell, year) receive equal weight during fitting.
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
CORE = HERE.parent / "core"
YEARS = list(range(2015, 2026))
REVERSE = ["LBI", "MCR", "ALLDIST"]


def entropy_weights(standard):
    proportions = standard.div(standard.sum(axis=0))
    # Evaluate the 0 log 0 limit as zero.
    positive = proportions.to_numpy()
    log_p = np.zeros_like(positive)
    np.log(positive, out=log_p, where=positive > 0)
    utility = 1 + (positive * log_p).sum(axis=0) / np.log(len(positive))
    return pd.Series(utility / utility.sum(), index=standard.columns)


def main():
    params = json.loads((CORE / "parameters.json").read_text(encoding="utf-8"))
    fields = params["fields"]
    lower = pd.Series(params["min"])[fields]
    upper = pd.Series(params["max"])[fields]
    weights = pd.Series(params["weights"])[fields]
    annual = pd.read_csv(CORE / "区域六项逐年指数与分项.csv").set_index("year")

    def load_panel(name, expected_grids):
        p = pd.read_csv(CORE / name)
        assert p.year.unique().tolist() == YEARS
        assert len(p) == expected_grids * len(YEARS)
        assert len(p.grid_id.unique()) == expected_grids
        assert not p.duplicated(["grid_id", "year"]).any()
        assert np.isfinite(p[fields + ["area_km2", "ER6"]]).all().all()
        assert (p.area_km2 > 0).all()
        z = (p[fields] - lower) / (upper - lower)
        z[REVERSE] = 1 - z[REVERSE]
        # CSV roundoff may move an endpoint several ulps outside [0,1].
        assert z.min().min() > -1e-12 and z.max().max() < 1 + 1e-12
        return p, z.clip(0, 1)

    _, coarse = load_panel("六项逐格逐年原值与得分_1000m.csv.gz", 1297)
    np.testing.assert_allclose(entropy_weights(coarse), weights, rtol=0, atol=1e-12)
    panel, fine = load_panel("六项逐格逐年原值与得分.csv.gz", 4478)
    np.testing.assert_allclose(fine.dot(weights), panel.ER6, rtol=0, atol=1e-12)

    alternate = entropy_weights(fine)
    panel["ER_500ref"] = fine.dot(alternate)
    rows = []
    for year, g in panel.groupby("year"):
        published = np.average(g.ER6, weights=g.area_km2)
        assert np.isclose(published, annual.at[year, "ER6"], rtol=0, atol=1e-12)
        rows.append({
            "year": year,
            "grids": len(g),
            "area_km2": g.area_km2.sum(),
            "ER_1000ref": published,
            "ER_500ref": np.average(g.ER_500ref, weights=g.area_km2),
            "grid_spearman": g.ER6.rank().corr(g.ER_500ref.rank()),
        })
    yearly = pd.DataFrame(rows).set_index("year")
    for key in ["1000ref", "500ref"]:
        yearly["annual_change_" + key] = yearly["ER_" + key].diff()

    w_table = pd.DataFrame({"weight_1000ref": weights, "weight_500ref": alternate})
    w_table["difference"] = alternate - weights
    w_table.to_csv(HERE / "熵权参照尺度_权重.csv", index_label="indicator", encoding="utf-8-sig", float_format="%.15g")
    yearly.to_csv(HERE / "熵权参照尺度_500m逐年结果.csv", encoding="utf-8-sig", float_format="%.15g")
    changes = yearly.loc[2025, ["ER_1000ref", "ER_500ref"]] - yearly.loc[2015, ["ER_1000ref", "ER_500ref"]]
    print(w_table.to_string())
    print(yearly.to_string())
    print("Net changes:", changes.to_dict())
    print("Spearman range:", yearly.grid_spearman.min(), yearly.grid_spearman.max())
    print("Same annual signs:", int((np.sign(yearly.annual_change_1000ref.dropna()) == np.sign(yearly.annual_change_500ref.dropna())).sum()))


if __name__ == "__main__":
    main()
