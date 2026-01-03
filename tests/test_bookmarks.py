import pytest
import os
import sqlite3
from src.core.storage import Storage
from src.core.services.bookmark_service import BookmarkService

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_metadata.db"
    return str(db_path)

@pytest.fixture
def storage(temp_db):
    return Storage(temp_db)

@pytest.fixture
def bookmark_service(storage):
    return BookmarkService(storage)

def test_toggle_bookmark(storage, bookmark_service):
    file_path = "C:/test/doc.pdf"
    
    # Initially False
    assert bookmark_service.is_bookmarked(file_path) is False
    
    # Toggle to True
    new_status = bookmark_service.toggle_bookmark(file_path)
    assert new_status is True
    assert bookmark_service.is_bookmarked(file_path) is True
    
    # Verify persistence
    meta = storage.get_pdf_metadata(file_path)
    assert meta['is_bookmarked'] == 1
    
    # Toggle back to False
    new_status = bookmark_service.toggle_bookmark(file_path)
    assert new_status is False
    assert bookmark_service.is_bookmarked(file_path) is False
    
    # Verify persistence
    meta = storage.get_pdf_metadata(file_path)
    assert meta['is_bookmarked'] == 0

def test_update_existing_record(storage, bookmark_service):
    file_path = "C:/test/existing.pdf"
    # Create record with other metadata
    storage.update_pdf_metadata(file_path, tags="work", notes="important", bookmarks="")
    
    # Toggle bookmark shouldn't affect other metadata
    bookmark_service.toggle_bookmark(file_path)
    
    meta = storage.get_pdf_metadata(file_path)
    assert meta['is_bookmarked'] == 1
    assert meta['tags'] == "work"
    assert meta['notes'] == "important"
