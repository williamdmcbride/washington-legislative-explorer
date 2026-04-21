#!/usr/bin/env python3
"""
Process Washington State Fire Code PDF and create vector database
"""

import os
import re
from pathlib import Path
from pypdf import PdfReader
import chromadb
from chromadb.utils import embedding_functions

# Paths
PDF_PATH = "data/WAC 51-54A.pdf"
CHROMA_PATH = "data/chroma_fire_code"

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    print(f"📄 Reading PDF: {pdf_path}")
    reader = PdfReader(pdf_path)
    
    text_chunks = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text.strip():
            text_chunks.append({
                'text': text,
                'page': i + 1,
                'metadata': {
                    'source': 'WAC 51-54A',
                    'page': i + 1
                }
            })
    
    print(f"✅ Extracted {len(text_chunks)} pages")
    return text_chunks

def chunk_text(text_chunks, chunk_size=1000, overlap=200):
    """Split text into smaller chunks with overlap"""
    print(f"✂️  Chunking text (size={chunk_size}, overlap={overlap})")
    
    chunks = []
    chunk_id = 0
    
    for page_data in text_chunks:
        text = page_data['text']
        page_num = page_data['page']
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        for para in paragraphs:
            # If adding this paragraph would exceed chunk size, save current chunk
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    'id': f'chunk_{chunk_id}',
                    'text': current_chunk.strip(),
                    'metadata': {
                        'source': 'WAC 51-54A',
                        'page': page_num,
                        'chunk_id': chunk_id
                    }
                })
                chunk_id += 1
                
                # Keep overlap from previous chunk
                words = current_chunk.split()
                overlap_text = ' '.join(words[-overlap:]) if len(words) > overlap else current_chunk
                current_chunk = overlap_text + '\n\n' + para
            else:
                current_chunk += '\n\n' + para if current_chunk else para
        
        # Save remaining text
        if current_chunk.strip():
            chunks.append({
                'id': f'chunk_{chunk_id}',
                'text': current_chunk.strip(),
                'metadata': {
                    'source': 'WAC 51-54A',
                    'page': page_num,
                    'chunk_id': chunk_id
                }
            })
            chunk_id += 1
    
    print(f"✅ Created {len(chunks)} chunks")
    return chunks

def create_vector_database(chunks):
    """Create Chroma vector database from chunks"""
    print(f"🗄️  Creating vector database at {CHROMA_PATH}")
    
    # Initialize Chroma client
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Use sentence transformers for embeddings
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    # Delete collection if it exists (for fresh start)
    try:
        client.delete_collection(name="fire_code")
        print("🗑️  Deleted existing collection")
    except:
        pass
    
    # Create new collection
    collection = client.create_collection(
        name="fire_code",
        embedding_function=embedding_fn,
        metadata={"description": "Washington State Fire Code WAC 51-54A"}
    )
    
    # Add chunks to collection
    print("⚡ Adding chunks to database...")
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        
        collection.add(
            ids=[c['id'] for c in batch],
            documents=[c['text'] for c in batch],
            metadatas=[c['metadata'] for c in batch]
        )
        
        print(f"   Added {min(i+batch_size, len(chunks))}/{len(chunks)} chunks")
    
    print(f"✅ Vector database created with {len(chunks)} chunks")
    return collection

def main():
    """Main processing pipeline"""
    print("🔥 Washington State Fire Code RAG Processing\n")
    
    # Check if PDF exists
    if not os.path.exists(PDF_PATH):
        print(f"❌ Error: PDF not found at {PDF_PATH}")
        return
    
    # Extract text from PDF
    text_chunks = extract_text_from_pdf(PDF_PATH)
    
    # Chunk the text
    chunks = chunk_text(text_chunks, chunk_size=1000, overlap=200)
    
    # Create vector database
    collection = create_vector_database(chunks)
    
    print("\n✅ Processing complete!")
    print(f"📊 Database stats:")
    print(f"   - Total chunks: {collection.count()}")
    print(f"   - Location: {CHROMA_PATH}")
    print(f"\n🔥 Fire Code RAG is ready to use!")

if __name__ == "__main__":
    main()
