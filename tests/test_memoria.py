"""
Tests for Memoria Tool - Long-term memory storage and retrieval.

Validates that:
- Memory storage works correctly
- Memory retrieval returns all entries
- Memory updates work
- Memory deletion works
- Different memory types are supported

NOTE: Uses mock storage to avoid embeddings dependency.
"""
import sys
import importlib.util
from ward import test, fixture

# Load memoria module directly
spec = importlib.util.spec_from_file_location(
    "memoria_module",
    "/home/user/liteagent/liteagent/tools/memoria.py"
)
memoria_module = importlib.util.module_from_spec(spec)
sys.modules['memoria_module'] = memoria_module
spec.loader.exec_module(memoria_module)
Memoria = memoria_module.Memoria
MemoryEntry = memoria_module.MemoryEntry
Storage = memoria_module.Storage


# Simple in-memory storage for testing (no embeddings)
class SimpleStorage(Storage):
    def __init__(self):
        self.memories = {}
        self.counter = 0

    async def store(self, entry: MemoryEntry) -> str:
        memory_id = str(self.counter)
        self.memories[memory_id] = entry
        self.counter += 1
        return memory_id

    async def retrieve(self) -> dict[str, MemoryEntry]:
        return self.memories.copy()

    async def delete(self, memory_id: str) -> bool:
        if memory_id in self.memories:
            del self.memories[memory_id]
            return True
        return False

    async def update(self, memory_id: str, new_content: str) -> bool:
        if memory_id in self.memories:
            self.memories[memory_id].content = new_content
            return True
        return False


@fixture
def memoria_tool():
    """Create Memoria with simple storage."""
    return Memoria(storage=SimpleStorage())


# ============================================
# Store Tests
# ============================================

@test("store saves single memory and returns ID")
async def _(memoria_tool=memoria_tool):
    """Tests that store saves a single memory."""
    entry = MemoryEntry(content="Remember: user prefers Python", type="semantic")

    result = await memoria_tool.store.handler(
        memoria_tool,
        memories=[entry]
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == "0"  # First ID


@test("store saves multiple memories and returns IDs")
async def _(memoria_tool=memoria_tool):
    """Tests that store can save multiple memories at once."""
    entries = [
        MemoryEntry(content="User likes cats", type="semantic"),
        MemoryEntry(content="User's birthday is Jan 1", type="episodic"),
        MemoryEntry(content="To send email: use smtp", type="procedural")
    ]

    result = await memoria_tool.store.handler(
        memoria_tool,
        memories=entries
    )

    assert isinstance(result, list)
    assert len(result) == 3
    assert result == ["0", "1", "2"]


@test("store supports different memory types")
async def _(memoria_tool=memoria_tool):
    """Tests that store supports semantic, episodic, and procedural memories."""
    entries = [
        MemoryEntry(content="Semantic fact", type="semantic"),
        MemoryEntry(content="Episodic event", type="episodic"),
        MemoryEntry(content="Procedural steps", type="procedural")
    ]

    ids = await memoria_tool.store.handler(memoria_tool, memories=entries)

    # Retrieve and verify types
    all_memories = await memoria_tool.retrieve.handler(memoria_tool)

    assert all_memories[ids[0]].type == "semantic"
    assert all_memories[ids[1]].type == "episodic"
    assert all_memories[ids[2]].type == "procedural"


# ============================================
# Retrieve Tests
# ============================================

@test("retrieve returns empty dict when no memories")
async def _(memoria_tool=memoria_tool):
    """Tests that retrieve returns empty dict initially."""
    result = await memoria_tool.retrieve.handler(memoria_tool)

    assert isinstance(result, dict)
    assert len(result) == 0


@test("retrieve returns all stored memories")
async def _(memoria_tool=memoria_tool):
    """Tests that retrieve returns all memories after storing."""
    # Store some memories
    entries = [
        MemoryEntry(content="First memory", type="semantic"),
        MemoryEntry(content="Second memory", type="episodic")
    ]
    await memoria_tool.store.handler(memoria_tool, memories=entries)

    # Retrieve
    result = await memoria_tool.retrieve.handler(memoria_tool)

    assert isinstance(result, dict)
    assert len(result) == 2
    assert "0" in result
    assert "1" in result
    assert result["0"].content == "First memory"
    assert result["1"].content == "Second memory"


# ============================================
# Update Tests
# ============================================

@test("update modifies existing memory content")
async def _(memoria_tool=memoria_tool):
    """Tests that update changes memory content."""
    # Store a memory
    entry = MemoryEntry(content="Original content", type="semantic")
    ids = await memoria_tool.store.handler(memoria_tool, memories=[entry])
    memory_id = ids[0]

    # Update it
    result = await memoria_tool.update.handler(
        memoria_tool,
        memory_id=memory_id,
        new_content="Updated content"
    )

    assert "successfully" in result.lower()

    # Verify update
    memories = await memoria_tool.retrieve.handler(memoria_tool)
    assert memories[memory_id].content == "Updated content"


@test("update returns not found for non-existent ID")
async def _(memoria_tool=memoria_tool):
    """Tests that update returns error for non-existent memory."""
    result = await memoria_tool.update.handler(
        memoria_tool,
        memory_id="999",
        new_content="New content"
    )

    assert "not found" in result.lower()


# ============================================
# Delete Tests
# ============================================

@test("delete removes memory successfully")
async def _(memoria_tool=memoria_tool):
    """Tests that delete removes a memory."""
    # Store a memory
    entry = MemoryEntry(content="To be deleted", type="semantic")
    ids = await memoria_tool.store.handler(memoria_tool, memories=[entry])
    memory_id = ids[0]

    # Verify it exists
    memories_before = await memoria_tool.retrieve.handler(memoria_tool)
    assert memory_id in memories_before

    # Delete it
    result = await memoria_tool.delete.handler(
        memoria_tool,
        memory_id=memory_id
    )

    assert "successfully" in result.lower()

    # Verify it's gone
    memories_after = await memoria_tool.retrieve.handler(memoria_tool)
    assert memory_id not in memories_after


@test("delete returns not found for non-existent ID")
async def _(memoria_tool=memoria_tool):
    """Tests that delete returns error for non-existent memory."""
    result = await memoria_tool.delete.handler(
        memoria_tool,
        memory_id="999"
    )

    assert "not found" in result.lower()


# ============================================
# Integration Tests
# ============================================

@test("full CRUD cycle works correctly")
async def _(memoria_tool=memoria_tool):
    """Tests complete create-read-update-delete cycle."""
    # Create
    entry = MemoryEntry(content="CRUD test memory", type="semantic")
    ids = await memoria_tool.store.handler(memoria_tool, memories=[entry])
    memory_id = ids[0]

    # Read
    memories = await memoria_tool.retrieve.handler(memoria_tool)
    assert memory_id in memories
    assert memories[memory_id].content == "CRUD test memory"

    # Update
    update_result = await memoria_tool.update.handler(
        memoria_tool,
        memory_id=memory_id,
        new_content="Updated CRUD memory"
    )
    assert "successfully" in update_result.lower()

    # Verify update
    memories = await memoria_tool.retrieve.handler(memoria_tool)
    assert memories[memory_id].content == "Updated CRUD memory"

    # Delete
    delete_result = await memoria_tool.delete.handler(
        memoria_tool,
        memory_id=memory_id
    )
    assert "successfully" in delete_result.lower()

    # Verify deletion
    memories = await memoria_tool.retrieve.handler(memoria_tool)
    assert memory_id not in memories
