from setuptools import find_packages, setup

setup(
    name="mrunner",
    version="0.2.10",
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
        "neptune",
        "munch",
        "gin-config",
        "gitignore_parser",
    ],
    entry_points={
        "console_scripts": ["mrunner=mrunner.cli.mrunner_cli:cli"],
    },
    extras_require={"dev": ["black", "isort", "pre-commit"]},
)
