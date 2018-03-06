#!/usr/bin/python3

"Create the package"

from setuptools import setup

setup(
    name='netdescribe',
    packages=['netdescribe'],
    version='0.2.3',
    description='Scripts for performing discovery on network devices.',
    long_description='Scripts for performing discovery on network devices.',
    author='James Fleming',
    url='https://github.com/equill/netdescribe',
    author_email='james@electronic-quill.net',
    keywords=['network', 'discovery', 'snmp'],
    install_requires=['pysnmp'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Telecommunications Industry',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking :: Monitoring',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5'],
    license='Apachev2'
)
