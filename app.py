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

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# WA State Legislative Web Services URLs
LEGISLATION_SERVICE = "https://wslwebservices.leg.wa.gov/LegislationService.asmx?WSDL"
RCW_SERVICE = "https://wslwebservices.leg.wa.gov/RcwCiteAffectedService.asmx?WSDL"
DOCUMENT_SERVICE = "https://wslwebservices.leg.wa.gov/LegislativeDocumentService.asmx?WSDL"
COMMITTEE_SERVICE = "https://wslwebservices.leg.wa.gov/CommitteeService.asmx?WSDL"

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

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text

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
        
        return jsonify({
            'success': True,
            'data': result
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