#!/bin/bash

# Function to show usage
usage() {
  echo "Usage: $0 --targets <file> [--prefix PREFIX] [--outdir OUTDIR] [nmap_args...]"
  exit 1
}

# Initialize variables
PREFIX=""
OUTDIR=""
TARGETS_FILE=""
NMAP_ARGS=()
CURRENT_TARGET=""
CURRENT_FILE=""

# Trap to handle Ctrl+C
cleanup_on_interrupt() {
  echo -e "\n[!] Interrupted. Cleaning up partial scan for: $CURRENT_TARGET"
  [ -n "$CURRENT_FILE" ] && rm -f "${CURRENT_FILE}".nmap "${CURRENT_FILE}".gnmap "${CURRENT_FILE}".xml
  exit 1
}
trap cleanup_on_interrupt INT

# Parse arguments
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --targets)
      shift
      [ -z "$1" ] && { echo "Error: --targets requires a value"; usage; }
      TARGETS_FILE="$1"
      shift
      ;;
    --prefix)
      shift
      [ -z "$1" ] && { echo "Error: --prefix requires a value"; usage; }
      PREFIX="$1"
      shift
      ;;
    --outdir)
      shift
      [ -z "$1" ] && { echo "Error: --outdir requires a value"; usage; }
      OUTDIR="$1"
      shift
      ;;
    *)
      NMAP_ARGS+=("$1")
      shift
      ;;
  esac
done

# Validate targets file
if [ -z "$TARGETS_FILE" ]; then
  echo "Error: --targets is required"
  usage
fi
if [ ! -f "$TARGETS_FILE" ]; then
  echo "Error: File '$TARGETS_FILE' does not exist."
  exit 1
fi

# Create output directory if specified
[ -n "$OUTDIR" ] && mkdir -p "$OUTDIR"

# Read and scan each target
while IFS= read -r TARGET || [ -n "$TARGET" ]; do
  [[ -z "$TARGET" || "$TARGET" == \#* ]] && continue

  CURRENT_TARGET="$TARGET"
  SAFE_NAME="${TARGET//\//_}"
  FILENAME="${PREFIX}${SAFE_NAME}"
  [ -n "$OUTDIR" ] && FILENAME="${OUTDIR%/}/$FILENAME"
  CURRENT_FILE="$FILENAME"

  if [ -f "${FILENAME}.gnmap" ]; then
    echo "Skipping ${TARGET} (already scanned)"
    continue
  fi

  echo "Scanning ${TARGET}..."
  nmap "${NMAP_ARGS[@]}" -oA "$FILENAME" "$TARGET"

  # Reset current vars after successful scan
  CURRENT_TARGET=""
  CURRENT_FILE=""
done < "$TARGETS_FILE"

# === Move files into separate folders ===
echo "Organizing scan output files..."
XML_DIR="${OUTDIR:-.}/xml"
GNMAP_DIR="${OUTDIR:-.}/gnmap"
NMAP_DIR="${OUTDIR:-.}/nmap"

mkdir -p "$XML_DIR" "$GNMAP_DIR" "$NMAP_DIR"

mv "${OUTDIR:-.}"/*.xml "$XML_DIR" 2>/dev/null
mv "${OUTDIR:-.}"/*.gnmap "$GNMAP_DIR" 2>/dev/null
mv "${OUTDIR:-.}"/*.nmap "$NMAP_DIR" 2>/dev/null

echo "Files organized into: $XML_DIR, $GNMAP_DIR, and $NMAP_DIR"
