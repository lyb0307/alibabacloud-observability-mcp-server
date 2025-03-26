from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcp_server_aliyun_observability",
    version="0.1.0",
    author="Alibaba Cloud",
    description="Aliyun Observability MCP Server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/mcp-server-aliyun-observability",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "mcp>=1.3.0",
        "pydantic>=2.10.0",
        "alibabacloud-tea-util>=0.3.0",
    ],
    dependency_links=[
        "file:src/mcp_server_aliyun_observability/libs/sls-20201230",
    ],
    entry_points={
        "console_scripts": [
            "mcp-server-aliyun-observability=mcp_server_aliyun_observability:main",
        ],
    },
    include_package_data=True,
    package_data={
        "mcp_server_aliyun_observability": ["py.typed"],
    },
)
