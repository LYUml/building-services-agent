"""Read-only committed reusable references, separate from project facts/files."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
from .workspace import ROOT

MAX_BYTES=524288
KINDS={'all','docs','schema','example','regulation'}


def git(*args):
    executable=shutil.which('git')
    if not executable:raise ValueError('Host Git runtime required for committed reference library')
    environment={key:value for key,value in os.environ.items() if key.upper() not in
        {'GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_NAMESPACE'}}
    result=subprocess.run([executable,'-C',str(ROOT),*args],capture_output=True,check=True,env=environment)
    return result.stdout


def category(path):
    p=Path(path);parts=p.parts
    if path in ('README.md','THIRD_PARTY.md') or len(parts)==2 and parts[0]=='docs' and p.suffix=='.md':return 'docs'
    if parts[0]=='contracts' and p.suffix=='.json':return 'schema'
    if parts[0]=='examples' and p.suffix in ('.json','.md'):return 'example'
    if parts[0]=='regulations' and p.suffix=='.json':return 'regulation'
    return None


def entries(revision):
    if not isinstance(revision,str) or not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}',revision):raise ValueError('Full immutable Git commit ID required')
    if git('cat-file','-t',revision).strip()!=b'commit':raise ValueError('Reference revision must identify a commit')
    result={}
    for record in git('ls-tree','-r','-l','-z',revision,'--','README.md','THIRD_PARTY.md','docs','contracts','examples','regulations').split(b'\0'):
        if not record:continue
        header,name=record.split(b'\t',1);mode,kind,blob,size=header.split();path=name.decode('utf-8')
        group=category(path)
        if mode not in (b'100644',b'100755') or kind!=b'blob' or group is None:continue
        key=hashlib.sha256(path.encode('utf-8')).hexdigest()[:24]
        if key in result:raise ValueError('Reference identifier collision')
        result[key]=dict(id=key,path=path,kind=group,git_blob=blob.decode('ascii'),bytes=int(size),readable=int(size)<=MAX_BYTES,
            uri=f'bsa://reference/{revision}/{key}')
    return result


def catalogue(kind='all',query='',offset=0,limit=20):
    if kind not in KINDS or not isinstance(query,str) or type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=50:raise ValueError('Known reference kind and bounded nonnegative pagination required')
    revision=git('rev-parse','--verify','HEAD').decode('ascii').strip()
    rows=sorted((r for r in entries(revision).values() if (kind=='all' or r['kind']==kind) and query.casefold() in r['path'].casefold()),key=lambda r:r['path'])
    return dict(revision=revision,kind=kind,query=query,total=len(rows),references=rows[offset:offset+limit],
        next_offset=offset+limit if offset+limit<len(rows) else None,
        classification='Reusable committed references, not project facts or execution-readiness claims',design_accepted=False)


def read(revision,reference_id):
    if not isinstance(reference_id,str) or not re.fullmatch('[0-9a-f]{24}',reference_id):raise ValueError('Listed reference identifier required')
    row=entries(revision).get(reference_id)
    if row is None:raise ValueError('Reference is not in the permitted committed library')
    if not row['readable']:raise ValueError('Reference exceeds bounded text size')
    content=git('cat-file','blob',row['git_blob'])
    if len(content)!=row['bytes']:raise ValueError('Committed reference size differs')
    text=content.decode('utf-8')
    return dict(**row,revision=revision,sha256=hashlib.sha256(content).hexdigest(),content_utf8=text,
        classification='Reusable committed reference; synthetic/assumed example values are not actual project facts',
        immutable_reference=f'git:{revision}:{row["path"]}',design_accepted=False)
