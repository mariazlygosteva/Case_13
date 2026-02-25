"""
Module for generating simulation report of a gas station.
"""

import random
from typing import Dict, List, Tuple, Any, Union

# Localisation
import ru_local as local

# Functions for time processing
from time_processing import standart_format_time
from arrivals_processing import ARRIVAL_TIME_KEY


def calculating_results(
    gas_prices: Dict[str, float],
    arrivals_served: List[Dict[str, Any]]
) -> Tuple[Dict[str, float], float]:
    """
    Calculate daily fuel volumes sold and total income
    based on served refueling requests and current fuel prices.

    Args:
        gas_prices: Dictionary with fuel types as keys and their prices as values.
        arrivals_served: List of dictionaries containing served arrivals.
                         Each dict must have keys:
                         - local.TYPE (str): fuel type
                         - local.VOLUME (str/int): amount of fuel refueled (liters)

    Returns:
        Tuple containing:
            - volumes_day: Dictionary with fuel types and total liters sold.
            - income: Total daily income from all refueling operations.
    """
    # Dictionary to accumulate daily volumes for each fuel type
    volumes_day: Dict[str, float] = {fuel: 0.0 for fuel in gas_prices}

    income = 0.0

    for arrival in arrivals_served:
        fuel_type = arrival[local.TYPE]
        fuel_volume = int(arrival[local.VOLUME])

        # If the required fuel is available at the station, process the refueling.
        if fuel_type in volumes_day:
            volumes_day[fuel_type] += fuel_volume
            income += fuel_volume * gas_prices[fuel_type]

    return volumes_day, income


def create_output_text(
    general_list: List[Dict[str, Any]],
    arrivals_all: List,
    volumes_day: Dict[str, float],
    income: float,
    left_count: int,
    stations: Dict[int, Tuple[int, List[str]]]
) -> str:
    """
    Generate a complete simulation report including events, totals, and analysis.

    The report contains step‑by‑step events, queue states, daily totals,
    extended statistics (by fuel type and dispenser), and economic analysis.

    Args:
        general_list: List of event dictionaries. Each event contains keys:
            - local.TIME (float): event time in minutes from midnight.
            - local.ARRIVAL (bool): True for arrival, False for departure.
            - local.TYPE (str): fuel type.
            - local.VOLUME (int): refuel volume in liters.
            - local.REFILL_DURATION (float): duration of refueling in minutes.
            - local.MACHINE (int, optional): dispenser number.
            - local.LEAVE (bool, optional): True for arrivals that leave immediately.
            - ARRIVAL_TIME_KEY (float, optional): original arrival time for departures.
        arrivals_all: List of all arrival events (used for total count).
        volumes_day: Dictionary with fuel types and total liters sold.
        income: Total daily income.
        left_count: Number of customers who left because the queue was too long.
        stations: Dispenser configuration.
                  Keys are dispenser numbers, values are tuples:
                  (max_queue_allowed, [list of fuel types dispensed]).

    Returns:
        Formatted string containing the complete simulation report.
    """
    lines = []

    # Queues at the time of event processing (for display)
    queues: Dict[int, List[float]] = {station: [] for station in stations}

    # Statistics by fuel type
    fuel_stats: Dict[str, Dict[str, Union[int, float]]] = {
        fuel: {'served': 0, 'volume': 0.0, 'refused': 0}
        for fuel in volumes_day.keys()
    }

    # Statistics by dispenser
    station_stats: Dict[int, Dict[str, Union[int, float, List[float]]]] = {
        station: {
            'served': 0,
            'volume': 0.0,
            'total_wait': 0,
            'total_duration': 0,
            'max_queue': 0,
            'wait_list': []
        }
        for station in stations
    }

    # Overall waiting indicators
    total_wait_all = 0.0
    total_served_all = 0
    max_wait_all = 0.0

    for e in general_list:
        event_time = e[local.TIME]
        event_time_str = standart_format_time(event_time)

        fuel = e[local.TYPE]
        liters = e[local.VOLUME]
        duration = e[local.REFILL_DURATION]
        station = e.get(local.MACHINE)

        if e[local.ARRIVAL]:                     # Arrival event
            if e.get(local.LEAVE) is True:       # Customer left without joining queue
                lines.append(
                    f"{local.IN} {event_time_str} {local.NEW_CLIENT}"
                    f"{event_time_str} {fuel} {int(liters)} {duration} "
                    f"{local.COULD_NOT}"
                )
                if fuel in fuel_stats:
                    fuel_stats[fuel]['refused'] += 1
            else:                                 # Customer joined a queue
                lines.append(
                    f"{local.IN} {event_time_str} {local.NEW_CLIENT}"
                    f"{event_time_str} {fuel} {int(liters)} {duration} "
                    f"{local.QUEUE} {station}"
                )
                queues[station].append(duration)
                current_q = len(queues[station])
                if current_q > station_stats[station]['max_queue']:
                    station_stats[station]['max_queue'] = current_q

        else:                                     # Departure event
            arrival_time = e.get(ARRIVAL_TIME_KEY)
            if arrival_time is None:
                arrival_time = event_time - duration
            arrival_time_str = standart_format_time(arrival_time)

            lines.append(
                f"{local.IN} {event_time_str} {local.CLIENT}"
                f"{arrival_time_str} {fuel} {int(liters)} {duration} "
                f"{local.REFUELED}"
            )

            start_time = event_time - duration
            wait = start_time - arrival_time      # Waiting time in queue

            if station is not None:
                st = station_stats[station]
                st['served'] += 1
                st['volume'] += liters
                st['total_duration'] += duration
                st['total_wait'] += wait
                st['wait_list'].append(wait)

                total_served_all += 1
                total_wait_all += wait
                if wait > max_wait_all:
                    max_wait_all = wait

                if fuel in fuel_stats:
                    fuel_stats[fuel]['served'] += 1
                    fuel_stats[fuel]['volume'] += liters

            # Remove customer from queue
            if queues[station]:
                queues[station].pop(0)

        # Display queue status after each event
        for sid in sorted(stations.keys()):
            max_q = stations[sid][0]
            fuels = " ".join(stations[sid][1])
            stars = "*" * len(queues[sid])
            lines.append(
                f"{local.AUTOMATIC_CONTROL_NUMBER} {sid} "
                f"{local.MAX} {max_q} "
                f"{local.STAMP_GASOLINE} {fuels} ->{stars}"
            )
        lines.append("")

    # Daily totals (mandatory part)
    lines.append("")
    lines.append(local.RESULT)
    for fuel in volumes_day:
        lines.append(f"{fuel}: {volumes_day[fuel]} {local.LITERS}")
    lines.append(f"{local.COME} {len(arrivals_all)}")
    lines.append(f"{local.AWAY} {left_count}")
    lines.append(f"{local.INCOME} {int(income)} {local.RUBLES}")

    # Additional statistics
    lines.append("")
    lines.append(local.ADDITIONAL_STATISTICS)
    lines.append(local.STAMP)
    for fuel in sorted(fuel_stats.keys()):
        s = fuel_stats[fuel]
        lines.append(
            f"  {fuel}: {local.SERVICED_1} {s['served']}, "
            f"{local.AMOUNT} {s['volume']:.1f} {local.LITERS}, "
            f"{local.REJECTION} {s['refused']}"
        )

    lines.append("")
    lines.append(local.MACHINES)
    for sid in sorted(stations.keys()):
        st = station_stats[sid]
        avg_wait = st['total_wait'] / st['served'] if st['served'] > 0 else 0.0
        load_percent = (st['total_duration'] / (24 * 60)) * 100.0
        lines.append(f"  {local.AUTOMATIC_CONTROL_NUMBER}{sid}:")
        lines.append(f"    {local.SERVICED_2} {st['served']}")
        lines.append(f"    {local.MARKET_LITERS} {st['volume']:.1f}")
        lines.append(f"    {local.AVERAGE_TIME} {avg_wait:.1f} {local.MINUTES}")
        lines.append(f"    {local.MAX_LINE} {st['max_queue']}")
        lines.append(f"    {local.LOADING} {load_percent:.1f}%")

    lines.append("")
    if total_served_all > 0:
        avg_wait_all = total_wait_all / total_served_all
        lines.append(f"{local.GENERAL_AVERAGE} {avg_wait_all:.1f} {local.MINUTES}")
        lines.append(f"{local.MAX_TIME} {max_wait_all:.0f} {local.MINUTES}")
    lines.append(
        f"{local.PERCENT} {left_count / len(arrivals_all) * 100.0:.1f}% "
        f"({left_count} {local.FROM} {len(arrivals_all)})"
    )

    # Economic analysis
    lines.append("")
    lines.append(local.ECONOMIC_ANALYSIS)
    expenses_permanent = (
        random.randint(150000, 180000)
        + int(income * 30 * 0.06)
        + random.randint(50000, 80000)
        + random.randint(20000, 30000)
    )
    expenses_variables = (income * 0.8 + income * 0.018) * 30.0
    expenses_month = expenses_permanent + expenses_variables
    income_month = income * 30.0

    lines.append(f"{local.QUOTED_CONSUMMENTS} {expenses_month // 30:.0f} {local.RUBLES}")
    lines.append(f"{local.AVERAGE_PASSAGE} {int(income_month)} {local.RUBLES}")
    lines.append(f"{local.AVERAGE_COSTS} {int(expenses_month)} {local.RUBLES}")
    lines.append(
        f"{local.PAYBACK_TIME}"
        f"{round(10000000 / (income_month - expenses_month), 1)} {local.YEAR}"
    )

    return "\n".join(lines)
