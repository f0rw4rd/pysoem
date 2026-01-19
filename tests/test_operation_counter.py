"""Unit tests for _OperationCounter class."""

import pytest
import threading
import time
from pysoem.pysoem import OperationCounter


def test_initial_state():
    """Test that counter starts at zero with event set."""
    counter = OperationCounter()
    # Should be able to wait immediately since count is 0
    assert counter.wait_for_zero(timeout=0.001)


def test_increment_decrement():
    """Test basic increment and decrement operations."""
    counter = OperationCounter()
    
    counter.increment()
    # Should not be at zero anymore
    assert not counter.wait_for_zero(timeout=0.001)
    
    counter.decrement()
    # Should be back at zero
    assert counter.wait_for_zero(timeout=0.001)


def test_multiple_increments():
    """Test multiple increments before decrements."""
    counter = OperationCounter()
    
    counter.increment()
    counter.increment()
    counter.increment()
    
    # Still not at zero
    assert not counter.wait_for_zero(timeout=0.001)
    
    counter.decrement()
    assert not counter.wait_for_zero(timeout=0.001)
    
    counter.decrement()
    assert not counter.wait_for_zero(timeout=0.001)
    
    counter.decrement()
    # Now at zero
    assert counter.wait_for_zero(timeout=0.001)


def test_reset():
    """Test reset operation."""
    counter = OperationCounter()
    
    counter.increment()
    counter.increment()
    counter.increment()
    
    # Not at zero
    assert not counter.wait_for_zero(timeout=0.001)
    
    counter.reset()
    # Reset should set to zero
    assert counter.wait_for_zero(timeout=0.001)


def test_threaded_increment_decrement():
    """Test thread safety of increment and decrement."""
    counter = OperationCounter()
    num_threads = 10
    iterations = 100
    
    def worker():
        for _ in range(iterations):
            counter.increment()
            time.sleep(0.0001)  # Small delay to encourage interleaving
            counter.decrement()
    
    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    # After all operations, should be back at zero
    assert counter.wait_for_zero(timeout=1.0)


def test_wait_for_zero_blocks():
    """Test that wait_for_zero blocks until count reaches zero."""
    counter = OperationCounter()
    counter.increment()
    
    result = []
    
    def waiter():
        # This should block until decrement is called
        success = counter.wait_for_zero(timeout=2.0)
        result.append(success)
    
    def decrementer():
        time.sleep(0.1)  # Wait a bit before decrementing
        counter.decrement()
    
    wait_thread = threading.Thread(target=waiter)
    dec_thread = threading.Thread(target=decrementer)
    
    start = time.time()
    wait_thread.start()
    dec_thread.start()
    
    wait_thread.join()
    dec_thread.join()
    elapsed = time.time() - start
    
    # Should have waited at least 0.1 seconds
    assert elapsed >= 0.1
    # Should have succeeded
    assert result[0] is True


def test_wait_for_zero_timeout():
    """Test that wait_for_zero times out correctly."""
    counter = OperationCounter()
    counter.increment()
    
    start = time.time()
    result = counter.wait_for_zero(timeout=0.1)
    elapsed = time.time() - start
    
    # Should have timed out
    assert result is False
    # Should have waited approximately the timeout duration
    assert 0.09 < elapsed < 0.2


def test_concurrent_operations():
    """Test concurrent increments and decrements."""
    counter = OperationCounter()
    num_threads = 20
    operations_per_thread = 50
    
    barrier = threading.Barrier(num_threads)
    
    def worker():
        # Synchronize start to maximize contention
        barrier.wait()
        for _ in range(operations_per_thread):
            counter.increment()
            counter.decrement()
    
    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    # Should be at zero after all operations
    assert counter.wait_for_zero(timeout=1.0)


def test_event_cleared_on_first_increment():
    """Test that event is cleared only on first increment from zero."""
    counter = OperationCounter()
    
    # Initially at zero, event should be set
    assert counter.wait_for_zero(timeout=0.001)
    
    # First increment should clear the event
    counter.increment()
    assert not counter.wait_for_zero(timeout=0.001)
    
    # Subsequent increments should keep it cleared
    counter.increment()
    assert not counter.wait_for_zero(timeout=0.001)
    
    # Decrement but not to zero
    counter.decrement()
    assert not counter.wait_for_zero(timeout=0.001)
    
    # Final decrement to zero should set the event
    counter.decrement()
    assert counter.wait_for_zero(timeout=0.001)


def test_multiple_waiters():
    """Test that multiple threads can wait for zero."""
    counter = OperationCounter()
    counter.increment()
    
    results = []
    
    def waiter(index):
        success = counter.wait_for_zero(timeout=2.0)
        results.append((index, success))
    
    # Create multiple waiters
    num_waiters = 5
    waiters = [threading.Thread(target=waiter, args=(i,)) for i in range(num_waiters)]
    
    for t in waiters:
        t.start()
    
    # Wait a bit to ensure all waiters are blocked
    time.sleep(0.05)
    
    # Decrement to zero - should wake all waiters
    counter.decrement()
    
    for t in waiters:
        t.join()
    
    # All waiters should have succeeded
    assert len(results) == num_waiters
    assert all(success for _, success in results)
