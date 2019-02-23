import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(name='kiesraad',
    version='0.0.0',
    description='Scrape and parse Dutch election results',
    long_description=README,
    long_description_content_type="text/markdown",
    author='dirkmjk',
    author_email='info@dirkmjk.nl',
    license="MIT",
    packages=['kiesraad'],
    include_package_data=True,
    install_requires=['pandas', 'selenium', 'bs4', 'xmltodict'],
    zip_safe=False)
