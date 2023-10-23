from setuptools import setup, find_packages
from infrapatch_cli.__init__ import __version__

setup(
    name='infrapatch_cli',
    description='CLI Tool to patch Terraform Providers and Modules.',
    version=__version__,
    packages=find_packages(
        where='.',
        include=['infrapatch_cli*']
    ),
    package_data={
        'infrapatch_cli': ['bin/*']
    },
    install_requires=[
        "click~=8.1.7",
        "rich~=13.6.0",
        "pygohcl~=1.0.7"
    ],
    python_requires='>=3.11',
    entry_points='''
        [console_scripts]
        infrapatch_cli=infrapatch_cli.__main__:main
    ''',
    author="Noah Canadea",
    url='https://github.com/Noahnc/infrapatch',
    author_email='noah@canadea.ch'
)
