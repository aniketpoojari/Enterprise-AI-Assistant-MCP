from setuptools import find_packages, setup

setup(
    name="enterprise-ai-assistant-mcp",
    version="1.0.0",
    description="Enterprise AI Assistant with MCP + Guardrails for e-commerce analytics",
    author="Aniket Poojari",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "langchain>=0.3.0",
        "langchain-groq>=0.2.0",
        "langchain-core>=0.3.0",
        "langgraph>=0.2.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0",
        "mcp>=1.0.0",
        "fastapi>=0.115.0",
        "uvicorn>=0.30.0",
        "streamlit>=1.38.0",
        "requests>=2.31.0",
        "matplotlib>=3.9.0",
        "numpy>=1.26.0",
        "huggingface-hub>=0.20.0",
    ],
)
