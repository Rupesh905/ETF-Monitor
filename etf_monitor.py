"""
iShares US Financials ETF (IXG) Holdings Monitor - GitHub Actions Version
Extracts and compares daily holdings data
"""

import requests
import json
from datetime import datetime
import os
from pathlib import Path

class ETFHoldingsMonitor:
    def __init__(self, data_dir="etf_data"):
        self.base_url = "https://www.ishares.com/us/products/239508/ishares-us-financials-etf"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    def get_holdings_data(self):
        """Fetch current holdings data from iShares"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        try:
            # Try to get holdings data - iShares uses dynamic loading
            # We'll try to get the JSON data directly
            holdings_url = f"{self.base_url}/1467271812596.ajax?tab=all&fileType=json"
            
            print(f"Fetching data from iShares...")
            response = requests.get(holdings_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                holdings = data.get('aaData', [])
                
                if holdings:
                    print(f"Successfully fetched {len(holdings)} holdings")
                    return holdings
                else:
                    print("No holdings data found in response")
                    return None
            else:
                print(f"Failed to fetch data. Status code: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    
    def save_holdings(self, holdings):
        """Save holdings data to JSON file"""
        if not holdings:
            return None
            
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = self.data_dir / f"holdings_{date_str}.json"
        
        data = {
            'date': date_str,
            'timestamp': datetime.now().isoformat(),
            'holdings': holdings,
            'total_count': len(holdings)
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved holdings to {filename}")
        return filename
    
    def load_previous_holdings(self):
        """Load most recent previous holdings data"""
        files = sorted(self.data_dir.glob("holdings_*.json"), reverse=True)
        
        if len(files) < 2:
            return None
            
        # Get second most recent file
        prev_file = files[1]
        
        try:
            with open(prev_file, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Error loading previous holdings: {e}")
            return None
    
    def compare_holdings(self, current_holdings, previous_data):
        """Compare current holdings with previous day"""
        if not previous_data:
            return {
                'status': 'first_run',
                'message': 'No previous data to compare',
                'total_holdings': len(current_holdings)
            }
        
        previous_holdings = previous_data.get('holdings', [])
        
        # Extract tickers and weights (assuming first column is ticker, third is weight)
        def extract_info(holdings):
            info = {}
            for h in holdings:
                if len(h) >= 3:
                    ticker = h[0]  # Usually ticker symbol
                    name = h[1] if len(h) > 1 else ""
                    weight = h[2] if len(h) > 2 else "0"
                    info[ticker] = {
                        'name': name,
                        'weight': weight
                    }
            return info
        
        current_info = extract_info(current_holdings)
        previous_info = extract_info(previous_holdings)
        
        current_tickers = set(current_info.keys())
        previous_tickers = set(previous_info.keys())
        
        new_holdings = current_tickers - previous_tickers
        removed_holdings = previous_tickers - current_tickers
        
        # Find weight changes
        weight_changes = []
        for ticker in current_tickers.intersection(previous_tickers):
            curr_weight_str = str(current_info[ticker]['weight']).replace('%', '').strip()
            prev_weight_str = str(previous_info[ticker]['weight']).replace('%', '').strip()
            
            try:
                curr_weight = float(curr_weight_str) if curr_weight_str else 0
                prev_weight = float(prev_weight_str) if prev_weight_str else 0
                
                if abs(curr_weight - prev_weight) > 0.01:
                    weight_changes.append({
                        'ticker': ticker,
                        'name': current_info[ticker]['name'],
                        'previous_weight': prev_weight,
                        'current_weight': curr_weight,
                        'change': curr_weight - prev_weight
                    })
            except (ValueError, TypeError):
                continue
        
        return {
            'status': 'success',
            'date': datetime.now().strftime("%Y-%m-%d"),
            'previous_date': previous_data.get('date', 'Unknown'),
            'total_holdings': len(current_holdings),
            'new_holdings': [{'ticker': t, 'name': current_info[t]['name']} for t in new_holdings],
            'removed_holdings': [{'ticker': t, 'name': previous_info[t]['name']} for t in removed_holdings],
            'weight_changes': sorted(weight_changes, key=lambda x: abs(x['change']), reverse=True),
            'significant_changes': len(new_holdings) + len(removed_holdings) + len(weight_changes)
        }
    
    def generate_report(self, comparison):
        """Generate a readable report of changes"""
        report = []
        report.append("=" * 70)
        report.append("iShares US Financials ETF (IXG) - Daily Holdings Report")
        report.append("=" * 70)
        report.append(f"\nReport Date: {comparison.get('date', 'N/A')}")
        
        if comparison['status'] == 'first_run':
            report.append(f"\nTotal Holdings: {comparison['total_holdings']}")
            report.append("\n⚠️  This is the first data collection.")
            report.append("No historical data available for comparison.")
            report.append("\nStarting tomorrow, you'll see daily changes!")
        else:
            report.append(f"Comparing with: {comparison.get('previous_date', 'N/A')}")
            report.append(f"\nTotal Holdings: {comparison['total_holdings']}")
            report.append(f"Total Changes Detected: {comparison['significant_changes']}")
            
            if comparison['new_holdings']:
                report.append(f"\n{'─' * 70}")
                report.append(f"📈 NEW HOLDINGS ADDED ({len(comparison['new_holdings'])})")
                report.append(f"{'─' * 70}")
                for holding in comparison['new_holdings']:
                    report.append(f"  ✓ {holding['ticker']}")
                    if holding['name']:
                        report.append(f"    {holding['name']}")
            
            if comparison['removed_holdings']:
                report.append(f"\n{'─' * 70}")
                report.append(f"📉 HOLDINGS REMOVED ({len(comparison['removed_holdings'])})")
                report.append(f"{'─' * 70}")
                for holding in comparison['removed_holdings']:
                    report.append(f"  ✗ {holding['ticker']}")
                    if holding['name']:
                        report.append(f"    {holding['name']}")
            
            if comparison['weight_changes']:
                report.append(f"\n{'─' * 70}")
                report.append(f"⚖️  SIGNIFICANT WEIGHT CHANGES (Top 10)")
                report.append(f"{'─' * 70}")
                
                for change in comparison['weight_changes'][:10]:
                    direction = "↑" if change['change'] > 0 else "↓"
                    report.append(f"\n  {direction} {change['ticker']}")
                    if change['name']:
                        report.append(f"    {change['name']}")
                    report.append(f"    {change['previous_weight']:.3f}% → {change['current_weight']:.3f}% "
                                f"({change['change']:+.3f}%)")
                
                if len(comparison['weight_changes']) > 10:
                    report.append(f"\n  ... and {len(comparison['weight_changes']) - 10} more weight changes")
            
            if comparison['significant_changes'] == 0:
                report.append(f"\n{'─' * 70}")
                report.append("✓ No significant changes detected since last update")
                report.append(f"{'─' * 70}")
        
        report.append(f"\n{'=' * 70}")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def run_daily_check(self):
        """Main function to run daily holdings check"""
        print(f"\n{'=' * 70}")
        print(f"Starting ETF Holdings Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 70}\n")
        
        # Fetch current data
        current_holdings = self.get_holdings_data()
        
        if not current_holdings:
            print("\n❌ Failed to fetch holdings data. Please try again later.")
            return None
        
        # Save current data
        self.save_holdings(current_holdings)
        
        # Load previous data
        previous_data = self.load_previous_holdings()
        
        # Compare
        comparison = self.compare_holdings(current_holdings, previous_data)
        
        # Generate and print report
        report = self.generate_report(comparison)
        print(f"\n{report}\n")
        
        # Save report
        date_str = datetime.now().strftime("%Y-%m-%d")
        report_file = self.data_dir / f"report_{date_str}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"📄 Report saved to: {report_file}")
        
        return comparison

def main():
    """Main entry point for GitHub Actions"""
    print("🚀 ETF Holdings Monitor - GitHub Actions Mode")
    print(f"Running in: {os.getcwd()}\n")
    
    monitor = ETFHoldingsMonitor()
    result = monitor.run_daily_check()
    
    if result:
        print("\n✅ Daily check completed successfully!")
    else:
        print("\n⚠️  Daily check completed with warnings")

if __name__ == "__main__":
    main()