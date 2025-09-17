import os
import hashlib
import socket
import requests

def is_in_tmux():
    return 'TMUX' in os.environ


def md5_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_internal_ip():
    return socket.gethostbyname(socket.gethostname())

def get_external_ip():
    while True:
        try:
        # https://ifconfig.me/
            response = requests.get("https://ifconfig.me/ip", timeout=5)
            response.raise_for_status()  # Raise an error for bad responses
            return response.text.strip()
        except requests.RequestException:
            # If the request fails, wait and retry
            print("Failed to retrieve external IP, retrying...")


import ipaddress
from pathlib import Path

def load_lines(file_path):
    """
    Loads non-empty, stripped lines from a file.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return []
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def write_lines(file_path, lines):
    """
    Write a list of lines to a file, one per line.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        for line in lines:
            f.write(f"{line}\n")

def expand_target_to_ips(target):
    """
    Expand a target (IP, CIDR, or range) into a list of IP addresses.
    """
    try:
        if "/" in target:
            network = ipaddress.ip_network(target, strict=False)
            return [str(ip) for ip in network.hosts()]
        else:
            return [str(ipaddress.ip_address(target))]
    except ValueError:
        # If it's a domain name, skip expansion (handled elsewhere).
        return []

def generate_leftover_chunks(targets, live_hosts, chunk_size, chunks_dir):
    """
    Generate chunks of leftover IPs from target scope minus discovered live hosts.
    Args:
        targets (list): List of targets from scope (IP/CIDR/hostname).
        live_hosts (list): List of live hosts discovered in Stage 1.
        chunk_size (int): Size of each chunk for leftover scanning.
        chunks_dir (Path): Directory to save leftover chunk files.
    """
    chunks_dir.mkdir(parents=True, exist_ok=True)
    live_hosts_set = set(live_hosts)
    any_leftover = False
    for target in targets:
        ips = expand_target_to_ips(target)
        leftover_ips = [ip for ip in ips if ip not in live_hosts_set]

        if not leftover_ips:
            continue

        any_leftover = True
        if len(leftover_ips) == 1:
            # Single leftover host file
            file_name = f"leftover_hosts_{leftover_ips[0]}.txt"
            file_path = chunks_dir / file_name
            write_lines(file_path, leftover_ips)
        else:
            # Break into chunks
            for i in range(0, len(leftover_ips), chunk_size):
                chunk = leftover_ips[i:i+chunk_size]
                start_ip_parts = chunk[0].split(".")
                end_ip_parts = chunk[-1].split(".")

                # Use the first three octets from start_ip and only last octet of start and end
                file_name = f"leftover_hosts_{'.'.join(start_ip_parts[:3])}.{start_ip_parts[3]}-{end_ip_parts[3]}.txt"

                file_path = chunks_dir / file_name
                write_lines(file_path, chunk)
    return any_leftover