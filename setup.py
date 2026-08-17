from setuptools import setup, find_packages

setup(
    name='migration-toolkit',
    version='1.0.0',
    packages=find_packages(),
    install_requires=['faker>=18.0', 'flask>=3.0'],
    python_requires='>=3.10',
)
