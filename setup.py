from setuptools import find_packages, setup

setup(
    name="moc-platform",
    version="1.0.0",
    packages=find_packages(include=["api", "api.*", "core", "core.*", "modules", "modules.*"]),
    py_modules=["app"],
    include_package_data=True,
)
