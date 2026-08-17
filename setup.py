import os
from glob import glob

from setuptools import setup, find_packages

PACKAGE_NAME = 'sentry_rclpy'

setup(
    name=PACKAGE_NAME,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + PACKAGE_NAME]),
        ('share/' + PACKAGE_NAME, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    author='Alexander Alderman Webb',
    author_email='alexander.webb@sentry.io',
    maintainer='Alexander Alderman Webb',
    maintainer_email='alexander.webb@sentry.io',
    description='A hackweek SDK for RCLPy (ROS client library for Python).',
    license='MIT',
)
