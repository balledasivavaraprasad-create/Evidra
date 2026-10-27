"""A failed, cancelled or unexpectedly skipped required job must fail CI Gate."""
import json
import os


def failures(needs):
    expected = ['validate', 'backend', 'frontend', 'security']
    if needs.get('validate', {}).get('outputs', {}).get('integration') == 'true':
        expected.append('e2e')
    failed = [name for name in expected if needs.get(name, {}).get('result') != 'success']
    if needs.get('e2e', {}).get('result') not in ('success', 'skipped') and 'e2e' not in failed:
        failed.append('e2e')
    return failed


if __name__ == '__main__':
    failed = failures(json.loads(os.environ['JOB_RESULTS']))
    if failed:
        raise SystemExit('Required CI jobs did not pass: ' + ', '.join(failed))
    print('All checks required for the declared implementation stage passed.')
