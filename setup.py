from codecs import open
from os import path

from setuptools import find_packages, setup

__version__ = "version read in next line"
exec(open("gspread_pandas/_version.py").read())

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

# get the dependencies and installs
with open(path.join(here, "requirements.txt"), encoding="utf-8") as f:
    all_reqs = f.read().split("\n")

install_requires = [x.strip() for x in all_reqs if "git+" not in x]
dependency_links = [
    x.strip().replace("git+", "") for x in all_reqs if x.startswith("git+")
]

# get the dependencies and installs
with open(path.join(here, "requirements_dev.txt"), encoding="utf-8") as f:
    dev_requires = f.read().split("\n")

setup(
    name="gspread-pandas",
    version=__version__,
    description=(
        "A package to easily open an instance of a Google spreadsheet and "
        "interact with worksheets through Pandas DataFrames."
    ),
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/Paradigmllc/gspread-pandas",
    download_url="https://github.com/Paradigmllc/gspread-pandas/tarball/v" + __version__,
    license="BSD",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Office/Business :: Financial :: Spreadsheet",
    ],
    keywords="gspread pandas google spreadsheets",
    packages=find_packages(exclude=["docs", "tests*"]),
    python_requires=">=3.9",
    include_package_data=True,
    author="Diego Fernandez",
    install_requires=install_requires,
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    extras_require={"dev": dev_requires},
    dependency_links=dependency_links,
    author_email="aiguo.fernandez@gmail.com",
)
