from setuptools import setup

# MANIFEST.in ensures that requirements are included in `sdist`
install_requires = open('requirements.txt').read().split()

setup(name='hashstore',
      version='0.0.7',
      classifiers=[
          # How mature is this project? Common values are
          #   3 - Alpha
          #   4 - Beta
          #   5 - Production/Stable
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: System :: Archiving :: Backup',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
      ],
      description='Content Addressable Storage',
      url='https://github.com/walnutgeek/hashstore',
      author='Walnut Geek',
      author_email='wg@walnutgeek.com',
      license='Apache 2.0',
      packages=['hashstore'],
      package_data={'': ['app/*']},
      entry_points={
          'console_scripts': [
              'shash=hashstore.shash:main',
              'shashd=hashstore.shashd:main',
          ],
      },
      install_requires=install_requires,
      zip_safe=False)