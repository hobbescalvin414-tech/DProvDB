#!/usr/bin/env python3
"""Download official UCI inputs, validate entire files, preserve originals, scale selected columns."""
import argparse, csv, gzip, hashlib, io, json, math, pathlib, shutil, subprocess, zipfile
from datetime import datetime, timezone
ROOT = pathlib.Path(__file__).resolve().parents[3]
BASE = ROOT / 'extensions/five-datasets'
DATA = ROOT / '.runtime/five-datasets'
CONFIG = {
 'bank': dict(id=222, n=45211, width=17, archive='bank+marketing.zip', member='bank-full.csv', delimiter=';', fields=[('age','age'),('balance','balance'),('duration','duration'),('campaign','campaign'),('previous','previous')], unit='bank marketing record'),
 'credit': dict(id=350, n=30000, width=25, fields=[('X5','age'),('X1','limit_bal'),('X12','bill_amt1'),('X18','pay_amt1'),('X19','pay_amt2')], unit='client record'),
 'shoppers': dict(id=468, n=12330, width=18, fields=[('ProductRelated','productrelated'),('ProductRelated_Duration','productrelated_duration'),('BounceRates','bouncerates'),('ExitRates','exitrates'),('PageValues','pagevalues')], unit='web session'),
 'diabetes': dict(id=296, n=101766, width=50, archive='diabetes+130-us+hospitals+for+years+1999-2008.zip', member='diabetic_data.csv', fields=[('time_in_hospital','time_in_hospital'),('num_lab_procedures','num_lab_procedures'),('num_medications','num_medications'),('number_outpatient','number_outpatient'),('number_inpatient','number_inpatient')], unit='hospital encounter, NOT patient'),
 'covertype': dict(id=31, n=581012, width=55, archive='covertype.zip', member='covtype.data.gz', fields=[('c0','elevation'),('c2','slope'),('c3','horizontal_distance_to_hydrology'),('c4','vertical_distance_to_hydrology'),('c5','horizontal_distance_to_roadways')], unit='30x30 metre forest cartographic cell, not personal data'),
}
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def fetch(url, path):
 path.parent.mkdir(parents=True, exist_ok=True)
 tmp=path.with_suffix(path.suffix+'.partial')
 subprocess.run(['curl','-fsSL','--retry','3','--connect-timeout','30','--max-time','1800',url,'-o',str(tmp)],check=True)
 tmp.replace(path)
def find_member(z, name):
 matches=[p for p in z.namelist() if pathlib.PurePosixPath(p).name==name]
 if matches:return z.read(matches[0])
 for p in z.namelist():
  if p.endswith('.zip'):
   try:return find_member(zipfile.ZipFile(io.BytesIO(z.read(p))),name)
   except KeyError:pass
 raise KeyError(name)
def rows(path,c):
 with path.open(newline='') as f:
  reader=csv.reader(f,delimiter=c.get('delimiter',','))
  header=['c'+str(i) for i in range(c['width'])] if c['id']==31 else next(reader)
  assert len(header)==c['width'], (path,header)
  for i,row in enumerate(reader,1):
   assert len(row)==len(header), (path,i,'truncated or malformed row',len(row))
   yield dict(zip(header,row))
def prepare(name, offline=False):
 c=CONFIG[name]; folder=DATA/name; folder.mkdir(parents=True,exist_ok=True)
 metadata_url=f"https://archive.ics.uci.edu/api/dataset?id={c['id']}"
 meta=DATA/(name+'-metadata.json')
 if not meta.exists():
  if offline:raise FileNotFoundError(meta)
  fetch(metadata_url,meta)
 metadata=json.loads(meta.read_text()); metadata=metadata.get('data',metadata)
 assert metadata['uci_id']==c['id']
 source=metadata['data_url']; archive_path=None
 if 'archive' in c:
  source=f"https://archive.ics.uci.edu/static/public/{c['id']}/{c['archive']}"
  archive_path=DATA/'downloads'/(name+'.zip')
  try:
   z=zipfile.ZipFile(archive_path); assert z.testzip() is None
  except (FileNotFoundError,zipfile.BadZipFile,AssertionError):
   if offline:raise
   fetch(source,archive_path);z=zipfile.ZipFile(archive_path);assert z.testzip() is None
  raw=folder/c['member']
  raw.write_bytes(find_member(z,c['member']))
  if raw.suffix=='.gz':
   original=raw;raw=folder/'covtype.data'
   with gzip.open(original,'rb') as f,raw.open('wb') as out:shutil.copyfileobj(f,out)
 else:
  raw=folder/'original.csv'
  existing=DATA/(name+'.csv')
  if not raw.exists() and existing.exists():shutil.copyfile(existing,raw)
  try:assert sum(1 for _ in rows(raw,c))==c['n']
  except (FileNotFoundError,AssertionError):
   if offline:raise
   fetch(source,raw)
 selected=[a for a,b in c['fields']]; output=[b for a,b in c['fields']]
 lo=[math.inf]*5; hi=[-math.inf]*5; missing=[0]*5; count=0; patients=set(); all_missing={}
 for row in rows(raw,c):
  count+=1
  if name=='diabetes':patients.add(row['patient_nbr'])
  for k,v in row.items():
   if v.strip() in ('','?','NA','NaN'):all_missing[k]=all_missing.get(k,0)+1
  for j,key in enumerate(selected):
   value=row[key]
   if value.strip() in ('','?','NA','NaN'):missing[j]+=1;continue
   x=float(value);assert math.isfinite(x)
   lo[j]=min(lo[j],x);hi[j]=max(hi[j],x)
 assert count==c['n'], (name,count,c['n'])
 assert not any(missing), (name,'missing selected values: define handling before continuing',missing)
 assert all(a<b for a,b in zip(lo,hi))
 processed=folder/'processed.csv'
 with processed.open('w',newline='') as f:
  writer=csv.writer(f,lineterminator='\n');writer.writerow(output)
  for row in rows(raw,c):
   writer.writerow([format((float(row[key])-lo[j])*1000/(hi[j]-lo[j]),'.12g') for j,key in enumerate(selected)])
 manifest=dict(dataset=name,uci_id=c['id'],name=metadata['name'],repository_url=metadata['repository_url'],metadata_url=metadata_url,download_url=source,uci_last_updated=metadata.get('last_updated'),prepared_utc=datetime.now(timezone.utc).isoformat(),raw_member=c.get('member','data.csv'),raw_rows=count,raw_columns=c['width'],processed_rows=count,missing_selected=missing,raw_missing_counts=all_missing,unit=c['unit'],sampling='none; all records retained',transform='z = 1000 * (x - observed_min) / (observed_max - observed_min); 12 significant digits; no integer rounding, imputation, clipping or row deletion',domain='[0,1000] in all five fields; bounds derived from PUBLIC benchmark data, not a private DP bounds estimation',fields=[dict(source=a,name=b,min=lo[j],max=hi[j],scaled_min=0,scaled_max=1000) for j,(a,b) in enumerate(c['fields'])],files=dict(raw=dict(path=str(raw.relative_to(ROOT)),sha256=sha(raw)),processed=dict(path=str(processed.relative_to(ROOT)),sha256=sha(processed)),metadata=dict(path=str(meta.relative_to(ROOT)),sha256=sha(meta))))
 if archive_path:manifest['files']['archive']=dict(path=str(archive_path.relative_to(ROOT)),sha256=sha(archive_path))
 if patients:manifest['distinct_patient_ids']=len(patients)
 dest=BASE/name;dest.mkdir(exist_ok=True)
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
 print(name,count,'rows validated',manifest['files']['processed']['sha256'],flush=True)
 return manifest

def schema():
 lines=['---','databases:']
 for name,c in CONFIG.items():
  lines += [f'- database: "{name}"','  dialect: "POSTGRESQL"','  namespace: "public"','  tables:','    - table: "records"','      columns:']
  for _,field in c['fields']:lines += [f'        - name: "{field}"','          type: "c"','          lb: 0','          ub: 1000']
 (BASE/'shared/schema.yaml').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--dataset',choices=list(CONFIG),action='append');p.add_argument('--offline',action='store_true');args=p.parse_args()
 schema()
 for name in args.dataset or CONFIG:prepare(name,args.offline)
