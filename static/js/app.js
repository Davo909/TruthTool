// TruthTool Frontend Application
class TruthToolApp {
    constructor() {
      this.currentTab = 'workspace';
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
      // Tabs
      document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
      });
  
      // Logic change
      document.getElementById('logic-type').addEventListener('change', () => this.updateLogicSettings());
  
      // Run
      document.getElementById('run-button').addEventListener('click', () => this.runSolver());
  
      // Keyboard: Ctrl+Enter to run
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
          e.preventDefault();
          this.runSolver();
        }
      });
  
      // Symbol palette
      document.querySelectorAll('.symbol-btn').forEach(btn => {
        btn.addEventListener('click', (e) => this.insertSymbol(e.target.dataset.symbol));
      });
    }
  
    switchTab(tabName) {
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      document.getElementById(tabName).classList.add('active');
      this.currentTab = tabName;
    }
  
    insertSymbol(symbol) {
      const premises = document.getElementById('premises');
      const conclusion = document.getElementById('conclusion');
      let field = document.activeElement === premises ? premises :
                  document.activeElement === conclusion ? conclusion : premises;
      const start = field.selectionStart, end = field.selectionEnd;
      field.value = field.value.substring(0, start) + symbol + field.value.substring(end);
      field.setSelectionRange(start + symbol.length, start + symbol.length);
      field.dispatchEvent(new Event('input', {bubbles:true}));
    }
  
    updateLogicSettings() {
      const logic = document.getElementById('logic-type').value;
      document.getElementById('modal-settings').style.display = (logic === 'MODAL') ? 'block' : 'none';
      document.getElementById('fol-settings').style.display = (logic === 'FOL') ? 'block' : 'none';
    }
  
    async runSolver() {
      if (this.isRunning) return;
      this.isRunning = true;
      this.updateRunButton(true);
  
      try {
        const premises = document.getElementById('premises').value
          .split('\n').map(s => s.trim()).filter(Boolean);
        const conclusion = document.getElementById('conclusion').value.trim();
        if (!premises.length || !conclusion) throw new Error('Please provide at least one premise and a conclusion.');
  
        const logic = document.getElementById('logic-type').value;
        const settings = {
          modalFrame: document.getElementById('modal-frame').value,
          domainSize: parseInt(document.getElementById('fol-domain').value || '2', 10),
          termDepth: parseInt(document.getElementById('fol-depth').value || '1', 10),
          timeout: parseInt(document.getElementById('timeout').value || '8', 10) * 1000
        };
  
        this.showResultSummary('⏳', 'Running solver…', 'status-unknown');
  
        const resp = await fetch('/api/solve', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ premises, conclusion, logic, settings })
        });
  
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.error || 'Solver failed.');
  
        this.displayResult(data.result);
  
      } catch (err) {
        console.error(err);
        this.showResultSummary('❌', `Error: ${err.message}`, 'status-error');
      } finally {
        this.isRunning = false;
        this.updateRunButton(false);
        this.switchTab('results');
      }
    }
  
    updateRunButton(running) {
      const b = document.getElementById('run-button');
      b.disabled = running;
      b.querySelector('.button-text').textContent = running ? 'Running…' : 'Prove or Find Countermodel';
      b.querySelector('.button-icon').textContent = running ? '⏳' : '▶';
    }
  
    showResultSummary(icon, text, className) {
      const summary = document.getElementById('result-summary');
      summary.innerHTML = `
        <div class="status-card">
          <div class="status-icon">${icon}</div>
          <div class="status-text ${className}">${text}</div>
        </div>`;
    }
  
    hideAllResultPanels() {
      ['truth-table','kripke','finite-structure'].forEach(id => {
        const panel = document.getElementById(`${id}-panel`);
        if (panel) panel.style.display = 'none';
      });
    }
  
    showResultPanel(id) {
      const panel = document.getElementById(`${id}-panel`);
      if (panel) panel.style.display = 'block';
    }
  
    displayResult(result) {
      const statusMap = {
        'VALID':   {icon:'✅', text:'Valid',   class:'status-valid'},
        'INVALID': {icon:'❌', text:'Invalid', class:'status-invalid'},
        'UNKNOWN': {icon:'❓', text:'Unknown', class:'status-unknown'},
        'ERROR':   {icon:'⚠️', text:'Error',   class:'status-error'}
      };
      const s = statusMap[result.status] || statusMap.ERROR;
      this.showResultSummary(s.icon, s.text, s.class);
  
      this.hideAllResultPanels();
  
      let shown = false;
      if (result.artifacts) {
        if (result.artifacts.truth_table) {
          this.displayTruthTable(result.artifacts.truth_table);
          this.showResultPanel('truth-table');
          shown = true;
        }
        if (result.artifacts.kripke) {
          this.displayKripkeModel(result.artifacts.kripke);
          this.showResultPanel('kripke');
          shown = true;
        }
        if (result.artifacts.structure) {
          this.displayFiniteStructure(result.artifacts.structure);
          this.showResultPanel('finite-structure');
          shown = true;
        }
      }
      if (!shown) this.showNoDataMessage();
    }
  
    displayTruthTable(truthTable) {
      const container = document.getElementById('truth-table-container');
      if (!truthTable || !truthTable.length) {
        container.innerHTML = '<p>No truth table data.</p>'; return;
      }
      const variables = Object.keys(truthTable[0].values);
      let html = '<div class="truth-table-wrapper"><table class="truth-table">';
      html += '<thead><tr>' + variables.map(v=>`<th>${v}</th>`).join('') + '<th>Result</th></tr></thead><tbody>';
      truthTable.forEach(row => {
        const rowClass = row.is_counterexample ? 'counterexample' : '';
        html += `<tr class="${rowClass}">`;
        for (const v of variables) {
          const cell = row.values[v] ? 'T' : 'F';
          const cc = row.is_counterexample ? 'highlight' : '';
          html += `<td class="${cc}">${cell}</td>`;
        }
        html += `<td class="${row.is_counterexample ? 'invalid-result' : 'valid-result'}">${row.is_counterexample?'❌':'✅'}</td>`;
        html += `</tr>`;
      });
      html += '</tbody></table></div>';
      const cexCount = truthTable.filter(r => r.is_counterexample).length;
      html += `<div class="truth-table-summary"><p><strong>${cexCount ? `Found ${cexCount} counterexample(s)` : 'No counterexamples found'}</strong></p></div>`;
      container.innerHTML = html;
    }
  
    // ===== Kripke visualization (SVG) =====
    displayKripkeModel(kripke) {
      const el = document.getElementById('kripke-container');
      if (!kripke) { el.innerHTML = '<p>No Kripke data.</p>'; return; }
  
      const W = 860, H = 520, R = Math.min(W, H)/2 - 80;
      const worlds = kripke.worlds || [];
      const edges = kripke.edges || [];
  
      // layout positions in a circle
      const positions = {};
      const n = worlds.length || 1;
      for (let i=0;i<n;i++) {
        const theta = (2*Math.PI * i) / n - Math.PI/2;
        positions[worlds[i].id] = {
          x: W/2 + (n>1 ? R*Math.cos(theta) : 0),
          y: H/2 + (n>1 ? R*Math.sin(theta) : 0)
        };
      }
  
      // SVG header with arrowhead markers
      let svg = `
        <svg class="kripke-svg" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" aria-label="Kripke Model">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z"></path>
            </marker>
          </defs>
          <rect x="0" y="0" width="${W}" height="${H}" class="kripke-bg"></rect>
      `;
  
      // Draw edges (under nodes)
      edges.forEach(e => {
        const u = positions[e.from], v = positions[e.to];
        if (!u || !v) return;
  
        const isLoop = e.from === e.to;
        const classes = ['edge'];
        if (e.properties && e.properties.includes('symmetric') && !isLoop) classes.push('edge-symmetric');
        if (e.properties && e.properties.includes('transitive') && !isLoop) classes.push('edge-transitive');
        if (e.properties && e.properties.includes('reflexive') && isLoop) classes.push('edge-reflexive');
  
        if (isLoop) {
          // self loop as an arc above the node
          const r = 26;
          const x = u.x, y = u.y;
          const path = `M ${x+r} ${y-4} a ${r} ${r} 0 1 1 -${2*r} 0`;
          svg += `<path d="${path}" class="${classes.join(' ')}" marker-end="url(#arrow)"></path>`;
        } else {
          const dx = v.x - u.x, dy = v.y - u.y;
          const len = Math.hypot(dx, dy) || 1;
          const off = 28; // node radius margin
          const sx = u.x + (dx/len)*off, sy = u.y + (dy/len)*off;
          const ex = v.x - (dx/len)*off, ey = v.y - (dy/len)*off;
          svg += `<line x1="${sx}" y1="${sy}" x2="${ex}" y2="${ey}" class="${classes.join(' ')}" marker-end="url(#arrow)"></line>`;
        }
      });
  
      // Draw nodes
      worlds.forEach(w => {
        const p = positions[w.id];
        const isRoot = !!w.is_root;
        svg += `<g class="node${isRoot?' node-root':''}" transform="translate(${p.x},${p.y})">`;
        svg += `<circle r="28"></circle>`;
        svg += `<text class="node-label" text-anchor="middle" dy="5">${w.id}</text>`;
        svg += `</g>`;
      });
  
      svg += `</svg>`;
  
      // Build HTML container with legend + SVG
      let html = `
        <div class="kripke-viz">
          <div class="kripke-meta">
            <div><strong>Frame:</strong> ${kripke.frame||'K'}</div>
            <div><strong>Worlds:</strong> ${worlds.length}</div>
          </div>
          <div class="kripke-legend">
            <span class="legend-item"><span class="legend-edge"></span> accessibility</span>
            <span class="legend-item"><span class="legend-edge symmetric"></span> symmetric</span>
            <span class="legend-item"><span class="legend-edge transitive"></span> transitive</span>
            <span class="legend-item"><span class="legend-node root"></span> root world</span>
          </div>
          ${svg}
      `;
  
      // Node annotations: valuation atoms + per-formula truth if provided
      const atomSet = new Set();
      worlds.forEach(w => {
        Object.keys(w.valuation||{}).forEach(a => atomSet.add(a));
      });
      const atoms = Array.from(atomSet);
  
      if (atoms.length || (kripke.formulas && kripke.truth)) {
        html += `<div class="kripke-annotations">`;
  
        if (atoms.length) {
          html += `<div class="anno-section"><h5>Atomic Propositions</h5>`;
          worlds.forEach(w=>{
            html += `<div class="anno-row"><strong>${w.id}</strong>: `;
            atoms.forEach(a=>{
              const v = !!(w.valuation && w.valuation[a]);
              html += `<span class="prop-chip ${v?'true':'false'}">${a}</span>`;
            });
            html += `</div>`;
          });
          html += `</div>`;
        }
  
        if (kripke.formulas && kripke.truth) {
          const labels = kripke.formulas;   // {P1: "□P", ..., C: "Q"}
          const truth = kripke.truth;       // {w0:{P1:true,...,C:false}, ...}
          const keys = Object.keys(labels);
          html += `<div class="anno-section"><h5>Formula Truth by World</h5>`;
          html += `<div class="formula-legend">` +
                  keys.map(k => `<span class="formula-chip">${k}: ${labels[k]}</span>`).join(' ') +
                  `</div>`;
          worlds.forEach(w=>{
            html += `<div class="anno-row"><strong>${w.id}</strong>: `;
            keys.forEach(k=>{
              const val = truth[w.id] ? truth[w.id][k] : false;
              const cls = k === 'C' ? 'conclusion' : 'premise';
              html += `<span class="formula-state ${cls} ${val?'true':'false'}">${k}</span>`;
            });
            html += `</div>`;
          });
          html += `</div>`;
        }
  
        html += `</div>`;
      }
  
      // Accessibility list (text)
      if (edges && edges.length) {
        html += '<div class="accessibility-relations"><h5>Accessibility Relations</h5>';
        edges.forEach(e=>{
          html += `<div class="accessibility-edge">${e.from} → ${e.to}${e.properties?` (${e.properties.join(', ')})`:''}</div>`;
        });
        html += '</div>';
      }
  
      html += `</div>`; // close kripke-viz
      el.innerHTML = html;
    }
  
    displayFiniteStructure(struct) {
      const el = document.getElementById('finite-structure-container');
      if (!struct) { el.innerHTML = '<p>No structure.</p>'; return; }
      let html = '<div class="structure">';
      // Domain
      html += '<div class="structure-section"><h4>Domain</h4>';
      html += `<div class="structure-domain">${(struct.domain||[]).join(', ')}</div></div>`;
      // Predicates
      if (struct.predicates && Object.keys(struct.predicates).length) {
        html += '<div class="structure-section"><h4>Predicates</h4>';
        Object.entries(struct.predicates).forEach(([name,info])=>{
          html += `<div class="predicate-card"><div class="predicate-name">${name}/${info.arity}</div>`;
          if (info.tuples && info.tuples.length) {
            html += '<table class="predicate-table"><thead><tr>';
            for (let i=0;i<info.arity;i++) html += `<th>arg${i+1}</th>`;
            html += '</tr></thead><tbody>';
            info.tuples.forEach(t=>{
              html += '<tr>' + t.map(x=>`<td>${x}</td>`).join('') + '</tr>';
            });
            html += '</tbody></table>';
          } else {
            html += '<div class="predicate-empty">No true tuples</div>';
          }
          html += '</div>';
        });
        html += '</div>';
      }
      html += '</div>';
      el.innerHTML = html;
    }
  
    showNoDataMessage() {
      const results = document.getElementById('results-container');
      const msg = document.createElement('div');
      msg.className = 'no-data-message';
      msg.innerHTML = '<p>No visualization data available for this result.</p>';
      const existing = results.querySelector('.no-data-message');
      if (existing) existing.remove();
      results.appendChild(msg);
    }
  
    // ===== Examples =====
  
    async loadExamples() {
      try {
        const r = await fetch('/api/examples');
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
        const ex = await r.json();
        this.displayExamples(ex);
      } catch (e) {
        console.error('Failed to load examples:', e);
        document.getElementById('examples-grid').innerHTML =
          `<p>Failed to load examples: ${e.message}</p>`;
      }
    }
  
    displayExamples(ex) {
      const container = document.getElementById('examples-grid');
      let html = '';
      if (ex.propositional) ex.propositional.forEach(x => html += this._exampleCard('PL', x));
      if (ex.modal)         ex.modal.forEach(x => html += this._exampleCard('MODAL', x));
      if (ex.fol)           ex.fol.forEach(x => html += this._exampleCard('FOL', x));
      container.innerHTML = html;
  
      // Delegated click handler: clicking any example fills the workspace
      container.addEventListener('click', (evt) => {
        const card = evt.target.closest('.example-card');
        if (!card) return;
  
        const logic = card.dataset.logic;                 // "PL" | "MODAL" | "FOL"
        const example = JSON.parse(card.dataset.example); // {name, premises, conclusion, description, settings?}
  
        // Switch to workspace and set logic
        this.switchTab('workspace');
        const logicSel = document.getElementById('logic-type');
        logicSel.value = logic;
        this.updateLogicSettings(); // show relevant settings panel
  
        // Fill premises & conclusion
        const premisesField = document.getElementById('premises');
        const conclusionField = document.getElementById('conclusion');
        premisesField.value = Array.isArray(example.premises) ? example.premises.join('\n') : (example.premises || '');
        conclusionField.value = example.conclusion || '';
  
        // Apply example-specific settings if present
        const settings = example.settings || {};
  
        if (logic === 'MODAL') {
          const frameSel = document.getElementById('modal-frame');
          // Prefer explicit setting; otherwise guess from example name
          if (settings.modalFrame) {
            frameSel.value = settings.modalFrame;
          } else if (typeof example.name === 'string') {
            const name = example.name.toUpperCase();
            if (name.includes('S5')) frameSel.value = 'S5';
            else if (name.includes('S4')) frameSel.value = 'S4';
            else if (/\bT\b/.test(name)) frameSel.value = 'T';
            else frameSel.value = 'K';
          } else {
            frameSel.value = 'K';
          }
        }
  
        if (logic === 'FOL') {
          const dom = document.getElementById('fol-domain');
          const depth = document.getElementById('fol-depth');
          if (Number.isInteger(settings.domainSize)) dom.value = settings.domainSize;
          if (Number.isInteger(settings.termDepth)) depth.value = settings.termDepth;
        }
  
        // Optional: focus conclusion for quick edits
        conclusionField.focus();
      });
    }
  
    _exampleCard(logic, ex) {
      // Store full example (incl. settings) into data-example
      const safe = JSON.stringify(ex).replace(/"/g, '&quot;');
      return `
        <div class="example-card" data-logic="${logic}" data-example="${safe}">
          <h3>${ex.name}</h3>
          <p>${ex.description || ''}</p>
          <div class="example-formula">
            <div class="example-premises"><strong>Premises:</strong> ${Array.isArray(ex.premises) ? ex.premises.join(', ') : ex.premises}</div>
            <div class="example-conclusion"><strong>Conclusion:</strong> ${ex.conclusion}</div>
          </div>
        </div>`;
    }
  }
  
  document.addEventListener('DOMContentLoaded', () => new TruthToolApp());
  