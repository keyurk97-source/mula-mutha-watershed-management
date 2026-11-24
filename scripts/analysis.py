from pathlib import Path
import sys,json,re,subprocess,itertools
import numpy as np,pandas as pd,h5py
from shapely.geometry import shape,Point,box
from shapely.ops import transform
from pyproj import Transformer
from scipy.stats import kendalltau,theilslopes,spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
repo=Path(__file__).resolve().parents[1]
root=Path(sys.argv[1]) if len(sys.argv)>1 else repo/'data'
out=repo/'results'; out.mkdir(exist_ok=True)
figdir=repo/'figures'; figdir.mkdir(exist_ok=True)
poly=shape(next(f['geometry'] for f in json.load(open(root/'watershed.geojson'))['features'] if f['geometry']['type']=='Polygon'))
proj=Transformer.from_crs(4326,32643,always_xy=True).transform
A=transform(proj,poly).area/1e6
L=pd.read_csv(next(root.glob('*LULC_Area*csv')));L['period']=L.period.str[:7]; L=L.rename(columns={'class_id':'class_id'});print('area',A,'land cover',L.groupby('period').area_km2.sum())
# NetCDF coordinate metadata governs ascending latitude; matching all 10 nonzero overlaps to valid grid confirms it.
with h5py.File(root/'imdweb_xkgOGU59.nc') as f:
 g=f['rain'];r=g['rain'][:]; lat=g['lat'][:];lon=g['lon'][:];dates=pd.to_datetime(g['time'][:],unit='D',origin='2015-01-01')
w=np.array([[transform(proj,poly.intersection(box(x-.125,y-.125,x+.125,y+.125))).area/1e6 for x in lon] for y in lat]);assert abs(w.sum()-A)<.01;assert np.isfinite(r[:,w>0]).all(); assert (r[:,w>0]>=0).all()
pd.DataFrame([(y,x,w[i,j],np.nanmean(r[:,i,j])*365.3 if w[i,j]>0 else np.nan) for i,y in enumerate(lat) for j,x in enumerate(lon)],columns=['lat','lon','overlap_km2','annual_mean_mm']).to_csv(out/'rain_grid_weights.csv',index=False)
P=np.nansum(r*w,axis=(1,2))/A; daily=pd.DataFrame({'date':dates,'rain_mm':P});daily['year']=dates.year;daily['monsoon']=dates.month.isin([6,7,8,9]);annual=daily.groupby('year').rain_mm.sum().rename('P_mm').to_frame();annual['monsoon_mm']=daily[daily.monsoon].groupby('year').rain_mm.sum();annual['nonmonsoon_mm']=annual.P_mm-annual.monsoon_mm
# CN assignment from TR-55 analogous cover; flooded vegetation explicit proxy, water and snow separate.
cn={1:(70,77,'Woods good'),2:(74,80,'Pasture good'),3:(95,95,'Wetland proxy'),4:(85,89,'Row crops straight good'),5:(70,77,'Brush fair'),6:(90,92,'Residential 65% impervious proxy'),7:(91,94,'Fallow bare soil')}
x=pd.read_csv(root/'MulaMutha_LULC_HSG_cross_tab.csv');x['class_id']=x.class_id.astype(int);assert set(x.hsg_code)=={3,4}
x=x.merge(L[['period','class_id','class_name','area_km2']].rename(columns={'area_km2':'full_class_km2'}),on=['period','class_id'],validate='many_to_one');x['class_valid_km2']=x.groupby(['period','class_id']).area_km2.transform('sum');x['scaled_area_km2']=x.area_km2/x.class_valid_km2*x.full_class_km2*A/L.mapped_area_km2.iloc[0];x['CN']=x.apply(lambda z:cn[z.class_id][int(z.hsg_code)-3] if z.class_id in cn else np.nan,axis=1);x['CN_mapping']=x.class_id.map({k:v[2] for k,v in cn.items()});x.to_csv(out/'soil_landcover_CN.csv',index=False)
print('cross coverage',x.groupby('period').area_km2.sum())
# Apply nonlinear equation to daily cell rainfall, then area-weight spatially; HRU proportions assumed homogeneous across IMD cells.
# Direct runoff excludes reservoirs/open water and trace snow. Each class area adjusted to original full class area.
for period,gr in x.dropna(subset=['CN']).groupby('period'):
 print('CN',period,np.average(gr.CN,weights=gr.scaled_area_km2),'landarea',gr.scaled_area_km2.sum())
 for case,shift in [('low',-5),('central',0),('high',5)]:
  v=np.zeros(len(dates))
  for _,row in gr.iterrows():
   c=np.clip(row.CN+shift,1,98);s=25400/c-254
   q=np.where(r>.2*s,(r-.2*s)**2/(r+.8*s),0)
   qmean=np.nansum(q*w,axis=(1,2))/A
   v+=qmean*row.scaled_area_km2/1000
  daily[f'Q_{period}_{case}_MCM']=v;annual[f'Q_{period}_{case}_MCM']=daily.groupby('year')[f'Q_{period}_{case}_MCM'].sum()
annual['Q_change_MCM']=annual['Q_2023-24_central_MCM']-annual['Q_2015-16_central_MCM'];annual['Q_change_pct']=100*annual.Q_change_MCM/annual['Q_2015-16_central_MCM'];daily.to_csv(out/'daily_rainfall_runoff.csv',index=False)
# PDF text extraction directly from historical source; preserve page & dates; coordinate filters.
def filt(df):return df[df.apply(lambda z:poly.covers(Point(z.Longitude,z.Latitude)),axis=1)].copy()
if (root/'pre-monsoon_2014-2024.pdf').exists():
 pretext=subprocess.check_output(['pdftotext','-layout',str(root/'pre-monsoon_2014-2024.pdf'),'-'],text=True)
 rows=[]; unparsed=[]
 for i,page in enumerate(pretext.split('\f'),1):
  for line in page.splitlines():
   if not re.match(r'\s*Maharashtra\s+Pune\s+',line,re.I):continue
   m=re.match(r'\s*Maharashtra\s+Pune\s{2,}(.*?)\s{2,}(.*?)\s+([\d.]+)\s+([\d.]+)\s+(\d{2}-\d{2}-\d{2})\s+([-\d.]+)\s*$',line)
   if m:
    b,v,la,lo,dt,dep=m.groups();rows.append((b,v,float(la),float(lo),dt,float(dep),i))
   else:unparsed.append(line)
 pre=pd.DataFrame(rows,columns=['Block','Village','Latitude','Longitude','Date','Depth_m_bgl','PDF_page']);print('pre raw Pune',len(pre),'unparsed',len(unparsed),unparsed[:3]);
 pre=filt(pre);pre['Year']=pd.to_datetime(pre.Date,format='%d-%m-%y').dt.year;pre=pre.drop_duplicates(['Latitude','Longitude','Date','Depth_m_bgl']);pre['Source']='CGWB pre-monsoon PDF';
else:
 pre=pd.read_csv(root/'pre_monsoon_catchment.csv')
 print('Using archived catchment pre-monsoon extract; original national PDF is optional.')
post=filt(pd.read_csv(root/'Pune_CGWB_post_monsoon_2015_2023 (1).csv')).drop_duplicates(['Latitude','Longitude','Date','Depth_m_bgl']);post['Source']='CGWB post-monsoon PDF extracted CSV';
q=pd.read_csv(root/'gwl_manual_quarterly_cgwb_mh_2021_2025.csv');q=filt(q);q['dt']=pd.to_datetime(q['Data Acquisition Time'],format='%d-%m-%Y %H:%M');q['Year']=q.dt.dt.year;q['Month']=q.dt.dt.month
# Supplement only 2024 November from quarterly; no combining different measurement rounds in historical series.
q24=q[(q.Year==2024)&(q.Month==11)].copy();q24['Village']=q24.Station;q24['Date']=q24.dt.dt.strftime('%d-%m-%y');q24['Depth_m_bgl']=q24['Groundwater Level Quarterly Manual (meter)'];q24['Source']='CGWB quarterly CSV November 2024';
cols=['Block','Village','Latitude','Longitude','Date','Depth_m_bgl','Year','Source'];post=pd.concat([post[cols+['PDF_page']],q24[cols]],ignore_index=True);pre=pre[pre.Year.between(2015,2024)];post=post[post.Year.between(2015,2024)]
for d in [pre,post]:
 d['lat_key']=d.Latitude.round(5);d['lon_key']=d.Longitude.round(5)
 d['well_id']=d.lat_key.astype(str)+'_'+d.lon_key.astype(str)
 assert (d.Depth_m_bgl>=0).all();print('well',len(d),d.well_id.nunique(),d.groupby('Year').size().to_dict(), 'duplicate',d.duplicated(['well_id','Year']).sum())
pre.to_csv(out/'pre_monsoon_catchment.csv',index=False);post.to_csv(out/'post_monsoon_catchment.csv',index=False);q.to_csv(out/'quarterly_catchment.csv',index=False)
# If same well-year duplicates, aggregate median; inspect separately.
pa=pre.groupby(['well_id','Year']).agg(well=('Village','first'),pre_depth_m=('Depth_m_bgl','median')).reset_index().merge(post.groupby(['well_id','Year']).agg(post_well=('Village','first'),post_depth_m=('Depth_m_bgl','median')).reset_index(),on=['well_id','Year']);pa['rise_m']=pa.pre_depth_m-pa.post_depth_m;pa.to_csv(out/'seasonal_pairs.csv',index=False); print('pairs',len(pa),pa.well_id.nunique(),pa.rise_m.describe(), 'signs', (pa.rise_m>0).sum(),(pa.rise_m==0).sum(),(pa.rise_m<0).sum());print(pa.groupby('Year').rise_m.agg(['size','median']))
tr=[]
for season,d in [('May',pre),('November',post)]:
 for id,g in d.groupby('well_id'):
  h=g.groupby('Year').Depth_m_bgl.median();
  if len(h)>=6:
   k=kendalltau(h.index,h.values);s=theilslopes(h.values,h.index);tr.append([season,id,g.Village.iloc[0],len(h),s.slope,k.statistic,k.pvalue])
tr=pd.DataFrame(tr,columns=['season','well_id','well','n','Sen_m_per_year','Kendall_tau','p_value']);tr.to_csv(out/'well_trends.csv',index=False);print(tr.to_string(index=False))
annual=annual.join(pa.groupby('Year').rise_m.agg(['median','size']).rename(columns={'median':'median_rise_m','size':'paired_wells'}));
a=annual.dropna(subset=['median_rise_m']);print('monsoon rise spearman',spearmanr(a.monsoon_mm,a.median_rise_m))
# ET validity: missing area tested with 0.5 to 1.5 times valid mean (not measured).
et=pd.read_csv(root/'MulaMutha_Annual_ET_2015_2024.csv').set_index('Year');annual=annual.join(et);annual['P_MCM']=annual.P_mm*A/1000;annual['ET_proxy_MCM']=annual.ET_mm*A/1000;annual['ET_low_MCM']=annual.ET_mm*(annual.Valid_area_km2+.5*(A-annual.Valid_area_km2))/1000;annual['ET_high_MCM']=annual.ET_mm*(annual.Valid_area_km2+1.5*(A-annual.Valid_area_km2))/1000;annual['P_minus_ET_proxy_MCM']=annual.P_MCM-annual.ET_proxy_MCM
# This is a diagnostic residual, not storage change, because direct runoff production not outlet flow.
annual['unallocated_P_ET_Q_MCM']=annual.P_MCM-annual.ET_proxy_MCM-annual['Q_2023-24_central_MCM']
# 2024 GSDA/CGWB assessment-unit table (ha-m to MCM). No spatial overlap allocation.
b=pd.DataFrame([['Haveli',110053.65,12202.4,721.3,11481.1,7079.4,61.7],['Mulshi',44401.58,8566.5,606.9,7959.6,1564.2,19.7],['Pune City',11500,1307.6,77.7,1229.9,623.2,50.7],['Maval',78615.53,8994.5,493.7,8500.7,1891.5,22.3],['Velhe',23194.43,5357.4,381.9,4975.5,449.6,9.0],['Bhor',34070.24,3834.7,227.4,3607.3,1673.3,46.4]],columns=['block','area_ha','recharge_ham','natural_discharge_ham','extractable_ham','extraction_ham','official_stage_pct']);b['extraction_depth_mm']=b.extraction_ham*1000/b.area_ha;b.to_csv(out/'regional_benchmarks.csv',index=False)
# GEC-style historical rainfall recharge sensitivity; normal proxy = ten-year mean, non-monsoon eligible if proxy normal > 10% annual; excludes other recharge sources.
threshold=annual.P_mm.mean()*.1;eligible=annual.nonmonsoon_mm.mean()>=threshold;print('threshold',threshold,'nonmonsoon average',annual.nonmonsoon_mm.mean(),'eligible',eligible)
rec=[]
for yr,row in annual.iterrows():
 for period,g in L.groupby('period'):
  v=g.set_index('class_name').area_km2*A/g.mapped_area_km2.iloc[0];eff=A-v['Water']-.7*v['Built area']
  for rif in [.02,.07,.13]:
   rm=max(0,min(row.monsoon_mm,3000)-threshold)*eff*rif/1000;rn=min(row.nonmonsoon_mm,3000)*eff*rif/1000 if eligible else 0
   rec.append([yr,period,rif,eff,rm,rn,rm+rn])
rec=pd.DataFrame(rec,columns=['year','period','RIF','effective_area_km2','monsoon_recharge_MCM','nonmonsoon_recharge_MCM','annual_rain_recharge_MCM']);rec.to_csv(out/'recharge.csv',index=False)
# benchmark demand scenarios observed blocks, not inferred actual catchment pumping. Include exact 2024 values.
bench=b[b.block.isin(['Haveli','Mulshi','Pune City'])].extraction_depth_mm
rates={'low':bench.min(),'central':bench.median(),'high':bench.max()};print('demand rates',rates)
strategies=[('Baseline',0,0),('Pumping -10%',.1,0),('Pumping -20%',.2,0),('Recharge +10%',0,.1),('Combined',.2,.1)];rr=[]
for _,row in rec[rec.period.eq('2023-24')].iterrows():
 for name,cut,inc in strategies:
  for dcase,dep in rates.items():
   R=row.annual_rain_recharge_MCM*(1+inc);D=dep*A/1000*(1-cut);E=.9*R;rr.append([row.year,row.RIF,dcase,name,R,.1*R,D,E-D,100*D/E if E>0 else np.nan])
s=pd.DataFrame(rr,columns=['year','RIF','demand_case','strategy','rain_recharge_MCM','natural_discharge_allowance_MCM','assumed_extraction_MCM','rain_only_margin_MCM','extraction_to_net_rain_recharge_pct']);s.to_csv(out/'scenarios.csv',index=False)
summary=s.groupby('strategy',sort=False).rain_only_margin_MCM.agg(['min','median','max',lambda a:100*(a>=0).mean()]).rename(columns={'<lambda_0>':'nonnegative_case_pct'});summary.to_csv(out/'scenario_summary.csv');print(summary);print(s[(s.year==2023)&(s.RIF==.07)&(s.demand_case=='central')].to_string(index=False));
for period in ['2015-16','2023-24']:
 annual[f'R_{period}_MCM']=rec[(rec.period==period)&(rec.RIF==.07)].set_index('year').annual_rain_recharge_MCM
annual.to_csv(out/'annual_results.csv');print(annual[['P_mm','monsoon_mm','ET_mm','Q_2015-16_central_MCM','Q_2023-24_central_MCM','Q_change_pct','R_2015-16_MCM','R_2023-24_MCM','unallocated_P_ET_Q_MCM']].round(2).to_string());print('means',annual.mean(numeric_only=True).to_string())
# Station check using coordinates, not river names. Nearest outside station not assumed to drain polygon.
if (root/'river_discharge_manual_daily_cwc_mh_2001_2025.csv').exists():
 dis=pd.read_csv(root/'river_discharge_manual_daily_cwc_mh_2001_2025.csv',usecols=['Station','Latitude','Longitude','River']).drop_duplicates();dis=dis.dropna(subset=['Latitude','Longitude']);poly_m=transform(proj,poly);dis['distance_to_boundary_km']=dis.apply(lambda z:poly_m.distance(transform(proj,Point(z.Longitude,z.Latitude)))/1000,axis=1);dis.sort_values('distance_to_boundary_km').head(15).to_csv(out/'nearest_discharge_stations.csv',index=False);print(dis.sort_values('distance_to_boundary_km').head(4).to_string(index=False))
else:
 print('Raw CWC discharge file not bundled; retaining archived station coverage check, if present. No observed discharge enters model.')
# Two results visuals, each a single multi-panel figure.
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
fig,ax=plt.subplots(2,2,figsize=(11,7),constrained_layout=True);years=annual.index
ax[0,0].plot(years,annual.P_mm,'o-',label='Rainfall');ax[0,0].plot(years,annual.ET_mm,'s-',label='ET (87% coverage)');ax[0,0].set(ylabel='Depth (mm/year)',title='A. Rainfall and evapotranspiration');ax[0,0].legend(fontsize=9)
ax[0,1].plot(years,annual['Q_2015-16_central_MCM'],'o-',label='2015–16 cover');ax[0,1].plot(years,annual['Q_2023-24_central_MCM'],'s-',label='2023–24 cover');ax[0,1].set(ylabel='Direct runoff (MCM/year)',title='B. SCS-CN runoff under identical rain');ax[0,1].legend(fontsize=9)
ax[1,0].plot(years,annual['R_2015-16_MCM'],'o-',label='2015–16 cover');ax[1,0].plot(years,annual['R_2023-24_MCM'],'s-',label='2023–24 cover');ax[1,0].set(ylabel='Rain recharge (MCM/year)',title='C. Rainfall recharge (7% RIF)');ax[1,0].legend(fontsize=9)
for yr,g in pa.groupby('Year'):ax[1,1].scatter(np.full(len(g),yr),g.rise_m,s=15,alpha=.55,color='#566b81')
ax[1,1].plot(years,annual.median_rise_m,'o',color='#b4552b',label='Year median');ax[1,1].axhline(0,color='gray',lw=.7);ax[1,1].set(ylabel='May–November rise (m)',title='D. Matched well observations');ax[1,1].legend(fontsize=9)
for a in ax.ravel():a.set_xticks([2015,2017,2019,2021,2023,2024]);a.tick_params(axis='x',labelrotation=30);a.grid(alpha=.18);a.set_xlabel('Year')
fig.suptitle('Figure 1. Observed hydroclimate and conditional hydrological estimates',fontweight='bold',fontsize=14);fig.savefig(figdir/'Figure_1_hydrology.png',dpi=240);plt.close(fig)
fig,ax=plt.subplots(1,2,figsize=(11,4.6),constrained_layout=True,gridspec_kw={'width_ratios':[1.05,1.3]});order=[i[0] for i in strategies];su=summary.loc[order];ax[0].barh(order,su.nonnegative_case_pct,color=['#8a9ba8']*4+['#276e75']);ax[0].invert_yaxis();ax[0].set(xlim=(0,100),xlabel='Non-negative cases (%)',title='A. Robustness across 90 cases per lever');
for i,v in enumerate(su.nonnegative_case_pct):ax[0].text(v+1,i,f'{v:.1f}%',va='center',fontsize=9)
ss=s[(s.RIF==.07)&(s.demand_case=='central')].pivot(index='strategy',columns='year',values='rain_only_margin_MCM').loc[order,[2023,2017,2019]];lim=max(abs(ss.min().min()),abs(ss.max().max()));im=ax[1].imshow(ss,cmap='RdBu',vmin=-lim,vmax=lim,aspect='auto');ax[1].set_xticks(range(3),['Dry 2023','Typical 2017','Wet 2019']);ax[1].set_yticks(range(5),order);ax[1].set_title('B. Rain-only resource margin (MCM)');
for i in range(5):
 for j in range(3):v=ss.iloc[i,j];ax[1].text(j,i,f'{v:+.1f}',ha='center',va='center',color='white' if abs(v)>.55*lim else '#17212a',fontsize=9)
fig.colorbar(im,ax=ax[1],shrink=.8,label='MCM/year');fig.suptitle('Figure 2. Groundwater-management screening under uncertainty',fontweight='bold',fontsize=14);fig.savefig(figdir/'Figure_2_management.png',dpi=240);plt.close(fig)
