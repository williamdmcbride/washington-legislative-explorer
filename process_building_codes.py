#!/usr/bin/env python3
"""
Unified Washington Building Codes RAG Processing
Processes all WAC Title 51 building codes into one searchable database
"""

import os
import re
from pathlib import Path
from pypdf import PdfReader
import chromadb
from chromadb.utils import embedding_functions

# Paths
BUILDING_CODES_DIR = "data/building_codes"
CHROMA_PATH = "data/chroma_building_codes"

# Code type mapping for better metadata
CODE_TYPES = {
    '51-04': {'name': 'Policies & Procedures', 'type': 'administrative'},
    '51-05': {'name': 'Building Permit Surcharges', 'type': 'administrative'},
    '51-06': {'name': 'Public Records', 'type': 'administrative'},
    '51-16': {'name': 'State Building Code Guidelines', 'type': 'administrative'},
    '51-50': {'name': 'Building Code (IBC)', 'type': 'building'},
    '51-51': {'name': 'Residential Code (IRC)', 'type': 'residential'},
    '51-52': {'name': 'Mechanical Code (IMC)', 'type': 'mechanical'},
    '51-54A': {'name': 'Fire Code (IFC)', 'type': 'fire'},
    '51-11C': {'name': 'Energy Code Commercial (IECC)', 'type': 'energy'},
    '51-11R': {'name': 'Energy Code Residential (IECC)', 'type': 'energy'},
    '51-56': {'name': 'Plumbing Code (UPC)', 'type': 'plumbing'},
    '51-55': {'name': 'Wildland-Urban Interface Code', 'type': 'wildland'}
}

def extract_code_info(filename):
    """Extract WAC code number and info from filename"""
    match = re.search(r'(51-\d+[A-Z]?)', filename, re.IGNORECASE)
    if match:
        code_num = match.group(1).upper()
        code_info = CODE_TYPES.get(code_num, {
            'name': f'WAC {code_num}',
            'type': 'unknown'
        })
        return code_num, code_info
    return 'Unknown', {'name': 'Unknown Code', 'type': 'unknown'}

def get_pdf_files():
    """Get all PDF files from building codes directory"""
    codes_path = Path(BUILDING_CODES_DIR)
    
    if not codes_path.exists():
        print(f"❌ Error: Directory not found: {BUILDING_CODES_DIR}")
        return []
    
    pdf_files = []
    for pdf_path in sorted(codes_path.glob("*.pdf")):
        code_num, code_info = extract_code_info(pdf_path.stem)
        pdf_files.append({
            'path': str(pdf_path),
            'code_num': code_num,
            'code_name': code_info['name'],
            'code_type': code_info['type'],
            'filename': pdf_path.name
        })
    
    return pdf_files

def extract_text_from_pdf(pdf_info):
    """Extract text from PDF file with metadata"""
    pdf_path = pdf_info['path']
    code_num = pdf_info['code_num']
    code_name = pdf_info['code_name']
    code_type = pdf_info['code_type']
    
    print(f"\n📄 Processing: {code_name}")
    print(f"   Code: WAC {code_num}")
    print(f"   Type: {code_type}")
    print(f"   File: {pdf_info['filename']}")
    
    try:
        reader = PdfReader(pdf_path)
        
        text_chunks = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                text_chunks.append({
                    'text': text,
                    'page': i + 1,
                    'metadata': {
                        'source': f'WAC {code_num}',
                        'code_name': code_name,
                        'code_type': code_type,
                        'code_num': code_num,
                        'page': i + 1,
                        'filename': pdf_info['filename']
                    }
                })
        
        print(f"   ✅ Extracted {len(text_chunks)} pages")
        return text_chunks
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return []

def chunk_text(text_chunks, chunk_size=1000, overlap=200):
    """Split text into smaller chunks with overlap and unique IDs"""
    chunks = []
    
    # Get unique prefix from first chunk's metadata
    if not text_chunks:
        return chunks
    
    code_num = text_chunks[0]['metadata']['code_num'].replace('-', '_')
    chunk_id = 0
    
    for page_data in text_chunks:
        text = page_data['text']
        metadata = page_data['metadata']
        
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    'id': f'{code_num}_chunk_{chunk_id}',
                    'text': current_chunk.strip(),
                    'metadata': {**metadata, 'chunk_id': chunk_id}
                })
                chunk_id += 1
                
                words = current_chunk.split()
                overlap_text = ' '.join(words[-overlap:]) if len(words) > overlap else current_chunk
                current_chunk = overlap_text + '\n\n' + para
            else:
                current_chunk += '\n\n' + para if current_chunk else para
        
        if current_chunk.strip():
            chunks.append({
                'id': f'{code_num}_chunk_{chunk_id}',
                'text': current_chunk.strip(),
                'metadata': {**metadata, 'chunk_id': chunk_id}
            })
            chunk_id += 1
    
    return chunks

def create_vector_database(all_chunks):
    """Create Chroma vector database from chunks"""
    print(f"\n🗄️  Creating unified vector database at {CHROMA_PATH}")
    
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    try:
        client.delete_collection(name="building_codes")
        print("   🗑️  Deleted existing collection")
    except:
        pass
    
    collection = client.create_collection(
        name="building_codes",
        embedding_function=embedding_fn,
        metadata={"description": "Washington State Building Codes - All WAC Title 51"}
    )
    
    print("   ⚡ Adding chunks to database...")
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i+batch_size]
        
        collection.add(
            ids=[c['id'] for c in batch],
            documents=[c['text'] for c in batch],
            metadatas=[c['metadata'] for c in batch]
        )
        
        print(f"      Added {min(i+batch_size, len(all_chunks))}/{len(all_chunks)} chunks")
    
    print(f"   ✅ Vector database created")
    
    print(f"\n📊 Database Statistics:")
    code_stats = {}
    for chunk in all_chunks:
        source = chunk['metadata']['source']
        code_name = chunk['metadata']['code_name']
        key = f"{source} - {code_name}"
        code_stats[key] = code_stats.get(key, 0) + 1
    
    for code, count in sorted(code_stats.items()):
        print(f"   - {code}: {count} chunks")
    
    print(f"\n   📦 Total: {len(all_chunks)} chunks across {len(code_stats)} codes")
    print(f"   📍 Location: {CHROMA_PATH}")
    
    return collection

def main():
    """Main processing pipeline"""
    print("=" * 70)
    print("🏗️  WASHINGTON STATE BUILDING CODES - UNIFIED RAG PROCESSING")
    print("=" * 70)
    
    pdf_files = get_pdf_files()
    
    if not pdf_files:
        print("\n❌ No PDF files found!")
        return
    
    print(f"\n📚 Found {len(pdf_files)} Building Code PDFs")
    print("\nCodes to process:")
    for pdf in pdf_files:
        print(f"   • WAC {pdf['code_num']}: {pdf['code_name']}")
    
    print("\n" + "=" * 70)
    print("PROCESSING PDFs")
    print("=" * 70)
    
    all_chunks = []
    for pdf_info in pdf_files:
        text_chunks = extract_text_from_pdf(pdf_info)
        if text_chunks:
            print(f"   ✂️  Chunking {len(text_chunks)} pages...")
            chunks = chunk_text(text_chunks, chunk_size=1000, overlap=200)
            print(f"   ✅ Created {len(chunks)} chunks")
            all_chunks.extend(chunks)
    
    if not all_chunks:
        print("\n❌ No chunks created!")
        return
    
    print("\n" + "=" * 70)
    print("CREATING VECTOR DATABASE")
    print("=" * 70)
    
    collection = create_vector_database(all_chunks)
    
    print("\n" + "=" * 70)
    print("✅ PROCESSING COMPLETE!")
    print("=" * 70)
    print("\n🏗️  All Washington Building Codes are now searchable!")
    print(f"📊 Total chunks indexed: {len(all_chunks)}")
    print(f"📁 Database location: {CHROMA_PATH}")
    print("\n💡 Users can now search across ALL building codes!")

if __name__ == "__main__":
    main()
