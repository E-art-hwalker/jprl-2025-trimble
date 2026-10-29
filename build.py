"""JPRL 2025 -> SHP (JTSK03, S-JTSK, ETRS89) + DXF (JTSK03, S-JTSK), split by lesny celok."""
import os, re, sys, json, time, unicodedata
import numpy as np, pandas as pd, geopandas as gpd, shapely, pyogrio, pyproj

DATA, OUT = sys.argv[1], sys.argv[2]
YEAR = 2026
pyproj.network.set_network_enabled(False)  # grid GKU je lokalne v PROJ_USER_WRITABLE_DIRECTORY

# explicitne zvolene oficialne operacie GKU (ziadny "ballpark" fallback)
T_JTSK = pyproj.transformer.TransformerGroup("EPSG:8353", "EPSG:5514", always_xy=True).transformers[0]
T_ETRS = pyproj.transformer.TransformerGroup("EPSG:8353", "EPSG:4258", always_xy=True).transformers[0]
assert "S-JTSK [JTSK03] to S-JTSK (1)" in T_JTSK.description, T_JTSK.description
assert "S-JTSK [JTSK03] to ETRS89 (1)" in T_ETRS.description, T_ETRS.description
print("JTSK :", T_JTSK.description); print("ETRS :", T_ETRS.description, flush=True)


def num(s):
    return pd.to_numeric(s.str.strip(), errors="coerce")


# ---- opis: jeden riadok na IDPS ----
o = pd.read_parquet(os.path.join(DATA, "opis.parquet"))
o["ET_n"], o["VYM_n"], o["VEK_n"], o["RZP_n"] = num(o.ET), num(o.VYM), num(o.VEK), num(o.RZP)
o["zas_et"] = sum(num(o[f"zas{i}"]).fillna(0) for i in range(1, 9))
# hlavna etaz: ET 0 ak existuje, inak najvacsia vymera z ET 1-4, ET 9 (zvysky) len ak nic ine
o["prio"] = np.select([o.ET_n == 0, o.ET_n.between(1, 4)], [0, 1], 2)
o = o.sort_values(["IDPS", "prio", "VYM_n", "ET_n"], ascending=[True, True, False, True])
main = o.drop_duplicates("IDPS").set_index("IDPS")
real = o[o.ET_n != 9]
agg = pd.DataFrame({
    "ET_POCET": o.groupby("IDPS").size(),
    "VEK_MIN": real[real.VEK_n > 0].groupby("IDPS").VEK_n.min(),
    "VEK_MAX": real.groupby("IDPS").VEK_n.max(),
    "ZAS_SPOLU": o.groupby("IDPS").zas_et.sum(),
})


def dreviny(m):
    parts = []
    for i in range(1, 9):
        dr, zs = m[f"DR{i}"].fillna("").str.strip(), num(m[f"ZS{i}"]).fillna(0)
        parts.append((dr + " " + zs.astype(int).astype(str)).where((dr != "") & (zs > 0), ""))
    return pd.concat(parts, axis=1).apply(lambda r: ", ".join(x for x in r if x), axis=1, raw=True)


s = lambda c: main[c].str.strip()
attr = pd.DataFrame(index=main.index)
attr["ET_HL"] = main.ET_n.astype("Int64")
attr = attr.join(agg)
attr["VEK"] = main.VEK_n.astype("Int64")
attr["VEK_AKT"] = (main.VEK_n + (YEAR - main.RZP_n)).where(main.VEK_n > 0).astype("Int64")
attr["VEK_MIN"] = attr.VEK_MIN.astype("Int64"); attr["VEK_MAX"] = attr.VEK_MAX.astype("Int64")
attr["ZAS_SPOLU"] = attr.ZAS_SPOLU.round(0).astype("Int64")
attr["DREVINY"] = dreviny(main)
for i in (1, 2, 3):
    attr[f"DR{i}"] = s(f"DR{i}"); attr[f"ZS{i}"] = num(main[f"ZS{i}"]).astype("Int64")
attr["ZASHA1"] = num(main.zasha1).astype("Int64")
for c, src in [("KL", "KL"), ("PK", "pk"), ("SOP", "SOP"), ("ZOP", "ZOP"), ("ZK", "ZK"), ("RS", "RS"),
               ("HSLT", "HSLT"), ("LT1", "LT1"), ("EXPOZ", "expoz"), ("SKLON", "sklon"), ("RD", "RD"),
               ("OD", "OD"), ("SOBH", "sobh"), ("PRAVOPLAT", "PravoPlat"), ("NS", "NS"), ("UEV", "UEV"),
               ("CHVU", "CHVU"), ("PHO", "PHO")]:
    attr[c] = s(src)
attr["POZNAMKA"] = main["Poznámka"].str.strip().str.replace(r"\s+", " ", regex=True).str.slice(0, 200)
del o, main, real, agg
print("opis agregovany:", len(attr), flush=True)

# ---- geometria ----
cols = ["IDPS", "DC", "CP", "PS", "KPL", "TxLC", "RZP", "RUP", "Plocha", "IDOLP", "DP", "PC", "TXDP_SKR", "idjprl"]
meta, _, _, geom, fields = (None,) * 5
meta = pyogrio.read_dataframe(os.path.join(DATA, "JPRL_JTSK03.gpkg"), columns=cols, read_geometry=False)
_, _, wkb, field_data = pyogrio.raw.read(os.path.join(DATA, "JPRL_JTSK03.gpkg"), columns=[])[0:4]
assert len(wkb) == len(meta)
print("geometrie:", len(wkb), flush=True)


def oznac(m):
    # porast: dielec + ciastkova plocha + porastova skupina (ako v IDPS, napr. 1299c, 1299c1, 2404_3)
    cp = m.CP.fillna("_").replace("", "_")
    ps = m.PS.fillna(0).astype(int)
    por = m.DC.astype(str) + np.where((cp == "_") & (ps == 0), "", cp) + np.where(ps > 0, ps.astype(str), "")
    olp = m.DP.astype(str) + "/" + m.PC.astype(str)  # ostatny lesny pozemok: dielec/plocha
    return pd.Series(np.where(m.IDPS.notna(), por, olp), index=m.index)


def ascii_name(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"^LESNY CELOK\s+", "", t.upper())
    return re.sub(r"[^A-Z0-9]+", "_", t).strip("_")[:40]


def xform(geoms, t):
    return shapely.transform(geoms, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1], errcheck=True)))


LAYERS = [("JPRL_POROSTY", 3), ("JPRL_INE_POZEMKY", 8), ("JPRL_OZNACENIE", 7)]


def write_dxf(path, geoms, labels, is_porast):
    """DXF R12 (AC1009): uzavrete POLYLINE + TEXT, suradnice v metroch, bez Z."""
    out = ["0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n9\n$DWGCODEPAGE\n3\nANSI_1250\n",
           "9\n$EXTMIN\n10\n%.3f\n20\n%.3f\n9\n$EXTMAX\n10\n%.3f\n20\n%.3f\n" % tuple(shapely.total_bounds(geoms)),
           "0\nENDSEC\n0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n%d\n" % len(LAYERS)]
    for name, color in LAYERS:
        out.append("0\nLAYER\n2\n%s\n70\n0\n62\n%d\n6\nCONTINUOUS\n" % (name, color))
    out.append("0\nENDTAB\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n")
    pts = shapely.point_on_surface(geoms)
    for g, lab, por, pt in zip(geoms, labels, is_porast, pts):
        lay = "JPRL_POROSTY" if por else "JPRL_INE_POZEMKY"
        for ring in shapely.get_rings(shapely.get_parts(g)):
            c = shapely.get_coordinates(ring)[:-1]
            out.append("0\nPOLYLINE\n8\n%s\n66\n1\n70\n1\n10\n0.0\n20\n0.0\n30\n0.0\n" % lay)
            out.append("".join("0\nVERTEX\n8\n%s\n10\n%.3f\n20\n%.3f\n30\n0.0\n" % (lay, x, y) for x, y in c))
            out.append("0\nSEQEND\n8\n%s\n" % lay)
        x, y = pt.x, pt.y
        out.append("0\nTEXT\n8\nJPRL_OZNACENIE\n10\n%.3f\n20\n%.3f\n30\n0.0\n40\n4.0\n1\n%s\n72\n1\n11\n%.3f\n21\n%.3f\n31\n0.0\n73\n2\n"
                   % (x, y, lab, x, y))
    out.append("0\nENDSEC\n0\nEOF\n")
    with open(path, "w", encoding="cp1250", newline="\r\n") as f:
        f.write("".join(out))


meta["OZNAC"] = oznac(meta)
meta = meta.join(attr, on="IDPS")
meta["PLOCHA_HA"] = (meta.Plocha / 10000).round(4)
meta = meta.drop(columns=["Plocha"]).rename(columns={"TXDP_SKR": "DRUH_POZ", "idjprl": "IDJPRL"})
order = ["IDJPRL", "IDPS", "IDOLP", "OZNAC", "KPL", "TxLC", "DC", "CP", "PS", "DP", "PC", "DRUH_POZ", "RZP", "RUP",
         "PLOCHA_HA"] + [c for c in attr.columns]
meta = meta[order]

variants = {"SHP_JTSK03": "EPSG:8353", "SHP_SJTSK": "EPSG:5514", "SHP_ETRS89": "EPSG:4258",
            "DXF_JTSK03": None, "DXF_SJTSK": None}
for v in variants:
    os.makedirs(os.path.join(OUT, v), exist_ok=True)

index_rows, t0 = [], time.time()
groups = meta.groupby("KPL", sort=True).indices
if os.environ.get("ONLY"):
    groups = {k: groups[k] for k in os.environ["ONLY"].split(",")}
n_fixed = [0]
for n, (kpl, idx) in enumerate(groups.items(), 1):
    names = meta.TxLC.iloc[idx].dropna().unique()
    lcname = ascii_name(names[0]) if len(names) else "BEZ_NAZVU"
    base = f"JPRL2025_{kpl}_{lcname}"
    g03 = shapely.force_2d(shapely.from_wkb(wkb[idx]))
    bad = ~shapely.is_valid(g03)
    if bad.any():  # opravit, ale ponechat len polygony
        g03[bad] = [shapely.union_all(shapely.get_parts(shapely.make_valid(x))[
            np.isin(shapely.get_type_id(shapely.get_parts(shapely.make_valid(x))), [3, 6])]) for x in g03[bad]]
        n_fixed[0] += int(bad.sum())
    gj = xform(g03, T_JTSK); ge = xform(g03, T_ETRS)
    df = meta.iloc[idx].reset_index(drop=True)
    for v, geoms, crs in [("SHP_JTSK03", g03, "EPSG:8353"), ("SHP_SJTSK", gj, "EPSG:5514"), ("SHP_ETRS89", ge, "EPSG:4258")]:
        gdf = gpd.GeoDataFrame(df, geometry=geoms, crs=crs)
        pyogrio.write_dataframe(gdf, os.path.join(OUT, v, base + ".shp"), encoding="UTF-8",
                                promote_to_multi=True)
    write_dxf(os.path.join(OUT, "DXF_JTSK03", base + ".dxf"), g03, df.OZNAC.values, df.IDPS.notna().values)
    write_dxf(os.path.join(OUT, "DXF_SJTSK", base + ".dxf"), gj, df.OZNAC.values, df.IDPS.notna().values)
    b3, bj, be = shapely.total_bounds(g03), shapely.total_bounds(gj), shapely.total_bounds(ge)
    index_rows.append({"KPL": kpl, "NAZOV_LC": names[0] if len(names) else "", "SUBOR": base,
                       "POCET_POLYGONOV": len(idx), "POROSTY": int(df.IDPS.notna().sum()),
                       "PLOCHA_HA": round(df.PLOCHA_HA.sum(), 2),
                       "ETRS89_LON_MIN": round(be[0], 6), "ETRS89_LAT_MIN": round(be[1], 6),
                       "ETRS89_LON_MAX": round(be[2], 6), "ETRS89_LAT_MAX": round(be[3], 6)})
    if n % 25 == 0 or n == len(groups):
        print(f"{n}/{len(groups)} {kpl} {time.time()-t0:.0f}s", flush=True)

pd.DataFrame(index_rows).to_csv(os.path.join(OUT, "ZOZNAM_LESNYCH_CELKOV.csv"), index=False, encoding="utf-8-sig", sep=";")
print("opravene neplatne geometrie:", n_fixed[0]); print("HOTOVO", time.time() - t0)
