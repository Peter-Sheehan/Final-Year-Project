// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
const vscode = require('vscode');
const { execSync } = require('child_process');
const path = require('path');

let diagnosticCollection;
let outputChannel;

/**
 * @param {vscode.ExtensionContext} context
 */
// Called when the extension is activated
function activate(context) {
	outputChannel = vscode.window.createOutputChannel('Docker Linter');
	outputChannel.show();
	outputChannel.appendLine('Dockerfile Linter extension activated');
	
	diagnosticCollection = vscode.languages.createDiagnosticCollection('dockerfile');
	context.subscriptions.push(diagnosticCollection);

	// Lint documents on open, save, and change
	vscode.workspace.onDidOpenTextDocument(lintDocument);
	
	vscode.workspace.onDidSaveTextDocument(lintDocument);
	
	vscode.workspace.onDidChangeTextDocument(e => lintDocument(e.document));
	
	context.subscriptions.push(
		vscode.commands.registerCommand('docker-linter.runLint', () => {
			const editor = vscode.window.activeTextEditor;
			if (editor) lintDocument(editor.document);
		})
	);
}

// Asynchronously lints a given document
async function lintDocument(document) {
	if (document.languageId !== 'dockerfile') return;

	try {
		const issues = await runLinter(document);
		showDiagnostics(document, issues);
	} catch (error) {
		vscode.window.showErrorMessage(`Linting failed: ${error.message}`);
	}
}

// Runs the external Python linter script
async function runLinter(document) {
	const tempDir = require('os').tmpdir();
	const tempPath = path.join(tempDir, `docker-linter-${Date.now()}.Dockerfile`);
	const content = document.getText();
	
	// Write document content to a temporary file for the linter
	require('fs').writeFileSync(tempPath, content);

	let output;

	try {
		const pythonScriptPath = `"${path.join(__dirname, '../../lint_cli.py').replace(/\\/g, '/')}"`;
		const quotedTempPath = `"${tempPath.replace(/\\/g, '/')}"`;
		const rulesPath = `"${path.join(__dirname, '../../../Code/Rules/rules.json').replace(/\\/g, '/')}"`;
		
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

		// Map linter line numbers to actual document line numbers
		// This is necessary if the linter reports based on its temporary file content
		if (result.issues) {
			result.issues = result.issues.map(issue => {
				// Find the actual line in the document that matches the content
				for (let i = 0; i < document.lineCount; i++) {
					const line = document.lineAt(i);
					if (line.text.trim() === issue.line_content?.trim()) {
						issue.line_number = i + 1; // Convert to 1-based index for linter
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
		// Always clean up the temporary file
		try {
			require('fs').unlinkSync(tempPath);
		} catch (err) {
			outputChannel.appendLine('Error cleaning temp file: ' + err);
		}
	}
}

// Displays linting issues as diagnostics in the editor
function showDiagnostics(document, issues) {
	outputChannel.appendLine(`Number of issues being processed in showDiagnostics: ${issues.length}`);
	const diagnostics = [];
	
	issues.forEach(issue => {
		try {
			let lineNumber = parseInt(issue.line_number, 10);
			if (isNaN(lineNumber)) {
				outputChannel.appendLine(`Skipping issue - Invalid line number format: ${issue.line_number}`);
				return;
			}
			
			// Adjust for 0-based indexing in VS Code API
			lineNumber = lineNumber - 1;
			
			// Validate line number is within document bounds
			if (lineNumber < 0 || lineNumber >= document.lineCount) {
				outputChannel.appendLine(`Skipping issue - Line number ${lineNumber + 1} out of bounds (document has ${document.lineCount} lines)`);
				return;
			}

			const line = document.lineAt(lineNumber);
			const lineText = line.text;
			
			let actualLineNumber = lineNumber;
			let actualLineText = lineText;
			
			// If the reported line is empty, find the next non-empty line for the diagnostic
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
			
			const range = new vscode.Range(
				new vscode.Position(actualLineNumber, 0),
				new vscode.Position(actualLineNumber, actualLineText.length || 1)
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

	// Clear previous diagnostics and set new ones
	diagnosticCollection.clear();
	diagnosticCollection.set(document.uri, diagnostics);
	outputChannel.appendLine(`Set ${diagnostics.length} diagnostics`);
}

// Converts severity string from config to VS Code DiagnosticSeverity
function getSeverity(severity) {
	const config = vscode.workspace.getConfiguration('dockerLinter').get('severityLevels');
	switch (config[severity] || 'information') {
		case 'error': return vscode.DiagnosticSeverity.Error;
		case 'warning': return vscode.DiagnosticSeverity.Warning;
		default: return vscode.DiagnosticSeverity.Information;
	}
}

// Called when the extension is deactivated
function deactivate() {}

module.exports = {
	activate,
	deactivate
}