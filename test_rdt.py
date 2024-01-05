import random
from dataclasses import dataclass
from multiprocessing.pool import ThreadPool
from typing import Any, Tuple, TypeAlias, Union

import pytest

from PA2_receiver import start_receiver
from PA2_sender import start_sender

SERVER_IP = "gaia.cs.umass.edu"
SERVER_PORT = 20008
FILENAME = "declaration.txt"
CHECKSUM_VAL = "18693"
TOTAL_NUMBER_OF_SEGMENTS = 10
NUMBER_OF_RUNS = 10
MAX_NUMBER_OF_THREADS = 4

taken_ids = set()


@dataclass
class ReceiverTestArgs:
    loss_rate: float
    corrupt_rate: float
    max_delay: int


@dataclass
class SenderTestArgs(ReceiverTestArgs):
    transmission_timeout: float


@dataclass
class Statistics:
    checksum_val: str = "00000"
    total_packet_sent: Union[int, float] = 0
    total_packet_recv: Union[int, float] = 0
    total_corrupted_pkt_recv: Union[int, float] = 0
    total_timeout: Union[int, float] = 0


SenderStatistics: TypeAlias = Statistics
ReceiverStatistics: TypeAlias = Statistics


@pytest.mark.parametrize(
    "test_name,sender_arg,receiver_arg",
    [
        (
            "Basic Test with all Zero Params",
            SenderTestArgs(loss_rate=0.0, corrupt_rate=0.0, max_delay=0, transmission_timeout=3.0),
            ReceiverTestArgs(loss_rate=0.0, corrupt_rate=0.0, max_delay=0),
        ),
        (
            "Basic Test with some receiver loss rate",
            SenderTestArgs(loss_rate=0.0, corrupt_rate=0.0, max_delay=0, transmission_timeout=1.0),
            ReceiverTestArgs(loss_rate=0.25, corrupt_rate=0.0, max_delay=0),
        ),
        (
            "Basic Test with some receiver corrupt rate",
            SenderTestArgs(loss_rate=0.0, corrupt_rate=0.0, max_delay=0, transmission_timeout=1.0),
            ReceiverTestArgs(loss_rate=0.0, corrupt_rate=0.25, max_delay=0),
        ),
        (
            "Basic Test with some sender loss rate",
            SenderTestArgs(loss_rate=0.25, corrupt_rate=0.0, max_delay=0, transmission_timeout=1.0),
            ReceiverTestArgs(loss_rate=0.0, corrupt_rate=0.0, max_delay=0),
        ),
        (
            "Basic Test with some sender corrupt rate",
            SenderTestArgs(loss_rate=0.0, corrupt_rate=0.25, max_delay=0, transmission_timeout=1.0),
            ReceiverTestArgs(loss_rate=0.0, corrupt_rate=0.0, max_delay=0),
        ),
    ],
)
def test_all(
    test_name: str,
    sender_arg: SenderTestArgs,
    receiver_arg: ReceiverTestArgs,
) -> None:
    number_of_runs = NUMBER_OF_RUNS

    sum_sender_stats, sum_receiver_stats = run_multiple_runs(NUMBER_OF_RUNS, sender_arg, receiver_arg)

    avg_sender_stats = generate_avg_stats(sum_sender_stats, number_of_runs)
    avg_receiver_stats = generate_avg_stats(sum_receiver_stats, number_of_runs)

    expected_sender_stats = generate_expected_sender_stats(sender_arg)

    # Assert Checksum
    assert avg_sender_stats.checksum_val == expected_sender_stats.checksum_val
    assert avg_receiver_stats.checksum_val == CHECKSUM_VAL

    assert_total_packet_sent(avg_sender_stats, expected_sender_stats, sender_arg, receiver_arg)
    assert_total_packet_recv(avg_sender_stats, expected_sender_stats, sender_arg, receiver_arg)
    assert_total_packet_corrupted(avg_sender_stats, expected_sender_stats, sender_arg, receiver_arg)
    assert_total_timeout(avg_sender_stats, expected_sender_stats, sender_arg, receiver_arg)


def run_multiple_runs(
    number_of_runs: int,
    sender_arg: SenderTestArgs,
    receiver_arg: ReceiverTestArgs,
) -> tuple[Statistics, Statistics]:
    sum_sender_stats, sum_receiver_stats = Statistics(), Statistics()

    def thread_func(_: Any) -> tuple[Statistics, Statistics]:
        connection_id = generate_connection_id()
        this_sender_stats, this_receiver_stats = run_sender_receiver(connection_id, sender_arg, receiver_arg)
        return this_sender_stats, this_receiver_stats

    with ThreadPool(min(number_of_runs, MAX_NUMBER_OF_THREADS)) as thread_pool:
        results = thread_pool.map(thread_func, range(number_of_runs))

    for sender_stats, receiver_stats in results:
        update_sum_stats(sum_sender_stats, update_with=sender_stats)
        update_sum_stats(sum_receiver_stats, update_with=receiver_stats)

    return sum_sender_stats, sum_receiver_stats


def generate_connection_id() -> str:
    while (random_id := str(random.randint(2001, 9999))) in taken_ids:
        pass
    taken_ids.add(random_id)
    return random_id


def run_sender_receiver(
    connection_id: str,
    sender_arg: SenderTestArgs,
    receiver_arg: ReceiverTestArgs,
) -> Tuple[Statistics, Statistics]:
    with ThreadPool(2) as thread_pool:
        # Start the receiver
        receiver_result = thread_pool.starmap_async(
            start_receiver,
            [
                (
                    SERVER_IP,
                    SERVER_PORT,
                    connection_id,
                    str(receiver_arg.loss_rate),
                    str(receiver_arg.corrupt_rate),
                    str(receiver_arg.max_delay),
                )
            ],
        )

        # Start the sender
        sender_result = thread_pool.starmap_async(
            start_sender,
            [
                (
                    SERVER_IP,
                    SERVER_PORT,
                    connection_id,
                    str(sender_arg.loss_rate),
                    str(sender_arg.corrupt_rate),
                    str(sender_arg.max_delay),
                    sender_arg.transmission_timeout,
                    FILENAME,
                ),
            ],
        )

        receiver_stats_actual = Statistics(*receiver_result.get())  # type: ignore
        sender_stats_actual = Statistics(*sender_result.get()[0])

    return sender_stats_actual, receiver_stats_actual


def update_sum_stats(sum_stats: Statistics, update_with: Statistics) -> None:
    assert update_with.checksum_val == CHECKSUM_VAL
    sum_stats.checksum_val = CHECKSUM_VAL
    sum_stats.total_packet_sent += update_with.total_packet_sent
    sum_stats.total_packet_recv += update_with.total_packet_recv
    sum_stats.total_corrupted_pkt_recv += update_with.total_corrupted_pkt_recv
    sum_stats.total_timeout += update_with.total_timeout


def generate_avg_stats(sum_stats: Statistics, number_of_runs: int) -> Statistics:
    return Statistics(
        checksum_val=sum_stats.checksum_val,
        total_packet_sent=sum_stats.total_packet_sent // number_of_runs,
        total_packet_recv=sum_stats.total_packet_recv // number_of_runs,
        total_corrupted_pkt_recv=sum_stats.total_corrupted_pkt_recv // number_of_runs,
        total_timeout=sum_stats.total_timeout // number_of_runs,
    )


def generate_expected_sender_stats(sender_arg: SenderTestArgs) -> Statistics:
    return Statistics(
        checksum_val=CHECKSUM_VAL,
        total_packet_sent=TOTAL_NUMBER_OF_SEGMENTS,
        total_packet_recv=TOTAL_NUMBER_OF_SEGMENTS,
        total_corrupted_pkt_recv=-100,
        total_timeout=TOTAL_NUMBER_OF_SEGMENTS * sender_arg.loss_rate,
    )


def assert_total_packet_sent(
    avg_sender_stats: Statistics,
    expected_sender_stats: Statistics,
    sender_arg: SenderTestArgs,
    receiver_arg: ReceiverTestArgs,
) -> None:
    expected_total_packets_sent = (
        expected_sender_stats.total_packet_sent
        + receiver_arg.corrupt_rate * expected_sender_stats.total_packet_sent
        + receiver_arg.loss_rate * expected_sender_stats.total_packet_sent
        + sender_arg.loss_rate * expected_sender_stats.total_packet_sent
        + sender_arg.corrupt_rate * expected_sender_stats.total_packet_sent
    )
    if sender_arg.transmission_timeout < sender_arg.max_delay:
        assert False, "Not supported"

    assert_value_in_range(expected_total_packets_sent, avg_sender_stats.total_packet_sent, 0.20, "sent")


def assert_total_packet_recv(
    avg_sender_stats: Statistics,
    expected_sender_stats: Statistics,
    sender_arg: SenderTestArgs,
    receiver_arg: ReceiverTestArgs,
) -> None:
    expected_total_packets_recv = expected_sender_stats.total_packet_sent
    expected_total_packets_recv += (
        avg_sender_stats.total_packet_sent - expected_sender_stats.total_packet_sent
    ) * (receiver_arg.loss_rate)
    expected_total_packets_recv += expected_sender_stats.total_packet_sent * (sender_arg.corrupt_rate)
    expected_total_packets_recv += avg_sender_stats.total_corrupted_pkt_recv

    if sender_arg.transmission_timeout < sender_arg.max_delay:
        assert False, "Not supported"

    assert_value_in_range(expected_total_packets_recv, avg_sender_stats.total_packet_recv, 0.20, "received")


def assert_total_packet_corrupted(
    avg_sender_stats: Statistics,
    expected_sender_stats: Statistics,
    sender_arg: SenderTestArgs,
    receiver_arg: ReceiverTestArgs,
) -> None:
    expected_total_packets_corrupted = avg_sender_stats.total_packet_sent * receiver_arg.corrupt_rate

    if sender_arg.transmission_timeout < sender_arg.max_delay:
        assert False, "Not supported"

    assert_value_in_range(
        expected_total_packets_corrupted,
        avg_sender_stats.total_corrupted_pkt_recv,
        0.50,
        "corrupted",
    )


def assert_total_timeout(
    avg_sender_stats: Statistics,
    expected_sender_stats: Statistics,
    sender_arg: SenderTestArgs,
    receiver_arg: ReceiverTestArgs,
) -> None:
    expected_timeouts = avg_sender_stats.total_packet_sent - expected_sender_stats.total_packet_sent

    if sender_arg.transmission_timeout < sender_arg.max_delay:
        assert False, "Not supported"

    assert_value_in_range(expected_timeouts, avg_sender_stats.total_timeout, 0.0, "timeouts")


def assert_value_in_range(expected: float, actual: float, error_rate: float, message: str) -> None:
    if actual == 0 and expected != 0:
        assert False, f"Expected({expected}) ~ Actual({actual}) for packets {message}"
    if actual == 0 and expected == 0:
        return
    if abs((expected - actual) / float(actual)) > error_rate:
        assert False, f"Expected({expected}) ~ Actual({actual}) for packets {message}"