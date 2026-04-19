from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from src.contracts.core import RawNewsItem
from src.db.repositories.jsonl import JsonlRawNewsRepository
from src.application.use_cases.ingest_news import IngestNewsUseCase

@pytest.fixture
def temp_data_dir():
    dir_path = Path("tests/tmp_ingest_test")
    dir_path.mkdir(parents=True, exist_ok=True)
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)

@pytest.fixture
def raw_news_repo(temp_data_dir):
    return JsonlRawNewsRepository(temp_data_dir / "raw_news.jsonl")

@pytest.fixture
def use_case(raw_news_repo):
    return IngestNewsUseCase(raw_news_repo=raw_news_repo)

@pytest.mark.asyncio
async def test_ingest_single_and_persistence(use_case, raw_news_repo):
    item = RawNewsItem(
        id="",
        source="test_source",
        source_id="12345",
        title="Test Title",
        body="Test Body",
        url="http://test.com",
        published_at=datetime.now(),
        collected_at=datetime.now(),
    )
    
    # 1. First ingestion
    refined_id = await use_case.execute_single(item)
    assert refined_id.startswith("raw_")
    
    # 2. Check persistence
    saved_item = await raw_news_repo.get(refined_id)
    assert saved_item is not None
    assert saved_item.source_id == "12345"
    assert saved_item.title == "Test Title"
    
    # 3. Duplicate ingestion (should not create new entry)
    refined_id_2 = await use_case.execute_single(item)
    assert refined_id == refined_id_2
    
    # Verify file has only 1 line (plus final newline)
    with raw_news_repo.path.open("r") as f:
        lines = [line for line in f if line.strip()]
        assert len(lines) == 1

@pytest.mark.asyncio
async def test_ingest_batch(use_case, raw_news_repo):
    items = [
        RawNewsItem(id="", source="src", source_id=str(i), title=f"T{i}", body="B", url="U", published_at=datetime.now(), collected_at=datetime.now())
        for i in range(5)
    ]
    
    count = await use_case.execute_batch(items)
    assert count == 5
    
    # Verify 5 items saved
    for i in range(5):
        exists = await raw_news_repo.exists(use_case._generate_id("src", str(i)))
        assert exists is True
