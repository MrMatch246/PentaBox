#!/bin/bash

VERSION="2.3"

# By default the first non-option argument is treated as the targets file
TARGET=""
MASSCAN_CONF=""
MASSCAN_XML=""

WORKING_DIR="$(cd "$(dirname "$0")" ; pwd -P)"
RESULTS_PATH="$WORKING_DIR/results"

RED="\033[1;31m"
GREEN="\033[1;32m"
BLUE="\033[1;36m"
YELLOW="\033[1;33m"
RESET="\033[0m"


displayLogo(){
echo -e "${GREEN}
 _______                     _______
|   |   |.---.-.-----.-----.|   |   |.---.-.-----.
|       ||  _  |__ --|__ --||       ||  _  |  _  |
|__|_|__||___._|_____|_____||__|_|__||___._|   __|${RESET} ${RED}v$VERSION${RESET}
                                           ${GREEN}|__|${RESET}    by ${YELLOW}@CaptMeelo${RESET}\n
"
}

usage(){
    echo -e "${GREEN}USAGE:${RESET} $0 [-c masscan.conf] [-x masscan.xml] <file-containing-list-of-IP/CIDR>"
    echo -e "  -c <file>    Use a masscan config file (passed to masscan as -c). If provided, the targets list argument is optional (masscan config can include targets)."
    echo -e "  -x <file>    Use an existing masscan XML output file instead of running masscan. If provided, masscan will NOT be executed and this XML will be used."
    echo -e "  -h           Show this help."
    echo
    echo -e "Notes:"
    echo -e "  If -x is supplied, it takes precedence: the script will use that masscan XML and skip running masscan."
    echo -e "  Nmap will be run in batches of 64 hosts to reduce per-run load. Each chunk uses -oA to write .nmap/.xml/.gnmap."
    echo -e "  If a previous per-chunk .nmap or .xml is present in results/ the script will try to resume that chunk using nmap --resume <file>."
    echo
    echo -e "Examples:"
    echo -e "  $0 targets.txt                     # use targets list (old behaviour)"
    echo -e "  $0 -c masscan.conf                 # use masscan config file"
    echo -e "  $0 -x masscan.xml                  # use an existing masscan XML output (skip masscan)"
    echo -e "  $0 -c masscan.conf targets.txt     # use config file (masscan -c), targets file is ignored by masscan but still validated here if given"
    exit 1
}

checkArgs(){
    # Either MASSCAN_CONF must be set and exist, or TARGET must be set and non-empty file,
    # or a MASSCAN_XML file must be provided.
    if [[ -z "$MASSCAN_CONF" && -z "$TARGET" && -z "$MASSCAN_XML" ]]; then
        echo -e "\t${RED}[!] ERROR:${RESET} Invalid argument!\n"
        usage
    fi

    if [[ -n "$MASSCAN_CONF" ]]; then
        if [[ ! -f "$MASSCAN_CONF" || ! -s "$MASSCAN_CONF" ]]; then
            echo -e "\t${RED}[!] ERROR:${RESET} Masscan config file '$MASSCAN_CONF' does not exist or is empty.\n"
            exit 1
        fi
    fi

    if [[ -n "$TARGET" ]]; then
        if [[ ! -f "$TARGET" || ! -s "$TARGET" ]]; then
            echo -e "\t${RED}[!] ERROR:${RESET} Target file '$TARGET' does not exist or is empty.\n"
            exit 1
        fi
    fi

    if [[ -n "$MASSCAN_XML" ]]; then
        if [[ ! -f "$MASSCAN_XML" || ! -s "$MASSCAN_XML" ]]; then
            echo -e "\t${RED}[!] ERROR:${RESET} Masscan XML file '$MASSCAN_XML' does not exist or is empty.\n"
            exit 1
        fi
    fi
}

portScan(){
    echo -e "${GREEN}[+] Checking if results directory already exists.${RESET}"
    if [ -d "$RESULTS_PATH" ]
    then
        echo -e "${BLUE}[-] Directory already exists. Skipping...${RESET}"
    else
        echo -e "${GREEN}[+] Creating results directory.${RESET}"
        mkdir -p "$RESULTS_PATH"
    fi

    # If a masscan XML was provided, use it and skip running masscan
    if [[ -n "$MASSCAN_XML" ]]; then
        echo -e "${GREEN}[+] Using supplied Masscan XML: $MASSCAN_XML${RESET}"
        cp -f "$MASSCAN_XML" "$RESULTS_PATH/masscan.xml"
        if [[ ! -s "$RESULTS_PATH/masscan.xml" ]]; then
            echo -e "${RED}[!] ERROR:${RESET} Failed to copy supplied masscan XML to $RESULTS_PATH/masscan.xml"
            exit 1
        fi
    else
        echo -e "${GREEN}[+] Running Masscan.${RESET}"

        # Build the masscan command depending on whether a config file was provided
        if [[ -n "$MASSCAN_CONF" ]]; then
            # When using -c the masscan config file typically contains targets and options.
            # We'll still force an XML output path so downstream parsing works.
            sudo masscan -c "$MASSCAN_CONF" -oX "$RESULTS_PATH/masscan.xml"
        else
            # previous/default behaviour: use -iL <targets-file> with explicit flags
            sudo masscan -p 1-65535 --rate 100000 --wait 0 --open -iL "$TARGET" -oX "$RESULTS_PATH/masscan.xml"
        fi

        if [ -f "$WORKING_DIR/paused.conf" ] ; then
            sudo rm "$WORKING_DIR/paused.conf"
        fi

        # If masscan produced no XML or empty, exit gracefully
        if [[ ! -s "$RESULTS_PATH/masscan.xml" ]]; then
            echo -e "${RED}[!] ERROR:${RESET} Masscan did not produce results at $RESULTS_PATH/masscan.xml or the file is empty."
            exit 1
        fi
    fi

    # At this point $RESULTS_PATH/masscan.xml exists and is non-empty
    open_ports=$(grep portid "$RESULTS_PATH/masscan.xml" | cut -d "\"" -f 10 | sort -n | uniq | paste -sd,)
    # For nmap targets extract address elements (this is what you used previously)
    grep portid "$RESULTS_PATH/masscan.xml" | cut -d "\"" -f 4 | sort -V | uniq > "$WORKING_DIR/nmap_targets.tmp"
    echo -e "${RED}[*] Masscan parsing Done!${RESET}"

    if [[ -z "$open_ports" ]]; then
        echo -e "${YELLOW}[!] No open ports found by masscan. Skipping nmap.${RESET}"
        sudo rm -f "$WORKING_DIR/nmap_targets.tmp"
        exit 0
    fi

    # ----- Chunked Nmap execution (64 hosts per chunk) -----
    CHUNK_SIZE=64
    CHUNK_PREFIX="$WORKING_DIR/nmap_chunk_"
    COMBINED_XML_TMP="$RESULTS_PATH/nmap.xml.tmp"
    COMBINED_XML_FINAL="$RESULTS_PATH/nmap.xml"

    # cleanup any previous chunk files that might exist
    rm -f "${CHUNK_PREFIX}"*.lst "$COMBINED_XML_TMP" "$COMBINED_XML_FINAL"

    # Split nmap_targets.tmp into chunks of CHUNK_SIZE lines
    echo -e "${GREEN}[+] Splitting targets into chunks of ${CHUNK_SIZE} hosts...${RESET}"
    # use split with numeric suffixes and .lst extension
    split -l "$CHUNK_SIZE" -d --additional-suffix=.lst "$WORKING_DIR/nmap_targets.tmp" "$CHUNK_PREFIX"

    # Prepare combined XML temporary with an XML header and opening root tag
    echo '<?xml version="1.0"?>' > "$COMBINED_XML_TMP"
    echo '<nmaprun>' >> "$COMBINED_XML_TMP"

    chunk_count=0
    for chunkfile in "${CHUNK_PREFIX}"*.lst; do
        # If no chunk files found (glob literal), break
        if [[ ! -f "$chunkfile" ]]; then
            continue
        fi

        chunk_count=$((chunk_count+1))
        echo -e "${GREEN}[+] Preparing Nmap chunk ${chunk_count} (file: ${chunkfile})...${RESET}"

        # define per-chunk basename in results (used with -oA)
        CHUNK_BASE="$RESULTS_PATH/nmap_chunk_${chunk_count}"
        CHUNK_XML="${CHUNK_BASE}.xml"
        CHUNK_NMAP="${CHUNK_BASE}.nmap"
        CHUNK_GNMAP="${CHUNK_BASE}.gnmap"

        # If a previous .nmap or .xml exists, attempt to resume using that file.
        RESUME_ARG=""
        if [[ -f "$CHUNK_NMAP" && -s "$CHUNK_NMAP" ]]; then
            echo -e "${YELLOW}[~] Found previous chunk .nmap file: $CHUNK_NMAP — attempting to resume.${RESET}"
            RESUME_ARG="--resume \"$CHUNK_NMAP\""
        elif [[ -f "$CHUNK_XML" && -s "$CHUNK_XML" ]]; then
            echo -e "${YELLOW}[~] Found previous chunk .xml file: $CHUNK_XML — attempting to resume.${RESET}"
            RESUME_ARG="--resume \"$CHUNK_XML\""
        fi

        if [[ -n "$RESUME_ARG" ]]; then
            # Use eval so the quoted resume argument is respected
            echo -e "${GREEN}[+] Resuming Nmap for chunk ${chunk_count} using: $RESUME_ARG -oA $CHUNK_BASE${RESET}"
            # shellcheck disable=SC2086
            sudo eval nmap -sVC -p "$open_ports" --open -vv -Pn -sS -A $RESUME_ARG -oA "$CHUNK_BASE"
        else
            echo -e "${GREEN}[+] Running fresh Nmap for chunk ${chunk_count} -oA $CHUNK_BASE${RESET}"
            sudo nmap -sVC -p "$open_ports" --open -vv -Pn -sS -A -iL "$chunkfile" -oA "$CHUNK_BASE"
        fi

        # If the XML doesn't exist or is empty after the run, warn and skip merging
        if [[ ! -s "$CHUNK_XML" ]]; then
            echo -e "${YELLOW}[!] Warning: chunk ${chunk_count} produced no nmap XML output (file $CHUNK_XML missing/empty). Skipping this chunk.${RESET}"
            continue
        fi

        # Append the inner XML (strip XML declaration and <nmaprun> wrapper) into combined file
        sed '1d;$d' "$CHUNK_XML" >> "$COMBINED_XML_TMP"
    done

    # Close combined XML root tag
    echo '</nmaprun>' >> "$COMBINED_XML_TMP"

    # Move combined tmp to final path (overwrite if exists)
    mv -f "$COMBINED_XML_TMP" "$COMBINED_XML_FINAL"

    # Cleanup chunk files and temp target list
    rm -f "${CHUNK_PREFIX}"*.lst
    sudo rm -f "$WORKING_DIR/nmap_targets.tmp"

    # If final combined file is empty or missing hosts, warn
    if [[ ! -s "$COMBINED_XML_FINAL" ]]; then
        echo -e "${RED}[!] ERROR:${RESET} Combined Nmap XML $COMBINED_XML_FINAL is missing or empty."
        exit 1
    fi

    # Also keep the per-chunk .nmap/.gnmap files (they are left in results/), but remove any zero-length ones
    find "$RESULTS_PATH" -type f -size 0 -name 'nmap_chunk_*' -exec rm -f {} \;

    # Generate HTML reports from the combined Nmap XML
    echo -e "${GREEN}[+] Generating HTML reports from combined Nmap output...${RESET}"
    xsltproc -o "$RESULTS_PATH/nmap-native.html" "$COMBINED_XML_FINAL"
    xsltproc -o "$RESULTS_PATH/nmap-bootstrap.html" "$WORKING_DIR/bootstrap-nmap.xsl" "$COMBINED_XML_FINAL"

    echo -e "${RED}[*] Nmap Done! View the HTML reports at $RESULTS_PATH${RESET}"
}


# ---------------------
# Parse options
# ---------------------
while getopts ":c:x:h" opt; do
  case ${opt} in
    c )
      MASSCAN_CONF="$OPTARG"
      ;;
    x )
      MASSCAN_XML="$OPTARG"
      ;;
    h )
      usage
      ;;
    \? )
      echo -e "${RED}[!] Invalid Option: -$OPTARG${RESET}" 1>&2
      usage
      ;;
    : )
      echo -e "${RED}[!] Invalid Option: -$OPTARG requires an argument${RESET}" 1>&2
      usage
      ;;
  esac
done
shift $((OPTIND -1))

# If an additional positional parameter remains, treat it as TARGET file
if [[ $# -ge 1 ]]; then
    TARGET="$1"
fi

displayLogo
checkArgs
portScan
