"""Setup sony_bravia_psk package."""
from setuptools import setup, find_packages

setup(
    name='pySonyBraviaPSK',
    version='0.1.4',
    description='Library for Sony Bravia TVs with Pre-Shared Key option',
    url='https://github.com/gerard33/sony_bravia_psk',
    maintainer='Gerard',
    maintainer_email='aankop3n@gmail.com',
    license='MIT',
    packages=find_packages(),
    install_requires=['requests'],
    keywords='Sony Bravia TV PSK for Home Assistant',
    include_package_data=True,
    zip_safe=False
)
