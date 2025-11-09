#!/usr/bin/env python3
"""
Data Summarization with Daytona Sandbox
Downloads data from CSV/JSON URLs, analyzes it, generates visualizations,
and displays results in a Flask web app running in a Daytona sandbox
"""

import requests
import json
import os
import re
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional, Tuple
import time
from io import StringIO, BytesIO
import base64
from daytona import Daytona, DaytonaConfig, SessionExecuteRequest

from dotenv import load_dotenv

load_dotenv()

class DataAnalyzer:
    """Main class for data analysis and summarization"""
    
    def __init__(self):
        """Initialize analyzer"""
        self.supported_formats = ['csv', 'json']
        sns.set_style("whitegrid")
    
    def load_data(self, data_input: str) -> Optional[pd.DataFrame]:
        """Load data from URL, local file path, or raw CSV/JSON text"""
        try:
            # First, try to parse as raw CSV/JSON text
            data_input_stripped = data_input.strip()
            
            # Check if it looks like CSV text (has commas and newlines, no http)
            if ',' in data_input_stripped and '\n' in data_input_stripped and not data_input_stripped.startswith('http'):
                try:
                    # Try parsing as CSV
                    df = pd.read_csv(StringIO(data_input_stripped))
                    if df.shape[0] > 0 and df.shape[1] > 1:
                        return df
                except:
                    pass
            
            # Check if it looks like JSON text
            if (data_input_stripped.startswith('{') or data_input_stripped.startswith('[')) and not data_input_stripped.startswith('http'):
                try:
                    data = json.loads(data_input_stripped)
                    if isinstance(data, list):
                        return pd.DataFrame(data)
                    elif isinstance(data, dict):
                        # Try to find a list in the dict
                        for key, value in data.items():
                            if isinstance(value, list):
                                return pd.DataFrame(value)
                        return pd.DataFrame([data])
                except:
                    pass
            
            # Check if it's a local file path
            if os.path.exists(data_input) and os.path.isfile(data_input):
                # Local file
                if data_input.endswith('.csv'):
                    return pd.read_csv(data_input)
                elif data_input.endswith('.json'):
                    with open(data_input, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            return pd.DataFrame(data)
                        elif isinstance(data, dict):
                            # Try to find a list in the dict
                            for key, value in data.items():
                                if isinstance(value, list):
                                    return pd.DataFrame(value)
                            return pd.DataFrame([data])
                        return pd.DataFrame(data)
                else:
                    # Try CSV first
                    try:
                        return pd.read_csv(data_input)
                    except:
                        # Try JSON
                        with open(data_input, 'r') as f:
                            return pd.DataFrame(json.load(f))
            
            # Otherwise, treat as URL
            return self.download_data_from_url(data_input)
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return None
    
    def download_data_from_url(self, url: str) -> Optional[pd.DataFrame]:
        """Download data from URL (CSV or JSON)"""
        try:
            
            # Handle Google Sheets CSV export URL
            if 'docs.google.com' in url and '/spreadsheets/' in url:
                # Extract spreadsheet ID and convert to CSV export format
                if '/export?format=csv' not in url:
                    # Extract spreadsheet ID from various URL formats
                    if '/spreadsheets/d/' in url:
                        parts = url.split('/spreadsheets/d/')[1].split('/')
                        spreadsheet_id = parts[0]
                        # Extract gid if present (for specific sheet tabs)
                        gid = '0'  # Default to first sheet
                        if 'gid=' in url:
                            gid = url.split('gid=')[1].split('&')[0].split('#')[0]
                        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
                    elif '/spreadsheets/' in url:
                        # Try to extract ID from other formats
                        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
                        if match:
                            spreadsheet_id = match.group(1)
                            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid=0"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Determine file type
            content_type = response.headers.get('content-type', '').lower()
            
            if 'csv' in content_type or url.endswith('.csv') or 'format=csv' in url:
                # Read CSV
                df = pd.read_csv(StringIO(response.text))
            elif 'json' in content_type or url.endswith('.json'):
                # Read JSON
                data = response.json()
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                elif isinstance(data, dict):
                    # Try to find a list in the dict
                    for key, value in data.items():
                        if isinstance(value, list):
                            df = pd.DataFrame(value)
                            break
                    else:
                        # Convert dict to DataFrame
                        df = pd.DataFrame([data])
                else:
                    df = pd.DataFrame(data)
            else:
                # Try CSV first, then JSON
                try:
                    df = pd.read_csv(StringIO(response.text))
                except:
                    df = pd.DataFrame(json.loads(response.text))
            
            return df
        except Exception as e:
            print(f"Error downloading data from URL: {str(e)}")
            return None
    
    def download_data(self, url: str) -> Optional[pd.DataFrame]:
        """Download data from URL (CSV or JSON) or local file path - deprecated, use load_data instead"""
        return self.load_data(url)
    
    def analyze_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform comprehensive data analysis"""
        analysis = {
            'shape': df.shape,
            'columns': df.columns.tolist(),
            'dtypes': df.dtypes.to_dict(),
            'summary_stats': {},
            'missing_values': df.isnull().sum().to_dict(),
            'insights': []
        }
        
        # Generate summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            analysis['summary_stats'] = df[numeric_cols].describe().to_dict()
            
            # Calculate additional insights
            for col in numeric_cols:
                col_data = df[col].dropna()
                if len(col_data) > 0:
                    analysis['insights'].append({
                        'column': col,
                        'type': 'numeric',
                        'mean': float(col_data.mean()),
                        'median': float(col_data.median()),
                        'std': float(col_data.std()),
                        'min': float(col_data.min()),
                        'max': float(col_data.max()),
                        'skewness': float(col_data.skew()) if len(col_data) > 2 else 0
                    })
        
        # Analyze categorical columns (skip dict/list columns)
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        for col in categorical_cols:
            try:
                col_data = df[col].dropna()
                if len(col_data) > 0:
                    # Check if column contains dicts or lists (unhashable types)
                    sample_val = col_data.iloc[0] if len(col_data) > 0 else None
                    if isinstance(sample_val, (dict, list)):
                        # Skip dict/list columns - they can't be analyzed with value_counts
                        analysis['insights'].append({
                            'column': col,
                            'type': 'complex',
                            'note': 'Contains nested data (dict/list)',
                            'sample_count': len(col_data)
                        })
                        continue
                    
                    # Try to get unique values count
                    try:
                        unique_count = int(col_data.nunique())
                        value_counts = col_data.value_counts()
                        analysis['insights'].append({
                            'column': col,
                            'type': 'categorical',
                            'unique_values': unique_count,
                            'top_values': {str(k): int(v) for k, v in value_counts.head(5).items()},
                            'most_common': str(value_counts.index[0]) if len(value_counts) > 0 else None
                        })
                    except (TypeError, ValueError) as e:
                        # If we can't hash the values, treat as complex type
                        analysis['insights'].append({
                            'column': col,
                            'type': 'complex',
                            'note': f'Cannot analyze: {str(e)[:50]}',
                            'sample_count': len(col_data)
                        })
            except Exception as e:
                # Skip columns that cause errors
                print(f"Warning: Could not analyze column {col}: {str(e)}")
                continue
        
        # Add overall insights
        total_cells = df.shape[0] * df.shape[1] if df.shape[0] > 0 and df.shape[1] > 0 else 1
        analysis['insights'].append({
            'type': 'overall',
            'total_rows': int(df.shape[0]),
            'total_columns': int(df.shape[1]),
            'total_missing': int(df.isnull().sum().sum()),
            'missing_percentage': float((df.isnull().sum().sum() / total_cells) * 100) if total_cells > 0 else 0
        })
        
        return analysis
    
    def generate_charts(self, df: pd.DataFrame, output_dir: str = "/tmp") -> List[str]:
        """Generate visualization charts"""
        chart_paths = []
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Generate histograms for numeric columns (limit to first 5)
        for i, col in enumerate(numeric_cols[:5]):
            try:
                plt.figure(figsize=(10, 6))
                df[col].dropna().hist(bins=30, edgecolor='black')
                plt.title(f'Distribution of {col}', fontsize=14, fontweight='bold')
                plt.xlabel(col, fontsize=12)
                plt.ylabel('Frequency', fontsize=12)
                plt.tight_layout()
                chart_path = os.path.join(output_dir, f'hist_{i}.png')
                plt.savefig(chart_path, dpi=100, bbox_inches='tight')
                plt.close()
                chart_paths.append(chart_path)
            except Exception as e:
                print(f"Error generating histogram for {col}: {str(e)}")
        
        # Generate bar charts for categorical columns (limit to first 3, skip dict/list columns)
        for i, col in enumerate(categorical_cols[:3]):
            try:
                col_data = df[col].dropna()
                if len(col_data) == 0:
                    continue
                
                # Check if column contains dicts or lists (unhashable types)
                sample_val = col_data.iloc[0] if len(col_data) > 0 else None
                if isinstance(sample_val, (dict, list)):
                    # Skip dict/list columns
                    continue
                
                try:
                    value_counts = df[col].value_counts().head(10)
                    if len(value_counts) > 0:
                        plt.figure(figsize=(10, 6))
                        value_counts.plot(kind='bar', color='steelblue', edgecolor='black')
                        plt.title(f'Top Values in {col}', fontsize=14, fontweight='bold')
                        plt.xlabel(col, fontsize=12)
                        plt.ylabel('Count', fontsize=12)
                        plt.xticks(rotation=45, ha='right')
                        plt.tight_layout()
                        chart_path = os.path.join(output_dir, f'bar_{i}.png')
                        plt.savefig(chart_path, dpi=100, bbox_inches='tight')
                        plt.close()
                        chart_paths.append(chart_path)
                except (TypeError, ValueError) as e:
                    # Skip columns that can't be charted
                    print(f"Warning: Cannot create bar chart for {col}: {str(e)}")
                    continue
            except Exception as e:
                print(f"Error generating bar chart for {col}: {str(e)}")
        
        # Generate correlation heatmap if we have multiple numeric columns
        if len(numeric_cols) >= 2:
            try:
                plt.figure(figsize=(10, 8))
                correlation_matrix = df[numeric_cols].corr()
                sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                           square=True, linewidths=1, cbar_kws={"shrink": 0.8})
                plt.title('Correlation Heatmap', fontsize=14, fontweight='bold')
                plt.tight_layout()
                chart_path = os.path.join(output_dir, 'correlation.png')
                plt.savefig(chart_path, dpi=100, bbox_inches='tight')
                plt.close()
                chart_paths.append(chart_path)
            except Exception as e:
                print(f"Error generating correlation heatmap: {str(e)}")
        
        return chart_paths
    
    def charts_to_base64(self, chart_paths: List[str]) -> List[Dict[str, str]]:
        """Convert chart images to base64 encoded strings"""
        encoded_charts = []
        for chart_path in chart_paths:
            try:
                with open(chart_path, 'rb') as f:
                    chart_data = f.read()
                    base64_data = base64.b64encode(chart_data).decode('utf-8')
                    encoded_charts.append({
                        'name': os.path.basename(chart_path),
                        'data': base64_data,
                        'type': 'image/png'
                    })
            except Exception as e:
                print(f"Error encoding chart {chart_path}: {str(e)}")
        return encoded_charts
    
    def format_analysis_report(self, analysis: Dict[str, Any]) -> str:
        """Format analysis results as HTML report"""
        report = f"""
        <div class="report-section">
            <h2>📊 Data Overview</h2>
            <p><strong>Total Rows:</strong> {analysis['shape'][0]:,}</p>
            <p><strong>Total Columns:</strong> {analysis['shape'][1]}</p>
            <p><strong>Columns:</strong> {', '.join(analysis['columns'])}</p>
        </div>
        
        <div class="report-section">
            <h2>📈 Summary Statistics</h2>
        """
        
        if analysis['summary_stats']:
            report += "<table class='stats-table'><thead><tr><th>Column</th><th>Mean</th><th>Median</th><th>Std Dev</th><th>Min</th><th>Max</th></tr></thead><tbody>"
            for col, stats in analysis['summary_stats'].items():
                if 'mean' in stats:
                    report += f"<tr><td><strong>{col}</strong></td>"
                    report += f"<td>{stats.get('mean', 0):.2f}</td>"
                    report += f"<td>{stats.get('50%', 0):.2f}</td>"
                    report += f"<td>{stats.get('std', 0):.2f}</td>"
                    report += f"<td>{stats.get('min', 0):.2f}</td>"
                    report += f"<td>{stats.get('max', 0):.2f}</td></tr>"
            report += "</tbody></table>"
        else:
            report += "<p>No numeric columns found for statistical analysis.</p>"
        
        report += "</div>"
        
        # Missing values section
        missing_data = {k: v for k, v in analysis['missing_values'].items() if v > 0}
        if missing_data:
            report += """
            <div class="report-section">
                <h2>⚠️ Missing Values</h2>
                <table class="stats-table">
                    <thead><tr><th>Column</th><th>Missing Count</th></tr></thead>
                    <tbody>
            """
            for col, count in missing_data.items():
                report += f"<tr><td><strong>{col}</strong></td><td>{count}</td></tr>"
            report += "</tbody></table></div>"
        
        # Key insights section
        report += """
        <div class="report-section">
            <h2>💡 Key Insights</h2>
            <ul class="insights-list">
        """
        for insight in analysis['insights']:
            if insight.get('type') == 'numeric':
                report += f"<li><strong>{insight['column']}:</strong> Mean = {insight['mean']:.2f}, Median = {insight['median']:.2f}, Range = {insight['min']:.2f} to {insight['max']:.2f}</li>"
            elif insight.get('type') == 'categorical':
                report += f"<li><strong>{insight['column']}:</strong> {insight['unique_values']} unique values. Most common: {insight['most_common']}</li>"
            elif insight.get('type') == 'complex':
                report += f"<li><strong>{insight['column']}:</strong> {insight.get('note', 'Complex data type')} ({insight.get('sample_count', 0)} samples)</li>"
            elif insight.get('type') == 'overall':
                report += f"<li><strong>Dataset:</strong> {insight['total_rows']:,} rows × {insight['total_columns']} columns. Missing data: {insight['missing_percentage']:.2f}%</li>"
        report += "</ul></div>"
        
        return report


def create_flask_app(analysis: Dict[str, Any], charts_base64: List[Dict[str, str]], data_url: str) -> str:
    """Create Flask web app code with analysis results and charts"""
    analyzer = DataAnalyzer()
    report_html = analyzer.format_analysis_report(analysis)
    
    charts_html = ""
    for i, chart in enumerate(charts_base64):
        chart_name = chart['name'].replace('_', ' ').replace('.png', '').title()
        chart_data = chart['data']
        charts_html += f"""
        <div class="chart-container">
            <h3>Chart {i+1}: {chart_name}</h3>
            <img src="data:image/png;base64,{chart_data}" alt="{chart['name']}" class="chart-image">
        </div>
        """
    
    # Format data source display
    if data_url.startswith('http'):
        data_source_display = f'<a href="{data_url}" target="_blank">{data_url}</a>'
    else:
        # Truncate long data previews
        preview = data_url[:100] + "..." if len(data_url) > 100 else data_url
        # Escape HTML special characters
        preview = preview.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        data_source_display = f'<span style="font-family: monospace; font-size: 0.9em;">{preview}</span>'
    
    # Use repr() to properly escape strings for Python code
    report_html_escaped = repr(report_html)
    charts_html_escaped = repr(charts_html)
    data_source_display_escaped = repr(data_source_display)  
    
    # Build the complete HTML by directly concatenating
    complete_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Analysis Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 20px;
        }
        .header-content {
            flex: 1;
        }
        .header h1 {
            font-size: 2.8em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
            font-weight: 700;
        }
        .header p {
            color: #666;
            font-size: 1.1em;
            margin: 0;
        }
        .logo-container {
            display: flex;
            gap: 20px;
            align-items: center;
            flex-wrap: wrap;
        }
        .logo {
            height: 60px;
            width: auto;
            object-fit: contain;
        }
        .data-source {
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 5px solid #2196f3;
        }
        .data-source strong {
            color: #1976d2;
            font-size: 1.1em;
        }
        .report-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .report-section:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .report-section h2 {
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 20px;
            margin-top: 0;
            font-size: 1.8em;
            font-weight: 600;
        }
        .stats-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            overflow-x: auto;
            display: block;
        }
        .stats-table thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .stats-table th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 1em;
        }
        .stats-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }
        .stats-table tbody tr {
            transition: background-color 0.2s;
        }
        .stats-table tbody tr:hover {
            background-color: #f5f7fa;
        }
        .insights-list {
            list-style-type: none;
            padding: 0;
        }
        .insights-list li {
            padding: 15px;
            margin: 12px 0;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-left: 5px solid #667eea;
            border-radius: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .insights-list li:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin: 25px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .chart-container:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.15);
        }
        .chart-container h3 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.4em;
            font-weight: 600;
        }
        .chart-image {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-top: 15px;
            transition: transform 0.3s;
        }
        .chart-image:hover {
            transform: scale(1.02);
        }
        .footer {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-top: 30px;
            text-align: center;
            color: #666;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .footer p {
            margin: 10px 0;
            font-size: 0.95em;
        }
        @media (max-width: 768px) {
            .header {
                flex-direction: column;
                text-align: center;
            }
            .header h1 {
                font-size: 2em;
            }
            .logo-container {
                justify-content: center;
            }
            .stats-table {
                font-size: 0.9em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-content">
                <h1>Data Analysis Report</h1>
                <p>AI-Powered Data Summarization Assistant</p>
            </div>
        </div>
        
        <div class="data-source">
            <strong>📎 Data Source:</strong> ''' + data_source_display + '''
        </div>
        
        ''' + report_html + '''
        
        <div class="report-section">
            <h2>📈 Visualizations</h2>
            ''' + charts_html + '''
        </div>
        
        <div class="footer">
            <p>Generated by <strong>Daytona Data Summarization Assistant</strong></p>
            <p>Powered by <strong>Daytona</strong> & <strong>Fetch.ai</strong></p>
        </div>
    </div>
</body>
</html>'''
    
    # Escape the complete HTML for embedding in Python string
    complete_html_escaped = repr(complete_html)
    
    flask_code = f'''from flask import Flask
import os

app = Flask(__name__)

@app.route('/callback')
def callback():
    return "ok", 200

@app.route('/healthz')
def healthz():
    return "ok", 200

@app.route('/')
def analysis():
    html_content = {complete_html_escaped}
    return html_content

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '3000'))
    app.run(host='0.0.0.0', port=port)
'''
    return flask_code


def run_data_analysis_sandbox(data_url: str) -> Tuple[Any, Optional[str]]:
    """Run data analysis in Daytona sandbox with web preview
    
    Args:
        data_url: URL to CSV/JSON data file or Google Sheets, or raw CSV/JSON text
    
    Returns:
        Tuple of (sandbox, preview_url) or (None, None) on error
    """
    
    # Initialize Daytona
    daytona_api_key = os.getenv('DAYTONA_API_KEY')
    if not daytona_api_key:
        print("Error: DAYTONA_API_KEY environment variable not set")
        return None, None
    
    daytona = Daytona(DaytonaConfig(api_key=daytona_api_key))
    
    # Create sandbox
    print("Creating Daytona sandbox...")
    sandbox = daytona.create()
    
    try:
        # Load and analyze data
        data_preview = data_url[:100] + "..." if len(data_url) > 100 else data_url
        print(f"Loading data: {data_preview}")
        analyzer = DataAnalyzer()
        df = analyzer.load_data(data_url)
        
        if df is None or df.empty:
            print("Error: Could not load or data is empty")
            sandbox.delete()
            return None, None
        
        print(f"Data loaded successfully! Shape: {df.shape}")
        
        # Analyze data
        print("Analyzing data...")
        analysis = analyzer.analyze_data(df)
        print("Analysis complete!")
        
        # Generate charts
        print("Generating visualizations...")
        chart_paths = analyzer.generate_charts(df, output_dir="/tmp/charts")
        print(f"Generated {len(chart_paths)} charts")
        
        # Convert charts to base64
        charts_base64 = analyzer.charts_to_base64(chart_paths)
        
        # Create Flask app with results
        flask_code = create_flask_app(analysis, charts_base64, data_url)
        
        # Upload Flask app to sandbox
        print("Uploading Flask app to sandbox...")
        sandbox.fs.upload_file(flask_code.encode(), "app.py")
        
        # Upload chart images to sandbox (for reference, though we use base64 in HTML)
        for chart_path in chart_paths:
            try:
                with open(chart_path, 'rb') as f:
                    chart_data = f.read()
                    chart_name = os.path.basename(chart_path)
                    sandbox.fs.upload_file(chart_data, f"static/{chart_name}")
            except Exception as e:
                print(f"Warning: Could not upload chart {chart_path}: {str(e)}")
        
        # Create session and run Flask app
        print("Starting Flask app in sandbox...")
        exec_session_id = "data-analysis-session"
        sandbox.process.create_session(exec_session_id)
        
        # Install required packages
        install_cmds = [
            "python3 -m pip install --no-cache-dir flask pandas matplotlib seaborn requests",
            "python -m pip install --no-cache-dir flask pandas matplotlib seaborn requests",
            "pip3 install --no-cache-dir flask pandas matplotlib seaborn requests",
            "pip install --no-cache-dir flask pandas matplotlib seaborn requests",
        ]
        for cmd in install_cmds:
            try:
                resp = sandbox.process.execute_session_command(
                    exec_session_id,
                    SessionExecuteRequest(
                        command=cmd,
                        run_async=False
                    )
                )
                break
            except Exception:
                continue
        
        # Start Flask app inside the session
        sandbox.process.execute_session_command(
            exec_session_id,
            SessionExecuteRequest(
                command="python3 app.py || python app.py",
                run_async=True
            )
        )
        
        # Get preview link
        preview_info = sandbox.get_preview_link(3000)
        terminal_info = None
        try:
            terminal_info = sandbox.get_preview_link(22222)
        except Exception:
            pass
        
        # Wait until the app is reachable
        url = preview_info.url
        health_url = url.rstrip('/') + '/callback'
        ready = False
        for _ in range(45):  # ~45s
            try:
                r = requests.get(health_url, timeout=2)
                if r.status_code == 200:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(1)
        
        print(f"\n✅ Data analysis app is running!")
        print(f"Preview URL: {url}")
        if terminal_info:
            print(f"Terminal URL: {terminal_info.url}")
        print(f"Sandbox ID: {sandbox.id}")
        if not ready:
            print("Note: App is starting up; if you see 502, wait a few seconds and refresh.")
        
        return sandbox, url
    
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        sandbox.delete()
        return None, None


def main():
    """Main entry point"""
    print("=" * 60)
    print("Data Summarization Assistant")
    print("=" * 60)
    data_url = input("Enter data URL (CSV or JSON, Google Sheets supported): ").strip()
    
    if data_url:
        sandbox, preview_url = run_data_analysis_sandbox(data_url)
        if sandbox:
            print("\nSandbox is running. Press Ctrl+C to stop and clean up.")
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nCleaning up sandbox...")
                sandbox.delete()
                print("Done!")
    else:
        print("Please enter a valid data URL.")


if __name__ == "__main__":
    main()

