"""Verify the website's vendored Gallery snapshot without network/private data."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

REPOSITORY = 'https://github.com/Chutj/sci-figure-gallery'
LOCK = 'gallery-component.lock.json'
RASTER = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.tif', '.tiff'}


def content_hash(content, name):
    if Path(name).suffix.lower() not in RASTER:
        content = content.replace(b'\r\n', b'\n')
    return hashlib.sha256(content).hexdigest()


def safe_name(name):
    if not isinstance(name,str):raise ValueError('Unsafe component path')
    path = PurePosixPath(name)
    if (not re.fullmatch(r'[A-Za-z0-9._/-]+',name) or path.is_absolute() or '..' in path.parts
            or str(path) != name or name.startswith(('.', 'public/', 'resources/'))
            or path.suffix.lower() in {'.pdf', '.sqlite', '.pem', '.key'}):
        raise ValueError('Unsafe component path')
    return name


def component_paths(descriptor, media):
    if (descriptor.get('schema_version') != 1 or descriptor.get('repository') != REPOSITORY
            or not isinstance(descriptor.get('files'), list)):
        raise ValueError('Invalid Gallery component descriptor')
    files = set(descriptor['files'])
    if len(files) != len(descriptor['files']):
        raise ValueError('Duplicate component source path')
    required = {'gallery-component.json', 'layouts/gallery.html', 'assets/js/gallery.js',
        'data/gallery/public.json', 'data/gallery/allowlist.json', 'data/gallery/media.json',
        'scripts/check_gallery_component.py', 'scripts/validate_public_gallery.py'}
    if not required <= files:
        raise ValueError('Incomplete Gallery component')
    from urllib.parse import urlsplit
    for entry in media['files']:
        parsed = urlsplit(entry['url'])
        if parsed.scheme != 'https' or parsed.netloc != 'chutj.github.io' or not parsed.path.startswith('/figures/approved/'):
            raise ValueError('This component export supports the reviewed Pages-hosted images only')
        files.add('static/'+parsed.path.lstrip('/'))
    for name in files:
        safe_name(name)
    return sorted(files)


def validate_component_lock(root):
    root = Path(root).resolve()
    lock = json.loads((root/LOCK).read_text(encoding='utf-8'))
    if (set(lock) != {'schema_version', 'repository', 'commit', 'files'}
            or lock['schema_version'] != 1 or lock['repository'] != REPOSITORY
            or not re.fullmatch(r'[a-f0-9]{40}', lock['commit'])):
        raise ValueError('Invalid Gallery version lock')
    descriptor = json.loads((root/'gallery-component.json').read_text(encoding='utf-8'))
    media = json.loads((root/'data/gallery/media.json').read_text(encoding='utf-8'))
    names = component_paths(descriptor, media)
    if set(names) != set(lock['files']):
        raise ValueError('Gallery lock does not cover the exact component files')
    for name in names:
        path = root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError('Component source missing or unsafe: '+name)
        if content_hash(path.read_bytes(), name) != lock['files'][name]:
            raise ValueError('Managed Gallery file changed outside its pinned component: '+name)
    return lock


if __name__ == '__main__':
    result = validate_component_lock(Path(__file__).resolve().parents[1])
    print('PASS: Gallery component pinned at '+result['commit'])
