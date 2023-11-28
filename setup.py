from setuptools import setup, find_packages
from infrapatch.cli.__init__ import __version__

setup(
    name="infrapatch",
    description="CLI Tool to patch Terraform Providers and Modules.",
    version=__version__,
    packages=find_packages(where=".", include=["infrapatch*"], exclude=["action*"]),
    package_data={"infrapatch": ["core/utils/terraform/bin/*"]},
    install_requires=["click~=8.1.7", "rich~=13.6.0", "pygohcl~=1.0.7", "GitPython~=3.1.40", "setuptools~=65.5.1", "semantic_version~=2.10.0", "pytablewriter~=1.2.0"],
    python_requires=">=3.11",
    entry_points="""
        [console_scripts]
        infrapatch=infrapatch.cli.__main__:main
    """,
    author="Noah Canadea",
    url="https://github.com/Noahnc/infrapatch",
    author_email="noah@canadea.ch",
)
