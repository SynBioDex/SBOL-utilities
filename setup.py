from setuptools import setup

setup(name='sbol-utilities',
      description='SBOL-utilities',
      version='1.0a',
      install_requires=[
            'sbol3',
            'graphviz'
      ],
      packages=['sbol_utilities'],
)
