"""Exact-byte allowlist for approved figures hosted by this Pages site.

Standard library only. External approved media continues to use the URL gate.
No private image discovery or copying takes place during production builds.
"""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

SITE = 'https://chutj.github.io'
RASTER = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.tif', '.tiff', '.ico'}
BRANDING_FILES = {'site-logo.png', 'favicon.ico', 'favicon-16x16.png',
                  'favicon-32x32.png', 'apple-touch-icon.png'}


def branding_paths(root, output=None):
    """Optional, exact-byte site branding; never a scientific-image exemption."""
    manifest = root / 'data/site-branding.json'
    if not manifest.exists():
        return set()
    data = json.loads(manifest.read_text(encoding='utf-8'))
    if set(data) != {'schema_version', 'files'} or data['schema_version'] != 1 or not isinstance(data['files'], list):
        raise ValueError('Invalid site branding manifest')
    paths = set()
    for entry in data['files']:
        if not isinstance(entry, dict) or set(entry) != {'path', 'sha256'}:
            raise ValueError('Invalid site branding fields')
        name = entry['path']
        if name not in {'static/site-branding/' + item for item in BRANDING_FILES} or name in paths:
            raise ValueError('Invalid or duplicate site branding path')
        if not isinstance(entry['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256']):
            raise ValueError('Invalid site branding digest')
        source = root / name
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()) or not source.is_file():
            raise ValueError('Site branding file missing or unsafe')
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Site branding bytes changed')
        if output:
            built = output / name.removeprefix('static/')
            if not built.is_file() or hashlib.sha256(built.read_bytes()).hexdigest() != entry['sha256']:
                raise ValueError('Published site branding missing or changed')
        paths.add(name)
    return paths


def validate_media(root, dataset, policy, output=None):
    manifest = root / 'data/gallery/media.json'
    entries = []
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding='utf-8'))
        if set(data) != {'schema_version', 'files'} or data['schema_version'] != 1:
            raise ValueError('Invalid public media manifest')
        entries = data['files']
    approvals = {record['id']: record for record in policy['approved_records']}
    expected = {}
    for record in dataset['records']:
        urls = [record['image'], record['thumbnail']]
        if 'legend' in record: urls.append(record['legend']['image'])
        urls += [part.strip().split()[0] for part in record['srcset'].split(',') if part.strip()]
        for url in urls:
            if url.startswith(SITE + '/'):
                expected[url] = record['id']
    seen = set(); paths = set()
    for entry in entries:
        if set(entry) != {'id', 'url', 'sha256'}:
            raise ValueError('Invalid public media fields')
        url = entry['url']; rid = entry['id']
        if url not in expected or expected[url] != rid or url in seen:
            raise ValueError('Media absent from exact approved dataset or duplicated')
        relative = PurePosixPath(urlsplit(url).path.lstrip('/'))
        if '..' in relative.parts or not str(relative).startswith('figures/approved/') or relative.suffix.lower() not in RASTER:
            raise ValueError('Invalid approved media path')
        source = root / 'static' / str(relative)
        if source.is_symlink() or not source.is_file():
            raise ValueError('Approved static file missing or symlink')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != entry['sha256']:
            raise ValueError('Approved media bytes changed')
        if url == approvals[rid]['image'] and digest != approvals[rid]['source_image_sha256']:
            raise ValueError('Original image differs from reviewed source')
        record = next(r for r in dataset['records'] if r['id']==rid)
        if url == record.get('legend',{}).get('image') and digest != record['legend']['sha256']:
            raise ValueError('Shared legend differs from reviewed metadata')
        if output:
            built = output / str(relative)
            if not built.is_file() or hashlib.sha256(built.read_bytes()).hexdigest() != digest:
                raise ValueError('Published image missing or changed')
        seen.add(url); paths.add(('static/' + str(relative)).replace('\\', '/'))
    if seen != set(expected):
        raise ValueError('Missing exact media approvals for site-hosted figures')
    paths.update(branding_paths(root, output))
    # Reject other raster files from public source, including ignored accidents.
    for directory in ('static', 'assets', 'content'):
        for source in (root / directory).rglob('*'):
            if source.is_file() and source.suffix.lower() in RASTER and source.relative_to(root).as_posix() not in paths:
                raise ValueError('Unapproved raster in public source: ' + source.relative_to(root).as_posix())
    if output:
        expected_output = {path.removeprefix('static/') for path in paths}
        actual = {path.relative_to(output).as_posix() for path in output.rglob('*') if path.is_file() and path.suffix.lower() in RASTER}
        if actual != expected_output:
            raise ValueError('Unexpected raster in publish output')
    return paths
