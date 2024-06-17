from setuptools import find_packages, setup

setup(
    name="mrunner",
    version="24.07-rc1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "cryptography>=2.2.2",
        "PyYAML",
        "fabric",
        "path.py",
        "jinja2",
        "six",
        "attrs>=17.3",
        "click",
        "docker",
        "kubernetes>=5.0.0",
        "google-cloud",
        "termcolor",
        "pyperclip",
        "cloudpickle",
        "neptune>=1.0.0",
        "munch",
        "gin-config",
        "gitignore_parser",
    ],
    entry_points={
        "console_scripts": ["mrunner=mrunner.cli.mrunner_cli:cli"],
    },
    extras_require={
        "dev": ["black", "isort", "pre-commit"],
        "doc": ["sphinx-rtd-theme", "sphinx"],
    },
)
