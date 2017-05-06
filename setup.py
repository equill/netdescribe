from setuptools import setup, find_packages

setup(
    name='netdescribe',
    version='0.1.0a',
    description='Scripts for performing discovery on network devices.',
    long_description='Scripts for performing discovery on network devices.',
    url='https://github.com/equill/netdescribe',
    author='James Fleming',
    author_email='james@electronic-quill.net',
    license='Apachev2',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Telecommunications Industry',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Netowrking :: Monitoring',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='network discovery snmp',
    install_requires=['pysnmp'],
    packages=find_packages(),
)
