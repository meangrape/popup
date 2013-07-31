import os.path
import sys

from setuptools import setup, find_packages
from build_manpage import build_manpage

HOME=os.path.expanduser('~')

setup(
    name='popup',
    version='0.2.0',
    author='Jay Edwards',
    cmdclass={'build_manpage': build_manpage},
    author_email='jay@meangrape.com',
    packages=['PopupServer', 'PopupServer.test'],
    package_data={'PopupServer': ['playbooks/*/*.yaml']},
    data_files=[('%s/.popup/config/ssh_configs' % HOME, []),
    ('%s/.popup/config/ssh_control' % HOME, []), ('%s/.popup/keys' % HOME, []),
    ('%s/.popup/manifests' % HOME, []), ('%s/share/man/man1' % sys.prefix, ['doc/popup.1']),
    ('.', ['CHANGES.txt', 'README.txt', 'LICENSE.txt'])],
    url="http://pypi.python.org/pypi/popup",
    license='BSD',
    description='Quickly setup an EC2 server running OpenVPN and other useful tools',
    long_description=open('README.txt').read(),
    install_requires=[
       "boto >= 2.7.0",
       ],
    setup_requires=[
       "github-distutils >= 0.1.0",
       "stdeb >= 0.6",
       ],
    entry_points = {
        'console_scripts': [
            'popup = PopupServer.popup:main',
        ],
        'distutils.commands': [
            'build_manpage = build_manpage.build_manpage',
        ]
    }
)
