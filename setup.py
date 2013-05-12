"""
GRobot
--------

Powerful Web Robot.

"""
from setuptools import setup, find_packages


setup(
    name='GRobot',
    version='0.0.2',
    url='https://github.com/DYFeng/GRobot',
    license='MIT',
    author='DY.Feng',
    author_email='yyfeng88625@gmail.com',
    description='Powerful Web Robot.',
    long_description=__doc__,
    install_requires=[
        'lxml',
        ],
    data_files=[
        ('grobot', ['README.md','license.txt']),
        ('javascripts', ['javascripts/atoms.js',
                              'javascripts/htmlutils.js',
                              'javascripts/license.txt'
        ]),
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)

