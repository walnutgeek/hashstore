from setuptools import setup

# MANIFEST.in ensures that requirements are included in `sdist`
install_requires = open('requirements.txt').read().split()

setup(name='hashstore',
      version='0.0.6',
      description='Content Addressable Storage',
      url='https://github.com/walnutgeek/hashstore',
      author='Walnut Geek',
      author_email='wg@walnutgeek.com',
      license='Apache 2.0',
      packages=['hashstore'],
      entry_points={
          'console_scripts': [
              'shash=hashstore.shash:main',
              'shashd=hashstore.shashd:main',
          ],
      },
      install_requires=install_requires,
      zip_safe=False)