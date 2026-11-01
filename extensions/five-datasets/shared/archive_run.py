#!/usr/bin/env python3
"""Archive only a successfully completed formal run; preserve its raw CSV unchanged."""
import csv,gzip,hashlib,pathlib,shutil,sys
BASE=pathlib.Path(__file__).resolve().parents[1]
for name in sys.argv[1:]:
 assert name in ('bank','credit','shoppers','diabetes','covertype')
 p=BASE/name;dest=p/'logs';dest.mkdir(exist_ok=True)
 timing=list(csv.DictReader((p/'raw.timing.tsv').open(),delimiter='\t'))
 assert len(timing)==1 and timing[0]['exit_code']=='0' and timing[0]['mode']=='formal'
 rows=list(csv.DictReader((p/'raw/results.csv').open()));assert len(rows)==216
 log=p/'raw.log';success=f'EXTENSION_SUCCESS dataset={name} records=216'
 with log.open() as f:
  count=0;finished=False
  for line in f:
   count+=line.startswith('EXTENSION_COMPLETE ')
   if success in line:finished=True
 assert count==216 and finished
 with log.open('rb') as f,(dest/'formal.log.gz').open('wb') as out:
  with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0) as g:shutil.copyfileobj(f,g)
 with gzip.open(dest/'formal.log.gz','rb') as f:assert hashlib.sha256(f.read()).digest()==hashlib.sha256(log.read_bytes()).digest()
 shutil.move(str(p/'raw.timing.tsv'),dest/'formal-timing.tsv')
 log.unlink()
 print(name,'formal log archived')
