import setuptools

try:
    with open("README.md", "r") as fh:
        long_description = fh.read()
except IOError:
    long_description = ""

setuptools.setup(
    name='framegram',
    version='0.1.0',
    description='A Python project',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Example Author",
    author_email="author@example.com",
    url='https://github.com/example/project',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    # packages=setuptools.find_packages()
    py_modules=["framegram"],
    python_requires='>=3.6',
    install_requires=['Pillow'],
    extras_require={
         'dev': ['mypy'],
         'test': ['pytest'],
    },
    # If there are data files included in your packages that need to be
    # installed, specify them here.
    package_data={  # Optional
         'framegram': ['ttf/*.ttf'],
    },
    entry_points={
        'console_scripts': [
            'framegram=framegram:main',
        ],
    },
)
