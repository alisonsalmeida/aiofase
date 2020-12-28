from setuptools import setup, find_packages

setup(
    name='aiofase',
    version='1.0.0',
    url='https://github.com/alisonsalmeida/aiofase',
    license='GPLv3',
    author='Alison Almeida',
    author_email='wsalisonxp@gmail.com',
    description='A Fast-Asynchronous-microService-Environment compatible with asyncio.',
    packages=find_packages(),
    py_modules=['aiofase'],
    platforms='any',
    install_requires=[],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Networking",
    ],
)
