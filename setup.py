from setuptools import find_packages, setup

setup(
    name="hindi2pt",
    version="0.1.0",
    description="Pega a legenda em hindi de um video do YouTube e salva como SRT",
    author="Gabriel Moreno Ribeiro",
    license="MIT",
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.6",
    install_requires=["youtube-dl"],
    extras_require={"dev": ["pytest>=3.6"]},
    entry_points={"console_scripts": ["hindi2pt=hindi2pt.cli:main"]},
)
