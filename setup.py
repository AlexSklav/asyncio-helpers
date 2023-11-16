#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext
from setuptools import find_packages
from setuptools import setup
import io
import re
import sys

import versioneer

# See https://blog.ionelmc.ro/2014/06/25/python-packaging-pitfalls/
setup(name='asyncio-helpers',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='Helper functions, etc. for asyncio development',
      keywords='',
      author='Christian Fobel',
      author_email='christian@fobel.net',
      url='https://github.com/sci-bots/asyncio-helpers',
      license='BSD',
      packages=['asyncio_helpers'],
      # Install data listed in `MANIFEST.in`
      include_package_data=True)
