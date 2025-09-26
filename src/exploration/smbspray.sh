#!/bin/bash -l

# Usage: ./smb_enum.sh <target_ip/range> <credentials_file> [-o output_file] [--format hashcat|pipe|colon] [nxc options]
# Prints successful SMB login lines (containing [+]) and enumerates shares for each
# Only actual share lines are printed (lines without [-], [*], [+])

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <target_ip/range> <credentials_file> [-o output_file] [--format hashcat|pipe|colon] [nxc options]"
    exit 1
fi

TARGET="$1"
CRED_FILE="$2"
shift 2

OUTPUT_FILE="results.txt"
FORMAT="hashcat"  # Default format
NXC_OPTIONS=()

# Parse optional flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        -o)
            shift
            OUTPUT_FILE="$1"
            ;;
        --format)
            shift
            FORMAT="$1"
            ;;
        *)
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
    LINE=$(echo -n "$RAW_LINE" \
           | sed 's/^\xEF\xBB\xBF//' \
           | tr -d '\r' \
           | sed -E 's/^[[:space:]\xC2\xA0]+//;s/[[:space:]\xC2\xA0]+$//')

    [[ -z "$LINE" ]] && continue

    case "$FORMAT" in
        hashcat)
            [[ "$LINE" != *:*:* ]] && continue
            USER=$(echo "$LINE" | cut -d: -f1 | sed -E 's/^[[:space:]\xC2\xA0]+//;s/[[:space:]\xC2\xA0]+$//')
            PASS=$(echo "$LINE" | cut -d: -f3- | sed -E 's/^[[:space:]\xC2\xA0]+//;s/[[:space:]\xC2\xA0]+$//')
            ;;
        pipe)
            [[ "$LINE" != *\|* ]] && continue
            USER=$(echo "$LINE" | cut -d'|' -f1 | sed -E 's/^[[:space:]\xC2\xA0]+//;s/[[:space:]\xC2\xA0]+$//')
            PASS=$(echo "$LINE" | cut -d'|' -f2- | sed -E 's/^[[:space:]\xC2\xA0]+//;s/[[:space:]\xC2\xA0]+$//')
            ;;
        colon)
            [[ "$LINE" != *:* ]] && continue
            USER=$(echo "$LINE" | cut -d: -f1 | sed -E 's/^[[:space:]\xC2\xA0]+//;s/[[:space:]\xC2\xA0]+$//')
            PASS=$(echo "$LINE" | cut -d: -f2- | sed -E 's/^[[:space:]\xC2\xA0]+//;s/[[:space:]\xC2\xA0]+$//')
            ;;
        *)
            echo "Error: Unknown format '$FORMAT'. Use hashcat, pipe, or colon."
            exit 1
            ;;
    esac

    [[ -z "$USER" || -z "$PASS" ]] && continue

    echo "Testing user: '$USER' with password: '$PASS'"

    SUCCESS_OUTPUT=$(nxc smb "$TARGET" -u "$USER" -p "$PASS" "${NXC_OPTIONS[@]}" 2>&1 | grep "\[+\]")

    if [[ -n "$SUCCESS_OUTPUT" ]]; then
        # Print successes live
        echo "$SUCCESS_OUTPUT" | tee -a "$OUTPUT_FILE"

        # Enumerate shares and only print actual share lines
        echo "[*] Enumerating shares for $USER on $TARGET" | tee -a "$OUTPUT_FILE"
        nxc smb "$TARGET" -u "$USER" -p "$PASS" --shares "${NXC_OPTIONS[@]}" 2>&1 \
            | grep -v "[-]" | grep -v "[*]" | grep -v "[+]" | grep -v "Running nxc against" | tee -a "$OUTPUT_FILE"
    fi

done < "$CRED_FILE"

echo "Scan complete. Results saved to $OUTPUT_FILE"
