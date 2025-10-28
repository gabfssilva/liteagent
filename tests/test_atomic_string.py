"""
Tests for AtomicString - Thread-safe string accumulation.

Validates that:
- AtomicString accumulates text correctly
- Async iteration works properly
- await_complete waits for completion
- Mutation protection after completion
- JSON parsing works correctly
"""
import asyncio
from ward import test

from liteagent.internal.atomic_string import AtomicString


@test("AtomicString appends text correctly")
async def _():
    """
    Tests that AtomicString can append text and get current value.

    Deterministic scenario:
    - Create empty AtomicString
    - Append multiple strings
    - Validate concatenation is correct
    """
    atomic = AtomicString()

    await atomic.append("Hello")
    assert await atomic.get() == "Hello"

    await atomic.append(" ")
    assert await atomic.get() == "Hello "

    await atomic.append("World")
    assert await atomic.get() == "Hello World"

    assert not atomic.is_complete

    await atomic.complete()
    assert atomic.is_complete


@test("AtomicString set replaces entire value")
async def _():
    """
    Tests that AtomicString.set replaces the entire value.

    Deterministic scenario:
    - Create AtomicString with initial value
    - Use set to replace entire content
    - Validate new value
    """
    atomic = AtomicString("Initial")

    assert await atomic.get() == "Initial"

    await atomic.set("Replaced")
    assert await atomic.get() == "Replaced"


@test("AtomicString await_complete waits for completion")
async def _():
    """
    Tests that await_complete blocks until string is completed.

    Deterministic scenario:
    - Create AtomicString
    - Start task that appends and completes after delay
    - await_complete should wait and return final value
    """
    atomic = AtomicString()

    async def append_with_delay():
        await atomic.append("First")
        await asyncio.sleep(0.1)
        await atomic.append(" Second")
        await asyncio.sleep(0.1)
        await atomic.append(" Third")
        await atomic.complete()

    # Start appending in background
    task = asyncio.create_task(append_with_delay())

    # Wait for completion
    final_value = await atomic.await_complete()

    assert final_value == "First Second Third"
    assert atomic.is_complete

    await task


@test("AtomicString async iteration yields incremental updates")
async def _():
    """
    Tests that iterating over AtomicString yields updates as they happen.

    Deterministic scenario:
    - Create AtomicString
    - Append values in background
    - Iterate and collect all yielded values
    """
    atomic = AtomicString()

    async def append_values():
        await asyncio.sleep(0.05)
        await atomic.append("A")
        await asyncio.sleep(0.05)
        await atomic.append("B")
        await asyncio.sleep(0.05)
        await atomic.append("C")
        await atomic.complete()

    # Start appending in background
    task = asyncio.create_task(append_values())

    # Collect all yielded values
    values = []
    async for value in atomic:
        values.append(value)

    # Should have yielded incremental updates
    assert len(values) > 0
    assert values[-1] == "ABC"  # Final value should be complete

    await task


@test("AtomicString cannot mutate after completion")
async def _():
    """
    Tests that AtomicString raises error when trying to mutate after completion.

    Deterministic scenario:
    - Create and complete AtomicString
    - Try to append - should raise RuntimeError
    - Try to set - should raise RuntimeError
    """
    atomic = AtomicString("Initial")
    await atomic.complete()

    # Should raise RuntimeError when trying to append after completion
    try:
        await atomic.append(" More")
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "Cannot mutate a complete AtomicString" in str(e)

    # Should raise RuntimeError when trying to set after completion
    try:
        await atomic.set("New value")
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "Cannot mutate a complete AtomicString" in str(e)


@test("AtomicString can be created as already completed")
async def _():
    """
    Tests that AtomicString can be initialized as completed.

    Deterministic scenario:
    - Create AtomicString with complete=True
    - Should already be complete
    - Should not accept mutations
    """
    atomic = AtomicString("Initial Value", complete=True)

    # Should be complete immediately
    assert atomic.is_complete

    # Can get value immediately
    value = await atomic.get()
    assert value == "Initial Value"

    # await_complete should return immediately
    final_value = await atomic.await_complete()
    assert final_value == "Initial Value"

    # Should not accept mutations
    try:
        await atomic.append(" More")
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        assert True


@test("AtomicString await_as_json parses JSON correctly")
async def _():
    """
    Tests that await_as_json parses JSON content correctly.

    Deterministic scenario:
    - Create AtomicString with JSON content
    - Use await_as_json to parse
    - Validate parsed structure
    """
    atomic = AtomicString()

    async def append_json():
        await atomic.append('{"name": "')
        await asyncio.sleep(0.05)
        await atomic.append('John')
        await asyncio.sleep(0.05)
        await atomic.append('", "age": 30}')
        await atomic.complete()

    task = asyncio.create_task(append_json())

    # Parse as JSON
    result = await atomic.await_as_json()

    assert result["name"] == "John"
    assert result["age"] == 30

    await task
