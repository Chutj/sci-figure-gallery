"""Exact-byte allowlist for approved figures hosted by this Pages site.

Standard library only. External approved media continues to use the URL gate.
No private image discovery or copying takes place during production builds.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

SITE = 'https://chutj.github.io'
RASTER = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.tif', '.tiff'}


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
        if output:
            built = output / str(relative)
            if not built.is_file() or hashlib.sha256(built.read_bytes()).hexdigest() != digest:
                raise ValueError('Published image missing or changed')
        seen.add(url); paths.add(('static/' + str(relative)).replace('\\', '/'))
    if seen != set(expected):
        raise ValueError('Missing exact media approvals for site-hosted figures')
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
