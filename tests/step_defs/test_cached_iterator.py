"""
BDD tests for Cached Iterator - Cached async iteration with replay support.

Validates that:
- CachedStringAccumulator maintains backward compatibility with AtomicString
- CachedAsyncIterator caches values and allows replay
- AppendableIterator provides push-based async iteration
- Multiple consumers can iterate with replay
"""
import asyncio
from pytest_bdd import scenarios, given, when, then, parsers
from pytest import fixture
import functools

from liteagent.internal.cached_iterator import (
    CachedStringAccumulator,
    CachedAsyncIterator,
    AppendableIterator
)


def async_to_sync(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


# Load all scenarios from cached_iterator.feature
scenarios('../features/cached_iterator.feature')


# ==================== FIXTURES ====================

@fixture
def iterator_context():
    """Context to store test state."""
    return {}


# ==================== GIVEN STEPS ====================

@given("a CachedStringAccumulator", target_fixture="test_accumulator")
def given_cached_string_accumulator(iterator_context):
    """Create a new CachedStringAccumulator."""
    accumulator = CachedStringAccumulator()
    iterator_context['accumulator'] = accumulator
    return accumulator


@given(parsers.parse('a completed CachedStringAccumulator with value "{value}"'), target_fixture="test_accumulator")
def given_completed_accumulator(iterator_context, value):
    """Create a completed CachedStringAccumulator."""
    async def _create():
        accumulator = CachedStringAccumulator(value)
        await accumulator.complete()
        return accumulator

    accumulator = async_to_sync(_create)()
    iterator_context['accumulator'] = accumulator
    return accumulator


@given("an AppendableIterator", target_fixture="test_appendable")
def given_appendable_iterator(iterator_context):
    """Create a new AppendableIterator."""
    appendable = AppendableIterator[str]()
    iterator_context['appendable'] = appendable
    return appendable


@given("a completed AppendableIterator", target_fixture="test_appendable")
def given_completed_appendable(iterator_context):
    """Create a completed AppendableIterator."""
    async def _create():
        appendable = AppendableIterator[str]()
        await appendable.complete()
        return appendable

    appendable = async_to_sync(_create)()
    iterator_context['appendable'] = appendable
    return appendable


@given(parsers.parse('a CachedAsyncIterator with source yielding "{values}"'), target_fixture="test_cached")
def given_cached_with_source(iterator_context, values):
    """Create a CachedAsyncIterator with simple source."""
    value_list = [v.strip().strip('"') for v in values.split(',')]

    async def source():
        for value in value_list:
            yield value

    cached = CachedAsyncIterator(source())
    iterator_context['cached'] = cached
    iterator_context['expected_values'] = value_list
    return cached


@given("a CachedAsyncIterator with delayed source", target_fixture="test_cached")
def given_cached_with_delayed_source(iterator_context):
    """Create a CachedAsyncIterator with delayed source."""
    async def source():
        yield "First"
        await asyncio.sleep(0.05)
        yield "Second"
        await asyncio.sleep(0.05)
        yield "Third"

    cached = CachedAsyncIterator(source())
    iterator_context['cached'] = cached
    return cached


@given("a CachedAsyncIterator with source yielding 5 values", target_fixture="test_cached")
def given_cached_with_5_values(iterator_context):
    """Create a CachedAsyncIterator yielding 5 values."""
    async def source():
        for i in range(5):
            yield f"Value{i}"
            await asyncio.sleep(0.01)

    cached = CachedAsyncIterator(source())
    iterator_context['cached'] = cached
    return cached


@given("a CachedAsyncIterator with slow source", target_fixture="test_cached")
def given_cached_with_slow_source(iterator_context):
    """Create a CachedAsyncIterator with slow source."""
    async def source():
        yield "A"
        await asyncio.sleep(0.1)
        yield "B"
        await asyncio.sleep(0.1)
        yield "C"

    cached = CachedAsyncIterator(source())
    iterator_context['cached'] = cached
    return cached


# ==================== WHEN STEPS ====================

@when(parsers.parse('I append "{text}"'))
def when_append_text(test_accumulator, text):
    """Append text to accumulator."""
    async def _append():
        await test_accumulator.append(text)
        await asyncio.sleep(0.01)  # Let append task run

    async_to_sync(_append)()


@when("I complete the accumulator")
def when_complete_accumulator(test_accumulator):
    """Complete the accumulator."""
    async def _complete():
        await test_accumulator.complete()
        await test_accumulator.await_complete()

    async_to_sync(_complete)()


@when("I append values with delays and complete in background")
def when_append_with_delays(test_accumulator, iterator_context):
    """Append values with delays in background."""
    async def _append():
        await test_accumulator.append("First")
        await asyncio.sleep(0.05)
        await test_accumulator.append(" Second")
        await asyncio.sleep(0.05)
        await test_accumulator.append(" Third")
        await test_accumulator.complete()

    # Store the coroutine to be executed in await_completion
    iterator_context['background_task'] = _append()


@when("I await completion", target_fixture="completion_result")
def when_await_completion(iterator_context):
    """Await completion of accumulator or cached iterator."""
    async def _await():
        # If there's a background task, start it and await completion
        if 'background_task' in iterator_context:
            task = asyncio.create_task(iterator_context['background_task'])
            result = await iterator_context['accumulator'].await_complete()
            await task
            return result
        elif 'accumulator' in iterator_context:
            return await iterator_context['accumulator'].await_complete()
        elif 'cached' in iterator_context:
            await iterator_context['cached'].await_complete()
            return None

    result = async_to_sync(_await)()
    iterator_context['completion_result'] = result
    return result


@when(parsers.parse('I try to append "{text}"'), target_fixture="error_result")
def when_try_append(iterator_context, text):
    """Try to append to completed iterator."""
    async def _try():
        try:
            if 'accumulator' in iterator_context:
                await iterator_context['accumulator'].append(text)
            elif 'appendable' in iterator_context:
                await iterator_context['appendable'].append(text)
            return None
        except RuntimeError as e:
            return str(e)

    result = async_to_sync(_try)()
    iterator_context['error'] = result
    return result


@when("I append JSON content in parts")
def when_append_json_parts(test_accumulator):
    """Append JSON in parts."""
    async def _append():
        await test_accumulator.append('{"name": "')
        await asyncio.sleep(0.05)
        await test_accumulator.append('John')
        await asyncio.sleep(0.05)
        await test_accumulator.append('", "age": 30}')
        await test_accumulator.complete()

    async_to_sync(_append)()


@when("I parse as JSON", target_fixture="json_result")
def when_parse_json(iterator_context):
    """Parse accumulator content as JSON."""
    async def _parse():
        return await iterator_context['accumulator'].await_as_json()

    result = async_to_sync(_parse)()
    iterator_context['json_result'] = result
    return result


@when(parsers.parse('I append values "{values}" and complete'))
def when_append_values_and_complete(test_appendable, values):
    """Append multiple values and complete."""
    value_list = [v.strip().strip('"') for v in values.split(',')]

    async def _append():
        for value in value_list:
            await test_appendable.append(value)
        await test_appendable.complete()

    async_to_sync(_append)()


@when("I iterate over the values", target_fixture="iterated_values")
def when_iterate_values(iterator_context):
    """Iterate over appendable values."""
    async def _iterate():
        values = []
        async for value in iterator_context['appendable']:
            values.append(value)
        return values

    values = async_to_sync(_iterate)()
    iterator_context['iterated_values'] = values
    return values


@when("I iterate over the cached values", target_fixture="iterated_values")
def when_iterate_cached(iterator_context):
    """Iterate over cached iterator values."""
    async def _iterate():
        values = []
        async for value in iterator_context['cached']:
            values.append(value)
        return values

    values = async_to_sync(_iterate)()
    iterator_context['iterated_values'] = values
    return values


@when("the first consumer iterates fully")
def when_first_consumer_iterates(iterator_context):
    """First consumer iterates fully."""
    async def _iterate():
        values = []
        async for value in iterator_context['cached']:
            values.append(value)
        return values

    values = async_to_sync(_iterate)()
    iterator_context['consumer1_values'] = values


@when("a second consumer starts late", target_fixture="consumer2_values")
def when_second_consumer_starts(iterator_context):
    """Second consumer starts late and gets replay."""
    async def _iterate():
        values = []
        async for value in iterator_context['cached']:
            values.append(value)
        return values

    values = async_to_sync(_iterate)()
    iterator_context['consumer2_values'] = values
    return values


@when("two consumers iterate concurrently")
def when_two_consumers_concurrent(iterator_context):
    """Two consumers iterate concurrently."""
    async def consumer():
        values = []
        async for value in iterator_context['cached']:
            values.append(value)
        return values

    async def _run():
        consumer1_task = asyncio.create_task(consumer())
        consumer2_task = asyncio.create_task(consumer())
        return await consumer1_task, await consumer2_task

    values1, values2 = async_to_sync(_run)()
    iterator_context['consumer1_values'] = values1
    iterator_context['consumer2_values'] = values2


# ==================== THEN STEPS ====================

@then(parsers.parse('the final value should be "{expected}"'))
def then_final_value_is(iterator_context, expected):
    """Validate final value."""
    if 'completion_result' in iterator_context:
        assert iterator_context['completion_result'] == expected
    else:
        async def _get():
            return await iterator_context['accumulator'].get()
        result = async_to_sync(_get)()
        assert result == expected


@then("the accumulator should be complete")
def then_accumulator_complete(iterator_context):
    """Validate accumulator is complete."""
    assert iterator_context['accumulator'].is_complete


@then("the iterator should be complete")
def then_iterator_complete(iterator_context):
    """Validate iterator is complete."""
    assert iterator_context['cached'].is_complete


@then(parsers.parse('it should raise a RuntimeError with message "{message}"'))
def then_raises_runtime_error(iterator_context, message):
    """Validate RuntimeError was raised."""
    assert iterator_context.get('error') is not None
    assert message in iterator_context['error']


@then(parsers.parse('the JSON should have field "{field}" equal to "{value}"'))
def then_json_field_equals_string(iterator_context, field, value):
    """Validate JSON field equals string value."""
    assert iterator_context['json_result'][field] == value


@then(parsers.parse('the JSON should have field "{field}" equal to {value:d}'))
def then_json_field_equals_int(iterator_context, field, value):
    """Validate JSON field equals integer value."""
    assert iterator_context['json_result'][field] == value


@then(parsers.parse('I should receive values in order: "{values}"'))
def then_values_in_order(iterator_context, values):
    """Validate values received in order."""
    expected = [v.strip().strip('"') for v in values.split(',')]
    assert iterator_context['iterated_values'] == expected


@then(parsers.parse('I should receive values: "{values}"'))
def then_values_received(iterator_context, values):
    """Validate values received."""
    expected = [v.strip().strip('"') for v in values.split(',')]
    assert iterator_context['iterated_values'] == expected


@then(parsers.parse('both consumers should receive: "{values}"'))
def then_both_consumers_receive(iterator_context, values):
    """Validate both consumers received same values."""
    expected = [v.strip().strip('"') for v in values.split(',')]
    assert iterator_context['consumer1_values'] == expected
    assert iterator_context['consumer2_values'] == expected


@then("both should receive all 5 values in order")
def then_both_receive_5_values(iterator_context):
    """Validate both consumers received 5 values."""
    expected = ["Value0", "Value1", "Value2", "Value3", "Value4"]
    assert iterator_context['consumer1_values'] == expected
    assert iterator_context['consumer2_values'] == expected
