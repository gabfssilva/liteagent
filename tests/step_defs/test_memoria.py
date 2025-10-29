"""
BDD tests for Memoria Tool - Long-term memory storage and retrieval.

Validates that:
- Memory storage works correctly
- Memory retrieval returns all entries
- Memory updates work
- Memory deletion works
- Different memory types are supported
"""
import sys
import importlib.util
from pytest_bdd import scenarios, given, when, then, parsers
from pytest import fixture
import asyncio
import functools


def async_to_sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


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


# Simple in-memory storage for testing
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


scenarios('../features/memoria.feature')


# ==================== FIXTURES ====================

@fixture
def memoria_tool():
    return Memoria(storage=SimpleStorage())


@fixture
def memoria_context():
    """Context to store state between steps."""
    return {}


# ==================== GIVEN STEPS ====================

@given("a memoria tool with simple storage", target_fixture="test_memoria")
def given_memoria_tool(memoria_tool):
    return memoria_tool


@given("an empty memoria storage", target_fixture="test_memoria")
def given_empty_memoria(memoria_tool):
    return memoria_tool


@given("I have stored 2 memories", target_fixture="test_memoria")
def given_stored_memories(memoria_tool, memoria_context):
    async def _store():
        entries = [
            MemoryEntry(content="First memory", type="semantic"),
            MemoryEntry(content="Second memory", type="episodic")
        ]
        ids = await memoria_tool.store.handler(memoria_tool, memories=entries)
        memoria_context['stored_ids'] = ids
        return memoria_tool
    return async_to_sync(_store)()


@given(parsers.parse('I have stored a memory with ID "{memory_id}"'), target_fixture="test_memoria")
def given_stored_memory_with_id(memoria_tool, memoria_context, memory_id):
    async def _store():
        entry = MemoryEntry(content="Test memory", type="semantic")
        ids = await memoria_tool.store.handler(memoria_tool, memories=[entry])
        memoria_context['memory_id'] = ids[0]
        return memoria_tool
    return async_to_sync(_store)()


# ==================== WHEN STEPS ====================

@when(parsers.parse('I store a memory with content "{content}" and type "{mem_type}"'), target_fixture="store_result")
def when_store_memory(test_memoria, memoria_context, content, mem_type):
    async def _store():
        entry = MemoryEntry(content=content, type=mem_type)
        result = await test_memoria.store.handler(test_memoria, memories=[entry])
        memoria_context['store_result'] = result
        return result
    return async_to_sync(_store)()


@when("I store multiple memories:", target_fixture="store_result")
def when_store_multiple_memories(test_memoria, memoria_context, datatable):
    """Store multiple memories from a datatable.

    The datatable is passed as Sequence[Sequence[object]] where:
    - First row contains headers (e.g., ["content", "type"])
    - Subsequent rows contain data values
    """
    async def _store():
        entries = []
        # First row is headers, subsequent rows are data
        headers = datatable[0]
        for row in datatable[1:]:
            # Convert row to dict using headers
            row_dict = dict(zip(headers, row))
            entries.append(MemoryEntry(content=row_dict['content'], type=row_dict['type']))
        result = await test_memoria.store.handler(test_memoria, memories=entries)
        memoria_context['store_result'] = result
        return result
    return async_to_sync(_store)()


@when("I store memories with different types", target_fixture="test_memoria")
def when_store_different_types(test_memoria, memoria_context):
    async def _store():
        entries = [
            MemoryEntry(content="Semantic fact", type="semantic"),
            MemoryEntry(content="Episodic event", type="episodic"),
            MemoryEntry(content="Procedural steps", type="procedural")
        ]
        ids = await test_memoria.store.handler(test_memoria, memories=entries)
        memoria_context['type_ids'] = ids
        return test_memoria
    return async_to_sync(_store)()


@when("I retrieve all memories", target_fixture="retrieve_result")
def when_retrieve_memories(test_memoria, memoria_context):
    async def _retrieve():
        result = await test_memoria.retrieve.handler(test_memoria)
        memoria_context['retrieve_result'] = result
        return result
    return async_to_sync(_retrieve)()


@when(parsers.parse('I update memory "{memory_id}" with new content "{new_content}"'), target_fixture="update_result")
def when_update_memory(test_memoria, memoria_context, memory_id, new_content):
    async def _update():
        actual_id = memoria_context.get('memory_id', memory_id)
        result = await test_memoria.update.handler(test_memoria, memory_id=actual_id, new_content=new_content)
        memoria_context['update_result'] = result
        return result
    return async_to_sync(_update)()


@when(parsers.parse('I try to update memory "{memory_id}" with content "{content}"'), target_fixture="update_result")
def when_try_update_memory(test_memoria, memoria_context, memory_id, content):
    async def _update():
        result = await test_memoria.update.handler(test_memoria, memory_id=memory_id, new_content=content)
        memoria_context['update_result'] = result
        return result
    return async_to_sync(_update)()


@when(parsers.parse('I delete memory "{memory_id}"'), target_fixture="delete_result")
def when_delete_memory(test_memoria, memoria_context, memory_id):
    async def _delete():
        actual_id = memoria_context.get('memory_id', memory_id)
        result = await test_memoria.delete.handler(test_memoria, memory_id=actual_id)
        memoria_context['delete_result'] = result
        return result
    return async_to_sync(_delete)()


@when(parsers.parse('I try to delete memory "{memory_id}"'), target_fixture="delete_result")
def when_try_delete_memory(test_memoria, memoria_context, memory_id):
    async def _delete():
        result = await test_memoria.delete.handler(test_memoria, memory_id=memory_id)
        memoria_context['delete_result'] = result
        return result
    return async_to_sync(_delete)()


@when(parsers.parse('I store a memory "{content}"'), target_fixture="crud_memory_id")
def when_store_crud_memory(test_memoria, memoria_context, content):
    async def _store():
        entry = MemoryEntry(content=content, type="semantic")
        ids = await test_memoria.store.handler(test_memoria, memories=[entry])
        memoria_context['crud_id'] = ids[0]
        return ids[0]
    return async_to_sync(_store)()


@when("I retrieve the memory")
def when_retrieve_crud_memory(test_memoria, memoria_context):
    async def _retrieve():
        result = await test_memoria.retrieve.handler(test_memoria)
        memoria_context['crud_retrieved'] = result
    async_to_sync(_retrieve)()


@when(parsers.parse('I update the memory with "{new_content}"'))
def when_update_crud_memory(test_memoria, memoria_context, new_content):
    async def _update():
        memory_id = memoria_context['crud_id']
        await test_memoria.update.handler(test_memoria, memory_id=memory_id, new_content=new_content)
    async_to_sync(_update)()


@when("I delete the memory")
def when_delete_crud_memory(test_memoria, memoria_context):
    async def _delete():
        memory_id = memoria_context['crud_id']
        await test_memoria.delete.handler(test_memoria, memory_id=memory_id)
    async_to_sync(_delete)()


# ==================== THEN STEPS ====================

@then(parsers.parse('the store operation should return {count:d} memory ID'))
@then(parsers.parse('the store operation should return {count:d} memory IDs'))
def then_store_returns_ids(store_result, count):
    assert isinstance(store_result, list)
    assert len(store_result) == count


@then(parsers.parse('the first memory ID should be "{expected_id}"'))
def then_first_id(store_result, expected_id):
    assert store_result[0] == expected_id


@then(parsers.parse('the memory IDs should be "{id1}", "{id2}", "{id3}"'))
def then_memory_ids_are(store_result, id1, id2, id3):
    assert store_result == [id1, id2, id3]


@then("I should be able to retrieve memories by type")
def then_retrieve_by_type(test_memoria, memoria_context):
    async def _check():
        memories = await test_memoria.retrieve.handler(test_memoria)
        return len(memories) > 0
    assert async_to_sync(_check)()


@then(parsers.parse('the {mem_type} memory should have type "{expected_type}"'))
def then_memory_has_type(test_memoria, memoria_context, mem_type, expected_type):
    async def _check():
        memories = await test_memoria.retrieve.handler(test_memoria)
        type_ids = memoria_context.get('type_ids', [])
        if mem_type == "semantic":
            idx = 0
        elif mem_type == "episodic":
            idx = 1
        else:  # procedural
            idx = 2
        return memories[type_ids[idx]].type == expected_type
    assert async_to_sync(_check)()


@then("the result should be an empty dict")
def then_empty_dict(retrieve_result):
    assert isinstance(retrieve_result, dict)
    assert len(retrieve_result) == 0


@then(parsers.parse('the result should contain {count:d} memories'))
@then(parsers.parse('the result should contain {count:d} memory'))
def then_result_contains_memories(retrieve_result, count):
    assert len(retrieve_result) == count


@then(parsers.parse('memory "{memory_id}" should have content "{expected_content}"'))
def then_memory_has_content(retrieve_result, memory_id, expected_content):
    assert memory_id in retrieve_result
    assert retrieve_result[memory_id].content == expected_content


@then("the update should succeed")
def then_update_succeeds(update_result):
    assert "successfully" in str(update_result).lower()


@then(parsers.parse('retrieving memory "{memory_id}" should show "{expected_content}"'))
def then_retrieving_shows_content(test_memoria, memoria_context, memory_id, expected_content):
    async def _check():
        memories = await test_memoria.retrieve.handler(test_memoria)
        actual_id = memoria_context.get('memory_id', memory_id)
        return memories[actual_id].content == expected_content
    assert async_to_sync(_check)()


@then(parsers.parse('the update should return "{expected}"'))
def then_update_returns(update_result, expected):
    assert expected.lower() in str(update_result).lower()


@then(parsers.parse('the delete should return "{expected}"'))
def then_delete_returns(delete_result, expected):
    assert expected.lower() in str(delete_result).lower()


@then("the delete should succeed")
def then_delete_succeeds(delete_result):
    assert "successfully" in str(delete_result).lower()


@then(parsers.parse('memory "{memory_id}" should no longer exist'))
def then_memory_not_exists(test_memoria, memoria_context, memory_id):
    async def _check():
        memories = await test_memoria.retrieve.handler(test_memoria)
        actual_id = memoria_context.get('memory_id', memory_id)
        return actual_id not in memories
    assert async_to_sync(_check)()


@then("the memory should no longer exist")
def then_crud_memory_not_exists(test_memoria, memoria_context):
    async def _check():
        memories = await test_memoria.retrieve.handler(test_memoria)
        memory_id = memoria_context['crud_id']
        return memory_id not in memories
    assert async_to_sync(_check)()
