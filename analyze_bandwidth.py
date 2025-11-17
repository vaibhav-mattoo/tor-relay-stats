#!/usr/bin/env python3
"""
Analyze Tor relay bandwidth data to identify diurnal and day-of-week patterns
Creates matplotlib plots showing average bandwidth by hour of day
"""

import argparse
import os
from datetime import datetime, timezone
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np


def extract_measurements_from_file(filepath):
    """
    Yield individual relay measurements from a bandwidth file.

    The authoritative timestamp for each measurement is contained in the
    trailing ``time=`` field on each relay line, so we parse that value per
    relay instead of assuming a single timestamp for the entire file.
    """
    in_header = True

    with open(filepath, "r", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line:
                continue

            if in_header:
                if line.startswith("===="):
                    in_header = False
                continue

            # Only process relay measurement lines that contain both node_id and time.
            if "node_id=" not in line or "time=" not in line:
                continue

            fields = {}
            for token in line.split():
                if "=" not in token:
                    continue
                key, value = token.split("=", 1)
                fields[key] = value

            node_id = fields.get("node_id")
            if not node_id:
                continue
            node_id = node_id.lstrip("$").upper()

            bandwidth = None
            for key in ("bw_mean", "bw"):
                if key in fields:
                    try:
                        bandwidth = int(fields[key])
                    except ValueError:
                        bandwidth = None
                    if bandwidth is not None:
                        break

            time_str = fields.get("time")
            if bandwidth is None or not time_str:
                continue

            try:
                measurement_time = datetime.strptime(
                    time_str, "%Y-%m-%dT%H:%M:%S"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            yield {
                "relay_id": node_id,
                "bandwidth": bandwidth,
                "datetime": measurement_time,
            }


def aggregate_bandwidth_by_hour(measurements, relay_id=None):
    """
    Aggregate bandwidth measurements by hour of day

    If relay_id is specified, only aggregate that relay's measurements
    Otherwise, aggregate total network bandwidth

    Returns:
    - hourly_avg: dict mapping hour (0-23) to average bandwidth
    - hourly_count: dict mapping hour to number of measurements
    """
    hourly_data = defaultdict(list)

    for measurement in measurements:
        if measurement["datetime"] is None:
            continue

        hour = measurement["datetime"].hour

        if relay_id:
            # Single relay analysis
            if relay_id in measurement["relays"]:
                bw = measurement["relays"][relay_id]
                hourly_data[hour].append(bw)
        else:
            # Total network bandwidth
            total_bw = sum(measurement["relays"].values())
            hourly_data[hour].append(total_bw)

    # Calculate averages
    hourly_avg = {}
    hourly_count = {}

    for hour in range(24):
        if hour in hourly_data and hourly_data[hour]:
            hourly_avg[hour] = np.mean(hourly_data[hour])
            hourly_count[hour] = len(hourly_data[hour])
        else:
            hourly_avg[hour] = 0
            hourly_count[hour] = 0

    return hourly_avg, hourly_count


def aggregate_bandwidth_by_day_of_week(measurements, relay_id=None):
    """
    Aggregate bandwidth by day of week

    Returns:
    - daily_avg: dict mapping day (0=Monday, 6=Sunday) to average bandwidth
    - daily_count: dict mapping day to number of measurements
    """
    daily_data = defaultdict(list)

    for measurement in measurements:
        if measurement["datetime"] is None:
            continue

        day = measurement["datetime"].weekday()  # 0=Monday, 6=Sunday

        if relay_id:
            if relay_id in measurement["relays"]:
                bw = measurement["relays"][relay_id]
                daily_data[day].append(bw)
        else:
            total_bw = sum(measurement["relays"].values())
            daily_data[day].append(total_bw)

    # Calculate averages
    daily_avg = {}
    daily_count = {}

    for day in range(7):
        if day in daily_data and daily_data[day]:
            daily_avg[day] = np.mean(daily_data[day])
            daily_count[day] = len(daily_data[day])
        else:
            daily_avg[day] = 0
            daily_count[day] = 0

    return daily_avg, daily_count


def process_measurement_incremental(
    measurement_time, bandwidth, hourly_sums, hourly_counts, daily_sums, daily_counts
):
    """
    Process a single measurement incrementally, updating aggregation dictionaries in place.
    This avoids storing all measurements in memory.
    
    Args:
        measurement_time: datetime object representing when the measurement was taken
        bandwidth: numeric bandwidth value (KB/s)
        hourly_sums: dict mapping hour to running sum (modified in place)
        hourly_counts: dict mapping hour to count (modified in place)
        daily_sums: dict mapping day to running sum (modified in place)
        daily_counts: dict mapping day to count (modified in place)
    """
    if measurement_time is None or bandwidth is None:
        return
    
    hour = measurement_time.hour
    day = measurement_time.weekday()

    hourly_sums[hour] += bandwidth
    hourly_counts[hour] += 1
    daily_sums[day] += bandwidth
    daily_counts[day] += 1


def process_files_incremental(bandwidth_dir, start_date=None, end_date=None, relay_id=None):
    """
    Process bandwidth files incrementally, aggregating as we go to avoid loading
    all data into memory at once.
    
    Returns:
    - hourly_avg: dict mapping hour (0-23) to average bandwidth
    - hourly_count: dict mapping hour to number of measurements
    - daily_avg: dict mapping day (0=Monday, 6=Sunday) to average bandwidth
    - daily_count: dict mapping day to number of measurements
    - total_measurements: total number of measurements processed
    - date_range: tuple of (first_date, last_date) or None
    """
    hourly_sums = defaultdict(float)
    hourly_counts = defaultdict(int)
    daily_sums = defaultdict(float)
    daily_counts = defaultdict(int)
    
    total_measurements = 0
    first_date = None
    last_date = None
    
    # Collect all file paths first (this is lightweight)
    file_paths = []
    for root, dirs, files in os.walk(bandwidth_dir):
        for filename in files:
            if filename.startswith(".") or "index" in filename.lower():
                continue
            file_paths.append(os.path.join(root, filename))
    
    # Sort files by path (which should roughly correspond to timestamp order)
    file_paths.sort()
    
    print(f"Processing {len(file_paths)} files...")
    
    stop_processing = False

    # Process each file one measurement at a time
    for filepath in file_paths:
        if stop_processing:
            break
        try:
            for measurement in extract_measurements_from_file(filepath):
                measurement_time = measurement["datetime"]

                if start_date and measurement_time < start_date:
                    continue
                if end_date and measurement_time >= end_date:
                    stop_processing = True
                    break
                if relay_id and measurement["relay_id"] != relay_id:
                    continue

                # Update date range tracking
                if first_date is None or measurement_time < first_date:
                    first_date = measurement_time
                if last_date is None or measurement_time > last_date:
                    last_date = measurement_time

                # Process incrementally
                process_measurement_incremental(
                    measurement_time,
                    measurement["bandwidth"],
                    hourly_sums,
                    hourly_counts,
                    daily_sums,
                    daily_counts,
                )
                total_measurements += 1

                # Progress indicator every 10k measurements to avoid excessive logging
                if total_measurements % 10000 == 0:
                    print(
                        f"  Processed {total_measurements} measurements...",
                        flush=True,
                    )

        except Exception:
            # Skip files that can't be parsed
            continue
    
    # Calculate averages from sums and counts
    hourly_avg = {}
    hourly_count = {}
    for hour in range(24):
        if hourly_counts[hour] > 0:
            hourly_avg[hour] = hourly_sums[hour] / hourly_counts[hour]
            hourly_count[hour] = hourly_counts[hour]
        else:
            hourly_avg[hour] = 0
            hourly_count[hour] = 0
    
    daily_avg = {}
    daily_count = {}
    for day in range(7):
        if daily_counts[day] > 0:
            daily_avg[day] = daily_sums[day] / daily_counts[day]
            daily_count[day] = daily_counts[day]
        else:
            daily_avg[day] = 0
            daily_count[day] = 0
    
    date_range = (first_date, last_date) if first_date and last_date else None
    
    return hourly_avg, hourly_count, daily_avg, daily_count, total_measurements, date_range


def parse_date_arg(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ValueError(f"Invalid date '{value}'. Please use YYYY-MM-DD format.")


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Analyze Tor relay bandwidth data for relays or the full network."
    )
    parser.add_argument(
        "bandwidth_dir",
        help="Directory containing extracted bandwidth measurement files.",
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--network",
        action="store_true",
        help="Analyze overall network bandwidth patterns.",
    )
    mode_group.add_argument(
        "--relay",
        metavar="FINGERPRINT",
        help="Analyze a specific relay fingerprint (40-character hex).",
    )
    parser.add_argument(
        "--start-date",
        metavar="YYYY-MM-DD",
        help="Start date (UTC). Defaults to 2024-01-01 if omitted.",
    )
    parser.add_argument(
        "--end-date",
        metavar="YYYY-MM-DD",
        help="End date (UTC, exclusive). Defaults to 2025-01-01 if omitted.",
    )
    parser.add_argument(
        "--output-prefix",
        help="Filename prefix for generated plots (default: network or relay_<fingerprint>).",
    )
    return parser


def plot_hourly_bandwidth(hourly_avg, relay_id=None, output_file=None):
    """
    Create a matplotlib plot of average bandwidth by hour of day
    """
    hours = sorted(hourly_avg.keys())
    bandwidths = [hourly_avg[h] for h in hours]

    plt.figure(figsize=(12, 6))
    plt.plot(hours, bandwidths, marker="o", linewidth=2, markersize=8)
    plt.xlabel("Hour of Day (UTC)", fontsize=12)
    plt.ylabel("Average Bandwidth (KB/s)", fontsize=12)

    if relay_id:
        plt.title(f"Average Bandwidth by Hour for Relay {relay_id[:8]}...", fontsize=14)
    else:
        plt.title("Average Total Network Bandwidth by Hour (UTC)", fontsize=14)

    plt.grid(True, alpha=0.3)
    plt.xticks(range(0, 24, 2))
    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Saved plot to {output_file}")
    else:
        plt.show()

    plt.close()


def plot_daily_bandwidth(daily_avg, relay_id=None, output_file=None):
    """
    Create a matplotlib plot of average bandwidth by day of week
    """
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    day_indices = sorted(daily_avg.keys())
    bandwidths = [daily_avg[d] for d in day_indices]

    plt.figure(figsize=(10, 6))
    plt.bar(range(7), bandwidths, color="steelblue", alpha=0.7)
    plt.xlabel("Day of Week", fontsize=12)
    plt.ylabel("Average Bandwidth (KB/s)", fontsize=12)

    if relay_id:
        plt.title(
            f"Average Bandwidth by Day of Week for Relay {relay_id[:8]}...", fontsize=14
        )
    else:
        plt.title("Average Total Network Bandwidth by Day of Week", fontsize=14)

    plt.xticks(range(7), days, rotation=45)
    plt.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Saved plot to {output_file}")
    else:
        plt.show()

    plt.close()


def analyze_relay(
    relay_id, bandwidth_dir, start_date=None, end_date=None, output_prefix=None
):
    """
    Main function to analyze a specific relay's bandwidth patterns using incremental processing

    Args:
        relay_id: Relay fingerprint (40-character hex string)
        bandwidth_dir: Directory containing extracted bandwidth files
        start_date: datetime object for start date (optional)
        end_date: datetime object for end date (optional)
        output_prefix: Prefix for output plot filenames
    """
    print(f"\nAnalyzing relay: {relay_id}")
    print(f"Processing measurements from {bandwidth_dir}...")

    # Process files incrementally
    hourly_avg, hourly_count, daily_avg, daily_count, total_measurements, date_range = process_files_incremental(
        bandwidth_dir, start_date, end_date, relay_id=relay_id
    )

    if total_measurements == 0:
        print("No measurements found!")
        return

    print(f"\nProcessed {total_measurements} measurements")
    if date_range:
        print(f"Date range: {date_range[0]} to {date_range[1]}")

    # Check if relay was found (if any hourly/daily counts are non-zero)
    relay_found = any(hourly_count[h] > 0 for h in range(24)) or any(daily_count[d] > 0 for d in range(7))

    if not relay_found:
        print(f"WARNING: Relay {relay_id} not found in any measurements!")
        print("This relay may not have been active during the specified period.")
        return

    print("\nAverage bandwidth by hour (UTC):")
    for hour in range(24):
        if hourly_count[hour] > 0:
            print(
                f"  {hour:02d}:00 - {hourly_avg[hour]:10.2f} KB/s ({hourly_count[hour]} measurements)"
            )

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    print("\nAverage bandwidth by day of week:")
    for day in range(7):
        if daily_count[day] > 0:
            print(
                f"  {days[day]:9s} - {daily_avg[day]:10.2f} KB/s ({daily_count[day]} measurements)"
            )

    # Create plots
    if output_prefix:
        hourly_file = f"{output_prefix}_hourly.png"
        daily_file = f"{output_prefix}_daily.png"
    else:
        hourly_file = f"relay_{relay_id[:8]}_hourly.png"
        daily_file = f"relay_{relay_id[:8]}_daily.png"

    print("\nGenerating plots...")
    plot_hourly_bandwidth(hourly_avg, relay_id, hourly_file)
    plot_daily_bandwidth(daily_avg, relay_id, daily_file)

    print(f"\nAnalysis complete for relay {relay_id}")


def analyze_network(
    bandwidth_dir, start_date=None, end_date=None, output_prefix="network"
):
    """
    Analyze overall network bandwidth patterns using incremental processing
    to avoid loading all data into memory at once.
    """
    print("\nAnalyzing overall network bandwidth...")
    print(f"Processing measurements from {bandwidth_dir}...")

    # Process files incrementally
    hourly_avg, hourly_count, daily_avg, daily_count, total_measurements, date_range = process_files_incremental(
        bandwidth_dir, start_date, end_date, relay_id=None
    )

    if total_measurements == 0:
        print("No measurements found!")
        return

    print(f"\nProcessed {total_measurements} measurements")
    if date_range:
        print(f"Date range: {date_range[0]} to {date_range[1]}")

    print("\nAverage total network bandwidth by hour (UTC):")
    for hour in range(24):
        if hourly_count[hour] > 0:
            bw_gbps = hourly_avg[hour] / 1_000_000  # Convert KB/s to GB/s
            print(
                f"  {hour:02d}:00 - {bw_gbps:8.3f} GB/s ({hourly_count[hour]} measurements)"
            )

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    print("\nAverage total network bandwidth by day of week:")
    for day in range(7):
        if daily_count[day] > 0:
            bw_gbps = daily_avg[day] / 1_000_000
            print(
                f"  {days[day]:9s} - {bw_gbps:8.3f} GB/s ({daily_count[day]} measurements)"
            )

    # Create plots
    hourly_file = f"{output_prefix}_hourly.png"
    daily_file = f"{output_prefix}_daily.png"

    print("\nGenerating plots...")
    plot_hourly_bandwidth(hourly_avg, None, hourly_file)
    plot_daily_bandwidth(daily_avg, None, daily_file)

    print("\nNetwork analysis complete")


if __name__ == "__main__":
    parser = build_arg_parser()
    args = parser.parse_args()

    default_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    default_end = datetime(2025, 1, 1, tzinfo=timezone.utc)

    try:
        start_date = parse_date_arg(args.start_date, default_start)
        end_date = parse_date_arg(args.end_date, default_end)
    except ValueError as exc:
        parser.error(str(exc))

    if end_date <= start_date:
        parser.error("--end-date must be later than --start-date")

    if args.network:
        output_prefix = args.output_prefix or "network"
        analyze_network(args.bandwidth_dir, start_date, end_date, output_prefix)
    else:
        relay_id = args.relay.upper()
        if len(relay_id) != 40 or any(c not in "0123456789ABCDEF" for c in relay_id):
            parser.error("Relay fingerprint must be a 40-character hexadecimal string.")
        output_prefix = args.output_prefix or f"relay_{relay_id[:8]}"
        analyze_relay(relay_id, args.bandwidth_dir, start_date, end_date, output_prefix)
