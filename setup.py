"""Setup sony_bravia_psk package."""
# read the contents of your README file
from os import path

from setuptools import find_packages, setup

from braviapsk.version import __version__ as version

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="pySonyBraviaPSK",
    version=version,
    description="Library for Sony Bravia TVs with Pre-Shared Key option",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gerard33/sony_bravia_psk",
    maintainer="Gerard",
    license="MIT",
    packages=find_packages(),
    install_requires=["requests"],
    keywords="Sony Bravia TV PSK for Home Assistant",
    include_package_data=True,
    zip_safe=False,
)
