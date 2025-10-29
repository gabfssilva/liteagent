"""
Tests for Cached Iterator - Cached async iteration with replay support.

Validates that:
- CachedStringAccumulator maintains backward compatibility with AtomicString
- CachedAsyncIterator caches values and allows replay
- AppendableIterator provides push-based async iteration
- Multiple consumers can iterate with replay
"""
import asyncio
from ward import test

from liteagent.internal.cached_iterator import (
    CachedStringAccumulator,
    CachedAsyncIterator,
    AppendableIterator
)


# ============================================
# CachedStringAccumulator Tests (AtomicString compatibility)
# ============================================

@test("CachedStringAccumulator appends text correctly")
async def _():
    """
    Tests that CachedStringAccumulator can append text and get current value.

    Deterministic scenario:
    - Create empty accumulator
    - Append multiple strings
    - Validate concatenation is correct
    """
    accumulator = CachedStringAccumulator()

    await accumulator.append("Hello")
    await asyncio.sleep(0.01)  # Let append task run
    result = await accumulator.get()
    assert result == "Hello"

    await accumulator.append(" ")
    await asyncio.sleep(0.01)
    result = await accumulator.get()
    assert result == "Hello "

    await accumulator.append("World")
    await asyncio.sleep(0.01)
    result = await accumulator.get()
    assert result == "Hello World"

    assert not accumulator.is_complete

    await accumulator.complete()
    # Await complete to ensure propagation
    final_value = await accumulator.await_complete()
    assert final_value == "Hello World"
    assert accumulator.is_complete


@test("CachedStringAccumulator await_complete waits for completion")
async def _():
    """
    Tests that await_complete blocks until string is completed.

    Deterministic scenario:
    - Create accumulator
    - Start task that appends and completes after delay
    - await_complete should wait and return final value
    """
    accumulator = CachedStringAccumulator()

    async def append_with_delay():
        await accumulator.append("First")
        await asyncio.sleep(0.05)
        await accumulator.append(" Second")
        await asyncio.sleep(0.05)
        await accumulator.append(" Third")
        await accumulator.complete()

    # Start appending in background
    task = asyncio.create_task(append_with_delay())

    # Wait for completion
    final_value = await accumulator.await_complete()

    assert final_value == "First Second Third"
    assert accumulator.is_complete

    await task


@test("CachedStringAccumulator cannot mutate after completion")
async def _():
    """
    Tests that accumulator raises error when trying to mutate after completion.

    Deterministic scenario:
    - Create and complete accumulator
    - Try to append - should raise RuntimeError
    """
    accumulator = CachedStringAccumulator("Initial")
    await accumulator.complete()

    # Should raise RuntimeError when trying to append after completion
    try:
        await accumulator.append(" More")
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "Cannot append to completed iterator" in str(e)


# TODO: Fix initialization with complete=True
# @test("CachedStringAccumulator can be created as already completed")
# async def _():
#     """
#     Tests that accumulator can be initialized as completed.
#
#     Deterministic scenario:
#     - Create accumulator with complete=True
#     - Should already be complete
#     - Should not accept mutations
#     """
#     accumulator = CachedStringAccumulator("Initial Value", complete=True)
#
#     # Give it a moment to complete async initialization
#     await asyncio.sleep(0.05)
#
#     # Should be complete
#     assert accumulator.is_complete
#
#     # await_complete should return value
#     final_value = await accumulator.await_complete()
#     assert final_value == "Initial Value"


@test("CachedStringAccumulator await_as_json parses JSON correctly")
async def _():
    """
    Tests that await_as_json parses JSON content correctly.

    Deterministic scenario:
    - Create accumulator with JSON content
    - Use await_as_json to parse
    - Validate parsed structure
    """
    accumulator = CachedStringAccumulator()

    async def append_json():
        await accumulator.append('{"name": "')
        await asyncio.sleep(0.05)
        await accumulator.append('John')
        await asyncio.sleep(0.05)
        await accumulator.append('", "age": 30}')
        await accumulator.complete()

    task = asyncio.create_task(append_json())

    # Parse as JSON
    result = await accumulator.await_as_json()

    assert result["name"] == "John"
    assert result["age"] == 30

    await task


# ============================================
# AppendableIterator Tests
# ============================================

@test("AppendableIterator yields appended values")
async def _():
    """
    Tests that AppendableIterator yields values in order.

    Deterministic scenario:
    - Create iterator
    - Append values
    - Iterate and verify order
    """
    appendable = AppendableIterator[str]()

    async def producer():
        await appendable.append("First")
        await appendable.append("Second")
        await appendable.append("Third")
        await appendable.complete()

    # Start producer
    task = asyncio.create_task(producer())

    # Consume
    values = []
    async for value in appendable:
        values.append(value)

    assert values == ["First", "Second", "Third"]
    await task


@test("AppendableIterator prevents append after complete")
async def _():
    """
    Tests that AppendableIterator rejects appends after completion.

    Deterministic scenario:
    - Create and complete iterator
    - Try to append - should raise RuntimeError
    """
    appendable = AppendableIterator[str]()
    await appendable.complete()

    try:
        await appendable.append("Should fail")
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "Cannot append to completed iterator" in str(e)


# ============================================
# CachedAsyncIterator Tests
# ============================================

@test("CachedAsyncIterator caches values from source")
async def _():
    """
    Tests that CachedAsyncIterator caches all values from source.

    Deterministic scenario:
    - Create source generator
    - Wrap in CachedAsyncIterator
    - Iterate and verify values
    """
    async def source():
        yield "A"
        yield "B"
        yield "C"

    cached = CachedAsyncIterator(source())

    values = []
    async for value in cached:
        values.append(value)

    assert values == ["A", "B", "C"]
    assert cached.is_complete


@test("CachedAsyncIterator allows replay for late consumers")
async def _():
    """
    Tests that late consumers get replayed cached values.

    Deterministic scenario:
    - Create cached iterator
    - First consumer iterates fully
    - Second consumer starts late and gets replay
    """
    async def source():
        yield "First"
        await asyncio.sleep(0.05)
        yield "Second"
        await asyncio.sleep(0.05)
        yield "Third"

    cached = CachedAsyncIterator(source())

    # First consumer
    consumer1_values = []
    async for value in cached:
        consumer1_values.append(value)

    # Second consumer (late joiner - should get replay)
    consumer2_values = []
    async for value in cached:
        consumer2_values.append(value)

    assert consumer1_values == ["First", "Second", "Third"]
    assert consumer2_values == ["First", "Second", "Third"]


@test("CachedAsyncIterator supports multiple concurrent consumers")
async def _():
    """
    Tests that multiple consumers can iterate concurrently.

    Deterministic scenario:
    - Create cached iterator
    - Start two consumers concurrently
    - Both should receive all values
    """
    async def source():
        for i in range(5):
            yield f"Value{i}"
            await asyncio.sleep(0.01)

    cached = CachedAsyncIterator(source())

    async def consumer():
        values = []
        async for value in cached:
            values.append(value)
        return values

    # Start two consumers concurrently
    consumer1_task = asyncio.create_task(consumer())
    consumer2_task = asyncio.create_task(consumer())

    values1 = await consumer1_task
    values2 = await consumer2_task

    expected = ["Value0", "Value1", "Value2", "Value3", "Value4"]
    assert values1 == expected
    assert values2 == expected


@test("CachedAsyncIterator await_complete waits for source exhaustion")
async def _():
    """
    Tests that await_complete blocks until source is done.

    Deterministic scenario:
    - Create slow source
    - Call await_complete
    - Should block until source finishes
    """
    async def slow_source():
        yield "A"
        await asyncio.sleep(0.1)
        yield "B"
        await asyncio.sleep(0.1)
        yield "C"

    cached = CachedAsyncIterator(slow_source())

    assert not cached.is_complete

    await cached.await_complete()

    assert cached.is_complete
