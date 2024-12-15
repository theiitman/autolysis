import os
import sys
import subprocess
import re
import pandas as pd
import seaborn as sns
import requests

# Inline script metadata
# requires-python = ">=3.12"
# dependencies = [
#     "chardet",
#     "pandas",
#     "python-dotenv",
#     "requests",
#     "seaborn",
# ]

# AI Proxy URL and token
AIPROXY_URL = "https://aiproxy.sanand.workers.dev/openai/v1/"

# Function to install dependencies from metadata
def install_dependencies():
    """Parse dependencies from script metadata and install them."""
    try:
        script_path = sys.argv[0]
        with open(script_path, "r") as file:
            content = file.read()

        # Extract dependencies
        match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            deps = re.findall(r'"([^"]+)"', match.group(1))  # Extract dependencies within quotes
            if deps:
                print(f"Installing dependencies: {', '.join(deps)}")
                subprocess.check_call([sys.executable, "-m", "pip", "install", *deps])
            else:
                print("No dependencies found to install.")
        else:
            print("No dependencies metadata found in script.")
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)



# Install dependencies
install_dependencies()

# Ensure the script receives a filename
if len(sys.argv) < 2:
    print("Usage: python autolysis.py <filename>")
    sys.exit(1)

# Get the filename from the command-line arguments
file_name = sys.argv[1]

# Check if file exists
if not os.path.exists(file_name):
    print(f"Error: File '{file_name}' not found.")
    sys.exit(1)

# Load the CSV file with a specified encoding to avoid decoding errors
try:
    df = pd.read_csv(file_name, encoding='ISO-8859-1')  # Use a robust encoding
    print("Data loaded successfully!")
except Exception as e:
    print(f"Error loading file: {e}")
    sys.exit(1)

# Summary statistics and missing values
def analyze_data(df):
    summary_stats = df.describe(include="all")
    missing_values = df.isnull().sum()

    # Correlation matrix for numerical columns
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    if len(numeric_cols) > 1:
        corr_matrix = df[numeric_cols].corr()
    else:
        corr_matrix = None

    return summary_stats, missing_values, corr_matrix

summary_stats, missing_values, corr_matrix = analyze_data(df)

# AI Proxy URL for generating insights
def generate_insights(summary_stats, missing_values):
    prompt = f"""
    I have a dataset with the following summary statistics:
    {summary_stats}

    Missing values per column:
    {missing_values}

    Please provide a detailed summary of the dataset, highlighting interesting insights and patterns.
    """
    
    headers = {
        "Authorization": f"Bearer {os.environ.get('AIPROXY_TOKEN')}"  # Use your AIPROXY_TOKEN
    }

    try:
        response = requests.post(
            AIPROXY_URL + "chat/completions",  # Use AI Proxy URL
            headers=headers,
            json={
                "model": "gpt-4o-mini",  # You can change the model if needed
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        response_data = response.json()

        if response.status_code == 200:
            insights = response_data['choices'][0]['message']['content']
            return insights
        else:
            return "Error generating insights."
    
    except Exception as e:
        return f"Error generating insights: {e}"

insights = generate_insights(summary_stats, missing_values)

# Create 1 distribution chart and 1 heatmap chart
def create_charts(df, folder_name):
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    chart_files = []

    # Distribution plot (for the first numeric column)
    if numeric_cols.size > 0:
        col = numeric_cols[0]
        sns.set_theme(style="whitegrid")  # Set a consistent theme
        dist_plot = sns.displot(df, x=col, kde=True, bins=30, height=6, aspect=1.5)
        dist_filename = f"{folder_name}/chart1.png"
        dist_plot.savefig(dist_filename)  # Save the figure directly from Seaborn
        chart_files.append(dist_filename)

    # Correlation heatmap (only if there are multiple numeric columns)
    if len(numeric_cols) > 1:
        corr_matrix = df[numeric_cols].corr()
        sns.set_theme(style="white")
        heatmap_plot = sns.heatmap(
            corr_matrix,
            annot=True,
            cmap="coolwarm",
            fmt=".2f",
            square=True,
            cbar_kws={'shrink': 0.8}
        )
        heatmap_filename = f"{folder_name}/chart2.png"
        heatmap_plot.figure.savefig(heatmap_filename)  # Save the figure from the heatmap
        chart_files.append(heatmap_filename)

    return chart_files

# Create charts and save them to the respective folder
folder_name = file_name.split('.')[0]  # Use the file name (without extension) as the folder name
os.makedirs(folder_name, exist_ok=True)

chart_files = create_charts(df, folder_name)

# Generate README file for the folder
def generate_readme(insights, chart_files, folder_name):
    with open(f"{folder_name}/README.md", "w") as f:
        f.write("# Automated Analysis Results\n\n")
        f.write("## Dataset Insights\n")
        f.write(insights)
        f.write("\n\n## Data Visualizations\n")
        for chart in chart_files:
            f.write(f"![{chart}]({chart})\n")

# Generate the README file
generate_readme(insights, chart_files, folder_name)

print("\nAnalysis complete. Results saved in the respective folder with README.md and visualizations as PNG.")
