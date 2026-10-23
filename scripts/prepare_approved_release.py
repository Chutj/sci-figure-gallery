"""Owner-only bridge: export an approved private Website plan as a public bundle.

Uses the existing local approval/evidence gate; no commit, push or FIG writes.
Private evidence bindings remain inside the Website's ignored directory.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def prepare(website, approval, output):
    website=Path(website).resolve();output=Path(output).resolve()
    approval=Path(approval)
    if not approval.is_absolute(): approval=website/approval
    private=(website/'.gallery-local').resolve()
    if not output.is_relative_to(private) or output==private:
        raise ValueError('Release bundle must be inside the Website .gallery-local directory')
    adapter=website/'scripts/gallery_workflow.py'
    if not adapter.is_file():
        raise ValueError('The owner local FIG workflow adapter is unavailable; public builds do not require it')
    sys.path.insert(0,str(website/'scripts'))
    spec=importlib.util.spec_from_file_location('owner_gallery_workflow',adapter)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    decision,batch,report,entries,dataset,policy=module.publication_plan(approval,website)
    files,new_media=module.media_payloads(website,entries)
    selected={e['record']['id'] for e in entries}
    media=module.load(website/'data/gallery/media.json',dict(schema_version=1,files=[]))
    media['files']=[m for m in media['files'] if m['id'] not in selected]+new_media
    from urllib.parse import urlsplit
    for entry in media['files']:
        name='static/'+urlsplit(entry['url']).path.lstrip('/')
        if name not in files:files[name]=(website/name).read_bytes()
    files.update({'data/gallery/public.json':module.encoded(dataset),'data/gallery/allowlist.json':module.encoded(policy),
        'data/gallery/media.json':module.encoded(media),'private-bindings.json':module.encoded({'records':entries})})
    if output.exists():raise ValueError('Use a new release-bundle directory; existing exports are preserved')
    for name,content in files.items():
        target=(output/name)
        if not target.resolve().is_relative_to(output):raise ValueError('Unsafe bundle path')
        module.importer.atomic_write(target,content)
    from public_gallery_media import validate_media
    from public_gallery_schema import validate_dataset
    validate_dataset(dataset,policy);validate_media(output,dataset,policy)
    return dict(batch=decision['batch'],public_figures=len(dataset['records']),bundle=str(output),
        note='Only explicit reviewed IDs were applied. private-bindings.json must never be committed or copied upstream.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--website',type=Path,required=True);parser.add_argument('--approval',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    try:print(json.dumps(prepare(args.website,args.approval,args.output),indent=2))
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('STOP: '+str(exc),file=sys.stderr);raise SystemExit(1)
