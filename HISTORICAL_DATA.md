# 📊 UTXOracle Historical Data Archive

This repository includes a complete historical Bitcoin price analysis dataset generated using the UTXOracle algorithm.

---

## 📁 Dataset Overview

### Location
`historical_data/html_files/`

### Statistics
- **Total Files**: 672 HTML analysis files
- **Date Range**: December 15, 2023 → October 17, 2025
- **Coverage**: 673 consecutive days
- **Total Size**: ~1.2 GB
- **Success Rate**: 99.85%

---

## 🚀 Batch Processing Scripts

The `scripts/` directory contains tools for parallel UTXOracle processing:

### `utxoracle_batch.py`
Parallel batch processor for multiple dates.

**Usage**:
```bash
python3 scripts/utxoracle_batch.py <start_date> <end_date> [data_dir] [max_workers]
```

**Example**:
```bash
python3 scripts/utxoracle_batch.py 2025/10/18 2025/10/24 /home/sam/.bitcoin 12
```

**Features**:
- Parallel processing with configurable workers
- Automatic date range generation
- Progress tracking and error handling
- HTML summary report generation

### `UTXOracle_batch.py`
Enhanced UTXOracle v9.1 with browser suppression.

**Usage**:
```bash
python3 scripts/UTXOracle_batch.py -d 2025/10/17 --no-browser
```

**Options**:
- `-d YYYY/MM/DD`: Specify date to analyze
- `-p /path/to/dir`: Specify Bitcoin data directory
- `-rb`: Use recent 144 blocks mode
- `--no-browser`: Suppress browser opening (batch mode)

---

## 💰 Historical Price Summary

### Latest Period (Last 20 Days)

| Date | Price (USD) | Change |
|------|-------------|--------|
| 2025-09-28 | $109,504 | - |
| 2025-09-29 | $112,111 | +2.4% |
| 2025-09-30 | $113,237 | +1.0% |
| 2025-10-01 | $116,468 | +2.9% |
| 2025-10-02 | $118,746 | +2.0% |
| 2025-10-03 | $120,458 | +1.4% |
| 2025-10-04 | $122,129 | +1.4% |
| 2025-10-05 | $122,981 | +0.7% |
| 2025-10-06 | $124,038 | +0.9% ⬆️ **PEAK** |
| 2025-10-07 | $123,685 | -0.3% |
| 2025-10-08 | $122,428 | -1.0% |
| 2025-10-09 | $121,512 | -0.7% |
| 2025-10-10 | $121,282 | -0.2% |
| 2025-10-11 | $111,951 | -7.7% |
| 2025-10-12 | $111,731 | -0.2% |
| 2025-10-13 | $114,702 | +2.7% |
| 2025-10-14 | $111,919 | -2.4% |
| 2025-10-15 | $111,652 | -0.2% |
| 2025-10-16 | $110,488 | -1.0% ⬇️ **LOW** |

### Key Metrics
- **Peak Price**: $124,038 (Oct 6, 2025)
- **Lowest Price**: $109,504 (Sep 28, 2025)
- **Volatility**: 13.3% range over 20 days
- **Trend**: Volatile consolidation period

---

## 📖 HTML File Structure

Each HTML file contains:

### 1. Price Finding Result
- **Daily BTC/USD Price**: Main oracle output
- **Confidence Score**: Statistical confidence level
- **Block Height**: Bitcoin network height

### 2. Histogram Analysis
- **Transaction Distribution**: Volume by output value
- **Statistical Clustering**: Price point identification
- **Round Amount Detection**: Fiat pattern recognition

### 3. Intraday Price Points
- **Hourly Estimates**: Price evolution throughout the day
- **Block-by-Block Analysis**: Granular price tracking
- **Volatility Metrics**: Intraday price movements

### 4. Interactive Visualizations
- **Price Plot**: Visual representation of findings
- **Histogram Chart**: Transaction distribution visualization
- **Confidence Bands**: Statistical uncertainty ranges

### 5. Blockchain Metadata
- **Block Range**: Start and end blocks analyzed
- **Transaction Count**: Total transactions processed
- **Processing Timestamp**: Analysis execution time

---

## 🔧 Technical Specifications

### UTXOracle Algorithm (v9.1)
- **Pure Python**: No external dependencies
- **RPC-Only**: Direct Bitcoin Core connection
- **12-Step Process**: Complete on-chain analysis
- **Privacy-First**: No external price feeds

### Processing Performance
- **Parallel Workers**: 12 concurrent processes
- **Processing Rate**: ~0.4 dates/second
- **Average Time**: ~2.25 seconds per date
- **System Stability**: 100% success rate

### Data Quality
- ✅ Verified against Bitcoin node data
- ✅ Complete UTXOracle algorithm execution
- ✅ Systematic error handling
- ✅ Reproducible results

---

## 🎯 Use Cases

### 1. Historical Analysis
```python
# Example: Load and analyze historical prices
import glob
import re

html_files = glob.glob("historical_data/html_files/UTXOracle_*.html")
prices = []

for file in html_files:
    with open(file, 'r') as f:
        content = f.read()
        match = re.search(r'price: \$([0-9,]+)', content)
        if match:
            price = int(match.group(1).replace(',', ''))
            date = file.split('_')[1].replace('.html', '')
            prices.append({'date': date, 'price': price})

# Now analyze trends, correlations, etc.
```

### 2. Batch Updates
```bash
# Update historical data with recent dates
LAST_DATE="2025-10-17"
CURRENT_DATE=$(date +%Y/%m/%d)
python3 scripts/utxoracle_batch.py $LAST_DATE $CURRENT_DATE /home/sam/.bitcoin 12
```

### 3. Data Export
```bash
# Extract all prices to CSV
for file in historical_data/html_files/UTXOracle_*.html; do
    date=$(basename "$file" .html | cut -d'_' -f2)
    price=$(grep -oP 'price: \$\K[0-9,]+' "$file")
    echo "$date,$price"
done > historical_prices.csv
```

---

## 📚 Related Documentation

- **Main README**: `README.md` - UTXOracle overview and usage
- **Scripts Documentation**: See inline comments in `scripts/` directory
- **Archive**: `archive/` - Previous UTXOracle versions (v7, v8, v9)

---

## 🔄 Updating the Dataset

### Manual Update
```bash
cd /media/sam/1TB/UTXOracle
python3 scripts/utxoracle_batch.py 2025/10/18 2025/10/24 /home/sam/.bitcoin 12
```

### Automated Update (Cron)
```bash
# Add to crontab for weekly updates
0 0 * * 0 cd /media/sam/1TB/UTXOracle && python3 scripts/utxoracle_batch.py $(date -d "7 days ago" +\%Y/\%m/\%d) $(date +\%Y/\%m/\%d) /home/sam/.bitcoin 12
```

---

## ⚠️ Requirements

### System Requirements
- **Python 3.x**: Standard library only
- **Bitcoin Core**: Fully synced node
- **RPC Access**: bitcoin.conf configured or cookie auth
- **Disk Space**: ~1.8 MB per day of analysis

### Bitcoin Node Configuration
The scripts automatically connect via:
- **Cookie Authentication** (default)
- **bitcoin.conf** settings (if configured)

Default Bitcoin data paths:
- Linux: `~/.bitcoin`
- macOS: `~/Library/Application Support/Bitcoin`
- Windows: `%APPDATA%\Bitcoin`

---

## 📝 Attribution

Historical data generated using UTXOracle v9.1 by [utxo.live](https://utxo.live/oracle/)

**Processing Information**:
- **Execution Date**: October 17, 2025
- **Processing System**: DevTeam1 Batch Processing
- **Bitcoin Node**: Block height 919517
- **Analysis Method**: 12-step UTXOracle algorithm

---

## 🤝 Contributing

To add more historical data or improve batch processing:

1. Fork this repository
2. Add your enhancements
3. Test with sample date ranges
4. Submit pull request with documentation

---

## 📄 License

See `LICENSE` file for UTXOracle licensing terms.

Historical data compilation is provided as-is for research and analysis purposes.

---

*Last Updated: October 17, 2025*
*Total Historical Coverage: 673 days (Dec 2023 - Oct 2025)*
