// Washington State Legislative Code Explorer - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Tab switching
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Update active states
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            button.classList.add('active');
            document.querySelector(`[data-tab-content="${tabName}"]`).classList.add('active');
        });
    });
    
    // Search handlers
    document.getElementById('search-bills-btn').addEventListener('click', searchBills);
    document.getElementById('search-rcw-btn').addEventListener('click', searchRCW);
    document.getElementById('load-committees-btn').addEventListener('click', loadCommittees);
    document.getElementById('clear-results').addEventListener('click', clearResults);
    
    // Enter key support
    document.getElementById('bill-search').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchBills();
    });
    
    document.getElementById('rcw-search').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchRCW();
    });
});

function showLoading() {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results-container').style.display = 'none';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showResults() {
    document.getElementById('results-container').style.display = 'block';
}

function clearResults() {
    document.getElementById('results-content').innerHTML = '';
    document.getElementById('results-container').style.display = 'none';
}

async function searchBills() {
    const searchTerm = document.getElementById('bill-search').value.trim();
    const biennium = document.getElementById('biennium').value;
    
    if (!searchTerm) {
        alert('Please enter a bill number');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch('/api/search/legislation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                search_term: searchTerm,
                biennium: biennium
            })
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.success) {
            displayLegislationResults(data.data);
        } else {
            displayError(data.error);
        }
    } catch (error) {
        hideLoading();
        displayError('Failed to connect to the server. Please try again.');
    }
}

async function searchRCW() {
    const rcwCite = document.getElementById('rcw-search').value.trim();
    const biennium = document.getElementById('biennium').value;
    
    showLoading();
    
    try {
        const response = await fetch('/api/search/rcw', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rcw_cite: rcwCite,
                biennium: biennium
            })
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.success) {
            displayRCWResults(data.data, rcwCite);
        } else {
            displayError(data.error);
        }
    } catch (error) {
        hideLoading();
        displayError('Failed to connect to the server. Please try again.');
    }
}

async function loadCommittees() {
    showLoading();
    
    try {
        const response = await fetch('/api/committees');
        const data = await response.json();
        
        hideLoading();
        
        if (data.success) {
            displayCommitteeResults(data.data);
        } else {
            displayError(data.error);
        }
    } catch (error) {
        hideLoading();
        displayError('Failed to connect to the server. Please try again.');
    }
}

function displayLegislationResults(data) {
    const resultsContent = document.getElementById('results-content');
    
    if (!data || (Array.isArray(data) && data.length === 0)) {
        resultsContent.innerHTML = `
            <div class="result-card">
                <p>No legislation found matching your search.</p>
            </div>
        `;
        showResults();
        return;
    }
    
    // Handle both single result and array of results
    const items = Array.isArray(data) ? data : [data];
    
    resultsContent.innerHTML = items.map(item => {
        const billNumber = item.BillId || item.billNumber || 'Unknown';
        const title = item.LongDescription || item.ShortDescription || 'No title available';
        const sponsor = item.PrimeSponsorName || item.sponsor || 'Unknown';
        const status = item.CurrentStatus?.BillStatus || item.status || 'Unknown';
        
        return `
            <div class="result-card">
                <h4 class="result-title">${escapeHtml(billNumber)}</h4>
                <div class="result-meta">
                    <div class="meta-item">
                        <span class="meta-label">Sponsor:</span>
                        <span>${escapeHtml(sponsor)}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Status:</span>
                        <span>${escapeHtml(status)}</span>
                    </div>
                </div>
                <div class="result-description">
                    ${escapeHtml(title)}
                </div>
            </div>
        `;
    }).join('');
    
    showResults();
}

function displayRCWResults(data, searchTerm) {
    const resultsContent = document.getElementById('results-content');
    
    if (!data || (Array.isArray(data) && data.length === 0)) {
        resultsContent.innerHTML = `
            <div class="result-card">
                <p>No RCW citations found${searchTerm ? ` for "${searchTerm}"` : ''}.</p>
            </div>
        `;
        showResults();
        return;
    }
    
    const items = Array.isArray(data) ? data : [data];
    
    resultsContent.innerHTML = `
        <div class="result-card">
            <h4 class="result-title">RCW Citations Affected</h4>
            <div class="result-description">
                ${searchTerm ? `<p><strong>Searching for:</strong> ${escapeHtml(searchTerm)}</p>` : ''}
                <p>Found ${items.length} result(s)</p>
                <div style="margin-top: 1rem; font-family: var(--font-mono); font-size: 0.9rem;">
                    ${items.slice(0, 50).map(item => `
                        <div style="padding: 0.5rem; border-bottom: 1px solid var(--border);">
                            ${escapeHtml(JSON.stringify(item))}
                        </div>
                    `).join('')}
                    ${items.length > 50 ? '<p style="margin-top: 1rem;"><em>Showing first 50 results...</em></p>' : ''}
                </div>
            </div>
        </div>
    `;
    
    showResults();
}

function displayCommitteeResults(data) {
    const resultsContent = document.getElementById('results-content');
    
    if (!data || (Array.isArray(data) && data.length === 0)) {
        resultsContent.innerHTML = `
            <div class="result-card">
                <p>No committees found.</p>
            </div>
        `;
        showResults();
        return;
    }
    
    const items = Array.isArray(data) ? data : [data];
    
    resultsContent.innerHTML = items.map(committee => {
        const name = committee.LongName || committee.Name || 'Unknown Committee';
        const acronym = committee.Acronym || '';
        const agency = committee.Agency || 'Legislature';
        
        return `
            <div class="result-card">
                <h4 class="result-title">${escapeHtml(name)}</h4>
                <div class="result-meta">
                    ${acronym ? `
                        <div class="meta-item">
                            <span class="meta-label">Acronym:</span>
                            <span>${escapeHtml(acronym)}</span>
                        </div>
                    ` : ''}
                    <div class="meta-item">
                        <span class="meta-label">Agency:</span>
                        <span>${escapeHtml(agency)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    showResults();
}

function displayError(message) {
    const resultsContent = document.getElementById('results-content');
    resultsContent.innerHTML = `
        <div class="result-card" style="border-left-color: #d32f2f;">
            <h4 class="result-title" style="color: #d32f2f;">Error</h4>
            <div class="result-description">
                <p>${escapeHtml(message)}</p>
            </div>
        </div>
    `;
    showResults();
}

function escapeHtml(text) {
    if (typeof text !== 'string') {
        return String(text);
    }
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
