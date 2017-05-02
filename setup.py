from setuptools import setup

setup(name='hashstore',
      version='0.0.4',
      description='Content Addressable Storage',
      url='https://github.com/walnutgeek/hashstore',
      author='Walnut Geek',
      author_email='wg@walnutgeek.com',
      license='Apache 2.0',
      packages=['hashstore'],
      entry_points={
          'console_scripts': [
              'shash=hashstore.shash:main',
          ],
      },
      install_requires=open('requirements.txt').read().split(),
      zip_safe=False)