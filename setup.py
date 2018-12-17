# To use a consistent encoding
from codecs import open
from os import path

from setuptools import setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pytunes-reporter',
    version='0.3.0',
    description='Library to interact with iTunes Reporter API',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/gifbitjapan/pytunes-reporter',
    author='Chason Chaffin',
    author_email='chason.c@routeone-power.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Topic :: Office/Business :: Financial',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='itunes reporter financial sales',
    py_modules=["reporter"],
    install_requires=['requests'],
    extras_require={
        'dev': ['bumpversion'],
        'test': [
            'pytest',
            'faker',
            'responses',
            'pytest-responses',
            'coverage',
            'python-coveralls',
            'pytest-cov',
        ],
    },
    python_requires='>=3.6',
)
