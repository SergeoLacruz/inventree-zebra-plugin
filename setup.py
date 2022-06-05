# -*- coding: utf-8 -*-

import setuptools

from inventree_zebra.version import ZEBRA_PLUGIN_VERSION

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setuptools.setup(
    name="inventree-zebra-plugin",

    version=ZEBRA_PLUGIN_VERSION,

    author="Michael Buchmann",

    author_email="michael@buchmann.ruhr",

    description="Zebra label printer plugin for InvenTree",

    long_description=long_description,

    long_description_content_type='text/markdown',

    keywords="inventree label printer printing inventory",

    url="https://github.com/SergeoLacruz/inventree-zebra-plugin",

    license="MIT",

    packages=setuptools.find_packages(),

    install_requires=[
        'zpl @ git+https://github.com/cod3monk/zpl',
    ],

    setup_requires=[
        "wheel",
        "twine",
    ],

    python_requires=">=3.6",

    entry_points={
        "inventree_plugins": [
            "ZebraLabeLPlugin = inventree_zebra.zebra_plugin:ZebraLabelPlugin"
        ]
    },
)
