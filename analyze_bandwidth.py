#!/usr/bin/env python3
"""
Analyze Tor relay bandwidth data to identify diurnal and day-of-week patterns
Creates matplotlib plots showing average bandwidth by hour of day
"""

import os
import re
from datetime import datetime, timezone
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np


def parse_bandwidth_file_v2(filepath):
    """
    Parse bandwidth file according to bandwidth-file-spec format

    Bandwidth file format:
    - First line: Unix timestamp (seconds since epoch)
    - Header lines: key=value pairs
    - Separator line: =====
    - Relay lines: node_id=<fingerprint> bw=<bandwidth_kb_s> ...
    """
    with open(filepath, "r", errors="ignore") as f:
        lines = f.readlines()

    timestamp = None
    relay_data = {}
    in_header = True

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # First line is timestamp
        if timestamp is None and line.isdigit():
            timestamp = int(line)
            continue

        # Separator marks end of header
        if line.startswith("===="):
            in_header = False
            continue

        # Skip header lines
        if in_header:
            continue

        # Parse relay measurement lines
        # Format: node_id=$<fingerprint> bw_mean=<kb/s> [other_params]
        if "node_id=" in line and "bw=" in line:
            node_id = None
            bandwidth = None

            # Extract node_id and bw using regex
            node_match = re.search(r"node_id=\$?([A-Fa-f0-9]{40})", line)
            # Prefer measured mean bandwidth if present, fall back to bw
            bw_mean_match = re.search(r"\bbw_mean=(\d+)", line)
            bw_match = re.search(r"\bbw=(\d+)", line)

            if node_match:
                node_id = node_match.group(1).upper()
            if bw_mean_match:
                bandwidth = int(bw_mean_match.group(1))
            elif bw_match:
                bandwidth = int(bw_match.group(1))

            if node_id and bandwidth is not None:
                relay_data[node_id] = bandwidth

    return {
        "timestamp": timestamp,
        "datetime": datetime.fromtimestamp(timestamp, tz=timezone.utc)
        if timestamp
        else None,
        "relays": relay_data,
    }


def collect_bandwidth_measurements(bandwidth_dir, start_date=None, end_date=None):
    """
    Collect all bandwidth measurements from a directory

    Returns:
    - List of dicts with timestamp, datetime, and relay measurements
    """
    measurements = []

    # Walk through all subdirectories to find bandwidth files
    for root, dirs, files in os.walk(bandwidth_dir):
        for filename in files:
            filepath = os.path.join(root, filename)

            # Skip non-bandwidth files (like index files)
            if filename.startswith(".") or "index" in filename.lower():
                continue

            try:
                data = parse_bandwidth_file_v2(filepath)

                if data["timestamp"] and data["relays"]:
                    # Filter by date range if specified
                    if start_date and data["datetime"] < start_date:
                        continue
                    if end_date and data["datetime"] > end_date:
                        continue

                    measurements.append(data)
            except Exception as e:
                # Skip files that can't be parsed
                continue

    # Sort by timestamp
    measurements.sort(key=lambda x: x["timestamp"])

    return measurements


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
    Main function to analyze a specific relay's bandwidth patterns

    Args:
        relay_id: Relay fingerprint (40-character hex string)
        bandwidth_dir: Directory containing extracted bandwidth files
        start_date: datetime object for start date (optional)
        end_date: datetime object for end date (optional)
        output_prefix: Prefix for output plot filenames
    """
    print(f"\nAnalyzing relay: {relay_id}")
    print(f"Loading measurements from {bandwidth_dir}...")

    measurements = collect_bandwidth_measurements(bandwidth_dir, start_date, end_date)

    if not measurements:
        print("No measurements found!")
        return

    print(f"Loaded {len(measurements)} measurements")
    print(
        f"Date range: {measurements[0]['datetime']} to {measurements[-1]['datetime']}"
    )

    # Check if relay exists in measurements
    relay_found = False
    for m in measurements:
        if relay_id in m["relays"]:
            relay_found = True
            break

    if not relay_found:
        print(f"WARNING: Relay {relay_id} not found in any measurements!")
        print("This relay may not have been active during the specified period.")
        return

    # Aggregate by hour
    print("\nAggregating by hour of day...")
    hourly_avg, hourly_count = aggregate_bandwidth_by_hour(measurements, relay_id)

    print("\nAverage bandwidth by hour (UTC):")
    for hour in range(24):
        if hourly_count[hour] > 0:
            print(
                f"  {hour:02d}:00 - {hourly_avg[hour]:10.2f} KB/s ({hourly_count[hour]} measurements)"
            )

    # Aggregate by day of week
    print("\nAggregating by day of week...")
    daily_avg, daily_count = aggregate_bandwidth_by_day_of_week(measurements, relay_id)

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
    Analyze overall network bandwidth patterns
    """
    print("\nAnalyzing overall network bandwidth...")
    print(f"Loading measurements from {bandwidth_dir}...")

    measurements = collect_bandwidth_measurements(bandwidth_dir, start_date, end_date)

    if not measurements:
        print("No measurements found!")
        return

    print(f"Loaded {len(measurements)} measurements")
    print(
        f"Date range: {measurements[0]['datetime']} to {measurements[-1]['datetime']}"
    )

    # Aggregate by hour
    print("\nAggregating by hour of day...")
    hourly_avg, hourly_count = aggregate_bandwidth_by_hour(measurements)

    print("\nAverage total network bandwidth by hour (UTC):")
    for hour in range(24):
        if hourly_count[hour] > 0:
            bw_gbps = hourly_avg[hour] / 1_000_000  # Convert KB/s to GB/s
            print(
                f"  {hour:02d}:00 - {bw_gbps:8.3f} GB/s ({hourly_count[hour]} measurements)"
            )

    # Aggregate by day of week
    print("\nAggregating by day of week...")
    daily_avg, daily_count = aggregate_bandwidth_by_day_of_week(measurements)

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
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Analyze specific relay:")
        print("    python analyze_bandwidth.py <bandwidth_dir> <relay_fingerprint>")
        print("  Analyze overall network:")
        print("    python analyze_bandwidth.py <bandwidth_dir> --network")
        print()
        print("Example:")
        print(
            "    python analyze_bandwidth.py bandwidth_data/bandwidths-2024-03 ABCD1234..."
        )
        sys.exit(1)

    bandwidth_dir = sys.argv[1]

    # Set date range for Mar 1 - May 1, 2024 to cover available data (Mar/Apr)
    start_date = datetime(2024, 3, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 5, 1, tzinfo=timezone.utc)

    if len(sys.argv) > 2 and sys.argv[2] == "--network":
        analyze_network(bandwidth_dir, start_date, end_date)
    elif len(sys.argv) > 2:
        relay_id = sys.argv[2].upper()
        analyze_relay(relay_id, bandwidth_dir, start_date, end_date)
    else:
        print("Please specify a relay fingerprint or --network")
