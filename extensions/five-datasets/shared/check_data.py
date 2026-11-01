#!/usr/bin/env python3
"""Independent full-file semantic checks for the official dataset variants."""
import collections,csv,json,pathlib,sys
from prepare_data import BASE,ROOT,CONFIG,rows,sha
for name in sys.argv[1:] or CONFIG:
 m=json.loads((BASE/name/'manifest.json').read_text());c=CONFIG[name];p=ROOT/m['files']['raw']['path']
 assert sha(p)==m['files']['raw']['sha256']
 count=0;ids=set();targets=collections.Counter()
 key={'bank':'y','credit':'Y','shoppers':'Revenue','diabetes':'readmitted','covertype':'c54'}[name]
 for row in rows(p,c):
  count+=1
  if name=='credit':ids.add(int(row['ID']))
  if name=='diabetes':ids.add(row['encounter_id'])
  targets[row[key]]+=1
 assert count==c['n']
 if name=='credit':assert ids==set(range(1,30001))
 if name=='diabetes':assert len(ids)==101766
 expected={'bank':{'no':39922,'yes':5289},'shoppers':{'FALSE':10422,'TRUE':1908}}
 if name in expected:assert {k.upper():v for k,v in targets.items()}=={k.upper():v for k,v in expected[name].items()}
 result=dict(passed=True,rows=count,target_field_not_used_in_queries=key,target_counts=dict(targets),unique_record_ids=len(ids) if ids else None,raw_sha256=sha(p))
 dest=BASE/name/'logs';dest.mkdir(exist_ok=True);(dest/'data-semantic-validation.json').write_text(json.dumps(result,indent=2)+'\n')
 print(name,'full-file semantic checks passed')
