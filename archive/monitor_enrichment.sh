#!/bin/bash

# Real-time enrichment monitor
# Run this in a separate terminal to watch enrichment progress

echo "================================================================"
echo "           ENRICHMENT REAL-TIME MONITOR"
echo "================================================================"
echo ""

if [ -z "$1" ]; then
    echo "Monitoring all enrichment activity..."
    echo "Tip: You can also monitor a specific job with: $0 <job_id>"
    echo ""
    tail -f app.log | grep -E --line-buffered "(Enriching record:|Enrichment confidence:|Serper API|search results found|owner found|website found|ERROR|WARNING|Processing batch|Job .* completed)" | while IFS= read -r line
    do
        # Color code the output
        if echo "$line" | grep -q "ERROR"; then
            echo -e "\033[31m$line\033[0m"  # Red for errors
        elif echo "$line" | grep -q "WARNING"; then
            echo -e "\033[33m$line\033[0m"  # Yellow for warnings
        elif echo "$line" | grep -q "Enriching record:"; then
            echo -e "\033[36m$line\033[0m"  # Cyan for new records
        elif echo "$line" | grep -q "confidence:"; then
            confidence=$(echo "$line" | grep -oP '\d+\.\d+%')
            confidence_value=$(echo "$confidence" | sed 's/%//')
            if (( $(echo "$confidence_value > 50" | bc -l) )); then
                echo -e "\033[32m$line\033[0m"  # Green for high confidence
            else
                echo -e "\033[33m$line\033[0m"  # Yellow for low confidence
            fi
        elif echo "$line" | grep -q "completed"; then
            echo -e "\033[32m$line\033[0m"  # Green for completion
        else
            echo "$line"
        fi
    done
else
    JOB_ID=$1
    echo "Monitoring job: $JOB_ID"
    echo ""
    tail -f app.log | grep --line-buffered "$JOB_ID"
fi