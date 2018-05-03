#!/usr/bin/env python
# coding=utf-8
# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from setuptools import setup

VERSION = "1.0.0"

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'License :: OSI Approved :: MIT License',
]

DEPENDENCIES = [
    'click',
    'requests',
    'paramiko',
    'scp'
]

setup(
    name='azure-iot-starterkit-cli',
    version=VERSION,
    description='Microsoft Azure IoT Starter Kit Companion CLI',
    long_description='Companion CLI for the Azure IoT Device Starter Kits',
    license='MIT',
    author='Azure CAT E2E',
    author_email='azcate2esupport@microsoft.com',
    url = 'https://github.com/Azure-Samples/azure-iot-starterkit-cli',
    download_url = 'https://github.com/Azure-Samples/azure-iot-starterkit-cli/archive/1.0.0.tar.gz',
    keywords = ['Azure', 'IoT', 'Microsoft', 'StarterKit', 'CLI', 'teXXmo', 'grove'],
    classifiers=CLASSIFIERS,
    py_modules=['iot'],
    include_package_data=True,
    install_requires=DEPENDENCIES,
    entry_points='''
        [console_scripts]
        iot=iot:cli
    '''
)
