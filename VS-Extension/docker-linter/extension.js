// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
const vscode = require('vscode');
const { execSync } = require('child_process');
const path = require('path');

let diagnosticCollection;
let outputChannel;

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
	outputChannel = vscode.window.createOutputChannel('Docker Linter');
	outputChannel.show();
	outputChannel.appendLine('Dockerfile Linter extension activated');
	
	diagnosticCollection = vscode.languages.createDiagnosticCollection('dockerfile');
	context.subscriptions.push(diagnosticCollection);

	// Lint on document open
	vscode.workspace.onDidOpenTextDocument(lintDocument);
	
	// Lint on document save
	vscode.workspace.onDidSaveTextDocument(lintDocument);
	
	// Lint on document change
	vscode.workspace.onDidChangeTextDocument(e => lintDocument(e.document));
	
	// Register manual lint command
	context.subscriptions.push(
		vscode.commands.registerCommand('docker-linter.runLint', () => {
			const editor = vscode.window.activeTextEditor;
			if (editor) lintDocument(editor.document);
		})
	);
}

async function lintDocument(document) {
	if (document.languageId !== 'dockerfile') return;

	try {
		const issues = await runLinter(document);
		showDiagnostics(document, issues);
	} catch (error) {
		vscode.window.showErrorMessage(`Linting failed: ${error.message}`);
	}
}

async function runLinter(document) {
	const tempDir = require('os').tmpdir();
	const tempPath = path.join(tempDir, `docker-linter-${Date.now()}.Dockerfile`);
	const content = document.getText();
	
	// Write the exact content without modifying line endings
	require('fs').writeFileSync(tempPath, content);

	let output;

	try {
		// Use double quotes for Windows paths
		const pythonScriptPath = `"${path.join(__dirname, '../../lint_cli.py').replace(/\\/g, '/')}"`;
		const quotedTempPath = `"${tempPath.replace(/\\/g, '/')}"`;
		const rulesPath = `"${path.join(__dirname, '../../../Code/rules.json').replace(/\\/g, '/')}"`;
		
		outputChannel.appendLine(`Running linter command: python ${pythonScriptPath} ${quotedTempPath} --format json --rules ${rulesPath}`);
		
		output = execSync(`python ${pythonScriptPath} ${quotedTempPath} --format json --rules ${rulesPath}`, {
			encoding: 'utf-8',
			windowsHide: true
		});

		outputChannel.appendLine('Raw linter output: ' + output);

		const result = JSON.parse(output);
		
		if (result.error) {
			throw new Error(result.error);
		}

		// Map the line numbers to actual document content
		if (result.issues) {
			result.issues = result.issues.map(issue => {
				// Find the actual line in the document that matches the content
				for (let i = 0; i < document.lineCount; i++) {
					const line = document.lineAt(i);
					if (line.text.trim() === issue.line_content?.trim()) {
						issue.line_number = i + 1; // Convert to 1-based index
						break;
					}
				}
				return issue;
			});
		}

		outputChannel.appendLine(`Number of issues received from linter: ${result.issues ? result.issues.length : 0}`);
		return result.issues || [];
	} catch (error) {
		if (error instanceof SyntaxError) {
			throw new Error(`Invalid JSON: ${output?.substring(0, 100) || 'No output'}`);
		}
		throw error;
	} finally {
		// Clean up temp file
		try {
			require('fs').unlinkSync(tempPath);
		} catch (err) {
			outputChannel.appendLine('Error cleaning temp file: ' + err);
		}
	}
}

function showDiagnostics(document, issues) {
	outputChannel.appendLine(`Number of issues being processed in showDiagnostics: ${issues.length}`);
	const diagnostics = [];
	
	issues.forEach(issue => {
		try {
			// Parse line number exactly as it comes from the linter
			let lineNumber = parseInt(issue.line_number, 10);
			if (isNaN(lineNumber)) {
				outputChannel.appendLine(`Skipping issue - Invalid line number format: ${issue.line_number}`);
				return;
			}
			
			// Convert to 0-based index
			lineNumber = lineNumber - 1;
			
			// Validate line number is within document bounds
			if (lineNumber < 0 || lineNumber >= document.lineCount) {
				outputChannel.appendLine(`Skipping issue - Line number ${lineNumber + 1} out of bounds (document has ${document.lineCount} lines)`);
				return;
			}

			// Get the line text and ensure we have content
			const line = document.lineAt(lineNumber);
			const lineText = line.text;
			
			// If the line is empty or whitespace, try to find the next non-empty line
			let actualLineNumber = lineNumber;
			let actualLineText = lineText;
			
			if (!lineText.trim() && lineNumber + 1 < document.lineCount) {
				for (let i = lineNumber + 1; i < document.lineCount; i++) {
					const nextLine = document.lineAt(i);
					if (nextLine.text.trim()) {
						actualLineNumber = i;
						actualLineText = nextLine.text;
						break;
					}
				}
			}
			
			// Create a range that covers the actual content
			const range = new vscode.Range(
				new vscode.Position(actualLineNumber, 0),
				new vscode.Position(actualLineNumber, actualLineText.length || 1) // Ensure at least 1 character
			);

			const diagnostic = new vscode.Diagnostic(
				range,
				`${issue.title}: ${issue.description}\nSuggestion: ${issue.suggestion}`,
				vscode.DiagnosticSeverity.Warning
			);
			
			diagnostic.source = 'Docker Linter';
			diagnostic.code = issue.rule_id;
			
			diagnostics.push(diagnostic);
			outputChannel.appendLine(`Added diagnostic for line ${lineNumber + 1} (actual line ${actualLineNumber + 1}) with range: ${range.start.line}:${range.start.character}-${range.end.line}:${range.end.character}`);
		} catch (error) {
			outputChannel.appendLine(`Error processing issue: ${error.message}`);
		}
	});

	// Clear existing diagnostics before setting new ones
	diagnosticCollection.clear();
	diagnosticCollection.set(document.uri, diagnostics);
	outputChannel.appendLine(`Set ${diagnostics.length} diagnostics`);
}

function getSeverity(severity) {
	const config = vscode.workspace.getConfiguration('dockerLinter').get('severityLevels');
	switch (config[severity] || 'information') {
		case 'error': return vscode.DiagnosticSeverity.Error;        // Red underline
		case 'warning': return vscode.DiagnosticSeverity.Warning;    // Yellow/Orange underline
		default: return vscode.DiagnosticSeverity.Information;       // Blue underline
	}
}

// This method is called when your extension is deactivated
function deactivate() {}

module.exports = {
	activate,
	deactivate
}