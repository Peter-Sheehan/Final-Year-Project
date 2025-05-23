# generate_graphs.py

import matplotlib.pyplot as plt
import numpy as np
import json
from pathlib import Path
import sys
import os # Import os module for creating directories

# --- Configuration ---
LINTER_SUMMARY_FILE_PATH = Path("testing/linter_comparison_summary.json")
OPTIMISATION_SUMMARY_FILE_PATH = Path("testing/optimisation_comparison_summary.json")
GRAPH_OUTPUT_DIR = Path("testing/graphs") # Define output directory for graphs

# --- Ensure Graph Output Directory Exists ---
try:
    os.makedirs(GRAPH_OUTPUT_DIR, exist_ok=True)
    print(f"Ensured graph output directory exists: {GRAPH_OUTPUT_DIR}")
except OSError as e:
    print(f"Error creating directory {GRAPH_OUTPUT_DIR}: {e}", file=sys.stderr)
    sys.exit(1)

# --- Load Data from Linter Comparison Summary ---
linter_data = {}
try:
    with open(LINTER_SUMMARY_FILE_PATH, 'r', encoding='utf-8') as f:
        linter_data = json.load(f)
    print(f"Loaded linter comparison summary from: {LINTER_SUMMARY_FILE_PATH}")
except FileNotFoundError:
    print(f"Error: Linter comparison summary file not found at '{LINTER_SUMMARY_FILE_PATH}'.", file=sys.stderr)
    print("Please run 'evaluate_results.py' first.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error reading linter summary file '{LINTER_SUMMARY_FILE_PATH}': {e}", file=sys.stderr)
    sys.exit(1)

# --- Load Data from Optimization Comparison Summary ---
optimisation_data = {}
try:
    with open(OPTIMISATION_SUMMARY_FILE_PATH, 'r', encoding='utf-8') as f:
        optimisation_data = json.load(f)
    print(f"Loaded optimisation comparison summary from: {OPTIMISATION_SUMMARY_FILE_PATH}")
except FileNotFoundError:
    print(f"Error: Optimisation comparison summary file not found at '{OPTIMISATION_SUMMARY_FILE_PATH}'.", file=sys.stderr)
    print("Please run 'evaluate_results.py' first.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error reading optimisation summary file '{OPTIMISATION_SUMMARY_FILE_PATH}': {e}", file=sys.stderr)
    sys.exit(1)

# --- Load Detailed Evaluation Results ---
DETAILED_RESULTS_FILE_PATH = Path("testing/detailed_evaluation_results.json")
detailed_data = []
try:
    with open(DETAILED_RESULTS_FILE_PATH, 'r', encoding='utf-8') as f:
        detailed_data = json.load(f)
    print(f"Loaded detailed evaluation results from: {DETAILED_RESULTS_FILE_PATH}")
except FileNotFoundError:
    print(f"Error: Detailed results file not found at '{DETAILED_RESULTS_FILE_PATH}'.", file=sys.stderr)
    # Allow script to continue if other graphs can be generated
    detailed_data = [] # Ensure it's an empty list
except Exception as e:
    print(f"Error reading detailed results file '{DETAILED_RESULTS_FILE_PATH}': {e}", file=sys.stderr)
    detailed_data = [] # Ensure it's an empty list

# --- Helper Function for Plotting --- #
def autolabel_float(ax, rects, precision=4):
    """Attach a float text label above each bar."""
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.{precision}f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')

def autolabel_int(ax, rects):
    """Attach an integer text label above each bar."""
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{int(height)}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')

# --- Graph 1: Linter Accuracy Comparison --- #
print("\nGenerating Graph 1: Linter Accuracy Comparison...")
custom_linter_metrics = linter_data.get("custom_linter", {})
hadolint_metrics = linter_data.get("hadolint", {})

linter_metric_labels = ['Precision', 'Recall', 'F1-Score']
custom_linter_scores = [
    custom_linter_metrics.get("precision", 0.0),
    custom_linter_metrics.get("recall", 0.0),
    custom_linter_metrics.get("f1_score", 0.0)
]
hadolint_scores = [
    hadolint_metrics.get("precision", 0.0),
    hadolint_metrics.get("recall", 0.0),
    hadolint_metrics.get("f1_score", 0.0)
]

if any(custom_linter_scores) or any(hadolint_scores):
    x_linter = np.arange(len(linter_metric_labels))
    width = 0.35

    fig_linter, ax_linter = plt.subplots(figsize=(10, 7))
    rects1_linter = ax_linter.bar(x_linter - width/2, custom_linter_scores, width, label='Custom Linter', color='darkorange')
    rects2_linter = ax_linter.bar(x_linter + width/2, hadolint_scores, width, label='Hadolint', color='steelblue')

    # Add labels, title, and ticks
    ax_linter.set_ylabel('Score (0.0 - 1.0)')
    ax_linter.set_title('Linter Accuracy Comparison (on Original Files)')
    ax_linter.set_xticks(x_linter)
    ax_linter.set_xticklabels(linter_metric_labels)
    ax_linter.set_ylim(0, 1.1)
    ax_linter.legend()

    autolabel_float(ax_linter, rects1_linter)
    autolabel_float(ax_linter, rects2_linter)

    fig_linter.tight_layout()

    # Save the linter comparison graph
    linter_graph_filename = GRAPH_OUTPUT_DIR / 'linter_accuracy.png'
    plt.savefig(linter_graph_filename)
    print(f"Saved graph: {linter_graph_filename}")
    plt.close(fig_linter)
else:
    print("Skipping Linter Accuracy graph: No data found.")

# --- Graph 2: Optimisation Effectiveness (Counts) --- #
print("\nGenerating Graph 2: Optimisation Effectiveness (Counts)...")
custom_opt_results = optimisation_data.get("custom_results", {})
baseline_opt_results = optimisation_data.get("baseline_results", {})

opt_count_metrics = ['Resolved Issues', 'Unresolved Issues', 'New Issues Introduced']
custom_opt_counts = [
    custom_opt_results.get("resolved", 0),
    custom_opt_results.get("unresolved", 0),
    custom_opt_results.get("new_introduced", 0)
]
baseline_opt_counts = [
    baseline_opt_results.get("resolved", 0),
    baseline_opt_results.get("unresolved", 0),
    baseline_opt_results.get("new_introduced", 0)
]

if any(custom_opt_counts) or any(baseline_opt_counts):
    x_opt_counts = np.arange(len(opt_count_metrics))
    width = 0.35

    fig_opt_counts, ax_opt_counts = plt.subplots(figsize=(10, 7))
    rects1_opt_counts = ax_opt_counts.bar(x_opt_counts - width/2, custom_opt_counts, width, label='Custom Method', color='coral')
    rects2_opt_counts = ax_opt_counts.bar(x_opt_counts + width/2, baseline_opt_counts, width, label='ChatGPT-4o', color='lightblue')

    # Add labels, title, and ticks
    ax_opt_counts.set_ylabel('Number of Issues')
    ax_opt_counts.set_title('Comparison of Optimisation Effectiveness (Issue Counts)')
    ax_opt_counts.set_xticks(x_opt_counts)
    ax_opt_counts.set_xticklabels(opt_count_metrics)
    max_count = max(max(custom_opt_counts), max(baseline_opt_counts))
    ax_opt_counts.set_ylim(0, max_count * 1.15 if max_count > 0 else 1)
    ax_opt_counts.legend()

    autolabel_int(ax_opt_counts, rects1_opt_counts)
    autolabel_int(ax_opt_counts, rects2_opt_counts)

    fig_opt_counts.tight_layout()

    # Save the optimisation effectiveness counts graph
    opt_counts_graph_filename = GRAPH_OUTPUT_DIR / 'optimisation_effectiveness_counts.png' # Renamed
    plt.savefig(opt_counts_graph_filename)
    print(f"Saved graph: {opt_counts_graph_filename}")
    plt.close(fig_opt_counts)
else:
    print("Skipping Optimisation Effectiveness Counts graph: No data found.")

# --- Graph 3: Optimisation Effectiveness (Metrics) --- #
print("\nGenerating Graph 3: Optimisation Effectiveness (Metrics)...")
opt_metric_labels = ['Recall\n(Resolution Rate)', 'F1-Score']
custom_opt_scores = [
    custom_opt_results.get("recall", 0.0),
    custom_opt_results.get("f1_score", 0.0)
]
baseline_opt_scores = [
    baseline_opt_results.get("recall", 0.0),
    baseline_opt_results.get("f1_score", 0.0)
]

if any(custom_opt_scores) or any(baseline_opt_scores):
    x_opt_scores = np.arange(len(opt_metric_labels))
    width = 0.35

    fig_opt_metrics, ax_opt_metrics = plt.subplots(figsize=(8, 6))
    rects1_opt_metrics = ax_opt_metrics.bar(x_opt_scores - width/2, custom_opt_scores, width, label='Custom Method', color='coral')
    rects2_opt_metrics = ax_opt_metrics.bar(x_opt_scores + width/2, baseline_opt_scores, width, label='ChatGPT-4o', color='lightblue')

    # Add labels, title, and ticks
    ax_opt_metrics.set_ylabel('Score (0.0 - 1.0)')
    ax_opt_metrics.set_title('Comparison of Optimisation Metrics')
    ax_opt_metrics.set_xticks(x_opt_scores)
    ax_opt_metrics.set_xticklabels(opt_metric_labels)
    ax_opt_metrics.set_ylim(0, 1.1)
    ax_opt_metrics.legend()

    autolabel_float(ax_opt_metrics, rects1_opt_metrics)
    autolabel_float(ax_opt_metrics, rects2_opt_metrics)

    # Add definitions below the x-axis
    recall_def = "Recall (Resolution Rate): Percentage of original issues fixed."
    f1_def = "F1-Score: Balances fixing issues (Recall) and avoiding new issues (Precision)."
    plt.figtext(0.5, 0.01, f"{recall_def}\n{f1_def}", wrap=True, horizontalalignment='center', fontsize=9, style='italic')

    fig_opt_metrics.tight_layout(rect=[0, 0.06, 1, 1]) # Adjust layout

    # Save the optimisation effectiveness metrics graph
    opt_metrics_graph_filename = GRAPH_OUTPUT_DIR / 'optimisation_effectiveness_metrics.png' # Renamed
    plt.savefig(opt_metrics_graph_filename)
    print(f"Saved graph: {opt_metrics_graph_filename}")
    plt.close(fig_opt_metrics)
else:
    print("Skipping Optimisation Effectiveness Metrics graph: No data found.")

# --- NEW Graph 4: Analysis Duration vs. Dockerfile Size --- #
print("\nGenerating Graph 4: Analysis Duration vs. Dockerfile Size...")

dockerfile_sizes_kb = []
analysis_durations_sec = []

for item in detailed_data:
    original_info = item.get("original", {})
    original_path_str = original_info.get("path")
    original_analysis = original_info.get("analysis", {})
    build_time = original_analysis.get("build_time") # Using build_time as analysis duration

    if original_path_str and isinstance(build_time, (int, float)):
        original_path = Path(original_path_str)
        if original_path.is_file():
            try:
                file_size_bytes = os.path.getsize(original_path)
                file_size_kb = file_size_bytes / 1024.0
                dockerfile_sizes_kb.append(file_size_kb)
                analysis_durations_sec.append(build_time)
            except OSError as e:
                print(f"Warning: Could not get size for {original_path}: {e}", file=sys.stderr)
        else:
            print(f"Warning: Original path not found or not a file: {original_path}", file=sys.stderr)

if dockerfile_sizes_kb and analysis_durations_sec:
    # Convert lists to numpy arrays for easier handling
    sizes_np = np.array(dockerfile_sizes_kb)
    durations_np = np.array(analysis_durations_sec)

    fig_size_dur, ax_size_dur = plt.subplots(figsize=(10, 7))

    # Create scatter plot
    ax_size_dur.scatter(sizes_np, durations_np, edgecolors='k', alpha=0.75)

    # Calculate line of best fit
    try:
        coeffs = np.polyfit(sizes_np, durations_np, 1) # 1st degree polynomial (linear fit)
        poly = np.poly1d(coeffs)
        line_of_best_fit = poly(np.unique(sizes_np))
        # Plot line of best fit using unique sorted x values for a smooth line
        ax_size_dur.plot(np.unique(sizes_np), line_of_best_fit, color='red', linestyle='--',
                         label=f'Line of Best Fit (y={coeffs[0]:.2f}x+{coeffs[1]:.2f})')
        ax_size_dur.legend() # Show legend only if line of best fit is plotted
    except Exception as e:
        print(f"Warning: Could not calculate or plot line of best fit: {e}", file=sys.stderr)

    # Add labels, title, grid, and set limits
    ax_size_dur.set_xlabel('Dockerfile Size (KB)')
    ax_size_dur.set_ylabel('Analysis Duration (seconds)') # Note: Using build_time here
    ax_size_dur.set_title('Analysis Duration vs. Dockerfile Size')
    ax_size_dur.grid(True, linestyle='--', alpha=0.6)
    ax_size_dur.set_xlim(left=0)
    ax_size_dur.set_ylim(bottom=0)

    fig_size_dur.tight_layout()

    # Save the graph
    size_dur_graph_filename = GRAPH_OUTPUT_DIR / 'analysis_duration_vs_filesize.png'
    plt.savefig(size_dur_graph_filename)
    print(f"Saved graph: {size_dur_graph_filename}")
    plt.close(fig_size_dur)
else:
    print("Skipping Analysis Duration vs. Dockerfile Size graph: No valid data found in detailed results.")

print("\nGraph generation complete.")