from setuptools import setup, find_packages

setup(
    name="flyvr",
    version="0.0.1",
    long_description=__doc__,
    packages=['flyvr'],
    include_package_data=True,
    install_requires=[
        'opencv-python',
        'pynput',
        'pyserial',
        'scikit-image'
    ],
    zip_safe=False
)
