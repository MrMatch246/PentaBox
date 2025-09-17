#!/usr/bin/env python3

import argparse
import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

console = Console()

# 🔑 Ordered SNMP OIDs (broad → narrow fallback)
OID_FALLBACKS = [
    "1",                        # Full walk
    "1.3.6.1.2.1.1",            # System MIB
    "1.3.6.1.2.1.2",            # Interfaces
    "1.3.6.1.2.1.4",            # IP layer info (ARP/routing)
    "1.3.6.1.2.1.25",           # Host resources (procs, storage, software)
    "1.3.6.1.2.1.6",            # TCP connections
    "1.3.6.1.2.1.7",            # UDP listeners
    "1.3.6.1.4.1.2021",         # Net-SNMP (Linux)
    "1.3.6.1.4.1.77",           # Windows users (LANMAN)
    "1.3.6.1.4.1.311",          # Microsoft extensions
    "1.3.6.1.4.1.9",            # Cisco-specific
    "1.3.6.1.2.1.43",           # Printer-MIB
    "1.3.6.1.4.1",              # Enterprise/vendor tree
]

def parse_args():
    parser = argparse.ArgumentParser(description="SNMP Dumper: Parse Nmap XML, extract SNMP creds, and run snmpbulkwalk.")
    parser.add_argument("--input", required=True, help="Input: directory (recursive) or single XML file")
    parser.add_argument("--output", required=True, help="Output directory for SNMP dumps")
    parser.add_argument("--prefix", default="", help="Prefix for output files")
    parser.add_argument("--quiet", action="store_true", help="Suppress prints")
    return parser.parse_args()

def log(msg, style="cyan", quiet=False):
    if not quiet:
        console.print(f"[{style}]{msg}[/{style}]")

def find_xml_files(input_path):
    p = Path(input_path)
    if p.is_file() and p.suffix == ".xml":
        return [p]
    elif p.is_dir():
        return list(p.rglob("*.xml"))
    else:
        raise ValueError(f"Invalid input path: {input_path}")

def extract_snmp_hosts(xml_files):
    snmp_hosts = {}
    for xml_file in xml_files:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for host in root.findall("host"):
            addr_elem = host.find("address[@addrtype='ipv4']")
            if addr_elem is None:
                continue
            ip = addr_elem.get("addr")

            port = host.find("ports/port[@protocol='udp'][@portid='161']")
            if port is None:
                continue

            creds = []
            for script in port.findall("script[@id='snmp-brute']"):
                for elem in script.findall("table"):
                    pwd = elem.find("elem[@key='password']")
                    state = elem.find("elem[@key='state']")
                    if pwd is not None and state is not None and "valid" in state.text.lower():
                        creds.append(pwd.text)

                output = script.get("output", "")
                if "Valid" in output and "-" in output:
                    parts = output.split("-")[0].strip().split()
                    if parts:
                        creds.append(parts[0])

            if creds:
                snmp_hosts[ip] = list(set(creds))
    return snmp_hosts

def run_snmpbulkwalk(host, communities, output_dir, prefix, quiet=False):
    outfile = Path(output_dir) / f"{prefix + '_' if prefix else ''}{host}_dump.snmp"

    if outfile.exists():
        log(f"[SKIP] {host} (already processed)", style="yellow", quiet=quiet)
        return

    tmpfile = outfile.with_suffix(".tmp")
    seen_oids = {}
    timeout = "5"

    def parse_snmp_output(community, output):
        for line in output.splitlines():
            if not line.strip() or "Timeout" in line:
                continue
            if " = " in line:
                oid, value = line.split(" = ", 1)
                seen_oids.setdefault(oid.strip(), []).append((community, value.strip()))

    def run_snmp_command(cmd, desc, community):
        community = community.replace("<empty>", '""')
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode in (0, 2) and result.stdout.strip():
                parse_snmp_output(community, result.stdout)
                if result.returncode == 0:
                    log(f"[SNMP] {host} ({desc})", style="blue", quiet=quiet)
                    return True
                elif result.returncode == 2:
                    log(f"[PARTIAL] {host} ({desc})", style="orange_red1", quiet=quiet)
                    return False
            return False
        except subprocess.TimeoutExpired:
            log(f"[TIMEOUT] {host} {desc}", style="red", quiet=quiet)
            return False

    try:
        for comm in communities:
            log(f"[+] Testing community '{comm}' on {host}", style="cyan", quiet=quiet)
            full_walk_success = False

            for oid in OID_FALLBACKS:
                # === SNMPv2c phase ===
                desc = f"OID {oid} v2c (community '{comm}')"
                success = False

                if run_snmp_command(["snmpbulkwalk", "-On", "-t", timeout, "-r1", "-v2c", "-c", comm, host, oid], desc, comm):
                    success = True
                elif run_snmp_command(["snmpbulkwalk", "-On", "-t", timeout, "-r1", "-Cr10", "-v2c", "-c", comm, host, oid], desc+" (-Cr10)", comm):
                    success = True
                elif run_snmp_command(["snmpwalk", "-On", "-Cc", "-t", timeout, "-r1", "-v2c", "-c", comm, host, oid], desc+" (walk)", comm):
                    success = True
                elif run_snmp_command(["snmpwalk", "-On", "-Cc", "-t", timeout, "-r1", "-v1", "-c", comm, host, oid], f"OID {oid} v1 (community '{comm}')", comm):
                    success = True

                if success:
                    if oid == "1":  # full tree capture
                        full_walk_success = True
                        break  # stop OID loop entirely
                    else:
                        continue  # skip v1 for this OID, go to next OID

            if full_walk_success:
                break  # done for this host/community

        if not seen_oids:
            log(f"[EMPTY] No SNMP data found for {host}", style="yellow", quiet=quiet)
            return

        with tmpfile.open("w") as out:
            out.write(f"# SNMP dump for {host}\n")
            out.write(f"# Communities tried: {', '.join(communities)}\n\n")
            for oid in sorted(seen_oids.keys()):
                values = seen_oids[oid]
                unique_values = {v for _, v in values}
                if len(unique_values) == 1:
                    out.write(f"{oid} = {values[0][1]}  # from {values[0][0]}\n")
                else:
                    for comm, val in values:
                        out.write(f"{oid} = {val}  # from {comm}\n")

        tmpfile.rename(outfile)
        log(f"[DONE] Dump saved: {outfile}", style="green", quiet=quiet)

    except KeyboardInterrupt:
        log(f"[INTERRUPT] Removing partial file: {tmpfile}", style="red", quiet=quiet)
        if tmpfile.exists(): tmpfile.unlink()
        log(f"[INTERRUPT] Process interrupted, exiting.", style="red", quiet=quiet)
        exit(0)


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    xml_files = find_xml_files(args.input)
    log(f"[+] Found {len(xml_files)} XML file(s)", style="cyan", quiet=args.quiet)

    snmp_hosts = extract_snmp_hosts(xml_files)
    log(f"[+] Found {len(snmp_hosts)} hosts with SNMP and valid creds", style="cyan", quiet=args.quiet)

    with open(Path(args.output) / "snmp_hosts_and_creds.json", "w") as f:
        f.write(snmp_hosts.__repr__())

    if args.quiet:
        for host, creds in snmp_hosts.items():
            run_snmpbulkwalk(host, creds, args.output, args.prefix, quiet=True)
    else:
        with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"), BarColumn(), TextColumn("{task.completed}/{task.total}"), console=console) as progress:
            task = progress.add_task("[white]Processing hosts...", total=len(snmp_hosts))
            for host, creds in snmp_hosts.items():
                run_snmpbulkwalk(host, creds, args.output, args.prefix, quiet=False)
                progress.advance(task)

if __name__ == "__main__":
    main()
