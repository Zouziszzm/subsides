"""The riscv64 packages must declare the glibc of the Ubuntu they are built on (#44)."""

from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
JOBS = yaml.load((ROOT / '.github/workflows/release.yml').read_text(), Loader=yaml.BaseLoader)['jobs']

# glibc of each GitHub-hosted Ubuntu runner the Linux package jobs use.
UBUNTU_GLIBC = {'ubuntu-22.04': '2.35', 'ubuntu-24.04': '2.39'}


class LinuxGlibcFloorTests(unittest.TestCase):
    def test_riscv64_declares_its_runners_glibc(self):
        job = JOBS['linux-riscv64']
        self.assertEqual(job['env']['GLIBC_FLOOR'], UBUNTU_GLIBC[job['runs-on']])


if __name__ == '__main__':
    unittest.main()
