from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in hibiscus_connect/__init__.py
from hibiscus_connect import __version__ as version

setup(
	name="hibiscus_connect",
	version=version,
	description="Austausch zu der Onlinebanking-Software Hibiscus",
	author="itsdave GmbH",
	author_email="dev@itsdave.de",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
