"""Sync an exact, committed public component snapshot into the academic website.

Default commands only report. apply writes reviewed managed paths and a lock;
no command commits, pushes, deletes files or reads FIG originals.
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import uuid

from check_gallery_component import (LOCK, REPOSITORY, component_paths, content_hash,
    validate_component_lock)
from public_gallery_schema import validate_dataset
from public_gallery_media import validate_media

ROOT = Path(__file__).resolve().parents[1]


def command(args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    if result.returncode:
        raise ValueError('Command failed: '+' '.join(map(str,args))+'\n'+result.stderr.decode('utf-8',errors='replace'))
    return result.stdout


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)+'\n').encode('utf-8')


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_bytes(content)
    temporary.replace(path)


def snapshot(source=ROOT, ref='HEAD'):
    source = Path(source).resolve()
    if command(['git','status','--porcelain'], source).strip():
        raise ValueError('Commit/review component changes before syncing a version')
    commit = command(['git','rev-parse',ref+'^{commit}'], source).decode().strip()
    def blob(name): return command(['git','show',commit+':'+name], source)
    descriptor = json.loads(blob('gallery-component.json'))
    media = json.loads(blob('data/gallery/media.json'))
    names = component_paths(descriptor, media)
    # A large gallery exceeds Windows' command-line length if every media path
    # is an argument. Archive the committed tree, then read only manifest entries.
    archive = command(['git','archive','--format=tar',commit], source)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as bundle:
        for member in bundle:
            if member.name not in names: continue
            if not member.isfile():
                raise ValueError('Unsafe or unexpected component archive entry')
            files[member.name] = bundle.extractfile(member).read()
    if set(files) != set(names):
        raise ValueError('Component manifest references uncommitted/missing files')
    provenance = json.loads(blob('PROVENANCE.json'))
    return commit, files, provenance


def plan(website, source=ROOT, ref='HEAD'):
    website = Path(website).resolve(); source = Path(source).resolve()
    if website == source or website.is_relative_to(source) or source.is_relative_to(website):
        raise ValueError('Website and component must be separate repositories')
    actual = Path(command(['git','rev-parse','--show-toplevel'],website).decode().strip()).resolve()
    if actual != website:
        raise ValueError('Use the website Git repository root')
    commit, files, provenance = snapshot(source, ref)
    old = validate_component_lock(website) if (website/LOCK).exists() else None
    if old and not set(old['files']) <= set(files):
        raise ValueError('Removed component paths need separate review; no automatic deletion')
    changes = []
    for name, content in files.items():
        path = website/name
        if path.is_symlink() or not path.resolve().is_relative_to(website):
            raise ValueError('Unsafe website target')
        if path.exists():
            current = content_hash(path.read_bytes(),name)
            if not old and current not in {content_hash(content,name),provenance['initial_site_files'].get(name)}:
                raise ValueError('Initial website file differs from reviewed source/provenance: '+name)
            if current != content_hash(content,name): changes.append(name)
        else: changes.append(name)
    lock = dict(schema_version=1, repository=REPOSITORY, commit=commit,
                files={name:content_hash(content,name) for name,content in sorted(files.items())})
    if not (website/LOCK).exists() or read(website/LOCK) != lock: changes.append(LOCK)
    return dict(repository=REPOSITORY,commit=commit,changes=sorted(changes),managed_files=len(files)), files, lock


def apply(website, source=ROOT, ref='HEAD', release_bundle=None):
    website = Path(website).resolve()
    report, files, lock = plan(website, source, ref)
    bindings = None
    if release_bundle:
        bundle = Path(release_bundle).resolve()
        if not bundle.is_relative_to((website/'.gallery-local').resolve()):
            raise ValueError('Private release bindings must stay in website .gallery-local')
        entries = read(bundle/'private-bindings.json')['records']
        # Validate actual evidence before updating the private publication bindings.
        sys.path.insert(0,str(website/'scripts'))
        from export_public_gallery import prepared_record
        from public_gallery_schema import APPROVAL_FIELDS
        catalog = {r['id']:r for r in read(website/'.gallery-local/catalog.json')['records']}
        inventory = {r['id']:r for r in read(website/'.gallery-local/inventory.json')['records']}
        dataset = json.loads(files['data/gallery/public.json'])
        published = {r['id']:r for r in dataset['records']}
        for entry in entries:
            record = entry['record']
            if published.get(record['id']) != record:
                raise ValueError('Release binding does not match the pinned public version')
            prepared_record(website,entry,{k:record[k] for k in APPROVAL_FIELDS},catalog,inventory)
        prior = read(website/'.gallery-local/publication-records.json') if (website/'.gallery-local/publication-records.json').exists() else {'records':[]}
        selected = {entry['record']['id'] for entry in entries}
        bindings = {'records':[e for e in prior['records'] if e['record']['id'] not in selected]+entries}
    if not report['changes']:
        if bindings is not None:
            write(website/'.gallery-local/publication-records.json',encoded(bindings))
        return dict(report,applied=False,reason='Already at the exact component version')
    backup = website/'.gallery-local/component-sync'/uuid.uuid4().hex
    for name in report['changes']:
        path = website/name
        if path.is_file(): write(backup/name,path.read_bytes())
    for name in report['changes']:
        write(website/name,encoded(lock) if name==LOCK else files[name])
    validate_component_lock(website)
    command([sys.executable,'-S','scripts/validate_public_gallery.py'],website)
    if bindings is not None:
        write(website/'.gallery-local/publication-records.json',encoded(bindings))
    result = dict(report,applied=True,backup=str(backup),commit_or_push=False)
    write(backup/'report.json',encoded(result))
    return result


def capture_public(bundle, reviewed=False, source=ROOT):
    if not reviewed: raise ValueError('Explicit --reviewed is required; software does not grant image permission')
    bundle=Path(bundle).resolve();source=Path(source).resolve()
    dataset=read(bundle/'data/gallery/public.json');policy=read(bundle/'data/gallery/allowlist.json')
    validate_dataset(dataset,policy); validate_media(bundle,dataset,policy)
    descriptor=read(source/'gallery-component.json'); media=read(bundle/'data/gallery/media.json')
    names={'data/gallery/public.json','data/gallery/allowlist.json','data/gallery/media.json'}
    names.update(n for n in component_paths(descriptor,media) if n.startswith('static/'))
    old_media=read(source/'data/gallery/media.json')
    old_names={n for n in component_paths(descriptor,old_media) if n.startswith('static/')}
    if not old_names <= names: raise ValueError('Removing approved media needs separate review; no automatic deletion')
    for name in names:
        path=(bundle/name)
        if path.is_symlink() or not path.resolve().is_relative_to(bundle): raise ValueError('Unsafe reviewed bundle')
        destination=source/name
        if destination.is_symlink() or not destination.resolve().is_relative_to(source): raise ValueError('Unsafe component target')
        content=path.read_bytes()
        if not destination.exists() or destination.read_bytes()!=content: write(destination,content)
    return dict(public_figures=len(dataset['records']),captured=True,commit_or_push=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='mode',required=True)
    for mode in ('plan','apply'):
        p=commands.add_parser(mode);p.add_argument('--website',type=Path,required=True);p.add_argument('--ref',default='HEAD')
        if mode=='apply':p.add_argument('--release-bundle',type=Path)
    p=commands.add_parser('capture-public');p.add_argument('--bundle',type=Path,required=True);p.add_argument('--reviewed',action='store_true')
    args=parser.parse_args()
    try:
        if args.mode=='plan':result=plan(args.website,ref=args.ref)[0]
        elif args.mode=='apply':result=apply(args.website,ref=args.ref,release_bundle=args.release_bundle)
        else:result=capture_public(args.bundle,args.reviewed)
        print(json.dumps(result,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('STOP: '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
