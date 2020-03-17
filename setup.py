"""Setup sony_bravia_psk package."""
from setuptools import setup, find_packages

from braviapsk.version import __version__ as version

setup(
    name='pySonyBraviaPSK',
    version=version,
    description='Library for Sony Bravia TVs with Pre-Shared Key option',
    long_description='Library for Sony Bravia TVs with Pre-Shared Key option'
    url='https://github.com/gerard33/sony_bravia_psk',
    maintainer='Gerard',
    license='MIT',
    packages=find_packages(),
    install_requires=['requests'],
    keywords='Sony Bravia TV PSK for Home Assistant',
    include_package_data=True,
    zip_safe=False
)
