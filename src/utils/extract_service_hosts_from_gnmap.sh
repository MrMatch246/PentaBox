#!/bin/bash

# Usage:
# ./extract_service_hosts.sh --input <file_or_directory> --service <service_name> --output <output_dir> [--prefix <prefix>] [--quiet]

set -e

# Default values
PREFIX=""
QUIET=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --input)
            INPUT="$2"
            shift 2
            ;;
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --output)
            OUTPUT="$2"
            shift 2
            ;;
        --prefix)
            PREFIX="$2"
            shift 2
            ;;
        --quiet)
            QUIET=true
            shift 1
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 --input <file_or_dir> --service <service> --output <output_dir> [--prefix <prefix>] [--quiet]"
            exit 1
            ;;
    esac
done

# Validate arguments
if [[ -z "$INPUT" || -z "$SERVICE" || -z "$OUTPUT" ]]; then
    echo "Error: --input, --service, and --output are required."
    exit 1
fi

if [[ ! -f "$INPUT" && ! -d "$INPUT" ]]; then
    echo "Error: Input must be a valid file or directory."
    exit 1
fi

mkdir -p "$OUTPUT"

# Output file
OUTFILE="$OUTPUT/${PREFIX:+${PREFIX}_}${SERVICE}_hosts.txt"

# Start processing
$QUIET || echo "[*] Collecting hosts with service '$SERVICE'..."
> "$OUTFILE"

# Find gnmap files
if [[ -f "$INPUT" ]]; then
    GNMAP_FILES=("$INPUT")
else
    mapfile -t GNMAP_FILES < <(find "$INPUT" -type f -name "*.gnmap")
fi

# Parse each gnmap file
for FILE in "${GNMAP_FILES[@]}"; do
    $QUIET || echo "  [+] Parsing: $FILE"
    grep -i " $SERVICE " "$FILE" | grep -oP 'Host: \K[\d.]+' >> "$OUTFILE" || true
done

# Deduplicate
sort -u -o "$OUTFILE" "$OUTFILE"

$QUIET || {
    echo "[+] Done! Found $(wc -l < "$OUTFILE") hosts. Output saved to:"
    echo "    $OUTFILE"
}
