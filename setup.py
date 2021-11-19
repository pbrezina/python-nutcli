import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="nutcli",
    version="1.2",
    author="Pavel Březina",
    author_email="brezinapavel@gmail.com",
    description="Build robust command line interface fast.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pbrezina/python-nutcli",
    packages=['nutcli'],
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ],
    install_requires=[
        'colorama',
    ],
    python_requires='>=3.6',
)
