// Tab switching functionality
document.addEventListener('DOMContentLoaded', function() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');
            
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            const activeContent = document.querySelector(`[data-tab-content="${tabName}"]`);
            if (activeContent) {
                activeContent.classList.add('active');
            }
        });
    });
    
    // Bill Search Handler
    const billSearchBtn = document.getElementById('search-bills-btn');
    const billSearchInput = document.getElementById('bill-search');
    
    if (billSearchBtn && billSearchInput) {
        billSearchBtn.addEventListener('click', () => {
            const searchTerm = billSearchInput.value.trim();
            const biennium = document.getElementById('biennium').value;
            
            if (!searchTerm) {
                alert('Please enter a bill number or search term');
                return;
            }
            
            searchLegislation(searchTerm, biennium);
        });
        
        billSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                billSearchBtn.click();
            }
        });
    }
    
    // RCW Search Handler
    const rcwSearchBtn = document.getElementById('search-rcw-btn');
    const rcwSearchInput = document.getElementById('rcw-search');
    
    if (rcwSearchBtn && rcwSearchInput) {
        rcwSearchBtn.addEventListener('click', () => {
            const rcwCite = rcwSearchInput.value.trim();
            const biennium = document.getElementById('biennium').value;
            
            searchRCW(rcwCite, biennium);
        });
        
        rcwSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                rcwSearchBtn.click();
            }
        });
    }
    
    // WAC Search Handler
    const wacSearchBtn = document.getElementById('search-wac-btn');
    const wacSearchInput = document.getElementById('wac-search');
    
    if (wacSearchBtn && wacSearchInput) {
        wacSearchBtn.addEventListener('click', () => {
            const searchTerm = wacSearchInput.value.trim();
            if (!searchTerm) {
                alert('Please enter a WAC section or topic');
                return;
            }
            
            searchWAC(searchTerm);
        });
        
        wacSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                wacSearchBtn.click();
            }
        });
    }
    
    // Committees Handler
    const committeesBtn = document.getElementById('load-committees-btn');
    
    if (committeesBtn) {
        committeesBtn.addEventListener('click', () => {
            loadCommittees();
        });
    }
    
    // Clear Results Handler
    const clearBtn = document.getElementById('clear-results');
    
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            hideResults();
        });
    }
});

function searchLegislation(searchTerm, biennium) {
    showLoading();
    
    fetch('/api/search/legislation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            search_term: searchTerm,
            biennium: biennium
        }),
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            displayResults(data.data);
        } else {
            displayError(data.error);
        }
    })
    .catch(error => {
        hideLoading();
        displayError('Error searching legislation: ' + error.message);
    });
}

function searchRCW(rcwCite, biennium) {
    showLoading();
    
    fetch('/api/search/rcw', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            rcw_cite: rcwCite,
            biennium: biennium
        }),
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            displayResults(data.data);
        } else {
            displayError(data.error);
        }
    })
    .catch(error => {
        hideLoading();
        displayError('Error searching RCW: ' + error.message);
    });
}

function searchWAC(searchTerm) {
    showLoading();
    
    fetch('/api/search/wac', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            search_term: searchTerm
        }),
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            displayResults(data.data);
        } else {
            displayError(data.error);
        }
    })
    .catch(error => {
        hideLoading();
        displayError('Error searching WAC: ' + error.message);
    });
}

function loadCommittees() {
    showLoading();
    
    fetch('/api/committees')
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            displayResults(data.data);
        } else {
            displayError(data.error);
        }
    })
    .catch(error => {
        hideLoading();
        displayError('Error loading committees: ' + error.message);
    });
}

function displayResults(results) {
    const resultsContainer = document.getElementById('results-container');
    const resultsContent = document.getElementById('results-content');
    
    if (!Array.isArray(results)) {
        results = [results];
    }
    
    resultsContent.innerHTML = '';
    
    results.forEach(result => {
        const card = document.createElement('div');
        card.className = 'result-card';
        
        let html = `<h3 class="result-title">${result.BillId || result.Name || 'Result'}</h3>`;
        
        if (result.PrimeSponsorName || result.Agency) {
            html += '<div class="result-meta">';
            
            if (result.PrimeSponsorName) {
                html += `
                    <div class="meta-item">
                        <span class="meta-label">Sponsor:</span>
                        <span>${result.PrimeSponsorName}</span>
                    </div>
                `;
            }
            
            if (result.CurrentStatus && result.CurrentStatus.BillStatus) {
                html += `
                    <div class="meta-item">
                        <span class="meta-label">Status:</span>
                        <span>${result.CurrentStatus.BillStatus}</span>
                    </div>
                `;
            }
            
            html += '</div>';
        }
        
        if (result.LongDescription) {
            html += `<div class="result-description">${formatDescription(result.LongDescription)}</div>`;
        }
        
        if (result.ShortDescription) {
            html += `<div class="result-description"><em>${formatDescription(result.ShortDescription)}</em></div>`;
        }
        
        card.innerHTML = html;
        resultsContent.appendChild(card);
    });
    
    resultsContainer.style.display = 'block';
}

function formatDescription(text) {
    // Convert markdown-style bold to HTML
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert newlines to paragraphs
    const paragraphs = text.split('\n\n');
    return paragraphs.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
}

function displayError(message) {
    const resultsContainer = document.getElementById('results-container');
    const resultsContent = document.getElementById('results-content');
    
    resultsContent.innerHTML = `
        <div class="result-card" style="border-left-color: #e74c3c;">
            <h3 class="result-title" style="color: #e74c3c;">Error</h3>
            <div class="result-description">${formatDescription(message)}</div>
        </div>
    `;
    
    resultsContainer.style.display = 'block';
}

function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function hideResults() {
    document.getElementById('results-container').style.display = 'none';
}
