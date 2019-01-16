from datetime import date
from dateutil.relativedelta import relativedelta
from setuptools import setup, find_packages, Command
from setuptools.command.sdist import sdist

import os

# MANIFEST.in ensures that requirements are included in `sdist`
VERSION_TXT = 'version.txt'

install_requires = open('requirements.txt').read().split()


class Version:
    def __init__(self, s):
        self.nums = s if isinstance(s, tuple) else tuple(map(int, s.split('.')))
        if len(self.nums) not in (2, 3):
            raise ValueError(f'version has to have 2 or 3 parts: {s}')

    def __str__(self):
        return '.'.join(map(str, self.nums))

    def __repr__(self):
        return f'Version({self.nums})'

    def next_major(self, now=date.today()):
        _nums = (now.year, now.month)
        if _nums > self.nums:
            return Version(_nums)
        else:
            now += relativedelta(months=1)
            _nums = (now.year, now.month)
            if _nums > self.nums:
                return Version(_nums)
            raise ValueError(
                f'cannot calc major version from: {current_ver} {now}')

    def next_minor(self, now=date.today()):
        last_num = 1
        if self.is_minor() :
            last_num = self.nums[2]
        _nums = (now.year, now.month, last_num)
        if self.nums == _nums:
            return Version((now.year, now.month, last_num + 1))
        else:
            _nums = (now.year, now.month, 1)
            if _nums > self.nums:
                return Version(_nums)
            now += relativedelta(months=1)
            _nums = (now.year, now.month, 1)
            if _nums > self.nums:
                return Version(_nums)
            raise ValueError(
                f'cannot calc version from: {self.nums} {now}')

    def is_minor(self):
        return len(self.nums) == 3


version = Version(open(VERSION_TXT).read().strip())

with open("README.md", "r") as fh:
    long_description = fh.read()

class ReleaseCommand(Command):

    description = "Trigger Release, change version, tag and push changes to git."

    user_options = [ ('major', None, "trigger major release ")]

    def initialize_options(self):
        self.major = False

    def finalize_options(self):
        """Post-process options."""
        if self.major != False:
            self.major = True

    def calculate_new_ver(self):
        if self.major:
            return version.next_major()
        else:
            return version.next_minor()

    def run(self):
        """Run command."""
        new_ver = str(self.calculate_new_ver())
        open(VERSION_TXT, 'wt').write(new_ver)
        print(f'New version: {new_ver}')
        os.system(f'git add {VERSION_TXT}')
        os.system(f'git tag -a v{new_ver} -m new_tag_v{new_ver}')
        os.system(f'git commit -m v{new_ver}')
        os.system(f'git push origin --tags')


class MySdistCommand(sdist):
    def run(self):
        import subprocess
        npm = 'npm'
        if os.name == 'nt':
            npm = 'npm.cmd'

        for c in ([npm, 'install'], [npm, 'run', 'build'] ):
            subprocess.check_call(c, cwd='hashstore/bakery/js')
        sdist.run(self)

setup(name='hashstore',
      version=str(version),
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: System :: Archiving :: Backup',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
      ],
      description='Content Addressable Storage',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/walnutgeek/hashstore',
      author='Walnut Geek',
      author_email='wg@walnutgeek.com',
      license='Apache 2.0',
      packages=find_packages(exclude=("tests",)),
      package_data={'': ['utils/file_types.json', 'bakery/app/*',
                         'bakery/app/fonts/*']},
      cmdclass={'sdist': MySdistCommand, 'release': ReleaseCommand},
      entry_points={
          'console_scripts': [ 'hs=hashstore.hs:main' ],
      },
      install_requires=install_requires,
      zip_safe=False)