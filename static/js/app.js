// TruthTool Frontend Application
class TruthToolApp {
    constructor() {
        this.currentTab = 'workspace';
        this.currentResultTab = 'truth-table';
        this.isRunning = false;
        this.currentResult = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadExamples();
        this.updateLogicSettings();
    }
    
    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
        
        // Result tab navigation disabled - tabs are automatically managed
        
        // Logic type change
        document.getElementById('logic-type').addEventListener('change', () => {
            this.updateLogicSettings();
        });
        
        // Run button
        document.getElementById('run-button').addEventListener('click', () => {
            this.runSolver();
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.runSolver();
            }
        });
    }
    
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');
        
        this.currentTab = tabName;
    }
    
    // switchResultTab function removed - result tabs are now automatically managed
    
    updateLogicSettings() {
        const logicType = document.getElementById('logic-type').value;
        
        // Show/hide relevant settings
        document.getElementById('modal-settings').style.display = 
            logicType === 'MODAL' ? 'block' : 'none';
        document.getElementById('fol-settings').style.display = 
            logicType === 'FOL' ? 'block' : 'none';
    }
    
    async runSolver() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.updateRunButton(true);
        
        try {
            // Get input data
            const premises = document.getElementById('premises').value
                .split('\n')
                .map(line => line.trim())
                .filter(line => line.length > 0);
            
            const conclusion = document.getElementById('conclusion').value.trim();
            
            if (premises.length === 0 || !conclusion) {
                throw new Error('Please provide at least one premise and a conclusion');
            }
            
            const logic = document.getElementById('logic-type').value;
            const settings = {
                modalFrame: document.getElementById('modal-frame').value,
                folDomainSize: parseInt(document.getElementById('fol-domain-size').value),
                folTermDepth: parseInt(document.getElementById('fol-term-depth').value),
                timeout: parseInt(document.getElementById('timeout').value) * 1000
            };
            
            // Show loading state
            this.showResultSummary('⏳', 'Running solver...', 'status-unknown');
            
            // Call solver API
            const response = await fetch('/api/solve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    premises,
                    conclusion,
                    logic,
                    settings
                })
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'Solver failed');
            }
            
            // Process result
            this.currentResult = result.result;
            this.displayResult(result.result);
            
        } catch (error) {
            console.error('Solver error:', error);
            this.showResultSummary('❌', `Error: ${error.message}`, 'status-error');
        } finally {
            this.isRunning = false;
            this.updateRunButton(false);
        }
    }
    
    updateRunButton(running) {
        const button = document.getElementById('run-button');
        const text = button.querySelector('.button-text');
        const icon = button.querySelector('.button-icon');
        
        if (running) {
            button.disabled = true;
            text.textContent = 'Running...';
            icon.textContent = '⏳';
        } else {
            button.disabled = false;
            text.textContent = 'Prove or Find Countermodel';
            icon.textContent = '▶';
        }
    }
    
    showResultSummary(icon, text, className) {
        const summary = document.getElementById('result-summary');
        summary.innerHTML = `
            <div class="status-card">
                <div class="status-icon">${icon}</div>
                <div class="status-text ${className}">${text}</div>
            </div>
        `;
    }
    
    displayResult(result) {
        // Update status
        const statusMap = {
            'VALID': { icon: '✅', text: 'Valid', class: 'status-valid' },
            'INVALID': { icon: '❌', text: 'Invalid', class: 'status-invalid' },
            'UNKNOWN': { icon: '❓', text: 'Unknown', class: 'status-unknown' },
            'ERROR': { icon: '⚠️', text: 'Error', class: 'status-error' }
        };
        
        const status = statusMap[result.status] || statusMap['ERROR'];
        this.showResultSummary(status.icon, status.text, status.class);
        
        // Hide result tabs - only show relevant visualizations automatically
        document.getElementById('result-tabs').style.display = 'none';
        
        // Switch to results tab
        this.switchTab('results');
        
        // Hide all result panels first
        this.hideAllResultPanels();
        
        // Display only relevant artifacts based on available data
        let hasRelevantData = false;
        
        if (result.artifacts) {
            // Show truth table for propositional logic (both valid and invalid)
            if (result.artifacts.truth_table) {
                this.displayTruthTable(result.artifacts.truth_table);
                this.showResultPanel('truth-table');
                hasRelevantData = true;
            }
            
            // Proof DAG functionality removed
            
            // Show Kripke model for modal logic
            if (result.artifacts.kripke) {
                this.displayKripkeModel(result.artifacts.kripke);
                this.showResultPanel('kripke');
                hasRelevantData = true;
            }
            
            // Show finite structure for FOL
            if (result.artifacts.structure) {
                this.displayFiniteStructure(result.artifacts.structure);
                this.showResultPanel('structure');
                hasRelevantData = true;
            }
        }
        
        // If no relevant data, show a message
        if (!hasRelevantData) {
            this.showNoDataMessage();
        }
    }
    
    displayTruthTable(truthTable) {
        const container = document.getElementById('truth-table-container');
        
        if (!truthTable || truthTable.length === 0) {
            container.innerHTML = '<p>No truth table data available</p>';
            return;
        }
        
        const variables = Object.keys(truthTable[0].values);
        
        let html = '<div class="truth-table-wrapper">';
        html += '<table class="truth-table">';
        html += '<thead><tr>';
        variables.forEach(varName => {
            html += `<th>${varName}</th>`;
        });
        html += '<th>Result</th>';
        html += '</tr></thead><tbody>';
        
        truthTable.forEach((row, index) => {
            const rowClass = row.is_counterexample ? 'counterexample' : '';
            html += `<tr class="${rowClass}" data-row="${index}">`;
            variables.forEach(varName => {
                const value = row.values[varName] ? 'T' : 'F';
                const cellClass = row.is_counterexample ? 'highlight' : '';
                html += `<td class="${cellClass}">${value}</td>`;
            });
            
            // Add result column
            const resultClass = row.is_counterexample ? 'invalid-result' : 'valid-result';
            const resultText = row.is_counterexample ? '❌' : '✅';
            html += `<td class="${resultClass}">${resultText}</td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table>';
        html += '</div>';
        
        // Add summary
        const counterexampleCount = truthTable.filter(row => row.is_counterexample).length;
        if (counterexampleCount > 0) {
            html += `<div class="truth-table-summary">
                <p><strong>Found ${counterexampleCount} counterexample(s)</strong> - highlighted in red</p>
            </div>`;
        } else {
            html += `<div class="truth-table-summary">
                <p><strong>No counterexamples found</strong> - argument is valid</p>
            </div>`;
        }
        
        container.innerHTML = html;
    }
    
    // displayProofDag function removed
    
    displayKripkeModel(kripke) {
        const container = document.getElementById('kripke-container');
        
        if (!kripke) {
            container.innerHTML = '<p>No Kripke model data available</p>';
            return;
        }
        
        let html = '<div class="kripke-container">';
        html += '<div class="kripke-header">';
        html += '<h4>Kripke Model</h4>';
        html += '<div class="kripke-info">';
        html += `<p><strong>Frame:</strong> ${kripke.frame || 'K'}</p>`;
        html += `<p><strong>Worlds:</strong> ${kripke.worlds ? kripke.worlds.length : 0}</p>`;
        html += '</div>';
        html += '</div>';
        
        if (kripke.worlds && kripke.worlds.length > 0) {
            html += '<div class="kripke-graph">';
            
            // Display worlds
            kripke.worlds.forEach((world, index) => {
                const worldClass = world.is_root ? 'world root' : 'world';
                html += `<div class="${worldClass}" data-world="${world.id}">`;
                html += `<div class="world-id">${world.id}</div>`;
                
                if (world.valuation && Object.keys(world.valuation).length > 0) {
                    html += '<div class="world-valuation">';
                    Object.entries(world.valuation).forEach(([prop, value]) => {
                        const valueClass = value ? 'true' : 'false';
                        html += `<span class="proposition ${valueClass}">${prop}</span>`;
                    });
                    html += '</div>';
                }
                
                html += '</div>';
            });
            
            // Display accessibility relations
            if (kripke.edges && kripke.edges.length > 0) {
                html += '<div class="accessibility-relations">';
                html += '<h5>Accessibility Relations</h5>';
                kripke.edges.forEach(edge => {
                    html += `<div class="accessibility-edge">`;
                    html += `${edge.from} → ${edge.to}`;
                    if (edge.properties) {
                        html += ` (${edge.properties.join(', ')})`;
                    }
                    html += '</div>';
                });
                html += '</div>';
            }
            
            html += '</div>';
        } else {
            html += '<div class="kripke-placeholder">';
            html += '<p>No worlds in this model</p>';
            html += '</div>';
        }
        
        html += '</div>';
        container.innerHTML = html;
    }
    
    displayFiniteStructure(structure) {
        const container = document.getElementById('structure-container');
        
        if (!structure) {
            container.innerHTML = '<p>No finite structure data available</p>';
            return;
        }
        
        let html = '<div class="structure-container">';
        html += '<div class="structure-header">';
        html += '<h4>Finite Structure</h4>';
        html += '<div class="structure-info">';
        html += `<p><strong>Domain Size:</strong> ${structure.domain ? structure.domain.length : 0}</p>`;
        html += `<p><strong>Predicates:</strong> ${structure.predicates ? Object.keys(structure.predicates).length : 0}</p>`;
        html += `<p><strong>Functions:</strong> ${structure.functions ? Object.keys(structure.functions).length : 0}</p>`;
        html += '</div>';
        html += '</div>';
        
        // Display domain
        if (structure.domain && structure.domain.length > 0) {
            html += '<div class="structure-section">';
            html += '<h5>Domain</h5>';
            html += '<div class="domain-list">';
            structure.domain.forEach((element, index) => {
                html += `<span class="domain-element">${element}</span>`;
            });
            html += '</div>';
            html += '</div>';
        }
        
        // Display predicates
        if (structure.predicates && Object.keys(structure.predicates).length > 0) {
            html += '<div class="structure-section">';
            html += '<h5>Predicates</h5>';
            Object.entries(structure.predicates).forEach(([predName, extensions]) => {
                html += `<div class="predicate-table">`;
                html += `<h6>${predName}</h6>`;
                html += '<table class="predicate-matrix">';
                
                // Create header row
                html += '<thead><tr>';
                for (let i = 0; i < structure.domain.length; i++) {
                    html += `<th>${structure.domain[i]}</th>`;
                }
                html += '</tr></thead>';
                
                // Create data rows
                html += '<tbody>';
                for (let i = 0; i < structure.domain.length; i++) {
                    html += '<tr>';
                    for (let j = 0; j < structure.domain.length; j++) {
                        const tuple = [structure.domain[i], structure.domain[j]];
                        const isTrue = extensions.some(ext => 
                            ext.length === tuple.length && 
                            ext.every((val, idx) => val === tuple[idx])
                        );
                        const cellClass = isTrue ? 'true' : 'false';
                        html += `<td class="${cellClass}">${isTrue ? 'T' : 'F'}</td>`;
                    }
                    html += '</tr>';
                }
                html += '</tbody>';
                html += '</table>';
                html += '</div>';
            });
            html += '</div>';
        }
        
        // Display functions
        if (structure.functions && Object.keys(structure.functions).length > 0) {
            html += '<div class="structure-section">';
            html += '<h5>Functions</h5>';
            Object.entries(structure.functions).forEach(([funcName, mapping]) => {
                html += `<div class="function-table">`;
                html += `<h6>${funcName}</h6>`;
                html += '<table class="function-matrix">';
                html += '<thead><tr><th>Input</th><th>Output</th></tr></thead>';
                html += '<tbody>';
                
                Object.entries(mapping).forEach(([input, output]) => {
                    html += '<tr>';
                    html += `<td>${input}</td>`;
                    html += `<td>${output}</td>`;
                    html += '</tr>';
                });
                
                html += '</tbody>';
                html += '</table>';
                html += '</div>';
            });
            html += '</div>';
        }
        
        html += '</div>';
        container.innerHTML = html;
    }
    
    hideAllResultPanels() {
        const panels = ['truth-table', 'kripke', 'structure'];
        panels.forEach(panelId => {
            const panel = document.getElementById(`${panelId}-panel`);
            if (panel) {
                panel.style.display = 'none';
            }
        });
    }
    
    showResultPanel(panelId) {
        const panel = document.getElementById(`${panelId}-panel`);
        if (panel) {
            panel.style.display = 'block';
        }
    }
    
    showNoDataMessage() {
        // Show a message when no relevant data is available
        const resultsContainer = document.getElementById('results-container');
        const noDataMessage = document.createElement('div');
        noDataMessage.className = 'no-data-message';
        noDataMessage.innerHTML = '<p>No visualization data available for this result.</p>';
        
        // Remove any existing no-data message
        const existingMessage = resultsContainer.querySelector('.no-data-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        resultsContainer.appendChild(noDataMessage);
    }
    
    async loadExamples() {
        try {
            const response = await fetch('/api/examples');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const examples = await response.json();
            
            this.displayExamples(examples);
        } catch (error) {
            console.error('Failed to load examples:', error);
            document.getElementById('examples-grid').innerHTML = 
                '<p>Failed to load examples: ' + error.message + '</p>';
        }
    }
    
    displayExamples(examples) {
        const container = document.getElementById('examples-grid');
        let html = '';
        
        // Propositional examples
        if (examples.propositional) {
            examples.propositional.forEach(example => {
                html += this.createExampleCard('PL', example);
            });
        }
        
        // Modal examples
        if (examples.modal) {
            examples.modal.forEach(example => {
                html += this.createExampleCard('MODAL', example);
            });
        }
        
        // FOL examples
        if (examples.fol) {
            examples.fol.forEach(example => {
                html += this.createExampleCard('FOL', example);
            });
        }
        
        container.innerHTML = html;
        
        // Add click handlers
        container.querySelectorAll('.example-card').forEach(card => {
            card.addEventListener('click', () => {
                const logic = card.dataset.logic;
                const example = JSON.parse(card.dataset.example);
                this.loadExample(logic, example);
            });
        });
    }
    
    createExampleCard(logic, example) {
        return `
            <div class="example-card" data-logic="${logic}" data-example='${JSON.stringify(example)}'>
                <h3>${example.name}</h3>
                <p>${example.description}</p>
                <div class="example-formula">
                    <div class="example-premises">Premises: ${example.premises.join(', ')}</div>
                    <div class="example-conclusion">Conclusion: ${example.conclusion}</div>
                </div>
            </div>
        `;
    }
    
    loadExample(logic, example) {
        // Switch to workspace
        this.switchTab('workspace');
        
        // Set logic type
        document.getElementById('logic-type').value = logic;
        this.updateLogicSettings();
        
        // Set modal frame for modal examples
        if (logic === 'MODAL' && example.name && example.name.includes('Barcan')) {
            document.getElementById('modal-frame').value = 'T';
        }
        
        // Set premises and conclusion
        if (Array.isArray(example.premises)) {
            document.getElementById('premises').value = example.premises.join('\n');
        } else {
            document.getElementById('premises').value = example.premises;
        }
        document.getElementById('conclusion').value = example.conclusion;
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TruthToolApp();
});
