import pytest
import os
from datetime import datetime
from src.open_amazon_chat_completions_server.cli.chat_history import ChatHistoryManager, ChatSession

@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary directory for chat history storage."""
    return str(tmp_path / "chat_history")

@pytest.fixture
def history_manager(temp_storage_dir):
    """Create a ChatHistoryManager instance with temporary storage."""
    return ChatHistoryManager(storage_dir=temp_storage_dir)

@pytest.fixture
def sample_session():
    """Create a sample chat session."""
    return ChatSession.create_new(
        model="test-model",
        name="Test Session"
    )

def test_create_new_session():
    """Test creating a new chat session."""
    session = ChatSession.create_new("test-model", "Test Session")
    assert session.model == "test-model"
    assert session.name == "Test Session"
    assert isinstance(session.id, str)
    assert isinstance(session.created_at, datetime)
    assert isinstance(session.updated_at, datetime)
    assert session.messages == []

def test_session_serialization():
    """Test session serialization and deserialization."""
    original = ChatSession.create_new("test-model", "Test Session")
    original.messages = [{"role": "user", "content": "Hello"}]
    
    # Test to_dict
    data = original.to_dict()
    assert data["model"] == "test-model"
    assert data["name"] == "Test Session"
    assert data["messages"] == [{"role": "user", "content": "Hello"}]
    
    # Test from_dict
    restored = ChatSession.from_dict(data)
    assert restored.model == original.model
    assert restored.name == original.name
    assert restored.messages == original.messages
    assert restored.created_at == original.created_at
    assert restored.updated_at == original.updated_at

def test_save_and_load_session(history_manager, sample_session):
    """Test saving and loading a chat session."""
    # Save session
    history_manager.save_session(sample_session)
    
    # Load session
    loaded = history_manager.load_session(sample_session.id)
    assert loaded.id == sample_session.id
    assert loaded.model == sample_session.model
    assert loaded.name == sample_session.name

def test_list_sessions(history_manager):
    """Test listing chat sessions."""
    # Create multiple sessions
    sessions = [
        ChatSession.create_new("model1", "Session 1"),
        ChatSession.create_new("model2", "Session 2"),
        ChatSession.create_new("model3", "Session 3")
    ]
    
    # Save all sessions
    for session in sessions:
        history_manager.save_session(session)
    
    # List sessions
    listed = history_manager.list_sessions()
    assert len(listed) == len(sessions)
    assert all(isinstance(s, ChatSession) for s in listed)
    
    # Check sorting (should be newest first)
    assert all(listed[i].created_at >= listed[i+1].created_at for i in range(len(listed)-1))

def test_delete_session(history_manager, sample_session):
    """Test deleting a chat session."""
    # Save session
    history_manager.save_session(sample_session)
    
    # Verify it exists
    assert os.path.exists(os.path.join(history_manager.storage_dir, f"{sample_session.id}.json"))
    
    # Delete session
    history_manager.delete_session(sample_session.id)
    
    # Verify it's gone
    assert not os.path.exists(os.path.join(history_manager.storage_dir, f"{sample_session.id}.json"))
    
    # Verify attempting to delete again raises error
    with pytest.raises(ValueError):
        history_manager.delete_session(sample_session.id)

def test_update_session(history_manager, sample_session):
    """Test updating a chat session."""
    # Save initial session
    history_manager.save_session(sample_session)
    initial_updated_at = sample_session.updated_at
    
    # Update session
    sample_session.messages.append({"role": "user", "content": "Hello"})
    history_manager.update_session(sample_session)
    
    # Load updated session
    updated = history_manager.load_session(sample_session.id)
    assert len(updated.messages) == 1
    assert updated.messages[0]["content"] == "Hello"
    assert updated.updated_at > initial_updated_at

def test_invalid_session_id(history_manager):
    """Test handling of invalid session IDs."""
    with pytest.raises(ValueError):
        history_manager.load_session("nonexistent-id")

def test_corrupted_session_file(history_manager, sample_session):
    """Test handling of corrupted session files."""
    # Save invalid JSON
    file_path = os.path.join(history_manager.storage_dir, f"{sample_session.id}.json")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        f.write("invalid json")
    
    # Verify the corrupted file is skipped when listing
    sessions = history_manager.list_sessions()
    assert len(sessions) == 0 