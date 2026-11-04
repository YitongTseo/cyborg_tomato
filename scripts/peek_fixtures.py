"""Original quick-look script from the first session (kept for provenance).

Decodes the three sample .raw fixtures in Nigel's ETL bundle with the formula
mV = mv_span * int32 / 2**32 and prints their basic stats. Superseded by
raw_loader.py + inventory.py, which handle any folder and .mat files too.

Usage: python -I scripts/peek_fixtures.py <folder containing extract/etl-raw-to-parquet-zip>
"""
import sys, numpy as np, datetime as dt
T = sys.argv[1] + "/extract/etl-raw-to-parquet-zip/psr-file-handler/test"
def cfg(p):
    d={}
    for line in open(p):
        k,_,v=line.strip().partition(',')
        if k and k!='parameter': d[k]=v.strip()
    return d
for raw,txt in [("raw_files_dir/one/test.raw","raw_files_dir/one/test.txt"),
                ("raw_files_dir/correct_raw_and_config/P1.raw","raw_files_dir/correct_raw_and_config/P1.txt"),
                ("raw_files_dir/1.raw","raw_files_dir/1.txt")]:
    c=cfg(f"{T}/{txt}"); f=np.fromfile(f"{T}/{raw}",dtype='<i4')
    sr=float(c['sample_rate']); span=float(c['mv_span'])
    mv=span*f.astype(np.float64)/2**32
    st=dt.datetime.utcfromtimestamp(float(c['start_timestamp']))
    print(f"== {raw}: {len(f):,} samples @ {sr} Hz = {len(f)/sr/3600:.2f} h; start {st}Z; "
          f"mV min/mean/max = {mv.min():.2f}/{mv.mean():.2f}/{mv.max():.2f}; first5={np.round(mv[:5],2).tolist()}")
try:
    import pyarrow.parquet as pq
    t=pq.read_table(f"{T}/parquet_no_timezone/year=2021/month=3/day=15/plant_id=viv-lab0-bb-1/5b25c6d6b692433a99c56ead164dc67b.parquet")
    print("== parquet sample:", t.num_rows, "rows; schema:", [(f.name,str(f.type)) for f in t.schema])
    print(t.slice(0,3).to_pandas())
except Exception as e: print("parquet read skipped:", e)
