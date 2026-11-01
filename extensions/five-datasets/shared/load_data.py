#!/usr/bin/env python3
"""Load validated CSV into new databases only, never replace an existing database."""
import argparse,json,pathlib,subprocess
from prepare_data import ROOT,BASE,CONFIG,sha

def sql(db,query):
 return subprocess.check_output(['docker','exec','dprovdb-repro-db','psql','-X','-v','ON_ERROR_STOP=1','-U','link','-d',db,'-Atc',query],text=True).strip()
def load(name):
 m=json.loads((BASE/name/'manifest.json').read_text());p=ROOT/m['files']['processed']['path']
 assert sha(p)==m['files']['processed']['sha256']
 exists=sql('postgres',f"SELECT 1 FROM pg_database WHERE datname='{name}'")
 if exists:raise RuntimeError(f'Database {name} already exists; refuse to replace it. Validate separately to reuse.')
 sql('postgres',f'CREATE DATABASE {name}')
 cols=', '.join(f'"{v["name"]}" double precision NOT NULL CHECK ("{v["name"]}" BETWEEN 0 AND 1000)' for v in m['fields'])
 sql(name,f'CREATE TABLE records ({cols})')
 target='/workspace/'+m['files']['processed']['path']
 sql(name,f"COPY records FROM '{target}' WITH (FORMAT csv, HEADER true)")
 sql(name,'ANALYZE records')
 n=int(sql(name,'SELECT COUNT(*) FROM records'))
 assert n==m['processed_rows']
 for f in m['fields']:assert sql(name,f'SELECT MIN({f["name"]}),MAX({f["name"]}) FROM records')=='0|1000'
 dest=BASE/name/'logs';dest.mkdir(exist_ok=True)
 (dest/'database-validation.json').write_text(json.dumps(dict(database=name,rows=n,columns=[v['name'] for v in m['fields']],all_column_domains=[0,1000],processed_sha256=sha(p)),indent=2)+'\n')
 print(name,n,'loaded and validated')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('datasets',nargs='+',choices=list(CONFIG));a=p.parse_args()
 for name in a.datasets:load(name)
