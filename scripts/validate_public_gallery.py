"""CI/public validator. Does not import Pillow or read .gallery-local/."""
import sys
sys.dont_write_bytecode = True
import argparse
import json
import re
import subprocess
from pathlib import Path
from public_gallery_schema import validate_dataset
from public_gallery_media import validate_media

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ('.gallery-local/', '.gallery-dev/', 'public/', 'resources/_gen/', 'assets/gallery-private/', 'static/gallery-private/')


def validate(root=ROOT, output=None):
    if (root/'gallery-component.lock.json').exists():
        from check_gallery_component import validate_component_lock
        validate_component_lock(root)
    elif (root/'gallery-component.json').exists():
        from check_gallery_component import component_paths
        descriptor=json.loads((root/'gallery-component.json').read_text(encoding='utf-8'))
        media=json.loads((root/'data/gallery/media.json').read_text(encoding='utf-8'))
        for name in component_paths(descriptor,media):
            path=root/name
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError('Missing or unsafe component export: '+name)
    dataset = json.loads((root/'data/gallery/public.json').read_text(encoding='utf-8-sig'))
    policy = json.loads((root/'data/gallery/allowlist.json').read_text(encoding='utf-8-sig'))
    count = validate_dataset(dataset,policy)
    validate_media(root, dataset, policy, output)
    tracked = subprocess.check_output(['git','-C',str(root),'ls-files','-z'],text=True).split('\0')
    bad = [p for p in tracked if p.startswith(FORBIDDEN)
           or Path(p).suffix.lower() in ('.pdf','.sqlite','.db','.pem','.key')
           or Path(p).name == 'private-bindings.json'
           or Path(p).name == '.env' or Path(p).name.startswith('.env.')]
    if bad:
        raise ValueError('Private/generated files tracked: '+', '.join(bad))
    if output:
        output = output.resolve()
        if not (output/'gallery/index.html').is_file():
            raise ValueError('Built Gallery page missing')
        for path in output.rglob('*'):
            if path.is_symlink():
                raise ValueError('Published symlinks are not allowed')
            if not path.is_file():
                continue
            name = path.relative_to(output).as_posix()
            if path.suffix.lower() in ('.pdf','.pem','.key'):
                raise ValueError('Private document/credential file in published output: '+name)
            if '.gallery-local' in name or 'gallery-private' in name:
                raise ValueError('Private publish path: '+name)
            if path.suffix.lower() in ('.html','.xml','.json','.css','.js','.txt'):
                text = path.read_text(encoding='utf-8-sig')
                if re.search(r'\.gallery-local|gallery-private/|file:///|[A-Za-z]:[\\/](?:Users|01_PhD)',text,re.I):
                    raise ValueError('Private path in published output: '+name)
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Additionally inspect the actual Hugo publish directory')
    args=parser.parse_args()
    try:
        count=validate(output=args.output)
        print(f'PASS: {count} explicitly approved public figures; tracking'+(' and publish output' if args.output else '')+' validated.')
    except (ValueError,OSError,KeyError,TypeError,subprocess.CalledProcessError) as exc:
        print('STOP: '+str(exc),file=sys.stderr);return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
