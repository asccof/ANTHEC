"""Validate inception metadata; never asserts application acceptance."""
import json
import re
from pathlib import Path


def validate(baseline, sources):
    errors = []
    if baseline.get('project') != 'ANTHEEC':
        errors.append('Independent project identity required')
    if baseline.get('languages') != ['ar', 'fr', 'en']:
        errors.append('Language baseline must include AR/FR/EN')
    if baseline.get('boundaries') != {
        'production': False, 'paid_services': False, 'real_person_data': False
    }:
        errors.append('Authorization boundary changed')
    source_ids = [s['id'] for s in sources]
    if len(source_ids) != len(set(source_ids)):
        errors.append('Duplicate source ID')
    for source in sources:
        if not re.fullmatch('[0-9a-f]{64}', source.get('sha256', '')):
            errors.append('Invalid source hash')
    requirements = baseline.get('requirements', [])
    ids = [r['id'] for r in requirements]
    if len(ids) != len(set(ids)):
        errors.append('Duplicate requirement ID')
    if not {f'AC-{i:02}' for i in range(1, 15)}.issubset(ids):
        errors.append('Missing executive acceptance coverage')
    tests = {t for r in requirements for t in r.get('design_tests', [])}
    if tests != {f'T{i:02}' for i in range(1, 13)}:
        errors.append('Incomplete or unknown detailed test mapping')
    for requirement in requirements:
        if requirement.get('source_id') not in source_ids:
            errors.append('Unknown source reference')
        if not requirement.get('section') or not requirement.get('task'):
            errors.append('Missing traceability')
        if requirement.get('status') not in {'planned', 'implemented', 'verified'}:
            errors.append('Unknown status')
        if requirement.get('status') == 'verified' and not requirement.get('evidence'):
            errors.append('Verified claim without evidence')
    return errors


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    errors = validate(
        json.loads((root / 'requirements/baseline.json').read_text()),
        json.loads((root / 'requirements/sources.json').read_text()),
    )
    for error in errors:
        print(error)
    if errors:
        raise SystemExit(1)
    print('PASS: metadata only; application acceptance remains planned.')
