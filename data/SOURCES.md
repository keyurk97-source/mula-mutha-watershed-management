# Data sources and provenance

| Dataset | File(s) | Source / access |
|---|---|---|
| IMD daily gridded rainfall, 2015–2024 | `imdweb_xkgOGU59.nc` | [IMD gridded data](https://imdweb.lwcc.in/) |
| Watershed boundary and river network | `watershed.geojson`, `watershed.zip` | Supplied study polygon; original delineation and outlet provenance not confirmed |
| Dynamic World V1, 10 m | `MulaMutha_DynamicWorld_LULC_Area_2015_16_vs_2023_24 (1).csv` | [Earth Engine catalog](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1) |
| HiHydroSoil v2.0, 250 m | `MulaMutha_HSG_Area.csv`, `MulaMutha_HSG_250m.tif`, `MulaMutha_LULC_HSG_cross_tab.csv` | [Community catalog](https://gee-community-catalog.org/projects/hihydro_soil/) |
| MODIS annual ET | `MulaMutha_Annual_ET_2015_2024.csv` | [MOD16A2GF v6.1](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD16A2GF) |
| CGWB pre-monsoon 2014–2024 | `pre_monsoon_catchment.csv` (filtered 2015–2024) | [CGWB](https://cgwb.gov.in/); original PDF `pre-monsoon_2014-2024.pdf` |
| CGWB November 2015–2023 | `Pune_CGWB_post_monsoon_2015_2023 (1).csv` | [CGWB](https://cgwb.gov.in/); original `post-monsoon_wl_1994-2023_compressed(1).pdf` |
| CGWB quarterly 2021–2025 | `gwl_manual_quarterly_cgwb_mh_2021_2025.csv` | [National Water Data Portal](https://nwdp.nwic.gov.in/en/dataset/gwl-manual-quarterly-central-ground-water-board-department) |
| 2024 groundwater resource assessment | [`regional_benchmarks.csv`](../results/regional_benchmarks.csv) | [GSDA report listing](https://gsda.maharashtra.gov.in/en-groundwater-resource-estimation/), 2024 assessment PDF p.102 (printed p.83) |
| CWC daily discharge 2001–2025 | [`nearest_discharge_stations.csv`](../results/nearest_discharge_stations.csv) | [National Water Data Portal](https://nwdp.nwic.gov.in/dataset/river-discharge-manual-dailly-central-water-commission-cwc); coverage check only |

## Original documents not bundled

The national groundwater PDFs, full CWC discharge CSV and official groundwater assessment reports are not included in this browser-upload package. The original source links above identify where to obtain them. For complete source-to-extract audit, provide the professor with authorized access to the original files through the course data repository or official portals. Do not publicly redistribute third-party datasets or reports unless their terms allow it. Some reports carry official-use markings. No data license is asserted by this repository.

To repeat the original pre-monsoon PDF parsing, place `pre-monsoon_2014-2024.pdf` in `data/` and install Poppler (`pdftotext` on PATH). To repeat the CWC station coverage audit, place `river_discharge_manual_daily_cwc_mh_2001_2025.csv` in `data/`. Neither is needed to reproduce the main model using the archived extract and inputs. The original November PDF is not parsed by the model; the Pune extract is its input.
