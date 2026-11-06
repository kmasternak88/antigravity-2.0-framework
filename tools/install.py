#!/usr/bin/env python3
"""Safe overlay installer: dry run by default, no overwrite of different files."""
import argparse, json, shutil
from pathlib import Path

def install(source,target,apply=False):
    source=source.resolve();target=target.resolve()
    if source==target or source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError('Source and target must be separate, non-nested directories')
    planned=[];conflicts=[]
    for p in sorted(source.rglob('*')):
        rel=p.relative_to(source)
        if any(x in {'__pycache__','.git','output'} for x in rel.parts) or rel.parts[:2] in [('.governance','state'),('.governance','evidence')]:continue
        if p.is_symlink():raise ValueError('Source symlink rejected')
        if not p.is_file():continue
        dest=target/rel
        # Resolve existing parent symlinks as well as leaf links.
        if not dest.resolve().is_relative_to(target):raise ValueError('Target path escapes root')
        if dest.is_symlink():raise ValueError('Target symlink rejected')
        if dest.exists():
            if not dest.is_file() or dest.read_bytes()!=p.read_bytes():conflicts.append(rel.as_posix())
        else:planned.append(rel.as_posix())
    if conflicts:return {'status':'CONFLICT','files':conflicts,'written':0}
    if apply:
        for rel in planned:
            dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/rel,dest)
    return {'status':'APPLIED' if apply else 'DRY_RUN','planned':planned,'written':len(planned) if apply else 0}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    try:r=install(Path(__file__).resolve().parents[1],Path(a.target),a.apply)
    except (ValueError,OSError) as e:r={'status':'ERROR','reason':str(e)}
    print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['status'] in {'APPLIED','DRY_RUN'} else 2)
