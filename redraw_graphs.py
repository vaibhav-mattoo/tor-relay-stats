#!/usr/bin/env python3
"""
Redraw graphs from SLURM output files with correct y-axis labels.
Parses the output files to extract the actual data and regenerates plots.
"""

import re
import matplotlib.pyplot as plt
import sys
import os


def parse_network_output(output_file):
    """Parse network analysis output file and extract hourly/daily data."""
    hourly_data = {}
    daily_data = {}
    
    with open(output_file, 'r') as f:
        content = f.read()
    
    # Parse hourly data (in GB/s) - handle variable whitespace
    hourly_pattern = r'(\d{2}):00\s+-\s+([\d.]+)\s+GB/s'
    for match in re.finditer(hourly_pattern, content):
        hour = int(match.group(1))
        bandwidth_gbps = float(match.group(2))
        hourly_data[hour] = bandwidth_gbps
    
    # Parse daily data (in GB/s) - handle variable whitespace
    daily_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+-\s+([\d.]+)\s+GB/s'
    day_map = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    for match in re.finditer(daily_pattern, content):
        day_name = match.group(1)
        bandwidth_gbps = float(match.group(2))
        daily_data[day_map[day_name]] = bandwidth_gbps
    
    return hourly_data, daily_data


def parse_relay_output(output_file):
    """Parse relay analysis output file and extract hourly/daily data."""
    hourly_data = {}
    daily_data = {}
    
    with open(output_file, 'r') as f:
        content = f.read()
    
    # Parse hourly data (in KB/s) - handle variable whitespace
    hourly_pattern = r'(\d{2}):00\s+-\s+([\d.]+)\s+KB/s'
    for match in re.finditer(hourly_pattern, content):
        hour = int(match.group(1))
        bandwidth_kbps = float(match.group(2))
        hourly_data[hour] = bandwidth_kbps
    
    # Parse daily data (in KB/s) - handle variable whitespace
    daily_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+-\s+([\d.]+)\s+KB/s'
    day_map = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    for match in re.finditer(daily_pattern, content):
        day_name = match.group(1)
        bandwidth_kbps = float(match.group(2))
        daily_data[day_map[day_name]] = bandwidth_kbps
    
    return hourly_data, daily_data


def plot_network_hourly(hourly_data, output_file):
    """Plot network hourly bandwidth with correct GB/s y-axis."""
    hours = sorted(hourly_data.keys())
    bandwidths = [hourly_data[h] for h in hours]
    
    plt.figure(figsize=(12, 6))
    plt.plot(hours, bandwidths, marker="o", linewidth=2, markersize=8)
    plt.xlabel("Hour of Day (UTC)", fontsize=12)
    plt.ylabel("Average Total Network Bandwidth (GB/s)", fontsize=12)
    plt.title("Average Total Network Bandwidth by Hour (UTC)", fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.xticks(range(0, 24, 2))
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Saved network hourly plot to {output_file}")
    plt.close()


def plot_network_daily(daily_data, output_file):
    """Plot network daily bandwidth with correct GB/s y-axis."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_indices = sorted(daily_data.keys())
    bandwidths = [daily_data[d] for d in day_indices]
    
    plt.figure(figsize=(10, 6))
    plt.bar(range(7), bandwidths, color="steelblue", alpha=0.7)
    plt.xlabel("Day of Week", fontsize=12)
    plt.ylabel("Average Total Network Bandwidth (GB/s)", fontsize=12)
    plt.title("Average Total Network Bandwidth by Day of Week", fontsize=14)
    plt.xticks(range(7), days, rotation=45)
    plt.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Saved network daily plot to {output_file}")
    plt.close()


def plot_relay_hourly(hourly_data, relay_id, output_file):
    """Plot relay hourly bandwidth with correct KB/s y-axis (or convert to MB/s if large)."""
    hours = sorted(hourly_data.keys())
    bandwidths_kbps = [hourly_data[h] for h in hours]
    
    # Convert to MB/s for better readability if values are large
    max_bw = max(bandwidths_kbps) if bandwidths_kbps else 0
    if max_bw > 100000:  # If > 100 MB/s, use MB/s
        bandwidths = [bw / 1000.0 for bw in bandwidths_kbps]
        ylabel = "Average Bandwidth (MB/s)"
    else:
        bandwidths = bandwidths_kbps
        ylabel = "Average Bandwidth (KB/s)"
    
    plt.figure(figsize=(12, 6))
    plt.plot(hours, bandwidths, marker="o", linewidth=2, markersize=8)
    plt.xlabel("Hour of Day (UTC)", fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.title(f"Average Bandwidth by Hour for Relay {relay_id[:8]}...", fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.xticks(range(0, 24, 2))
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Saved relay hourly plot to {output_file}")
    plt.close()


def plot_relay_daily(daily_data, relay_id, output_file):
    """Plot relay daily bandwidth with correct KB/s y-axis (or convert to MB/s if large)."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_indices = sorted(daily_data.keys())
    bandwidths_kbps = [daily_data[d] for d in day_indices]
    
    # Convert to MB/s for better readability if values are large
    max_bw = max(bandwidths_kbps) if bandwidths_kbps else 0
    if max_bw > 100000:  # If > 100 MB/s, use MB/s
        bandwidths = [bw / 1000.0 for bw in bandwidths_kbps]
        ylabel = "Average Bandwidth (MB/s)"
    else:
        bandwidths = bandwidths_kbps
        ylabel = "Average Bandwidth (KB/s)"
    
    plt.figure(figsize=(10, 6))
    plt.bar(range(7), bandwidths, color="steelblue", alpha=0.7)
    plt.xlabel("Day of Week", fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.title(f"Average Bandwidth by Day of Week for Relay {relay_id[:8]}...", fontsize=14)
    plt.xticks(range(7), days, rotation=45)
    plt.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Saved relay daily plot to {output_file}")
    plt.close()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python redraw_graphs.py <output_file> [output_file2 ...]")
        print()
        print("Example:")
        print("  python redraw_graphs.py slurm_logs/tor-bw-analyze-2024_13590694.out")
        print("  python redraw_graphs.py slurm_logs/tor-bw-relay-04102613_13592052.out")
        sys.exit(1)
    
    for output_file in sys.argv[1:]:
        if not os.path.exists(output_file):
            print(f"Warning: File not found: {output_file}")
            continue
        
        print(f"\nProcessing {output_file}...")
        
        # Determine if it's network or relay analysis
        with open(output_file, 'r') as f:
            content = f.read()
        
        if "Analyzing overall network bandwidth" in content or "--network" in content:
            # Network analysis
            hourly_data, daily_data = parse_network_output(output_file)
            
            if hourly_data:
                plot_network_hourly(hourly_data, "network_hourly_corrected.png")
            if daily_data:
                plot_network_daily(daily_data, "network_daily_corrected.png")
        
        elif "Analyzing relay:" in content:
            # Relay analysis - extract relay ID
            relay_match = re.search(r'Analyzing relay: ([A-F0-9]{40})', content)
            if relay_match:
                relay_id = relay_match.group(1)
                hourly_data, daily_data = parse_relay_output(output_file)
                
                if hourly_data:
                    plot_relay_hourly(hourly_data, relay_id, f"relay_{relay_id[:8]}_hourly_corrected.png")
                if daily_data:
                    plot_relay_daily(daily_data, relay_id, f"relay_{relay_id[:8]}_daily_corrected.png")
            else:
                print(f"Warning: Could not extract relay ID from {output_file}")
        else:
            print(f"Warning: Could not determine analysis type for {output_file}")


if __name__ == "__main__":
    main()

