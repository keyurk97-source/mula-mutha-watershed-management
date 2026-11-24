"""
Mula-Mutha catchment: land-cover change analysis (2015-16 vs 2023-24)
Input : CSV exported from Google Earth Engine (gee_dynamicworld_lulc.js)
Output: change table (CSV), QA checks (printed), Figure1_LULC_change.png

Usage: python lulc_change_analysis.py MulaMutha_DynamicWorld_LULC_Area_2015_16_vs_2023_24.csv
"""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

csv_path = sys.argv[1] if len(sys.argv) > 1 else "MulaMutha_DynamicWorld_LULC_Area_2015_16_vs_2023_24.csv"
df = pd.read_csv(csv_path)

# ---- 1. Pivot to one row per class -------------------------------------
p1 = df[df["period"].str.startswith("2015-16")].set_index("class_name")["area_km2"]
p2 = df[df["period"].str.startswith("2023-24")].set_index("class_name")["area_km2"]
mapped = df["mapped_area_km2"].iloc[0]

out = pd.DataFrame({"area_2015_16_km2": p1, "area_2023_24_km2": p2})
out["change_km2"] = out["area_2023_24_km2"] - out["area_2015_16_km2"]            # Change = A(2023-24) - A(2015-16)
out["relative_change_pct"] = out["change_km2"] / out["area_2015_16_km2"] * 100   # relative to 2015-16 area
out["share_2015_16_pct"] = out["area_2015_16_km2"] / mapped * 100
out["share_2023_24_pct"] = out["area_2023_24_km2"] / mapped * 100
out["change_pct_points"] = out["share_2023_24_pct"] - out["share_2015_16_pct"]
out = out.sort_values("area_2015_16_km2", ascending=False)

# ---- 2. QA checks -------------------------------------------------------
print("QA: sum of class areas 2015-16 =", round(p1.sum(), 3), "km2 | 2023-24 =", round(p2.sum(), 3),
      "km2 | mapped area =", round(mapped, 3), "km2")
assert abs(p1.sum() - mapped) < 0.01 and abs(p2.sum() - mapped) < 0.01, "Class areas do not sum to mapped area"
assert len(p1) == len(p2) == 9, "Expected 9 Dynamic World classes in each period"
print("QA passed: class areas add up to mapped area in both periods.\n")

out.round(2).to_csv("LULC_change_table.csv")
print(out.round(2).to_string())

# ---- 3. Figure 1 (main classes only) -----------------------------------
classes = ["Built area", "Trees", "Shrub and scrub", "Crops", "Water"]
labels  = ["Built area", "Trees", "Shrub &\nscrub", "Crops", "Water"]
x = range(len(classes)); w = 0.38
fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
ax.bar([i - w/2 for i in x], out.loc[classes, "area_2015_16_km2"], w, color="#8ba8c4", label="2015-16")
ax.bar([i + w/2 for i in x], out.loc[classes, "area_2023_24_km2"], w, color="#1f4e79", label="2023-24")
for i, c in enumerate(classes):
    ax.text(i + w/2, out.loc[c, "area_2023_24_km2"] + 8, f"{out.loc[c,'change_km2']:+.0f} km²",
            ha="center", fontsize=8, fontweight="bold")
ax.set_xticks(list(x)); ax.set_xticklabels(labels)
ax.set_ylabel("Area (km²)")
ax.set_title(f"Mula–Mutha catchment land-cover change (mapped area {mapped:,.1f} km²)", fontsize=10)
ax.legend(frameon=False)
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.text(0.01, 0.01, "Source: Google/WRI Dynamic World V1 (10 m), class areas from Earth Engine export", fontsize=7)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig("Figure1_LULC_change.png")
print("\nSaved: LULC_change_table.csv, Figure1_LULC_change.png")
