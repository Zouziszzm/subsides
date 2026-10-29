"""The per-app craft-i18n pin (craft-i18n.rev) and its checkout."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTION = 'checkout-craft-i18n'


def load(path):
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)


def workflow(name):
    return load(Path('.github/workflows') / name)


def uses(steps, action):
    return any(action in step.get('uses', '') for step in steps)


def builds(steps):
    return any('rust-toolchain' in step.get('uses', '') or 'freebsd-vm' in step.get('uses', '')
               for step in steps)


def bash(script, cwd, env=None):
    return subprocess.run(['bash', '-eo', 'pipefail', '-c', script], cwd=cwd, capture_output=True,
                          text=True, env={**os.environ, **(env or {})})


class CraftI18nWorkflowTests(unittest.TestCase):
    def test_every_build_job_checks_out_craft_i18n(self):
        for name in ('release.yml', 'freebsd.yml', 'windows-arm64.yml'):
            for job, data in workflow(name)['jobs'].items():
                steps = data.get('steps', [])
                if builds(steps):
                    with self.subTest(workflow=name, job=job):
                        self.assertTrue(uses(steps, ACTION), f'{name}: {job} builds without craft-i18n')

    def test_freebsd_guests_get_the_craft_i18n_env(self):
        # The VM doesn't see the host's GITHUB_ENV: each guest script exports it itself.
        for name, job in (('release.yml', 'freebsd'), ('freebsd.yml', 'freebsd')):
            scripts = [step['run'] for step in workflow(name)['jobs'][job]['steps']
                       if step.get('shell') == 'freebsd {0}'
                       and ('cargo build' in step['run'] or 'package.sh' in step['run'])]
            self.assertTrue(scripts)
            for script in scripts:
                with self.subTest(workflow=name):
                    self.assertIn('CRAFT_I18N_DIR="$PWD/craft-i18n" CRAFT_I18N_REQUIRED=1', script)


class CheckoutActionTests(unittest.TestCase):
    STEPS = load('actions/checkout-craft-i18n/action.yml')['runs']['steps']
    READ = next(step['run'] for step in STEPS if step.get('id') == 'pin')

    def read_pin(self, content=None):
        with tempfile.TemporaryDirectory() as directory:
            if content is not None:
                Path(directory, 'craft-i18n.rev').write_bytes(content)
            output = Path(directory, 'output')
            output.touch()
            result = bash(self.READ, directory, {'GITHUB_OUTPUT': str(output)})
            return result.returncode, output.read_text()

    def test_no_pin_file_changes_nothing(self):
        self.assertEqual(self.read_pin(), (0, ''))
        later = [step for step in self.STEPS if step.get('id') != 'pin']
        self.assertTrue(all(step['if'] == "steps.pin.outputs.rev != ''" for step in later))

    def test_crlf_pin_is_trimmed(self):
        sha = 'a' * 40
        self.assertEqual(self.read_pin(f'{sha}\r\n'.encode()), (0, f'rev={sha}\n'))

    def test_a_pin_that_is_not_one_sha_fails(self):
        self.assertEqual(self.read_pin(b'main\n')[0], 1)


if __name__ == '__main__':
    unittest.main()
