from datetime import date, timedelta
from setuptools import setup, find_packages, Command
from setuptools.command.sdist import sdist
from subprocess import check_call, check_output, CalledProcessError

import os

# MANIFEST.in ensures that requirements are included in `sdist`
from hashstore.utils import ensure_string

VERSION_TXT = 'version.txt'

install_requires = open('requirements.txt').read().split()


def next_month(d):
    cur_month = d.month
    while cur_month == d.month:
        d += timedelta(days=1)
    return d

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
            now = next_month(now)
            _nums = (now.year, now.month)
            if _nums > self.nums:
                return Version(_nums)
            raise ValueError(
                f'cannot calc major version from: {self.nums} {now}')

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
            now = next_month(now)
            _nums = (now.year, now.month, 1)
            if _nums > self.nums:
                return Version(_nums)
            raise ValueError(
                f'cannot calc version from: {self.nums} {now}')

    def is_minor(self):
        return len(self.nums) == 3

    def type(self):
        return "minor" if self.is_minor() else "major"


version = Version(open(VERSION_TXT).read().strip())

with open("README.md", "r") as fh:
    long_description = fh.read()



class ReleaseCommand(Command):

    description = f"""
        Check release:
            return success errorCode if {VERSION_TXT} match 
            current tag on branch. 
        
        Trigger release:
            change {VERSION_TXT}, tag and push changes to git.
            
        """

    user_options = [
        ('minor', None, "trigger minor release "),
        ('major', None, "trigger major release ")
    ]

    def initialize_options(self):
        self.major = False
        self.minor = False

    def finalize_options(self):
        """Post-process options."""
        if self.major != False:
            self.major = True
        if self.minor != False:
            self.minor = True


    def run(self):
        """Run command."""
        new_ver = None
        if self.major:
            new_ver = version.next_major()
        elif self.minor:
            new_ver = version.next_minor()
        else:
            try:
                tag=ensure_string(
                    check_output([
                        'git', 'describe','--tags','--exact-match'])
                ).strip()
                version_ = f'v{version}'
                print(f'version.txt={repr(version_)} git={repr(tag)}')
                match = tag == version_
            except CalledProcessError:
                print(f'no tag found')
                match = False
            if match:
                print(f'{version.type()} release. Git tag matched.')
                raise SystemExit(0)
            else:
                raise SystemExit(-1)
        open(VERSION_TXT, 'wt').write(str(new_ver))
        print(f'New version: {new_ver}')
        tag = f'v{new_ver}'
        msg = ['-m', tag]
        check_call(['git', 'add', VERSION_TXT])
        check_call(['git', 'commit', *msg ])
        check_call(['git', 'tag', '-a', tag, *msg])
        # check_call(f'git push origin --tags'.split())
        check_call('git push --tags origin HEAD'.split())
        check_call('git push -u origin master'.split())


class MySdistCommand(sdist):
    def run(self):
        npm = 'npm'
        if os.name == 'nt':
            npm = 'npm.cmd'

        for c in ([npm, 'install'], [npm, 'run', 'build'] ):
            check_call(c, cwd='hashstore/bakery/js')
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