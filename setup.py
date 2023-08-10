from __init__ import __version__

with open("requirements.txt", "r") as fh:
    requirements = fh.readlines()

from setuptools import setup, find_packages

setup(
    name='smart-investor',
    version=__version__,
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    # ...
    entry_points={
        'console_scripts': [
            'stock-list=stock.stock_recommender:main',
        ],
    },
)
