from setuptools import setup

setup(name='hashstore',
      version='0.1',
      description='Content Addressable Storage',
      url='https://github.com/walnutgeek/hashstore',
      author='Walnut Geek',
      author_email='wg@walnutgeek.com',
      license='Apache 2.0',
      packages=open('requirements.txt').read().split(),
      zip_safe=False)