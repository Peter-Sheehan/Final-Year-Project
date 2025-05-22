# evaluate_results.py

import os
import json # Needed for Hadolint output and saving summaries
import csv
import subprocess # Needed for Hadolint
from pathlib import Path
from collections import defaultdict
import sys

# Attempt to import the custom linter
try:
    # Assuming dockerfile_linter.py is in the parent directory relative to 'testing'
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dockerfile_linter import DockerfileLinter, LinterIssue
    LINTER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import DockerfileLinter. Linter evaluation will be skipped. Error: {e}", file=sys.stderr)
    LINTER_AVAILABLE = False
except Exception as e:
    print(f"Warning: An unexpected error occurred during linter import. Linter evaluation will be skipped. Error: {e}", file=sys.stderr)
    LINTER_AVAILABLE = False

# --- Configuration ---
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
ANNOTATIONS_FILE = WORKSPACE_ROOT / "testing" / "Dockerfiles_set" / "benchmark_annotations.csv"
BENCHMARK_DIR = WORKSPACE_ROOT / "testing" / "Dockerfiles_set" # Need directory of original files for Hadolint
RULES_FILE = WORKSPACE_ROOT / "Rules" / "rules.json"
OPTIMIZED_OUTPUT_DIR = WORKSPACE_ROOT / "testing" / "output" # Directory containing optimized files

# Naming conventions for optimized files
CUSTOM_OPTIMIZED_PREFIX = "optimised-"
BASELINE_OPTIMIZED_PREFIX = "example1_baseline_"

# --- Rule Mapping (Hadolint Code -> Annotation Title) ---
# Re-introduce mapping for Hadolint comparison
HADOLINT_MAP = {
    "DL3000": "Use absolute path for WORKDIR", # Example, adjust as needed
    "DL3001": "For some bash commands it's better to write them in a script and use COPY/ADD",
    "DL3002": "Prevent running as root user",
    "DL3003": "Use WORKDIR instead of RUN cd",
    "DL3006": "Use COPY instead of ADD",
    "DL3007": "Avoid using latest tag",
    "DL3008": "Pin versions in apt get install", # General rule
    "DL3009": "Delete the apt-get lists after installing packages",
    "DL3010": "Use ADD for remote URLs", # Specific to ADD url
    "DL3013": "Pin versions in pip install", # General rule
    "DL3015": "Avoid apt-get upgrade or dist-upgrade",
    "DL3016": "Pin versions in npm install", # General rule
    "DL3018": "Pin versions in apk add", # General rule
    "DL3019": "Use the --no-cache option with apk add",
    "DL3028": "Pin versions in gem install", # General rule
    "DL3042": "Avoid use of cache directory with pip", # Relates to --no-cache-dir
    "DL3059": "Combine multiple RUN commands",
    "DL4000": "MAINTAINER is deprecated",
    "DL4001": "Either use Wget or Curl but not both",
    "DL4006": "Set the SHELL option",
    "SC1091": "Not following: File not found", # ShellCheck issues
    "SC2155": "Declare and assign separately to avoid masking return values",
    # Add mappings for other rules found in your annotations or Hadolint output
    # Custom rules added based on previous annotations:
    "Custom::AvoidUpdateAlone": "Avoid apt-get update alone",
    "Custom::NoInstallRecommends": "Use apt-get install --no-install-recommends",
    "Custom::CombineRun": "Combine multiple RUN commands", # Map generic combine
    "Custom::UnnecessaryPackages": "Avoid installing unnecessary packages",
    "Custom::AddLocal": "Use COPY instead of ADD", # Map specifically for local ADD
    "Custom::EmptyEnv": "Ensure ENV is not empty",
    "Custom::SingleProcess": "Run one process per container",
    "Custom::CleanApkCache": "Clean apk cache",
    "Custom::CleanNpmCache": "Clean npm cache",
    "Custom::AptPinningRisk": "Avoid pinning versions on latest tag"
}

# --- Helper Functions ---

def load_annotations(filepath: Path) -> dict[str, set[tuple[int, str]]]:
    """Loads annotations from CSV into a dictionary mapping filename to a set of (line, rule_title) tuples."""
    annotations = defaultdict(set)
    try:
        with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
            # Skip empty lines or lines starting with '#' (comments)
            filtered_lines = (line for line in csvfile if line.strip() and not line.strip().startswith('#'))
            reader = csv.DictReader(filtered_lines)
            if not reader.fieldnames or not all(f in reader.fieldnames for f in ['Filename', 'LineNumber', 'RuleTitle']):
                 print(f"Error: Annotation file {filepath} is missing required headers (Filename, LineNumber, RuleTitle).", file=sys.stderr)
                 sys.exit(1)

            for i, row in enumerate(reader):
                try:
                    # Use the base name of the file as the key
                    base_filename = Path(row['Filename']).name
                    # Ensure LineNumber is treated carefully
                    line_num_str = row['LineNumber']
                    if not line_num_str or not line_num_str.isdigit():
                         print(f"Warning: Skipping invalid LineNumber '{line_num_str}' in annotations row {i+2}: {row}", file=sys.stderr)
                         continue
                    line_num = int(line_num_str)

                    rule_title = row['RuleTitle']
                    if not rule_title:
                        print(f"Warning: Skipping missing RuleTitle in annotations row {i+2}: {row}", file=sys.stderr)
                        continue

                    annotations[base_filename].add((line_num, rule_title.strip()))

                except KeyError as e:
                    print(f"Warning: Skipping row {i+2} due to missing key {e} in annotations file: {row}", file=sys.stderr)
                except Exception as e: # Catch other potential issues like unexpected file content
                     print(f"Warning: Skipping row {i+2} due to unexpected error '{e}' in annotations file: {row}", file=sys.stderr)


    except FileNotFoundError:
        print(f"Error: Annotations file not found at {filepath}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading annotations file {filepath}: {e}", file=sys.stderr)
        sys.exit(1)
    # Filter out entries with rule title "No Issues Expected"
    cleaned_annotations = {}
    for fname, issues in annotations.items():
        filtered_issues = {issue for issue in issues if issue[1] != "No Issues Expected"}
        if filtered_issues: # Only add if there are actual issues annotated
            cleaned_annotations[fname] = filtered_issues
    return cleaned_annotations

def calculate_metrics(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Calculates Precision, Recall, and F1-Score."""
    # Precision: How many of the issues *found* (or implied by TP+FP) were correctly identified/resolved?
    # In our case, TP = Resolved Issues, FP = New Issues. Precision = TP / (TP + FP_new)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    # Recall (Resolution Rate): How many of the *original* issues were resolved?
    # TP = Resolved Issues, FN = Unresolved Issues. Recall = TP / (TP + FN)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    # F1 Score: Harmonic mean, balancing resolution rate and avoidance of new issues.
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def run_linter_on_file(linter: DockerfileLinter, filepath: Path) -> set[tuple[int, str]]:
    """Runs the linter on a file and returns a set of found issues (line, title)."""
    found_issues = set()
    if not filepath or not filepath.is_file():
        print(f"    Error: Linter input file not found or invalid: {filepath}", file=sys.stderr)
        return found_issues # Return empty set if file doesn't exist

    try:
        linter_issues: list[LinterIssue] = linter.lint_file(str(filepath))
        for issue in linter_issues:
            try:
                # Use validated line number and rule title
                if isinstance(issue.line_number, int) and issue.rule and issue.rule.title:
                     found_issues.add((issue.line_number, issue.rule.title.strip()))
                else:
                     print(f"    Warning: Skipping malformed linter issue object for {filepath.name}: {issue}", file=sys.stderr)
            except AttributeError:
                 print(f"    Warning: Skipping malformed linter issue object (missing attributes) for {filepath.name}: {issue}", file=sys.stderr)
    except Exception as e:
        print(f"    Error running linter on {filepath}: {e}", file=sys.stderr)
        # Cannot determine issues if linter fails
    return found_issues

def run_hadolint(filepath: Path) -> set[tuple[int, str]]:
    """Runs Hadolint on a file and returns a mapped set of issues (line, mapped_title)."""
    hadolint_issues_mapped = set()
    if not filepath or not filepath.is_file():
        print(f"    Error: Hadolint input file not found or invalid: {filepath}", file=sys.stderr)
        return hadolint_issues_mapped

    try:
        # Use --no-fail to ensure JSON output even if violations are found
        result = subprocess.run(["hadolint", "--no-fail", "-f", "json", str(filepath)], capture_output=True, text=True, check=False)
        if result.returncode != 0 and result.stderr:
             # Hadolint might output warnings/errors to stderr even with --no-fail
             print(f"    Warning/Error running Hadolint on {filepath}: {result.stderr.strip()}", file=sys.stderr)

        # Process stdout even if return code != 0, as violations might be there
        if result.stdout:
            try:
                issues = json.loads(result.stdout)
                comparable_annotation_titles = set(HADOLINT_MAP.values())
                for issue in issues:
                    rule_code = issue.get('code')
                    line_num = issue.get('line')
                    if rule_code in HADOLINT_MAP and isinstance(line_num, int):
                        mapped_title = HADOLINT_MAP[rule_code]
                        hadolint_issues_mapped.add((line_num, mapped_title))
                    # else:
                        # Optional: print unmapped Hadolint issues
                        # print(f"    Debug Hadolint Unmapped: {filepath.name} - Code: {rule_code}, Line: {line_num}, Level: {issue.get('level')}, Message: {issue.get('message')}")
            except json.JSONDecodeError:
                print(f"    Error: Could not decode Hadolint JSON output for {filepath}: {result.stdout}", file=sys.stderr)
        # else:
        #     print(f"    Debug Hadolint: No stdout received for {filepath.name}. Return code: {result.returncode}")

    except FileNotFoundError:
        print("Error: 'hadolint' command not found. Please ensure Hadolint is installed and in your PATH.", file=sys.stderr)
        # Optionally exit or return empty set depending on desired behavior
        # sys.exit(1)
    except Exception as e:
        print(f"    Error running Hadolint process on {filepath}: {e}", file=sys.stderr)
    return hadolint_issues_mapped

# --- Main Evaluation Logic ---

print("Starting Combined Evaluation...")
print(f"1. Linter Accuracy (Custom vs Hadolint on Originals vs Annotations: {ANNOTATIONS_FILE})")
print(f"2. Optimization Effectiveness (Custom vs Baseline on Optimized vs Annotations: {ANNOTATIONS_FILE})")
print(f"Original files expected in: {BENCHMARK_DIR}")
print(f"Optimized files expected in: {OPTIMIZED_OUTPUT_DIR}")

# 0. Check if Linter is available and rules file exists
if not LINTER_AVAILABLE:
    print("DockerfileLinter could not be imported. Cannot perform evaluation.")
    sys.exit(1)

if not RULES_FILE.is_file():
    print(f"Error: Linter rules file not found at {RULES_FILE}")
    sys.exit(1)

# 1. Load Ground Truth Annotations (Original Issues)
ground_truth_annotations = load_annotations(ANNOTATIONS_FILE)
if not ground_truth_annotations:
    print("No valid annotations with actual issues loaded. Exiting.")
    sys.exit(1)

print(f"Loaded annotations for {len(ground_truth_annotations)} files from {ANNOTATIONS_FILE}")

# 2. Initialise Metrics Accumulators
# Linter Accuracy (on Originals)
custom_linter_tp, custom_linter_fp, custom_linter_fn = 0, 0, 0
hadolint_tp, hadolint_fp, hadolint_fn = 0, 0, 0
# Optimization Effectiveness (on Optimized files vs Original Annotations)
# TP = Resolved, FN = Unresolved, FP = New Issues Introduced
custom_opt_tp, custom_opt_fp, custom_opt_fn = 0, 0, 0
baseline_opt_tp, baseline_opt_fp, baseline_opt_fn = 0, 0, 0

# 3. Instantiate the Custom Linter
try:
    linter = DockerfileLinter(rules_path=str(RULES_FILE))
    print(f"DockerfileLinter initialized with rules from {RULES_FILE}")
except Exception as e:
    print(f"Error initializing DockerfileLinter: {e}")
    sys.exit(1)

# 4. Process Each Annotated Original File
files_processed_count = 0
comparable_files_count = 0 # Count files where both optimized versions were found
benchmark_filenames = list(ground_truth_annotations.keys())

for original_filename_base in benchmark_filenames:
    original_stem = Path(original_filename_base).stem
    annotation_set = ground_truth_annotations[original_filename_base]
    original_dockerfile_path = BENCHMARK_DIR / original_filename_base

    if not annotation_set:
        print(f"\nSkipping {original_filename_base}: No specific issues annotated.")
        continue
    if not original_dockerfile_path.is_file():
        print(f"\nWarning: Skipping {original_filename_base} - Original Dockerfile not found at {original_dockerfile_path}", file=sys.stderr)
        continue

    print(f"\nProcessing Original: {original_filename_base} (Issues annotated: {len(annotation_set)})")
    files_processed_count += 1

    # --- Linter Accuracy Evaluation (on Original File) ---
    print("  Evaluating Linters on Original File...")
    # Custom Linter on Original
    issues_custom_linter = run_linter_on_file(linter, original_dockerfile_path)
    tp_cl = len(issues_custom_linter.intersection(annotation_set))
    fp_cl = len(issues_custom_linter.difference(annotation_set))
    fn_cl = len(annotation_set.difference(issues_custom_linter))
    custom_linter_tp += tp_cl
    custom_linter_fp += fp_cl
    custom_linter_fn += fn_cl
    print(f"    Custom Linter Results: TP={tp_cl}, FP={fp_cl}, FN={fn_cl}")

    # Hadolint on Original
    issues_hadolint_mapped = run_hadolint(original_dockerfile_path)
    # Compare only against annotations that Hadolint *could* map to
    comparable_annotation_titles_for_hadolint = set(HADOLINT_MAP.values())
    annotation_set_comparable_hadolint = {(line, title) for line, title in annotation_set if title in comparable_annotation_titles_for_hadolint}

    if annotation_set_comparable_hadolint: # Only calculate if there are relevant annotations
        tp_h = len(issues_hadolint_mapped.intersection(annotation_set_comparable_hadolint))
        fp_h = len(issues_hadolint_mapped.difference(annotation_set_comparable_hadolint))
        fn_h = len(annotation_set_comparable_hadolint.difference(issues_hadolint_mapped))
        hadolint_tp += tp_h
        hadolint_fp += fp_h
        hadolint_fn += fn_h
        print(f"    Hadolint Results (Comparable): TP={tp_h}, FP={fp_h}, FN={fn_h}")
    else:
        print(f"    Hadolint Results (Comparable): Skipping (No comparable annotations for this file)")

    # --- Optimization Effectiveness Evaluation --- #
    # Find corresponding optimized files
    # ... (File finding logic remains the same, including debug prints)
    custom_opt_path_v1 = OPTIMIZED_OUTPUT_DIR / f"{CUSTOM_OPTIMIZED_PREFIX}{original_stem}.dockerfile"
    custom_opt_path_v2 = OPTIMIZED_OUTPUT_DIR / f"{CUSTOM_OPTIMIZED_PREFIX}{original_stem}.Dockerfile" # Handle capitalization
    baseline_opt_path_v1 = OPTIMIZED_OUTPUT_DIR / f"{BASELINE_OPTIMIZED_PREFIX}{original_stem}.dockerfile"
    baseline_opt_path_v2 = OPTIMIZED_OUTPUT_DIR / f"{BASELINE_OPTIMIZED_PREFIX}{original_stem}.Dockerfile"

    custom_optimized_file = None
    # print(f"  Checking Custom Path 1: {custom_opt_path_v1} (Exists: {custom_opt_path_v1.is_file()})") # DEBUG REMOVED
    if custom_opt_path_v1.is_file():
        custom_optimized_file = custom_opt_path_v1
    elif custom_opt_path_v2:
        # print(f"  Checking Custom Path 2: {custom_opt_path_v2} (Exists: {custom_opt_path_v2.is_file()})") # DEBUG REMOVED
        if custom_opt_path_v2.is_file():
            custom_optimized_file = custom_opt_path_v2

    baseline_optimized_file = None
    # print(f"  Checking Baseline Path 1: {baseline_opt_path_v1} (Exists: {baseline_opt_path_v1.is_file()})") # DEBUG REMOVED
    if baseline_opt_path_v1.is_file():
        baseline_optimized_file = baseline_opt_path_v1
    elif baseline_opt_path_v2:
        # print(f"  Checking Baseline Path 2: {baseline_opt_path_v2} (Exists: {baseline_opt_path_v2.is_file()})") # DEBUG REMOVED
        if baseline_opt_path_v2.is_file():
            baseline_optimized_file = baseline_opt_path_v2

    # If both optimized files found, proceed with effectiveness comparison
    if custom_optimized_file and baseline_optimized_file:
        comparable_files_count += 1
        print(f"  Found Optimized Files: Custom='{custom_optimized_file.name}', Baseline='{baseline_optimized_file.name}'")
        print("  Evaluating Optimization Effectiveness...")

        # Evaluate Custom Optimized File vs Original Annotations
        issues_found_custom_opt = run_linter_on_file(linter, custom_optimized_file)
        resolved_custom = annotation_set.difference(issues_found_custom_opt)
        unresolved_custom = annotation_set.intersection(issues_found_custom_opt)
        new_issues_custom = issues_found_custom_opt.difference(annotation_set)
        tp_c_opt = len(resolved_custom)
        fn_c_opt = len(unresolved_custom)
        fp_c_opt = len(new_issues_custom)
        custom_opt_tp += tp_c_opt
        custom_opt_fn += fn_c_opt
        custom_opt_fp += fp_c_opt
        print(f"    Custom Opt. Results: Resolved={tp_c_opt}, Unresolved={fn_c_opt}, New Issues={fp_c_opt}")

        # Evaluate Baseline Optimized File vs Original Annotations
        issues_found_baseline_opt = run_linter_on_file(linter, baseline_optimized_file)
        resolved_baseline = annotation_set.difference(issues_found_baseline_opt)
        unresolved_baseline = annotation_set.intersection(issues_found_baseline_opt)
        new_issues_baseline = issues_found_baseline_opt.difference(annotation_set)
        tp_b_opt = len(resolved_baseline)
        fn_b_opt = len(unresolved_baseline)
        fp_b_opt = len(new_issues_baseline)
        baseline_opt_tp += tp_b_opt
        baseline_opt_fn += fn_b_opt
        baseline_opt_fp += fp_b_opt
        print(f"    Baseline Opt. Results: Resolved={tp_b_opt}, Unresolved={fn_b_opt}, New Issues={fp_b_opt}")

    else:
        print("  Warning: Skipping Optimization Effectiveness comparison for this file (missing one or both optimized versions).", file=sys.stderr)


# 5. Calculate and Report Overall Metrics
print("\n--- Overall Results ---")

# Linter Accuracy Results
print("\nPart 1: Linter Accuracy Comparison (on Original Files)")
print(f"Files Processed: {files_processed_count}")
print("\n{:<15} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10}".format(
    "Linter", "TP", "FP", "FN", "Precision", "Recall", "F1-Score"
))
print("-"*85)
# Custom Linter Accuracy
if (custom_linter_tp + custom_linter_fn) > 0: # Avoid division by zero if no relevant issues
    precision_cl, recall_cl, f1_cl = calculate_metrics(custom_linter_tp, custom_linter_fp, custom_linter_fn)
    print("{:<15} | {:<10} | {:<10} | {:<10} | {:<10.4f} | {:<10.4f} | {:<10.4f}".format(
        "Custom", custom_linter_tp, custom_linter_fp, custom_linter_fn, precision_cl, recall_cl, f1_cl
    ))
else:
    print("{:<15} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10}".format("Custom", custom_linter_tp, custom_linter_fp, custom_linter_fn, "N/A", "N/A", "N/A"))

# Hadolint Accuracy
if (hadolint_tp + hadolint_fn) > 0:
    precision_h, recall_h, f1_h = calculate_metrics(hadolint_tp, hadolint_fp, hadolint_fn)
    print("{:<15} | {:<10} | {:<10} | {:<10} | {:<10.4f} | {:<10.4f} | {:<10.4f}".format(
        "Hadolint", hadolint_tp, hadolint_fp, hadolint_fn, precision_h, recall_h, f1_h
    ))
else:
     print("{:<15} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10}".format("Hadolint", hadolint_tp, hadolint_fp, hadolint_fn, "N/A", "N/A", "N/A"))

# Optimization Effectiveness Results
print("\nPart 2: Optimization Effectiveness Comparison (on Optimized Files vs Original Annotations)")
if comparable_files_count > 0:
    # Calculate metrics for Custom Opt method
    precision_c_opt, recall_c_opt, f1_c_opt = calculate_metrics(custom_opt_tp, custom_opt_fp, custom_opt_fn)
    total_original_issues_opt = custom_opt_tp + custom_opt_fn

    # Calculate metrics for Baseline Opt method
    precision_b_opt, recall_b_opt, f1_b_opt = calculate_metrics(baseline_opt_tp, baseline_opt_fp, baseline_opt_fn)
    # Sanity check:
    if total_original_issues_opt != (baseline_opt_tp + baseline_opt_fn):
         print("\nWarning: Mismatch in total original issues counted for optimization comparison. Check logs.")

    print(f"Files Compared: {comparable_files_count}")
    print(f"Total Original Issues Annotated (across compared files): {total_original_issues_opt}")
    print("\n{:<15} | {:<10} | {:<12} | {:<15} | {:<10} | {:<10}".format(
        "Method", "Resolved", "Unresolved", "New Introduced", "Recall", "F1-Score"
    ))
    print("-"*80)
    print("{:<15} | {:<10} | {:<12} | {:<15} | {:<10.4f} | {:<10.4f}".format(
        "Custom", custom_opt_tp, custom_opt_fn, custom_opt_fp, recall_c_opt, f1_c_opt
    ))
    print("{:<15} | {:<10} | {:<12} | {:<15} | {:<10.4f} | {:<10.4f}".format(
        "Baseline", baseline_opt_tp, baseline_opt_fn, baseline_opt_fp, recall_b_opt, f1_b_opt
    ))
    print("\nRecall = Resolution Rate (Resolved / Original)")
    print("F1-Score = Balances Resolution Rate and Avoidance of New Issues")

    # --- Save Summaries --- #
    # Save Linter Comparison Summary
    linter_summary_data = {
        "files_processed": files_processed_count,
        "custom_linter": {
            "tp": custom_linter_tp, "fp": custom_linter_fp, "fn": custom_linter_fn,
            "precision": precision_cl, "recall": recall_cl, "f1_score": f1_cl
        },
        "hadolint": {
            "tp": hadolint_tp, "fp": hadolint_fp, "fn": hadolint_fn,
            "precision": precision_h, "recall": recall_h, "f1_score": f1_h
        }
    }
    linter_summary_file_path = WORKSPACE_ROOT / "testing" / "linter_comparison_summary.json"
    try:
        with open(linter_summary_file_path, 'w', encoding='utf-8') as f:
            json.dump(linter_summary_data, f, indent=2)
        print(f"\nSaved linter comparison summary to: {linter_summary_file_path}")
    except Exception as e:
        print(f"\nError saving linter comparison summary: {e}", file=sys.stderr)

    # Save Optimization Comparison Summary
    opt_summary_data = {
        "files_compared": comparable_files_count,
        "total_original_issues": total_original_issues_opt,
        "custom_results": {
            "resolved": custom_opt_tp,
            "unresolved": custom_opt_fn,
            "new_introduced": custom_opt_fp,
            "recall": recall_c_opt,
            "f1_score": f1_c_opt
        },
        "baseline_results": {
            "resolved": baseline_opt_tp,
            "unresolved": baseline_opt_fn,
            "new_introduced": baseline_opt_fp,
            "recall": recall_b_opt,
            "f1_score": f1_b_opt
        }
    }
    opt_summary_file_path = WORKSPACE_ROOT / "testing" / "optimization_comparison_summary.json" # Renamed file
    try:
        # import json # Already imported
        with open(opt_summary_file_path, 'w', encoding='utf-8') as f:
            json.dump(opt_summary_data, f, indent=2)
        print(f"Saved optimization comparison summary to: {opt_summary_file_path}")
    except Exception as e:
        print(f"\nError saving optimization comparison summary: {e}", file=sys.stderr)

else:
    print("\nNo files could be fully processed for optimization comparison (missing optimized files?).")

print("\nEvaluation Complete.")

# Remove old summary saving logic if it exists
# Remove debug prints (done above by commenting out) 