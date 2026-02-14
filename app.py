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
import logging
import json
import re
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# WA State Legislative Web Services URLs
LEGISLATION_SERVICE = "https://wslwebservices.leg.wa.gov/LegislationService.asmx?WSDL"
RCW_SERVICE = "https://wslwebservices.leg.wa.gov/RcwCiteAffectedService.asmx?WSDL"
DOCUMENT_SERVICE = "https://wslwebservices.leg.wa.gov/LegislativeDocumentService.asmx?WSDL"
COMMITTEE_SERVICE = "https://wslwebservices.leg.wa.gov/CommitteeService.asmx?WSDL"

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
                retry_delay *= 2  # Exponential backoff
            else:
                # Last attempt failed or non-overload error
                raise api_error

def strip_all_html_from_text(text):
    """Nuclear option: Remove ALL HTML-like content from text"""
    # Remove everything between < and >
    text = re.sub(r'<[^>]*>', '', text)
    
    # Remove target="_blank" and similar attributes even without tags
    text = re.sub(r'target\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'rel\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'style\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'href\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'class\s*=\s*["\'][^"\']*["\']', '', text)
    
    # Remove stray > characters that appear before WAC or RCW
    text = re.sub(r'>\s*(WAC|RCW|KCC)', r'\1', text)
    
    # Clean up any remaining quotes and angle brackets
    text = re.sub(r'["\']?\s*>', '', text)
    
    # Fix multiple spaces
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
2. **Common bill types**: What kind of bills typically address this (e.g., "Budget bills", "Policy bills", "Joint resolutions")
3. **Suggested bill number ranges**: Based on WA State's numbering system:
   - HB 1000-1999: House bills (lower numbers = higher priority)
   - SB 5000-5999: Senate bills (lower numbers = higher priority)
   - HJR 4000-4999: House joint resolutions
   Suggest 3-5 specific bill numbers they might want to search for.
4. **Keywords to try**: List 3-5 specific search terms
5. **Where to find more**: Suggest which legislative committees typically handle this topic
6. **Pro tip**: One insider tip about this topic in WA State legislation

Be specific, actionable, and concise. Format your response in clear sections."""

    return call_claude_api_with_retry(client, prompt, max_tokens=1500)

@app.route('/')
def index():
    """Render the main search interface"""
    return render_template('index.html')

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
        
        # Check if it looks like a bill number (e.g., HB 1001, SB 5050)
        bill_prefixes = ['HB', 'SB', 'HJR', 'SJR', 'HCR', 'SCR', 'ESSB', 'ESHB']
        is_bill_number = any(search_term.upper().startswith(prefix) for prefix in bill_prefixes)
        
        if is_bill_number:
            # Direct bill search
            client = Client(LEGISLATION_SERVICE)
            try:
                result = client.service.GetLegislation(
                    biennium=biennium,
                    billNumber=search_term.upper()
                )
                
                if result:
                    return jsonify({
                        'success': True,
                        'data': [{
                            'BillId': str(result.BillId) if hasattr(result, 'BillId') else search_term,
                            'LongDescription': str(result.LongDescription) if hasattr(result, 'LongDescription') else 'No description available',
                            'ShortDescription': str(result.ShortDescription) if hasattr(result, 'ShortDescription') else '',
                            'PrimeSponsorName': str(result.PrimeSponsorName) if hasattr(result, 'PrimeSponsorName') else 'Unknown',
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
        
        # Natural language search - provide AI guidance
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
    """Search Washington Administrative Code with AI guidance"""
    try:
        data = request.json
        search_term = data.get('search_term', '').strip()
        
        if not search_term:
            return jsonify({
                'success': False,
                'error': 'Please enter a WAC section or topic'
            }), 400
        
        # Use AI to provide WAC guidance
        from anthropic import Anthropic
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise Exception("ANTHROPIC_API_KEY not found")
        
        client = Anthropic(api_key=api_key)
        
        prompt = f"""You are an expert on Washington State Administrative Code (WAC). A user is searching for: "{search_term}"

Format your response EXACTLY like this example with clear sections and line breaks:

**What this WAC section covers**
Brief explanation in 1-2 sentences.

**Administering agency**
Department name

**Related RCW sections**
1. RCW 19.27 (State Building Code Act)
2. RCW 19.27A (Energy Code)

**Common WAC citations in this area**
1. WAC 51-52 (Washington State Mechanical Code)
2. WAC 51-54A (Washington State Energy Code)
3. WAC 51-50 (International Building Code amendments)

**How to access**
Visit apps.leg.wa.gov/wac/ to access the full text.

**Pro tip**
One practical insider tip in 1-2 sentences.

CRITICAL FORMATTING RULES:
- Put EACH numbered item on its OWN LINE with a line break after it
- Use numbered lists (1. 2. 3.) NOT narrative paragraphs
- Write "1. WAC 51-52 (description)" on one line, then move to next line for "2. WAC 51-54A..."
- DO NOT write citations in sentences like "The citations include WAC 51-52 which is..."
- NO HTML tags, NO anchor tags, NO href, NO target, NO rel, NO style attributes
- Just plain text with proper line breaks and numbered lists"""

        wac_guidance = call_claude_api_with_retry(client, prompt, max_tokens=1500)
        
        # Apply nuclear HTML cleaning
        wac_guidance = strip_all_html_from_text(wac_guidance)
        
        return jsonify({
            'success': True,
            'data': [{
                'BillId': '📜 WAC Search Assistant',
                'LongDescription': wac_guidance,
                'ShortDescription': f'Washington Administrative Code guidance for: "{search_term}"',
                'PrimeSponsorName': 'Claude AI',
                'CurrentStatus': {
                    'BillStatus': 'Administrative Rules Analysis'
                }
            }]
        })
        
    except Exception as e:
        logging.error(f"WAC search error: {e}")
        error_msg = str(e)
        if "overloaded" in error_msg.lower():
            error_msg = "Claude AI is experiencing high demand. Please try again in a few moments."
        return jsonify({
            'success': False,
            'error': f'WAC search error: {error_msg}'
        }), 500

@app.route('/api/search/kittitas', methods=['POST'])
def search_kittitas():
    """Search Kittitas County Code with AI guidance"""
    try:
        data = request.json
        search_term = data.get('search_term', '').strip()
        
        if not search_term:
            return jsonify({
                'success': False,
                'error': 'Please enter a topic or code section'
            }), 400
        
        # Use AI to provide Kittitas County guidance
        from anthropic import Anthropic
        
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise Exception("ANTHROPIC_API_KEY not found")
        
        client = Anthropic(api_key=api_key)
        
        prompt = f"""You are an expert on Kittitas County, Washington regulations and codes. A user is searching for: "{search_term}"

Provide helpful guidance in this format:

**What this covers in Kittitas County**
Brief explanation of how this topic is regulated at the county level.

**Relevant county departments**
Which Kittitas County departments handle this (e.g., Planning, Building & Fire Safety, Public Works)

**Related county code sections**
List 3-5 relevant Kittitas County Code (KCC) sections:
1. KCC 14.04 (Building Code)
2. KCC 17.15 (Zoning/Allowed Uses)
3. KCC 18.01 (Code Enforcement)

**State code connections**
How this relates to Washington State RCW or WAC:
- RCW sections that apply
- WAC sections Kittitas County enforces

**How to access county code**
Visit co.kittitas.wa.us/boc/countycode/ for the full Kittitas County Code.

**Local tip**
One practical tip about navigating Kittitas County regulations.

FORMATTING RULES:
- Use numbered lists for code sections
- Write "KCC 14.04" or "RCW 19.27" as plain text
- NO HTML tags or markup
- Clear line breaks between sections"""

        kittitas_guidance = call_claude_api_with_retry(client, prompt, max_tokens=1500)
        
        # Apply HTML cleaning
        kittitas_guidance = strip_all_html_from_text(kittitas_guidance)
        
        return jsonify({
            'success': True,
            'data': [{
                'BillId': '🏛️ Kittitas County Assistant',
                'LongDescription': kittitas_guidance,
                'ShortDescription': f'Kittitas County guidance for: "{search_term}"',
                'PrimeSponsorName': 'Claude AI',
                'CurrentStatus': {
                    'BillStatus': 'County Code Analysis'
                }
            }]
        })
        
    except Exception as e:
        logging.error(f"Kittitas search error: {e}")
        error_msg = str(e)
        if "overloaded" in error_msg.lower():
            error_msg = "Claude AI is experiencing high demand. Please try again in a few moments."
        return jsonify({
            'success': False,
            'error': f'Kittitas County search error: {error_msg}'
        }), 500

@app.route('/api/search/rcw', methods=['POST'])
def search_rcw():
    """Search for bills affecting specific RCW sections"""
    try:
        data = request.json
        rcw_cite = data.get('rcw_cite', '')
        biennium = data.get('biennium', '2023-24')
        
        client = Client(RCW_SERVICE)
        result = client.service.GetRcwCitesAffected(biennium=biennium)
        
        # Filter by RCW cite if provided
        if rcw_cite:
            filtered = [r for r in result if rcw_cite.lower() in str(r).lower()]
            result = filtered
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logging.error(f"Error in search_rcw: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bill/<biennium>/<bill_number>')
def get_bill_details(biennium, bill_number):
    """Get detailed information about a specific bill"""
    try:
        leg_client = Client(LEGISLATION_SERVICE)
        doc_client = Client(DOCUMENT_SERVICE)
        
        # Get legislation details
        legislation = leg_client.service.GetLegislation(
            biennium=biennium,
            billNumber=bill_number
        )
        
        # Get documents for this bill
        documents = doc_client.service.GetDocuments(
            biennium=biennium,
            namedLike=bill_number
        )
        
        return jsonify({
            'success': True,
            'legislation': legislation,
            'documents': documents
        })
        
    except Exception as e:
        logging.error(f"Error in get_bill_details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/committees')
def get_committees():
    """Get list of all committees"""
    try:
        client = Client(COMMITTEE_SERVICE)
        result = client.service.GetCommittees(biennium='2023-24')
        
        # Convert zeep objects to dictionaries
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

@app.route('/api/bienniums')
def get_bienniums():
    """Get list of available bienniums"""
    bienniums = [
        '2023-24',
        '2021-22', 
        '2019-20',
        '2017-18',
        '2015-16',
        '2013-14',
        '2011-12',
        '2009-10'
    ]
    
    return jsonify({
        'success': True,
        'bienniums': bienniums
    })

if __name__ == '__main__':
    if not os.getenv('ANTHROPIC_API_KEY'):
        logging.warning("WARNING: ANTHROPIC_API_KEY not found. AI-powered search will not work.")
        logging.warning("Add your API key to the .env file")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
