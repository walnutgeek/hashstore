from setuptools import setup, find_packages
from setuptools.command.sdist import sdist
from subprocess import check_call
import os
from hashstore.kernel.misc.setup import get_version_and_add_release_cmd


class MySdistCommand(sdist):
    def run(self):
        npm = 'npm'
        if os.name == 'nt':
            npm = 'npm.cmd'

        for c in ([npm, 'install'], [npm, 'run', 'build'] ):
            check_call(c, cwd='hashstore/bakery/js')
        sdist.run(self)

cmdclass_dict = {'sdist': MySdistCommand}


# MANIFEST.in ensures that requirements are included in `sdist`
install_requires = open('requirements.txt').read().split()

with open("README.md", "r") as fh:
    long_description = fh.read()

version = get_version_and_add_release_cmd('version.txt', cmdclass_dict)

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
      package_data={'': ['kernel/file_types.json', 'bakery/app/*',
                         'bakery/app/fonts/*']},
      cmdclass=cmdclass_dict,
      entry_points={
          'console_scripts': [ 'hs=hashstore.hs:main' ],
      },
      install_requires=install_requires,
      zip_safe=False)