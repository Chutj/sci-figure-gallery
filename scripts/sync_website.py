"""Sync an exact, committed public component snapshot into the academic website.

Default commands only report. apply writes reviewed managed paths and a lock.
Explicit --retire-media archives obsolete, hash-verified public media privately
before removing their published copies. No command commits, pushes or reads FIG.
"""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import uuid
from urllib.parse import urlsplit

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


def filesystem_path(path):
    path=Path(path)
    if os.name=='nt':
        value=str(path.resolve())
        if not value.startswith('\\\\?\\'):
            path=Path('\\\\?\\UNC\\'+value[2:] if value.startswith('\\\\') else '\\\\?\\'+value)
    return path


def write(path, content):
    path=filesystem_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_bytes(content)
    temporary.replace(path)


def retired_media(old_names, new_names, old_media, allow):
    removed=set(old_names)-set(new_names)
    if removed and not allow:
        raise ValueError('Removed component paths need separate review; use explicit --retire-media after review')
    hashes={'static/'+urlsplit(m['url']).path.lstrip('/'):m['sha256'] for m in old_media['files']}
    if not removed <= set(hashes):
        raise ValueError('Only previous approved static media may be retired')
    return {name:hashes[name] for name in sorted(removed)}


def verify_retired(root, retired):
    root=Path(root).resolve()
    for name,digest in retired.items():
        path=root/name
        if (not name.startswith('static/figures/approved/') or path.is_symlink()
                or not path.resolve().is_relative_to(root) or not path.is_file()
                or content_hash(path.read_bytes(),name)!=digest):
            raise ValueError('Retired public media changed or unsafe: '+name)


def archive_retired(root, retired, backup):
    root=Path(root).resolve();backup=Path(backup).resolve()
    if not any(backup.is_relative_to(root/private) for private in ('.gallery-local','.gallery-dev')):
        raise ValueError('Retired public media archive must stay in a private local directory')
    verify_retired(root,retired)
    for name,digest in retired.items():
        path=root/name;content=path.read_bytes();write(backup/name,content)
        if content_hash(filesystem_path(backup/name).read_bytes(),name)!=digest:
            raise ValueError('Retired media archive verification failed')
        # Only this exact reviewed file is removed; FIG is never a target.
        path.unlink()


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


def plan(website, source=ROOT, ref='HEAD', retire_media=False):
    website = Path(website).resolve(); source = Path(source).resolve()
    if website == source or website.is_relative_to(source) or source.is_relative_to(website):
        raise ValueError('Website and component must be separate repositories')
    actual = Path(command(['git','rev-parse','--show-toplevel'],website).decode().strip()).resolve()
    if actual != website:
        raise ValueError('Use the website Git repository root')
    commit, files, provenance = snapshot(source, ref)
    old = validate_component_lock(website) if (website/LOCK).exists() else None
    retired=retired_media(old['files'] if old else [],files,read(website/'data/gallery/media.json'),retire_media)
    verify_retired(website,retired)
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
    return dict(repository=REPOSITORY,commit=commit,changes=sorted(changes),retired=sorted(retired),managed_files=len(files)), files, lock


def apply(website, source=ROOT, ref='HEAD', release_bundle=None, retire_media=False):
    website = Path(website).resolve()
    report, files, lock = plan(website, source, ref,retire_media=retire_media)
    old_media=read(website/'data/gallery/media.json')
    retired=retired_media(report['retired'],[],old_media,retire_media)
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
        bindings = {'records':[e for e in prior['records'] if e['record']['id'] not in selected and e['record']['id'] in published]+entries}
    if not report['changes']:
        if bindings is not None:
            write(website/'.gallery-local/publication-records.json',encoded(bindings))
        return dict(report,applied=False,reason='Already at the exact component version')
    backup = website/'.gallery-local/component-sync'/uuid.uuid4().hex
    for name in report['changes']:
        path = website/name
        if path.is_file(): write(backup/name,path.read_bytes())
    if bindings is not None and (website/'.gallery-local/publication-records.json').exists():
        write(backup/'private-publication-records.json',(website/'.gallery-local/publication-records.json').read_bytes())
    archive_retired(website,retired,backup)
    for name in report['changes']:
        write(website/name,encoded(lock) if name==LOCK else files[name])
    validate_component_lock(website)
    command([sys.executable,'-S','scripts/validate_public_gallery.py'],website)
    if bindings is not None:
        write(website/'.gallery-local/publication-records.json',encoded(bindings))
    result = dict(report,applied=True,backup=str(backup),commit_or_push=False)
    write(backup/'report.json',encoded(result))
    return result


def capture_public(bundle, reviewed=False, source=ROOT, retire_media=False):
    if not reviewed: raise ValueError('Explicit --reviewed is required; software does not grant image permission')
    bundle=Path(bundle).resolve();source=Path(source).resolve()
    dataset=read(bundle/'data/gallery/public.json');policy=read(bundle/'data/gallery/allowlist.json')
    validate_dataset(dataset,policy); validate_media(bundle,dataset,policy)
    descriptor=read(source/'gallery-component.json'); media=read(bundle/'data/gallery/media.json')
    names={'data/gallery/public.json','data/gallery/allowlist.json','data/gallery/media.json'}
    names.update(n for n in component_paths(descriptor,media) if n.startswith('static/'))
    old_media=read(source/'data/gallery/media.json')
    old_names={n for n in component_paths(descriptor,old_media) if n.startswith('static/')}
    retired=retired_media(old_names,names,old_media,retire_media)
    archive=source/'.gallery-dev/retired-public'/uuid.uuid4().hex
    archive_retired(source,retired,archive)
    for name in names:
        path=(bundle/name)
        if path.is_symlink() or not path.resolve().is_relative_to(bundle): raise ValueError('Unsafe reviewed bundle')
        destination=source/name
        if destination.is_symlink() or not destination.resolve().is_relative_to(source): raise ValueError('Unsafe component target')
        content=path.read_bytes()
        if not destination.exists() or destination.read_bytes()!=content: write(destination,content)
    return dict(public_figures=len(dataset['records']),retired_media=len(retired),retired_archive=str(archive) if retired else None,captured=True,commit_or_push=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='mode',required=True)
    for mode in ('plan','apply'):
        p=commands.add_parser(mode);p.add_argument('--website',type=Path,required=True);p.add_argument('--ref',default='HEAD')
        p.add_argument('--retire-media',action='store_true',help='Archive and retire only exact previously approved media removed from the new manifest')
        if mode=='apply':p.add_argument('--release-bundle',type=Path)
    p=commands.add_parser('capture-public');p.add_argument('--bundle',type=Path,required=True);p.add_argument('--reviewed',action='store_true');p.add_argument('--retire-media',action='store_true')
    args=parser.parse_args()
    try:
        if args.mode=='plan':result=plan(args.website,ref=args.ref,retire_media=args.retire_media)[0]
        elif args.mode=='apply':result=apply(args.website,ref=args.ref,release_bundle=args.release_bundle,retire_media=args.retire_media)
        else:result=capture_public(args.bundle,args.reviewed,retire_media=args.retire_media)
        print(json.dumps(result,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('STOP: '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
