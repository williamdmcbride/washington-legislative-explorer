"""
Washington State Legislative Code Search Application
A Flask web application that connects to WA State Legislative Web Services
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from flask import Flask, render_template, request, jsonify
from zeep import Client
from zeep.exceptions import Fault
from zeep.helpers import serialize_object
import logging
import json
import re
import time
import requests
import chromadb
from chromadb.utils import embedding_functions
from anthropic import Anthropic

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize Chroma client for Fire Code
CHROMA_PATH = "data/chroma_fire_code"
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

try:
    fire_code_collection = chroma_client.get_collection(
        name="fire_code",
        embedding_function=embedding_fn
    )
    print(f"✅ Loaded Fire Code database: {fire_code_collection.count()} chunks")
except Exception as e:
    print(f"⚠️  Fire Code database not found: {e}")
    fire_code_collection = None

anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")) if os.getenv("ANTHROPIC_API_KEY") else None

# WA State Legislative Web Services URLs
LEGISLATION_SERVICE = "https://wslwebservices.leg.wa.gov/LegislationService.asmx?WSDL"
RCW_SERVICE = "https://wslwebservices.leg.wa.gov/RcwCiteAffectedService.asmx?WSDL"
DOCUMENT_SERVICE = "https://wslwebservices.leg.wa.gov/LegislativeDocumentService.asmx?WSDL"
COMMITTEE_SERVICE = "https://wslwebservices.leg.wa.gov/CommitteeService.asmx?WSDL"


def session_year_from_biennium(biennium: str) -> int:
    """First calendar year of a biennium string (e.g. 2023-24 -> 2023)."""
    if not biennium or not isinstance(biennium, str):
        return 2024
    parts = biennium.split("-")
    if parts and parts[0].isdigit() and len(parts[0]) == 4:
        return int(parts[0])
    return 2024

def call_claude_api_with_retry(client, prompt, max_tokens=1500, max_retries=3):
    """Call Claude API with retry logic for handling overload errors"""
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as api_error:
            error_message = str(api_error)
            if "overloaded" in error_message.lower() and attempt < max_retries - 1:
                logging.warning(f"API overloaded on attempt {attempt + 1}/{max_retries}, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise api_error

def _normalize_perplexity_citations(api_json):
    """Build a deduped list of {url, title} from Perplexity response fields."""
    citations = []
    seen = set()
    for url in api_json.get('citations') or []:
        if isinstance(url, str) and url.startswith('http'):
            if url not in seen:
                seen.add(url)
                citations.append({'url': url, 'title': url})
    for item in api_json.get('search_results') or []:
        if not isinstance(item, dict):
            continue
        u = (item.get('url') or '').strip()
        if not u or u in seen:
            continue
        seen.add(u)
        title = (item.get('title') or item.get('name') or u).strip()
        citations.append({'url': u, 'title': title})
    return citations


def call_perplexity_api(query, max_retries=3):
    """Call Perplexity API (model: sonar). Returns dict with answer text and citations."""
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        raise Exception("PERPLEXITY_API_KEY not found")
    
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            url = "https://api.perplexity.ai/chat/completions"
            
            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "user",
                        "content": query
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            logging.info(f"Calling Perplexity API with query: {query[:100]}...")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logging.info(f"Perplexity response status: {response.status_code}")
            
            if response.status_code != 200:
                logging.error(f"Perplexity error response: {response.text}")
            
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            citations = _normalize_perplexity_citations(data)
            return {'content': content, 'citations': citations}
            
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"Perplexity HTTP error: {http_err}")
            logging.error(f"Response text: {response.text if 'response' in locals() else 'No response'}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise Exception(f"Perplexity API returned an error. Please check your API key and try again.")
        except Exception as api_error:
            logging.error(f"Perplexity API error: {api_error}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise Exception(f"Could not connect to Perplexity API: {str(api_error)}")

def strip_all_html_from_text(text):
    """Nuclear option: Remove ALL HTML-like content from text"""
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'target\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'rel\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'style\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'href\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'class\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'>\s*(WAC|RCW|KCC)', r'\1', text)
    text = re.sub(r'["\']?\s*>', '', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()

def get_ai_search_guidance(user_query, biennium):
    """Use Claude to provide intelligent search guidance"""
    from anthropic import Anthropic
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise Exception("ANTHROPIC_API_KEY not found in environment variables")
    
    client = Anthropic(api_key=api_key)
    
    prompt = f"""You are an expert on Washington State legislation. A user is searching for: "{user_query}" in the {biennium} legislative session.

Provide helpful guidance in the following format:

1. **What they're looking for**: Brief summary of the legislative topic
2. **Common bill types**: What kind of bills typically address this
3. **Suggested bill number ranges**: Based on WA State's numbering system, suggest 3-5 specific bill numbers they might want to search for
4. **Keywords to try**: List 3-5 specific search terms
5. **Where to find more**: Suggest which legislative committees typically handle this topic
6. **Pro tip**: One insider tip about this topic in WA State legislation

Be specific, actionable, and concise. Format your response in clear sections."""

    return call_claude_api_with_retry(client, prompt, max_tokens=1500)


def search_fire_code(query, n_results=3):
    """Search Fire Code using RAG"""
    if not fire_code_collection:
        return {
            'success': False,
            'error': 'Fire Code database not initialized. Run process_fire_code.py first.'
        }

    if not anthropic_client:
        return {
            'success': False,
            'error': 'Anthropic API not configured. Set ANTHROPIC_API_KEY.'
        }

    try:
        # Search vector database
        results = fire_code_collection.query(
            query_texts=[query],
            n_results=n_results
        )

        # Extract relevant chunks
        chunks = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = {}
                metas = results.get('metadatas')
                if metas and metas[0] and i < len(metas[0]):
                    metadata = metas[0][i] or {}
                if not isinstance(metadata, dict):
                    metadata = {}
                chunks.append({
                    'text': doc,
                    'page': metadata.get('page', 'Unknown'),
                    'source': metadata.get('source', 'WAC 51-54A')
                })

        if not chunks:
            return {
                'success': False,
                'error': 'No relevant sections found in Fire Code.'
            }

        # Limit each chunk to ~500 chars to avoid rate limits
        context = "\n\n---\n\n".join([
            f"[Page {c['page']}]\n{c['text'][:500]}..." for c in chunks
        ])

        # Create Claude prompt
        prompt = f"""You are a helpful assistant for the Washington State Fire Code (WAC 51-54A).

Based on the following sections from the Fire Code, answer the user's question. Always cite the specific page numbers in your response.

FIRE CODE SECTIONS:
{context}

USER QUESTION: {query}

Provide a clear, accurate answer based on the Fire Code sections above. Always cite page numbers like this: (Page 5) or (Pages 5-7). If the sections don't fully answer the question, say so."""

        # Call Claude API
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        answer = message.content[0].text

        # Format response
        return {
            'success': True,
            'data': {
                'BillId': '🔥 Fire Code Search',
                'ResearchType': 'fire_code_rag',
                'LongDescription': answer,
                'Citations': [
                    {
                        'title': f"WAC 51-54A Page {c['page']}",
                        'url': f"#page-{c['page']}"
                    } for c in chunks
                ],
                'DataSourceNote': f'Retrieved from {len(chunks)} relevant sections of WAC 51-54A (Washington State Fire Code)'
            }
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Error searching Fire Code: {str(e)}'
        }


@app.route('/')
def index():
    """Render the main search interface"""
    return render_template('index.html')

@app.route('/about')
def about():
    """Render the about page"""
    return render_template('about.html')

@app.route('/api/search/legislation', methods=['POST'])
def search_legislation():
    """Search for legislation by bill number or get AI guidance for natural language queries"""
    try:
        data = request.json
        search_term = data.get('search_term', '').strip()
        biennium = data.get('biennium', '2023-24')
        
        if not search_term:
            return jsonify({
                'success': False,
                'error': 'Please enter a search term'
            }), 400
        
        bill_prefixes = ['HB', 'SB', 'HJR', 'SJR', 'HCR', 'SCR', 'ESSB', 'ESHB']
        is_bill_number = any(search_term.upper().startswith(prefix) for prefix in bill_prefixes)
        
        if is_bill_number:
            client = Client(LEGISLATION_SERVICE)
            try:
                result = client.service.GetLegislation(
                    biennium=biennium,
                    billNumber=search_term.upper()
                )
                
                if result:
                    session_year = session_year_from_biennium(biennium)
                    return jsonify({
                        'success': True,
                        'data': [{
                            'BillId': str(result.BillId) if hasattr(result, 'BillId') else search_term,
                            'LongDescription': str(result.LongDescription) if hasattr(result, 'LongDescription') else 'No description available',
                            'ShortDescription': str(result.ShortDescription) if hasattr(result, 'ShortDescription') else '',
                            'PrimeSponsorName': str(result.PrimeSponsorName) if hasattr(result, 'PrimeSponsorName') else 'Unknown',
                            'SessionYear': session_year,
                            'CurrentStatus': {
                                'BillStatus': str(result.CurrentStatus.BillStatus) if hasattr(result, 'CurrentStatus') and hasattr(result.CurrentStatus, 'BillStatus') else 'Unknown'
                            }
                        }]
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'No bill found for {search_term}'
                    }), 404
                    
            except Exception as e:
                logging.error(f"Error fetching bill: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Could not find bill {search_term}. Please check the bill number format.'
                }), 404
        
        try:
            logging.info(f"Getting AI guidance for: {search_term}")
            
            guidance = get_ai_search_guidance(search_term, biennium)
            
            return jsonify({
                'success': True,
                'data': [{
                    'BillId': '🤖 AI Search Assistant',
                    'LongDescription': guidance,
                    'ShortDescription': f'Search guidance for: "{search_term}"',
                    'PrimeSponsorName': 'Claude AI',
                    'CurrentStatus': {
                        'BillStatus': f'Analysis for {biennium} session'
                    }
                }]
            })
            
        except Exception as e:
            logging.error(f"AI search error: {e}")
            return jsonify({
                'success': False,
                'error': f'AI search error: {str(e)}. Try searching by bill number (e.g., HB 1001).'
            }), 500
        
    except Exception as e:
        logging.error(f"Error in search_legislation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search/wac', methods=['POST'])
def search_wac():
    """Search Washington Administrative Code via Perplexity web research (not live WAC API)."""
    try:
        data = request.json
        search_term = data.get('search_term', '').strip()
        
        if not search_term:
            return jsonify({
                'success': False,
                'error': 'Please enter a WAC section or topic'
            }), 400
        
        perplexity_query = f"{search_term} Washington Administrative Code WAC"
        logging.info(f"Perplexity WAC query: {perplexity_query[:120]}...")
        
        pr = call_perplexity_api(perplexity_query)
        answer_text = pr['content']
        citations = pr['citations']
        
        return jsonify({
            'success': True,
            'data': [{
                'BillId': '📜 WAC Search',
                'LongDescription': answer_text,
                'ShortDescription': f'Web research (WAC): "{search_term}"',
                'PrimeSponsorName': 'Perplexity · Web research',
                'CurrentStatus': {
                    'BillStatus': 'Web research (not live legislative API data)'
                },
                'ResearchType': 'wac_web_research',
                'Citations': citations,
                'DataSourceNote': (
                    'Searches use web research. For official codes, visit apps.leg.wa.gov/wac'
                ),
            }]
        })
        
    except Exception as e:
        logging.error(f"WAC search error: {e}")
        error_msg = str(e)
        return jsonify({
            'success': False,
            'error': f'WAC search error: {error_msg}'
        }), 500

@app.route('/api/search/county', methods=['POST'])
def search_county():
    """Washington county codes via Perplexity; users name counties naturally in the query."""
    try:
        data = request.json
        search_term = data.get('search_term', '').strip()

        if not search_term:
            return jsonify({
                'success': False,
                'error': 'Please enter a topic or code section'
            }), 400

        perplexity_query = (
            f"{search_term} Washington State county municipal codes ordinances "
            f"local government land use zoning building permits"
        )
        logging.info(f"Perplexity county query: {perplexity_query[:120]}...")

        pr = call_perplexity_api(perplexity_query)
        answer_text = pr['content']
        citations = pr['citations']

        return jsonify({
            'success': True,
            'data': [{
                'BillId': '🏛️ County codes search',
                'LongDescription': answer_text,
                'ShortDescription': f'County codes (web research): "{search_term}"',
                'PrimeSponsorName': 'Perplexity · Web research',
                'CurrentStatus': {
                    'BillStatus': 'Web research (not live legislative API data)'
                },
                'ResearchType': 'county_web_research',
                'Citations': citations,
                'CountySlug': '',
                'CountyWebsite': '',
                'CountyScope': 'natural_language',
                'DataSourceNote': (
                    'Searches use web research. For official codes, visit your county website'
                ),
            }]
        })

    except Exception as e:
        logging.error(f"County search error: {e}")
        error_msg = str(e)
        return jsonify({
            'success': False,
            'error': f'County search error: {error_msg}'
        }), 500

@app.route('/api/search/research', methods=['POST'])
def search_research():
    """Research legislative topics using Perplexity AI"""
    try:
        data = request.json
        search_term = data.get('search_term', '').strip()
        
        if not search_term:
            return jsonify({
                'success': False,
                'error': 'Please enter a research query'
            }), 400
        
        research_query = f"Research Washington State legislation and policy regarding: {search_term}. Include recent developments, key bills, and relevant policy context. Provide citations to official sources."

        logging.info(f"Perplexity research query: {search_term}")
        
        research_result = call_perplexity_api(research_query)
        
        return jsonify({
            'success': True,
            'data': [{
                'BillId': '🔍 Research & News',
                'LongDescription': research_result['content'],
                'ShortDescription': f'Research findings for: "{search_term}"',
                'PrimeSponsorName': 'Perplexity AI',
                'CurrentStatus': {
                    'BillStatus': 'Legislative Research'
                }
            }]
        })
        
    except Exception as e:
        logging.error(f"Research search error: {e}")
        return jsonify({
            'success': False,
            'error': f'Research error: {str(e)}'
        }), 500

@app.route('/api/search/rcw', methods=['POST'])
def search_rcw():
    """Return RCW summary + legislation affecting that cite."""
    try:
        data = request.json
        rcw_cite = (data.get('rcw_cite') or '').strip()
        biennium = data.get('biennium', '2023-24')
        session_year = session_year_from_biennium(biennium)

        if not rcw_cite:
            return jsonify({
                'success': False,
                'error': 'Please enter an RCW cite (for example, 9.41 or 9.41.010).'
            }), 400

        # 1) Web summary of what the RCW says
        rcw_query = f"{rcw_cite} Washington Revised Code of Washington"
        logging.info(f"Perplexity RCW summary query: {rcw_query}")
        rcw_summary = call_perplexity_api(rcw_query)

        # 2) Live WA Legislature API call for affected bills
        client = Client(RCW_SERVICE)
        cite_parts = [p for p in rcw_cite.split('.') if p]
        is_specific_section = len(cite_parts) >= 3
        if is_specific_section:
            api_result = client.service.GetLegislationAffectingRcwCite(
                biennium=biennium,
                rcwCite=rcw_cite
            )
        else:
            api_result = client.service.GetLegislationAffectingRcw(
                biennium=biennium,
                rcwCite=rcw_cite
            )

        rows = []
        if api_result:
            rows = api_result if isinstance(api_result, (list, tuple)) else [api_result]

        affected_bills = []
        for r in rows:
            raw = serialize_object(r)
            if not isinstance(raw, dict):
                raw = {'Raw': str(raw)}
            try:
                d = json.loads(json.dumps(raw, default=str))
            except (TypeError, ValueError):
                d = {k: str(v) for k, v in raw.items()} if isinstance(raw, dict) else {'Raw': str(raw)}
            if not isinstance(d, dict):
                d = {'Raw': str(d)}

            bill_number = (
                d.get('BillNumber')
                or d.get('BillId')
                or d.get('LegislationNumber')
                or d.get('BillNo')
                or ''
            )
            title = d.get('ShortDescription') or d.get('LongDescription') or d.get('Description') or ''
            status = d.get('Status') or d.get('CurrentStatus') or d.get('BillStatus') or 'Status unavailable'
            if isinstance(status, dict):
                status = status.get('BillStatus') or json.dumps(status, default=str)

            affected_bills.append({
                'BillNumber': str(bill_number).strip(),
                'Title': str(title).strip(),
                'Status': str(status).strip(),
                'Raw': d,
                'SessionYear': session_year
            })

        return jsonify({
            'success': True,
            'data': [{
                'ResearchType': 'rcw_combined',
                'RcwCitation': rcw_cite,
                'RcwSummary': rcw_summary.get('content', ''),
                'RcwCitations': rcw_summary.get('citations', []),
                'OfficialRcwUrl': f'https://app.leg.wa.gov/RCW/default.aspx?cite={rcw_cite}',
                'AffectedBills': affected_bills,
                'Biennium': biennium,
                'SessionYear': session_year,
            }]
        })

    except Exception as e:
        logging.error(f"Error in search_rcw: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/search/fire-code', methods=['POST'])
def api_search_fire_code():
    """Fire Code RAG search endpoint"""
    try:
        data = request.get_json()
        query = data.get('search_term', '').strip()

        if not query:
            return jsonify({
                'success': False,
                'error': 'Please enter a search query'
            })

        result = search_fire_code(query)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/committees')
def get_committees():
    """Get list of all committees"""
    try:
        client = Client(COMMITTEE_SERVICE)
        result = client.service.GetCommittees(biennium='2023-24')
        
        committees = []
        if result:
            if not isinstance(result, list):
                result = [result]
            
            for committee in result:
                committees.append({
                    'Name': str(committee.Name) if hasattr(committee, 'Name') else 'Unknown',
                    'LongName': str(committee.LongName) if hasattr(committee, 'LongName') else '',
                    'Agency': str(committee.Agency) if hasattr(committee, 'Agency') else '',
                    'Id': str(committee.Id) if hasattr(committee, 'Id') else '',
                })
        
        return jsonify({
            'success': True,
            'data': committees
        })
        
    except Exception as e:
        logging.error(f"Error in get_committees: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    if not os.getenv('ANTHROPIC_API_KEY'):
        logging.warning("WARNING: ANTHROPIC_API_KEY not found. AI-powered search will not work.")
    
    if not os.getenv('PERPLEXITY_API_KEY'):
        logging.warning("WARNING: PERPLEXITY_API_KEY not found. Research feature will not work.")
    
    app.run(debug=True, host='0.0.0.0', port=5001)