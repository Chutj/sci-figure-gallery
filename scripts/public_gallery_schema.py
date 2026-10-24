"""Public Gallery contract. Standard library only; never loads local FIG data."""
import datetime
import hashlib
import ipaddress
import json
import re
from urllib.parse import urlsplit

EDITOR_FIELDS = ('id', 'title', 'primary', 'categories', 'journal', 'year', 'doi',
                 'figure', 'paper', 'author', 'source', 'sections', 'translation_status', 'width', 'height')
RIGHTS_FIELDS = ('status', 'public_use_allowed', 'human_reviewed', 'approved_by', 'approved_at',
                'permission_basis', 'license', 'license_url', 'evidence_reference', 'attribution', 'review_evidence_sha256',
                'modification_status', 'additional_credit')
PUBLIC_FIELDS = set(EDITOR_FIELDS) | {'source_image_sha256', 'metadata_sha256', 'rights', 'image', 'thumbnail', 'srcset'}
OPTIONAL_EDITOR_FIELDS = {'legend'}
APPROVAL_FIELDS = {'id', 'source_image_sha256', 'metadata_sha256', 'rights', 'image', 'thumbnail', 'srcset'}
SECTIONS = {'What the figure shows', 'Statistics & symbols', 'Color & encoding', 'Design lessons', 'Verification & limitations'}
HASH = re.compile(r'^[a-f0-9]{64}$')
LOCAL_TEXT = re.compile(r'\.gallery-local|gallery-private|file://|(?<![A-Za-z0-9])[A-Za-z]:[\\/]|[\u3400-\u9fff]', re.I)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def editor_payload(record):
    result = {key: record[key] for key in EDITOR_FIELDS}
    result.update({key:record[key] for key in OPTIONAL_EDITOR_FIELDS if key in record})
    result['source'] = 'https://doi.org/' + result['doi']
    return result


def metadata_hash(record):
    return hashlib.sha256(json.dumps(editor_payload(record), ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def https_url(value, hosts=None):
    require(isinstance(value, str) and value, 'URL required')
    require(not LOCAL_TEXT.search(value) and ',' not in value and not re.search(r'\s', value), 'Private/invalid URL')
    parsed = urlsplit(value)
    host = parsed.hostname or ''
    require(parsed.scheme == 'https' and parsed.username is None and parsed.password is None
            and not parsed.query and not parsed.fragment and parsed.port in (None, 443), 'Public HTTPS URL without credentials/query required')
    require('.' in host and not host.endswith(('.local', '.localhost', '.internal', '.test')), 'Public hostname required')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    require(address is None or address.is_global, 'Private IP URL rejected')
    if hosts is not None:
        require(host in hosts, 'Image hostname is not explicitly allowed')
    return value


def validate_rights(rights):
    require(isinstance(rights, dict) and set(rights) == set(RIGHTS_FIELDS), 'Explicit, complete public rights fields required')
    require(rights['status'] == 'approved' and rights['public_use_allowed'] is True
            and rights['human_reviewed'] is True, 'Unverified or non-human-reviewed rights cannot be public')
    for field in ('approved_by', 'approved_at', 'license', 'evidence_reference', 'attribution', 'modification_status', 'additional_credit'):
        require(isinstance(rights[field], str) and rights[field].strip(), f'Missing rights.{field}')
    require(not LOCAL_TEXT.search(json.dumps(rights, ensure_ascii=False)), 'Private/non-English rights text rejected')
    try:
        approved = datetime.date.fromisoformat(rights['approved_at'])
    except (ValueError, TypeError):
        raise ValueError('approved_at must be YYYY-MM-DD')
    require(approved <= datetime.datetime.now(datetime.timezone.utc).date(), 'Future review date rejected')
    require(re.fullmatch(r'[A-Za-z0-9._-]+', rights['evidence_reference']), 'Use an opaque permission evidence ID, not a private file path')
    require(isinstance(rights['review_evidence_sha256'],str) and HASH.fullmatch(rights['review_evidence_sha256']), 'Reviewed PDF/credit/license evidence fingerprint required')
    require(rights['permission_basis'] in ('license', 'written_permission'), 'Permission basis required')
    if rights['permission_basis'] == 'license':
        https_url(rights['license_url'])
    elif rights['license_url']:
        https_url(rights['license_url'])


def validate_approval(approval, hosts):
    require(isinstance(approval, dict) and set(approval) == APPROVAL_FIELDS, 'Unexpected/missing allowlist fields')
    require(isinstance(approval['id'], str) and re.fullmatch(r'[A-Za-z0-9._-]{1,160}', approval['id']), 'Invalid public ID')
    for field in ('source_image_sha256', 'metadata_sha256'):
        require(isinstance(approval[field], str) and HASH.fullmatch(approval[field]), 'SHA256 pin required')
    validate_rights(approval['rights'])
    https_url(approval['image'], hosts); https_url(approval['thumbnail'], hosts)
    require(isinstance(approval['srcset'], str), 'srcset must be a string')
    if approval['srcset']:
        for variant in approval['srcset'].split(','):
            parts = variant.strip().split()
            require(len(parts) == 2 and re.fullmatch(r'[1-9]\d*w', parts[1]), 'Invalid responsive image candidate')
            https_url(parts[0], hosts)


def validate_policy(policy):
    require(isinstance(policy, dict) and set(policy) == {'schema_version','image_hosts','approved_records'}
            and policy['schema_version'] == 1, 'Invalid public allowlist schema')
    require(isinstance(policy['image_hosts'], list) and all(isinstance(h,str) for h in policy['image_hosts']), 'Image host list required')
    require(len(policy['image_hosts']) == len(set(policy['image_hosts'])), 'Duplicate image hostname')
    for host in policy['image_hosts']:
        https_url('https://' + host + '/policy-probe')
    require(isinstance(policy['approved_records'], list), 'Approval list required')
    approved = {}
    for approval in policy['approved_records']:
        validate_approval(approval, policy['image_hosts'])
        require(approval['id'] not in approved, 'Duplicate allowlist ID')
        approved[approval['id']] = approval
    return approved


def validate_dataset(dataset, policy):
    approved = validate_policy(policy)
    require(isinstance(dataset,dict) and set(dataset) == {'schema_version','records'}
            and dataset['schema_version'] == 1 and isinstance(dataset['records'],list), 'Invalid public dataset schema')
    seen = set()
    for record in dataset['records']:
        require(isinstance(record,dict) and PUBLIC_FIELDS <= set(record) <= PUBLIC_FIELDS | OPTIONAL_EDITOR_FIELDS, 'Private or unknown record fields rejected')
        uid = record['id']
        require(uid in approved and uid not in seen, 'Record absent from whitelist or duplicated')
        seen.add(uid)
        approval = approved[uid]
        for field in APPROVAL_FIELDS:
            require(record[field] == approval[field], 'Record differs from pinned approval: '+field)
        require(record['metadata_sha256'] == metadata_hash(record), 'Public metadata changed after review')
        if 'legend' in record:
            legend = record['legend']
            require(isinstance(legend,dict) and set(legend)=={'image','sha256','width','height','label'}, 'Explicit complete shared legend required')
            https_url(legend['image'],policy['image_hosts'])
            require(bool(HASH.fullmatch(legend.get('sha256',''))), 'Legend SHA256 required')
            require(all(type(legend[k]) is int and 0 < legend[k] <= 100000 for k in ('width','height')), 'Invalid legend dimensions')
            require(isinstance(legend['label'],str) and bool(legend['label'].strip()), 'Legend label required')
        require(record['translation_status'] == 'reviewed', 'Unreviewed English description rejected')
        for field in ('title','primary','journal','doi','figure','paper','author','source'):
            require(isinstance(record[field],str) and record[field].strip(), 'Missing public '+field)
        require(re.fullmatch(r'10\.\d{4,9}/\S+',record['doi']), 'DOI required')
        require(record['source'] == 'https://doi.org/'+record['doi'], 'Source must use the reviewed DOI')
        require(type(record['year']) is int and 1800 <= record['year'] <= 2200, 'Invalid publication year')
        require(isinstance(record['categories'],list) and record['categories']
                and all(isinstance(c,str) and c.strip() for c in record['categories'])
                and record['primary'] in record['categories'], 'Invalid public categories')
        require(isinstance(record['sections'],dict) and set(record['sections']) == SECTIONS
                and all(isinstance(v,str) and v.strip() for v in record['sections'].values()), 'Reviewed descriptions required')
        require(all(type(record[k]) is int and 0 < record[k] <= 100000 for k in ('width','height')), 'Image dimensions required')
        require(not LOCAL_TEXT.search(json.dumps(record,ensure_ascii=False)), 'Private paths or non-English public data rejected')
    return len(seen)
