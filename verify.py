"""Overenie vystupov build.py voci zdrojovym datam NLC. Pouzitie: python verify.py DATA OUT"""
import os, sys, glob
import numpy as np, pandas as pd, pyogrio, shapely, pyproj

DATA, OUT = sys.argv[1], sys.argv[2]
pyproj.network.set_network_enabled(False)
pct = [50, 99, 100]


def shp(v):
    return sorted(glob.glob(os.path.join(OUT, v, "*.shp")))


def load(v, cols):
    return pd.concat([pyogrio.read_dataframe(f, columns=cols) for f in shp(v)], ignore_index=True)


src = pyogrio.read_dataframe(os.path.join(DATA, "JPRL_JTSK03.gpkg"), columns=["idjprl", "IDPS"])
uniq = src.idjprl[~src.idjprl.duplicated(keep=False)]
print(f"Zdroj NLC JTSK03: {len(src)} polygonov")

# 1) uplnost: kazdy polygon prave raz v kazdej variante
for v in ["SHP_JTSK03", "SHP_SJTSK", "SHP_ETRS89"]:
    a = load(v, ["IDJPRL", "IDPS", "DREVINY"])
    print(f"[{v}] suborov {len(shp(v))}, polygonov {len(a)} (zdroj {len(src)}), "
          f"rovnaka mnozina IDJPRL: {sorted(a.IDJPRL) == sorted(src.idjprl)}, "
          f"porasty s pripojenym opisom: {a.IDPS.notna().sum()} / {src.IDPS.notna().sum()}")

# 2) JTSK03: geometria bez zmeny voci zdroju
mine = load("SHP_JTSK03", ["IDJPRL"]).set_index("IDJPRL").loc[uniq]
ref = pyogrio.read_dataframe(os.path.join(DATA, "JPRL_JTSK03.gpkg"), columns=["idjprl"]).set_index("idjprl").loc[uniq]
hd = shapely.hausdorff_distance(mine.geometry.values, shapely.force_2d(ref.geometry.values))
print("[SHP_JTSK03 vs NLC JTSK03] Hausdorff p50/p99/max [m]:", np.percentile(hd, pct).round(4))
del mine, ref

# 3) S-JTSK: nezavisle porovnanie s oficialnou S-JTSK verziou od NLC (JPRL.gpkg)
mine = load("SHP_SJTSK", ["IDJPRL"]).set_index("IDJPRL").loc[uniq]
ref = pyogrio.read_dataframe(os.path.join(DATA, "JPRL.gpkg"), columns=["idjprl"]).set_index("idjprl").loc[uniq]
hd = shapely.hausdorff_distance(mine.geometry.values, shapely.force_2d(ref.geometry.values))
print("[SHP_SJTSK vs NLC S-JTSK] Hausdorff p50/p99/max [m]:", np.percentile(hd, pct).round(4))
del mine, ref

# 4) ETRS89: spat do JTSK03 kľucom GKU ETRS89->JTSK03 (Ferianc 2011) a porovnanie so zdrojom
fwd = pyproj.Transformer.from_pipeline(
    "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=push +v_3 +step +proj=cart +ellps=GRS80 "
    "+step +proj=helmert +x=-485.021 +y=-169.465 +z=-483.839 +rx=7.786342 +ry=4.397554 +rz=4.102655 +s=0 "
    "+convention=coordinate_frame +step +inv +proj=cart +ellps=bessel +step +proj=pop +v_3 "
    "+step +proj=krovak +lat_0=49.5 +lon_0=24.8333333333333 +alpha=30.2881397527778 +k=0.9999 +x_0=0 +y_0=0 +ellps=bessel")
e = load("SHP_ETRS89", ["IDJPRL"]).set_index("IDJPRL").loc[uniq]
j = load("SHP_JTSK03", ["IDJPRL"]).set_index("IDJPRL").loc[uniq]
ce, cj = shapely.get_coordinates(e.geometry.values), shapely.get_coordinates(j.geometry.values)
x, y = fwd.transform(ce[:, 0], ce[:, 1])
d = np.hypot(x - cj[:, 0], y - cj[:, 1])
print("[SHP_ETRS89 -> JTSK03 klucom GKU vs zdroj] odchylka p50/p99/max [m]:", np.percentile(d, pct).round(4), "bodov", len(d))
del e, j

# 5) DXF: rovnaky pocet obrysov a popisov ako v SHP, rovnaky rozsah
for v_dxf, v_shp in [("DXF_JTSK03", "SHP_JTSK03"), ("DXF_SJTSK", "SHP_SJTSK")]:
    bad = 0
    for f in shp(v_shp):
        base = os.path.splitext(os.path.basename(f))[0]
        s = pyogrio.read_dataframe(f, columns=[])
        dx = pyogrio.read_dataframe(os.path.join(OUT, v_dxf, base + ".dxf"))
        rings = sum(len(shapely.get_rings(shapely.get_parts(g))) for g in s.geometry.values)
        n_poly = (dx.Layer != "JPRL_OZNACENIE").sum(); n_txt = (dx.Layer == "JPRL_OZNACENIE").sum()
        if n_poly != rings or n_txt != len(s) or np.abs(dx.total_bounds - s.total_bounds).max() > 0.001:
            bad += 1; print("  NESEDI", v_dxf, base, n_poly, rings, n_txt, len(s))
    print(f"[{v_dxf}] suborov {len(shp(v_shp))}, nesuladov s SHP: {bad}")
