"""工具入参 schema。

工具名、参数名、参数描述、工具描述共同构成「模型可见的 Tool Schema」，
属于提示词的一部分。字段名刻意采用驼峰命名以保持稳定的模型可见契约，
请勿改为下划线风格。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReadFileInput(BaseModel):
    fileName: str = Field(..., description="Name of a file to read")


class WriteFileInput(BaseModel):
    fileName: str = Field(..., description="Name of the file to write")
    content: str = Field(..., description="Content to write to the file")


class GeneratePdfInput(BaseModel):
    fileName: str = Field(..., description="Name of the file to save the generated PDF")
    content: str = Field(..., description="Content to be included in the PDF")


class DownloadResourceInput(BaseModel):
    url: str = Field(..., description="URL of the resource to download")
    fileName: str = Field(..., description="Name of the file to save the downloaded resource")


class TerminalCommandInput(BaseModel):
    command: str = Field(..., description="Command to execute in the terminal")


class ScrapeWebPageInput(BaseModel):
    url: str = Field(..., description="URL of the web page to scrape")


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query keyword")


class TerminateInput(BaseModel):
    """终止工具无入参。"""
