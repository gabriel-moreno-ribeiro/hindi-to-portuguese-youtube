from setuptools import find_packages, setup

setup(
    name="hindi2pt",
    version="0.5.0",
    description="Traduz a legenda em hindi de um video do YouTube pra portugues do Brasil, e dubla se quiser",
    author="Gabriel Moreno Ribeiro",
    license="MIT",
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.6",
    install_requires=["youtube-dl"],
    extras_require={
        "free": ["googletrans==2.4.0"],
        "dub": ["gTTS>=2.0"],
        "dev": ["pytest>=3.6"],
    },
    entry_points={"console_scripts": ["hindi2pt=hindi2pt.cli:main"]},
)
