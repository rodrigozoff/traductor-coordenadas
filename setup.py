from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="traductor-coordenadas",
    version="0.1.0",
    author="Tu Nombre",
    author_email="tu@email.com",
    description="Traductor de coordenadas entre Google Maps y Gauss-Krüger para Argentina",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tuusuario/traductor-coordenadas",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pyproj>=3.6.1",
        "pandas>=2.1.0",
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'traductor-coordenadas=traductor_coordenadas.cli:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
