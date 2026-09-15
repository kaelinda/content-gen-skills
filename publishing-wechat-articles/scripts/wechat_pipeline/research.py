"""Validate editorial evidence records, not the truth of their contents.

No network requests or credentials: a human/agent must read the linked sources.
"""
from __future__ import annotations

from urllib.parse import urlsplit


def check_research(payload: object) -> dict:
    findings: list[str] = []
    def require(condition, message):
        if not condition:
            findings.append(message)
    def text(value):
        return isinstance(value, str) and bool(value.strip())

    if not isinstance(payload, dict):
        return {'passed': False, 'findings': ['research must be an object']}
    for field in ('reader', 'problem', 'benefit', 'increment', 'gift_review'):
        require(text(payload.get(field)), f'{field} is required')
    duplicate = payload.get('duplicate_check', {})
    if not isinstance(duplicate, dict):
        duplicate = {}
    require(text(duplicate.get('scope')), 'duplicate check needs an honest scope')
    require(duplicate.get('result') in ('distinct', 'new-angle'), 'duplicate or unchecked topic')
    if duplicate.get('result') == 'new-angle':
        require(text(duplicate.get('difference')), 'reused topic requires a different reader task')

    sources = payload.get('sources')
    if not isinstance(sources, list):
        sources = []
    require(bool(sources), 'sources are required')
    by_id = {}
    read_urls = set()
    official_read = False
    for source in sources:
        if not isinstance(source, dict):
            findings.append('source must be an object'); continue
        identifier = source.get('id')
        if not text(identifier):
            findings.append('source id is required'); continue
        require(identifier not in by_id, 'source ids must be unique')
        by_id[identifier] = source
        url = source.get('url')
        try:
            parsed = urlsplit(url) if isinstance(url, str) else None
            safe = bool(parsed and parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password)
        except ValueError:
            safe = False
        require(safe, f'{identifier}: public HTTP(S) source URL required')
        read = source.get('status') in ('read', 'claim-verified') and text(source.get('excerpt'))
        if read and safe:
            read_urls.add(url)
            official_read |= source.get('kind') == 'official'
    require(len(read_urls) >= 2, 'read at least two distinct sources; snippets and duplicate URLs do not count')
    require(type(payload.get('official_available')) is bool, 'official_available must be explicit')
    if payload.get('official_available') is True:
        require(official_read, 'open and read the available official documentation')
    if payload.get('official_available') is False:
        require(text(payload.get('official_search_note')), 'document the unsuccessful official source search')

    claims = payload.get('claims')
    if not isinstance(claims, list):
        claims = []
    require(bool(claims), 'key claim-to-source mapping is required')
    for claim in claims:
        if not isinstance(claim, dict):
            findings.append('claim must be an object'); continue
        require(text(claim.get('text')), 'claim text is required')
        require(claim.get('kind') in ('official_claim', 'customer_case', 'independent_test', 'editorial_analysis', 'assumption'), 'classify each claim, do not imply an independent test')
        refs = claim.get('source_ids')
        if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs):
            refs = []
        require(bool(refs), 'claim references are required')
        urls = set()
        for ref in refs:
            source = by_id.get(ref)
            if not source:
                findings.append('claim references an unknown source'); continue
            require(source.get('status') in ('read', 'claim-verified') and text(source.get('excerpt')), 'claim references unread evidence')
            if isinstance(source.get('url'), str):
                urls.add(source['url'])
        status = claim.get('status')
        require(status in ('verified', 'attributed', 'analysis'), 'unresolved or conflicting claims block readiness')
        if status == 'verified' and claim.get('material', True):
            require(len(urls) >= 2, 'material verified claim requires corroboration or explicit attribution')
        if status in ('attributed', 'analysis'):
            require(text(claim.get('limitation')), 'attributed claims and analysis require a boundary')
    limitations = payload.get('limitations')
    require(isinstance(limitations, list) and bool(limitations) and all(text(item) for item in limitations), 'explicit limitations are required, including whether local tests were run')
    return {'passed': not findings, 'findings': findings, 'scope': 'record completeness only; not automated fact verification'}
