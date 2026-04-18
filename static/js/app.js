// Tab switching functionality (banner pills)
let activeSearchTab = 'bills';

document.addEventListener('DOMContentLoaded', function() {
    const tabButtons = document.querySelectorAll('.top-banner .tab-button[data-tab]');
    const mainPanels = document.querySelectorAll('.main-panel');

    function activateTab(tabName) {
        activeSearchTab = tabName;
        mainPanels.forEach(panel => {
            const isActive = panel.getAttribute('data-tab-content') === tabName;
            panel.classList.toggle('active', isActive);
        });

        tabButtons.forEach(btn => {
            const isMatch = btn.getAttribute('data-tab') === tabName;
            btn.classList.toggle('active', isMatch);
            btn.setAttribute('aria-selected', isMatch ? 'true' : 'false');
        });
    }

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            activateTab(button.getAttribute('data-tab'));
        });
    });

    const constructionSection = document.getElementById('construction-resources-section');
    const constructionToggle = document.getElementById('construction-resources-toggle');
    const constructionChevron = document.getElementById('construction-resources-chevron');
    const constructionQuickToggle = document.getElementById('construction-quick-toggle');
    const constructionQuickSubmenu = document.getElementById('construction-quick-submenu');
    const constructionQuickChevron = document.getElementById('construction-quick-chevron');
    const codeRefModal = document.getElementById('code-ref-modal');
    const codeRefBtn = document.getElementById('construction-code-ref-btn');
    const codeRefClose = document.getElementById('code-ref-close');

    function runWacQuickSearch(term) {
        const wacInput = document.getElementById('wac-search');
        if (!wacInput) {
            window.location.href = '/?wac_q=' + encodeURIComponent(term);
            return;
        }
        activateTab('wac');
        wacInput.value = term;
        searchWAC(term);
    }

    function openCodeRefModal() {
        if (!codeRefModal) {
            return;
        }
        codeRefModal.removeAttribute('hidden');
        document.body.style.overflow = 'hidden';
    }

    function closeCodeRefModal() {
        if (!codeRefModal) {
            return;
        }
        codeRefModal.setAttribute('hidden', '');
        document.body.style.overflow = '';
    }

    if (constructionToggle && constructionSection) {
        constructionToggle.addEventListener('click', () => {
            const isExpanded = constructionSection.classList.toggle('is-expanded');
            constructionToggle.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
            if (constructionChevron) {
                constructionChevron.textContent = isExpanded ? '▼' : '▶';
            }
        });
    }

    if (constructionQuickToggle && constructionQuickSubmenu) {
        constructionQuickToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isHidden = constructionQuickSubmenu.hasAttribute('hidden');
            if (isHidden) {
                constructionQuickSubmenu.removeAttribute('hidden');
                constructionQuickToggle.setAttribute('aria-expanded', 'true');
                if (constructionQuickChevron) {
                    constructionQuickChevron.textContent = '▼';
                }
            } else {
                constructionQuickSubmenu.setAttribute('hidden', '');
                constructionQuickToggle.setAttribute('aria-expanded', 'false');
                if (constructionQuickChevron) {
                    constructionQuickChevron.textContent = '▶';
                }
            }
        });
    }

    document.querySelectorAll('.construction-wac-quick').forEach(btn => {
        btn.addEventListener('click', () => {
            const term = btn.getAttribute('data-wac-term') || '';
            runWacQuickSearch(term);
        });
    });

    if (codeRefBtn) {
        codeRefBtn.addEventListener('click', openCodeRefModal);
    }
    if (codeRefClose) {
        codeRefClose.addEventListener('click', closeCodeRefModal);
    }
    if (codeRefModal) {
        codeRefModal.addEventListener('click', (e) => {
            if (e.target === codeRefModal) {
                closeCodeRefModal();
            }
        });
    }
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeCodeRefModal();
        }
    });

    const urlParams = new URLSearchParams(window.location.search);
    const wacQ = urlParams.get('wac_q');
    if (wacQ && document.getElementById('wac-search')) {
        runWacQuickSearch(wacQ);
        history.replaceState({}, '', window.location.pathname);
    }
    if (urlParams.get('tab') === 'county' && document.getElementById('county-search')) {
        activateTab('county');
        history.replaceState({}, '', window.location.pathname);
    }
    
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
    
    // County codes search (natural language; Perplexity)
    const countySearchBtn = document.getElementById('search-county-btn');
    const countySearchInput = document.getElementById('county-search');

    if (countySearchBtn && countySearchInput) {
        countySearchBtn.addEventListener('click', () => {
            const searchTerm = countySearchInput.value.trim();
            if (!searchTerm) {
                alert('Please enter a topic or code section');
                return;
            }

            searchCountyCodes(searchTerm);
        });

        countySearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                countySearchBtn.click();
            }
        });
    }
    
    // Research & News Search Handler
    const researchSearchBtn = document.getElementById('search-research-btn');
    const researchSearchInput = document.getElementById('research-search');
    
    if (researchSearchBtn && researchSearchInput) {
        researchSearchBtn.addEventListener('click', () => {
            const searchTerm = researchSearchInput.value.trim();
            if (!searchTerm) {
                alert('Please enter a research query');
                return;
            }
            
            searchResearch(searchTerm);
        });
        
        researchSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                researchSearchBtn.click();
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

function searchCountyCodes(searchTerm) {
    showLoading();

    fetch('/api/search/county', {
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
        displayError('Error searching county codes: ' + error.message);
    });
}

function searchResearch(searchTerm) {
    showLoading();
    
    fetch('/api/search/research', {
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
        displayError('Error performing research: ' + error.message);
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

const COMMITTEE_LISTING_URL = 'https://app.leg.wa.gov/legislature/pages/committeelisting.aspx';

function escapeHtml(text) {
    if (text == null || text === undefined) {
        return '';
    }
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function externalLinkMarkerHtml() {
    return '<span class="result-external-marker" aria-hidden="true"> ↗</span>';
}

function getSessionStartYear() {
    const el = document.getElementById('biennium');
    if (!el || !el.value) {
        return new Date().getFullYear();
    }
    const m = /^(\d{4})/.exec(el.value);
    return m ? parseInt(m[1], 10) : new Date().getFullYear();
}

function buildBillSummaryUrl(billNumberToken, year) {
    const bn = String(billNumberToken).trim();
    const y = Number(year) && Number(year) > 1900 ? Number(year) : getSessionStartYear();
    return `https://app.leg.wa.gov/billsummary?BillNumber=${encodeURIComponent(bn)}&Year=${y}`;
}

function shouldLinkBillHeading(billId) {
    if (billId == null || billId === undefined) {
        return false;
    }
    const s = String(billId).trim();
    if (/[\uD800-\uDBFF][\uDC00-\uDFFF]/.test(s) || /^[\u2600-\u27BF]/.test(s)) {
        return false;
    }
    return /^(?:(?:ES|SS|SH)?(?:HB|SB|HJR|SJR|HCR|SCR))\s+\d+/i.test(s);
}

function sponsorChamberFromBillId(billId) {
    const t = String(billId || '').trim().toUpperCase().replace(/\s+/g, ' ');
    if (/^(ESSB|SSB|SB|SJR|SCR|SJM)\b/.test(t)) {
        return 'senate';
    }
    return 'house';
}

function sponsorListingUrl(billId) {
    return sponsorChamberFromBillId(billId) === 'senate'
        ? 'https://leg.wa.gov/senate/senators'
        : 'https://leg.wa.gov/house/representatives';
}

function shouldLinkSponsorName(name) {
    if (!name || !String(name).trim()) {
        return false;
    }
    return !/^(claude ai|perplexity)/i.test(String(name).trim());
}

function formatBillTitleHtml(billId, sessionYear) {
    const y = sessionYear != null ? Number(sessionYear) : getSessionStartYear();
    const label = escapeHtml(String(billId));
    if (!shouldLinkBillHeading(billId)) {
        return label;
    }
    const href = escapeHtml(buildBillSummaryUrl(billId, y));
    return `<a class="result-external-link" href="${href}" target="_blank" rel="noopener noreferrer">${label}${externalLinkMarkerHtml()}</a>`;
}

function formatSponsorHtml(name, billId) {
    const label = escapeHtml(String(name));
    if (!shouldLinkSponsorName(name)) {
        return label;
    }
    const href = escapeHtml(sponsorListingUrl(billId));
    return `<a class="result-external-link" href="${href}" target="_blank" rel="noopener noreferrer">${label}${externalLinkMarkerHtml()}</a>`;
}

function isCommitteeCard(result) {
    if (!result || !result.Name || result.ResearchType) {
        return false;
    }
    if (result.BillNumber) {
        return false;
    }
    if (result.BillId && shouldLinkBillHeading(result.BillId)) {
        return false;
    }
    return Object.prototype.hasOwnProperty.call(result, 'Agency')
        && result.Id !== undefined
        && result.Id !== null;
}

function applyInlineLegislativeLinks(escapedText, ctx) {
    const sessionYear = ctx && ctx.sessionYear != null ? Number(ctx.sessionYear) : getSessionStartYear();
    const countyWebsite = ctx && ctx.countyWebsite ? String(ctx.countyWebsite).trim() : '';
    let s = escapedText;

    s = s.replace(/\bRCW\s+(\d+(?:\.\d+)*)\b/gi, (match, cite) => {
        const c = encodeURIComponent(cite);
        return `<a class="result-external-link" href="https://app.leg.wa.gov/RCW/default.aspx?cite=${c}" target="_blank" rel="noopener noreferrer">${escapeHtml('RCW ' + cite)}${externalLinkMarkerHtml()}</a>`;
    });

    s = s.replace(/\bWAC\s+([\d]+(?:-[\d]+)*)\b/gi, (match, cite) => {
        const c = encodeURIComponent(cite);
        return `<a class="result-external-link" href="https://app.leg.wa.gov/WAC/default.aspx?cite=${c}" target="_blank" rel="noopener noreferrer">${escapeHtml('WAC ' + cite)}${externalLinkMarkerHtml()}</a>`;
    });

    if (countyWebsite && /^https?:\/\//i.test(countyWebsite)) {
        const safeCounty = escapeHtml(countyWebsite);
        s = s.replace(/\bKCC\s+([\d.]+)\b/gi, (match, sec) => {
            return `<a class="result-external-link" href="${safeCounty}" target="_blank" rel="noopener noreferrer">${escapeHtml('KCC ' + sec)}${externalLinkMarkerHtml()}</a>`;
        });
    }

    s = s.replace(/\b((?:ES|SS|SH)?(?:HB|SB|HJR|SJR|HCR|SCR))\s+(\d+)\b/gi, (match, prefix, num) => {
        const token = `${prefix} ${num}`;
        const href = escapeHtml(buildBillSummaryUrl(token, sessionYear));
        return `<a class="result-external-link" href="${href}" target="_blank" rel="noopener noreferrer">${escapeHtml(token)}${externalLinkMarkerHtml()}</a>`;
    });

    return s;
}

function formatInlineSnippet(text, linkContext) {
    let t = escapeHtml(String(text));
    t = applyInlineLegislativeLinks(t, linkContext || {});
    return t;
}

function formatDescription(text, linkContext) {
    if (text == null || text === undefined) {
        return '';
    }
    let t = escapeHtml(String(text));
    t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    t = applyInlineLegislativeLinks(t, linkContext || {});
    const paragraphs = t.split('\n\n');
    return paragraphs.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
}

function buildCitationListHtml(citations) {
    if (!citations || !citations.length) {
        return '';
    }
    const items = [];
    citations.forEach(c => {
        const url = (c && c.url) ? String(c.url).trim() : '';
        if (!/^https?:\/\//i.test(url)) {
            return;
        }
        const title = ((c && c.title) ? String(c.title).trim() : '') || url;
        const href = escapeHtml(url);
        items.push(
            `<li><a class="citation-link result-external-link" href="${href}" target="_blank" rel="noopener noreferrer">${escapeHtml(title)}${externalLinkMarkerHtml()}</a></li>`
        );
    });
    if (!items.length) {
        return '';
    }
    return `
        <div class="citation-section">
            <h4 class="citation-heading">Sources</h4>
            <ul class="citation-list">${items.join('')}</ul>
        </div>
    `;
}

function resolveResultTitle(result) {
    return result.BillId || result.BillNumber || result.Name || 'Result';
}

function getTopSourceBadgeHtml(results) {
    const first = Array.isArray(results) && results.length ? results[0] : null;
    const liveBadge = '<span style="background: #10b981; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; display: inline-block;">✅ Live API Data</span>';
    const webBadge = '<span style="background: #3b82f6; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; display: inline-block;">🔍 Web Research</span>';

    if (first && first.ResearchType === 'rcw_combined') {
        return `<div style="margin-bottom: 1rem;">${webBadge} ${liveBadge}</div>`;
    }
    if (activeSearchTab === 'wac' || activeSearchTab === 'county' || activeSearchTab === 'research') {
        return `<div style="margin-bottom: 1rem;">${webBadge}</div>`;
    }
    if (activeSearchTab === 'committees' || activeSearchTab === 'bills') {
        return `<div style="margin-bottom: 1rem;">${liveBadge}</div>`;
    }
    if (activeSearchTab === 'rcw') {
        return `<div style="margin-bottom: 1rem;">${webBadge} ${liveBadge}</div>`;
    }
    return '';
}

function getSourceBadgesHtml(result, opts = {}) {
    const badges = [];
    const isCommittee = !!opts.isCommittee;
    const isWebResearch = result.ResearchType === 'wac_web_research'
        || result.ResearchType === 'county_web_research';
    const isResearchNews = (result.BillId || '') === '🔍 Research & News';

    if (isCommittee) {
        badges.push('<span class="result-badge result-badge--live">✅ Live API Data</span>');
    } else if (isWebResearch) {
        badges.push('<span class="result-badge result-badge--web">🔍 Web Research</span>');
    } else if (isResearchNews) {
        badges.push('<span class="result-badge result-badge--web">🔍 Web Research</span>');
        badges.push('<span class="result-badge result-badge--news">📰 Real-time News</span>');
    } else if (result.ResearchType !== 'rcw_combined') {
        // Bills and other SOAP-backed records default to live API data.
        badges.push('<span class="result-badge result-badge--live">✅ Live API Data</span>');
    }

    return badges.join('');
}

function renderRcwCombinedHtml(result, sessionYear) {
    const rcwCite = result.RcwCitation || '';
    const officialUrl = result.OfficialRcwUrl || `https://app.leg.wa.gov/RCW/default.aspx?cite=${encodeURIComponent(rcwCite)}`;
    const bills = Array.isArray(result.AffectedBills) ? result.AffectedBills : [];

    let html = `
        <div class="result-subsection">
            <div class="result-subsection-header">
                <h3 class="result-subsection-title">What RCW ${escapeHtml(rcwCite)} Says</h3>
                <span class="result-badge result-badge--web">🔍 Web Research</span>
            </div>
            <div class="result-description">${formatDescription(result.RcwSummary || '', { sessionYear })}</div>
            ${buildCitationListHtml(result.RcwCitations)}
            <a class="result-external-link rcw-official-link" href="${escapeHtml(officialUrl)}" target="_blank" rel="noopener noreferrer">📖 View Official RCW ${escapeHtml(rcwCite)}${externalLinkMarkerHtml()}</a>
        </div>
        <div class="result-subsection result-subsection--live">
            <div class="result-subsection-header">
                <h3 class="result-subsection-title">Recent Bills Affecting RCW ${escapeHtml(rcwCite)}</h3>
                <span class="result-badge result-badge--live">✅ Live API Data</span>
            </div>
    `;

    if (!bills.length) {
        html += `<p class="result-description">No recent legislation affects this RCW.</p>`;
    } else {
        html += '<div class="rcw-bill-list">';
        bills.forEach(b => {
            const billNo = (b.BillNumber || '').trim();
            const title = (b.Title || '').trim() || 'No title available';
            const status = (b.Status || '').trim() || 'Status unavailable';
            const billLink = billNo
                ? `<a class="result-external-link" href="${escapeHtml(buildBillSummaryUrl(billNo, b.SessionYear || sessionYear))}" target="_blank" rel="noopener noreferrer">${escapeHtml(billNo)}${externalLinkMarkerHtml()}</a>`
                : 'Unknown bill';
            html += `
                <div class="rcw-bill-item">
                    <div class="rcw-bill-title">${billLink}</div>
                    <div class="rcw-bill-desc">${formatInlineSnippet(title, { sessionYear })}</div>
                    <div class="rcw-bill-status"><span class="meta-label">Status:</span> ${formatInlineSnippet(status, { sessionYear })}</div>
                </div>
            `;
        });
        html += '</div>';
    }

    html += '</div>';
    return html;
}

function displayResults(results) {
    const resultsContainer = document.getElementById('results-container');
    const resultsContent = document.getElementById('results-content');
    const badgeContainer = document.getElementById('results-source-badge');
    
    if (!Array.isArray(results)) {
        results = [results];
    }
    
    resultsContent.innerHTML = '';
    
    // SET THE BADGE HTML HERE
    if (badgeContainer) {
        badgeContainer.innerHTML = getTopSourceBadgeHtml(results);
    }
    
    results.forEach(result => {
        const card = document.createElement('div');
        card.className = 'result-card';

        const sessionYear = result.SessionYear != null ? Number(result.SessionYear) : getSessionStartYear();
        const linkContext = {
            sessionYear,
            countyWebsite: result.CountyWebsite || '',
            countySlug: result.CountySlug || ''
        };

        const isWebResearch = result.ResearchType === 'wac_web_research'
            || result.ResearchType === 'county_web_research';
        const titleRaw = resolveResultTitle(result);
        const committee = isCommitteeCard(result);
        let html = '';

        if (result.ResearchType === 'rcw_combined') {
            card.innerHTML = renderRcwCombinedHtml(result, sessionYear);
            resultsContent.appendChild(card);
            return;
        }

        if (committee) {
            html += `
                <div class="result-title-row">
                    <h3 class="result-title"><a class="result-external-link" href="${escapeHtml(COMMITTEE_LISTING_URL)}" target="_blank" rel="noopener noreferrer">${escapeHtml(result.Name)}${externalLinkMarkerHtml()}</a></h3>
                    ${getSourceBadgesHtml(result, { isCommittee: true })}
                </div>
            `;
            if (result.Agency) {
                html += `<div class="result-meta"><div class="meta-item"><span class="meta-label">Chamber:</span><span>${escapeHtml(result.Agency)}</span></div></div>`;
            }
            if (result.LongName) {
                html += `<div class="result-description">${formatDescription(result.LongName, linkContext)}</div>`;
            }
            card.innerHTML = html;
            resultsContent.appendChild(card);
            return;
        }

        if (isWebResearch) {
            html += `
                <div class="result-title-row">
                    <h3 class="result-title">${escapeHtml(String(titleRaw))}</h3>
                    ${getSourceBadgesHtml(result)}
                </div>
            `;
        } else {
            const titleHtml = shouldLinkBillHeading(titleRaw)
                ? formatBillTitleHtml(titleRaw, sessionYear)
                : escapeHtml(String(titleRaw));
            html += `
                <div class="result-title-row">
                    <h3 class="result-title">${titleHtml}</h3>
                    ${getSourceBadgesHtml(result)}
                </div>
            `;
        }

        if (result.PrimeSponsorName || result.Agency) {
            html += '<div class="result-meta">';

            if (result.PrimeSponsorName && !isWebResearch) {
                const billRef = result.BillId || result.BillNumber || '';
                html += `
                    <div class="meta-item">
                        <span class="meta-label">Sponsor:</span>
                        <span>${formatSponsorHtml(result.PrimeSponsorName, billRef)}</span>
                    </div>
                `;
            }

            if (result.CurrentStatus && result.CurrentStatus.BillStatus) {
                html += `
                    <div class="meta-item">
                        <span class="meta-label">Status:</span>
                        <span>${formatInlineSnippet(result.CurrentStatus.BillStatus, linkContext)}</span>
                    </div>
                `;
            }

            html += '</div>';
        }

        if (isWebResearch && result.DataSourceNote) {
            html += `<p class="data-source-note">${escapeHtml(result.DataSourceNote)}</p>`;
        }

        const bodyText = result.LongDescription || result.Summary || result.Text;
        if (bodyText) {
            html += `<div class="result-description">${formatDescription(bodyText, linkContext)}</div>`;
        }

        if (result.ShortDescription) {
            html += `<div class="result-description"><em>${formatDescription(result.ShortDescription, linkContext)}</em></div>`;
        }

        if (isWebResearch) {
            html += buildCitationListHtml(result.Citations);
        }

        card.innerHTML = html;
        resultsContent.appendChild(card);
    });
    
    resultsContainer.style.display = 'block';
}

function displayError(message) {
    const resultsContainer = document.getElementById('results-container');
    const resultsContent = document.getElementById('results-content');
    const badgeContainer = document.getElementById('results-source-badge');
    if (badgeContainer) {
        badgeContainer.innerHTML = '';
    }
    
    resultsContent.innerHTML = `
        <div class="result-card" style="border-left-color: #e74c3c;">
            <h3 class="result-title" style="color: #e74c3c;">Error</h3>
            <div class="result-description">${formatDescription(String(message), {})}</div>
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
    const badgeContainer = document.getElementById('results-source-badge');
    if (badgeContainer) {
        badgeContainer.innerHTML = '';
    }
}