#!/bin/bash -l

# Usage: ./smb_enum.sh <target_ip/range> <credentials_file> [-o output_file] [nxc options]
# Prints only successful SMB login lines (containing [+]) live
# You can supply extra nxc smb options like --local-auth --users

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <target_ip/range> <credentials_file> [-o output_file] [nxc options]"
    exit 1
fi

TARGET="$1"
CRED_FILE="$2"
shift 2

# Default output file
OUTPUT_FILE="results.txt"

# Parse optional -o flag
while [[ $# -gt 0 ]]; do
    case "$1" in
        -o)
            shift
            OUTPUT_FILE="$1"
            ;;
        *)
            # Remaining args are passed to nxc
            NXC_OPTIONS+=("$1")
            ;;
    esac
    shift
done

if [[ ! -f "$CRED_FILE" ]]; then
    echo "Error: File '$CRED_FILE' not found."
    exit 1
fi

> "$OUTPUT_FILE"

while IFS= read -r RAW_LINE || [[ -n "$RAW_LINE" ]]; do
    # Normalize line: remove BOM, CR, leading/trailing spaces & NBSP
    LINE=$(echo -n "$RAW_LINE" \
           | sed 's/^\xEF\xBB\xBF//' \
           | tr -d '\r' \
           | sed -E 's/^[[:space:]\xC2\xA0]+//;s/[[:space:]\xC2\xA0]+$//')

    [[ -z "$LINE" || "$LINE" != *:*:* ]] && continue

    # Extract username and password (password may contain colons)
    USER=$(echo "$LINE" | cut -d: -f1 | sed -E 's/^[[:space:]\xC2\xA0]+//;s/[[:space:]\xC2\xA0]+$//')
    PASS=$(echo "$LINE" | cut -d: -f3- | sed -E 's/^[[:space:]\xC2\xA0]+//;s/[[:space:]\xC2\xA0]+$//')

    [[ -z "$USER" || -z "$PASS" ]] && continue

    echo "Testing user: '$USER' with password: '$PASS'"

    # Run nxc smb with extra options, target IP/range, live output
    nxc smb "$TARGET" -u "$USER" -p "$PASS" "${NXC_OPTIONS[@]}" 2>&1 \
        | grep --line-buffered "[+]" | tee -a "$OUTPUT_FILE"

done < "$CRED_FILE"

echo "Scan complete. Results saved to $OUTPUT_FILE"
