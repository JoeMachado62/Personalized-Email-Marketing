#!/bin/bash

echo "=== BATCH PROCESSING MONITOR ==="
echo "Time: $(date)"
echo ""

# Check process
if pgrep -f simple_batch_processor > /dev/null; then
    echo "✓ Batch processor is running"
else
    echo "✗ Batch processor is NOT running"
fi

# Check batches
TOTAL_BATCHES=$(ls uploads/batch_temp/batch_*.csv 2>/dev/null | wc -l)
COMPLETED_BATCHES=$(ls uploads/batch_temp/result_*.csv 2>/dev/null | wc -l)

echo "Batches: $COMPLETED_BATCHES / $TOTAL_BATCHES completed"
echo ""

# Check current enrichment
if pgrep -f enricher_v2 > /dev/null; then
    CURRENT_BATCH=$(ps aux | grep enricher_v2 | grep -v grep | head -1 | grep -oP 'batch_\d+' || echo "unknown")
    echo "Currently processing: $CURRENT_BATCH"
fi

# System resources
echo ""
echo "System Resources:"
echo "Memory: $(free -h | grep Mem | awk '{print $3 " / " $2 " (" int($3/$2 * 100) "%)"}')"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"

# Check output file
if [ -f "a7e98f55_full_enriched.csv" ]; then
    RECORDS=$(wc -l a7e98f55_full_enriched.csv | awk '{print $1-1}')
    echo ""
    echo "Output file has $RECORDS records"
fi

echo ""
echo "Recent activity:"
tail -5 batch_processing.log 2>/dev/null || echo "No log output yet"