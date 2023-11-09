# Standard libraries
from pathlib import Path

# drf-serializer-prefetch
from setuptools import find_packages, setup

VERSION = "1.1.6"
DESCRIPTION = "An automatic prefetcher for django-rest-framework."
this_directory = Path(__file__).parent
LONG_DESCRIPTION = (this_directory / "README.md").read_text()

setup(
    name="drf-serializer-prefetch",
    version=VERSION,
    author="Maxime Toussaint",
    author_email="m.toussaint@mail.com",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=("django>=3.2.0", "djangorestframework>=3.12"),
    url="https://github.com/MaxDude132/drf-serializer-prefetch",
)
