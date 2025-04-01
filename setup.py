from setuptools import find_packages, setup

setup(
    name="mcp-server-aliyun-observability",
    version="0.1.0",
    description="aliyun observability mcp server",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="",
    author_email="",
    url="",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "mcp>=1.3.0",
        "pydantic>=2.10.0",
        "alibabacloud_arms20190808==8.0.0",
        "alibabacloud_sls20201230==5.7.0",
    ],
    entry_points={
        "console_scripts": [
            "mcp-server-aliyun-observability=mcp_server_aliyun_observability:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
