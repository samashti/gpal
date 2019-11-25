from setuptools import setup, find_packages

try:
      from future_builtins import filter
except ImportError:
      pass

with open("README.md", "r") as fh:
    long_description = fh.read()

__version__ = "0.1.0"

setup(
    name="geopackagepy",
    version=__version__,
    author="Nikhil S Hubballi",
    author_email="nikhil.hubballi@gmail.com",
    description="geopackage read/write with sql queries (uses geopandas and pandas)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nsh-764/GeoPackage-py",
    packages = find_packages(),
    install_requires= ['setuptools', 'geopandas', 'pysqlite3', 'pandas'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: GNU General Public License v3.0",
        "Operating System :: OS Independent",
    ],
    zip_safe=False
)
