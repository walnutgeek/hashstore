from setuptools import setup,find_packages
from setuptools.command.sdist import sdist

# MANIFEST.in ensures that requirements are included in `sdist`
install_requires = open('requirements.txt').read().split()
version = open('version.txt').read().strip()


class MySdistCommand(sdist):
    def run(self):
        import subprocess
        for c in (['npm', 'install'], ['npm', 'run', 'build'] ):
            subprocess.check_call(c, cwd='hashstore/bakery/js')
        sdist.run(self)

setup(name='hashstore',
      version=version,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: System :: Archiving :: Backup',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
      ],
      description='Content Addressable Storage',
      url='https://github.com/walnutgeek/hashstore',
      author='Walnut Geek',
      author_email='wg@walnutgeek.com',
      license='Apache 2.0',
      packages=find_packages(exclude=("tests",)),
      package_data={'': ['utils/file_types.json', 'bakery/app/*',
                         'bakery/app/fonts/*']},
      cmdclass={'sdist': MySdistCommand},
      entry_points={
          'console_scripts': [ 'hs=hashstore.hs:main' ],
      },
      install_requires=install_requires,
      zip_safe=False)