from flask import Flask, render_template, request, jsonify, send_file
from docx import Document
import cohere
import os
import tempfile
import traceback
from dotenv import load_dotenv
import re
import sys
import time

# For document loading
from PyPDF2 import PdfReader
import docx2txt

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Cohere configuration - usando cliente directo
cohere_api_key = os.getenv('COHERE_API_KEY')
if not cohere_api_key:
    print("Error: No COHERE_API_KEY found in environment variables.")
    print("Please create a .env file with your Cohere API key.")
else:
    co = cohere.Client(cohere_api_key)

# Constants for chunking
MAX_INPUT_TOKENS = 3500  # Reserve space for prompt context
MAX_CHUNK_LENGTH = 15000  # Conservative character estimate per chunk

# Función para dividir texto en chunks
def split_text(text, max_length=MAX_CHUNK_LENGTH):
    """Split text into chunks of approximately max_length characters"""
    # If text is short enough, return it as a single chunk
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    # Split text by paragraphs
    paragraphs = text.split('\n')
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed the max length, 
        # save the current chunk and start a new one
        if len(current_chunk) + len(paragraph) + 1 > max_length and current_chunk:
            chunks.append(current_chunk)
            current_chunk = paragraph + '\n'
        else:
            current_chunk += paragraph + '\n'
    
    # Add the last chunk if it has content
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

# Templates
# Template for legal consultation
legal_consultation_template = """
You are an expert legal assistant. Your task is to respond to legal questions in a clear, precise, and professional manner.
Maintain a formal but accessible tone, and always cite relevant laws or regulations when possible.

Format your response using proper Markdown:
- Use headers (## and ###) for sections
- Use bullet points or numbered lists for listing items
- Use **bold** or *italic* for emphasis
- Organize complex information into well-structured sections

User's legal query: {query}

Response (in markdown format):
"""

# Template for document chunk analysis
document_chunk_analysis_template = """
You are a legal document analyst. Review the following document chunk and extract key legal information.
This is chunk {chunk_num} of {total_chunks} from the document.

Use proper Markdown formatting in your response:
- Use headers (## and ###) for sections
- Use bullet lists or numbered lists for listing items
- Use **bold** for key terms or important provisions
- Format any citations or references properly

Document chunk: {document_chunk}

Key information from this chunk (focus only on what's contained in this chunk, using markdown formatting):
"""

# Template for document final analysis
document_final_analysis_template = """
You are a legal document analyst. Based on the key information extracted from all parts of a document, provide a comprehensive analysis with these key points.

Follow this structure for your analysis, using clear headings with ## and well-formatted paragraphs:

## Document Type and Purpose
Provide a detailed analysis of the document type and its intended purpose

## Key Provisions or Clauses
Analyze the major provisions, clauses, or sections of the document
- First key provision: Brief explanation
- Additional provisions as needed: Brief explanation

## Potential Legal Issues or Concerns
Analyze possible legal issues, risks, or concerns with the document
- First potential issue: Brief explanation
- Additional issues as needed: Brief explanation

## Plain Language Summary
Provide a clear, jargon-free explanation of the document's content and implications

## Recommended Actions
Suggest next steps or considerations based on document analysis
- First recommendation: Brief explanation
- Additional recommendations as needed: Brief explanation

Key information extracted from the document:
{document_key_info}

Provide your complete analysis following the structure above, using clear markdown formatting:
"""

# Template for legal document templates
legal_template_generator = """
You are a legal document specialist. Create a professional {document_type} template following standard legal practices.
Make the template comprehensive but easy to customize, with clear instructions for users to fill in their specific information.

Follow these critical rules:
- Create a complete, ready-to-use template with proper legal formatting and structure
- DO NOT include any disclaimers or explanatory messages such as "Note: This is a template only and should be reviewed by a qualified attorney"
- DO NOT add statements like "This document is provided for informational purposes only and does not constitute legal advice"
- DO NOT include cautionary messages such as "Always consult with a licensed legal professional before using this document"
- DO NOT include footnotes, endnotes, or comments explaining the limitations of the template
- DO NOT add any text suggesting the document requires professional review or validation
- DO NOT add headers, footers, or watermarks containing advisory statements about professional consultation
- DO NOT add instructions on how to use the template
- All customization instructions should be embedded within the document as clear placeholders (e.g., [COMPANY NAME]) without additional explanatory commentary

Create a complete, ready-to-use {document_type} template:
"""

# Funciones auxiliares para generar respuestas usando Cohere directamente
def get_consultation_response(query):
    prompt = legal_consultation_template.format(query=query)
    response = co.generate(
        prompt=prompt,
        temperature=0.1,
        max_tokens=1024,
        return_likelihoods='NONE'
    )
    return response.generations[0].text

def get_chunk_analysis(document_chunk, chunk_num, total_chunks):
    prompt = document_chunk_analysis_template.format(
        document_chunk=document_chunk,
        chunk_num=chunk_num,
        total_chunks=total_chunks
    )
    response = co.generate(
        prompt=prompt,
        temperature=0.1,
        max_tokens=1024,
        return_likelihoods='NONE'
    )
    return response.generations[0].text

def get_final_analysis(document_key_info):
    prompt = document_final_analysis_template.format(document_key_info=document_key_info)
    response = co.generate(
        prompt=prompt,
        temperature=0.1,
        max_tokens=1024,
        return_likelihoods='NONE'
    )
    return response.generations[0].text

def get_template(document_type):
    prompt = legal_template_generator.format(document_type=document_type)
    response = co.generate(
        prompt=prompt,
        temperature=0.1,
        max_tokens=1024,
        return_likelihoods='NONE'
    )
    return response.generations[0].text

@app.route('/')
def index():
    print("Loading index page")
    return render_template('index.html')

@app.route('/status', methods=['GET'])
def status():
    """Simple endpoint to check API connectivity"""
    try:
        response = co.generate(
            prompt="Hello",
            temperature=0.1,
            max_tokens=5,
            return_likelihoods='NONE'
        )
        return f"API connection working! Response: {response.generations[0].text}"
    except Exception as e:
        error_message = f"API connection error: {str(e)}"
        print(error_message, file=sys.stderr)
        return error_message

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        print("Received request to /api/chat")
        data = request.json
        print(f"Request data: {data}")
        message = data.get('message')
        feature = data.get('feature', 'legal-consult')
        
        print(f"Message: {message}")
        print(f"Feature: {feature}")
        
        if not message:
            print("Error: Missing message parameter")
            return jsonify({'error': 'Missing message parameter'}), 400
        
        # Handle different features
        if feature == 'legal-consult':
            print("Processing legal consultation")
            try:
                response_content = get_consultation_response(message)
                print(f"Consultation response generated: {str(response_content)[:100]}...")
            except Exception as chain_error:
                print(f"Error in consultation chain: {str(chain_error)}")
                print(traceback.format_exc())
                # Generic message without technical details
                return jsonify({'response': 'Sorry, I encountered an issue answering your legal question. Please try again or rephrase your question.'}), 200
            return jsonify({'response': response_content})
        
        elif feature == 'document-analysis':
            print("Processing document analysis")
            try:
                # Always use chunking for document analysis
                print("Splitting document into chunks")
                chunks = split_text(message)
                print(f"Document split into {len(chunks)} chunks")
                
                # Process multiple chunks
                print("Processing chunks")
                chunk_analyses = []
                for i, chunk in enumerate(chunks):
                    print(f"Processing chunk {i+1}/{len(chunks)}")
                    chunk_content = get_chunk_analysis(
                        chunk,
                        i+1,
                        len(chunks)
                    )
                    chunk_analyses.append(chunk_content)
                
                # Combine analyses
                print("Combining chunk analyses for final analysis")
                combined_analysis = "\n\n".join(chunk_analyses)
                response_content = get_final_analysis(combined_analysis)
                
                print(f"Analysis response generated: {response_content[:100]}...")
                
            except Exception as analysis_error:
                print(f"Error in document analysis: {str(analysis_error)}")
                print(traceback.format_exc())
                return jsonify({'response': 'Sorry, I encountered an issue analyzing this document. Please try again with a different document or format.'}), 200
            
            return jsonify({'response': response_content})
        
        elif feature == 'legal-templates':
            print("Processing legal template generation")
            try:
                print(f"Attempting to generate template for: '{message}'")
                
                template_content = get_template(message)
                print(f"Template generated for '{message}'")
                
                response_data = {
                    'response': f"I've created a {message} template for you. You can use this as a starting point and customize it to your specific needs.",
                    'template': template_content,
                    'templateType': message
                }
                
                return jsonify(response_data)
                
            except Exception as template_error:
                print(f"ERROR IN TEMPLATE GENERATION: {str(template_error)}")
                print(f"Error type: {type(template_error).__name__}")
                print(f"Template type requested: '{message}'")
                print(traceback.format_exc())
                
                # Generic message without technical details
                return jsonify({'response': 'Sorry, I encountered an issue creating this template. Please try a different template type or check your request.'}), 200
        
        else:
            print(f"Invalid feature specified: {feature}")
            return jsonify({'error': 'Invalid feature specified'}), 400
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unhandled error in /api/chat: {str(e)}")
        print(error_traceback)
        # Generic message without technical details
        return jsonify({'response': 'Sorry, an unexpected error occurred. Please try again.'}), 200

@app.route('/api/document-upload', methods=['POST'])
def document_upload():
    print("Received request to /api/document-upload")
    if 'file' not in request.files:
        print("Error: No file part in request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    print(f"File received: {file.filename}")
    
    if file.filename == '':
        print("Error: No selected file")
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)
        print(f"File saved to {file_path}")
        
        # Use specialized document loaders based on file type
        content = ""
        filename = file.filename.lower()
        
        try:
            if filename.endswith('.pdf'):
                print("Processing PDF file")
                # Usamos PyPDF2 directamente en lugar de LangChain loader
                pdf_reader = PdfReader(file_path)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
                print(f"Extracted {len(pdf_reader.pages)} pages from PDF")
                    
            elif filename.endswith('.docx'):
                print("Processing DOCX file")
                # Usamos docx2txt en vez de LangChain loader
                content = docx2txt.process(file_path)
                print("DOCX content extracted")
                    
            elif filename.endswith('.txt'):
                print("Processing TXT file")
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                print("TXT content extracted")
            else:
                print(f"Unsupported file format: {filename}")
                return jsonify({'response': 'Unsupported file format. Please upload PDF, DOCX, or TXT files.'}), 200
        finally:
            # Clean up the file after processing
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Temporary file {file_path} removed")
        
        # ALWAYS use chunking regardless of document size
        print("Splitting document into chunks")
        chunks = split_text(content)
        print(f"Document split into {len(chunks)} chunks")
        
        # Process chunks
        print("Processing chunks")
        chunk_analyses = []
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}")
            chunk_content = get_chunk_analysis(
                chunk,
                i+1,
                len(chunks)
            )
            chunk_analyses.append(chunk_content)
        
        # Combine analyses
        print("Combining chunk analyses for final analysis")
        combined_analysis = "\n\n".join(chunk_analyses)
        response_content = get_final_analysis(combined_analysis)
        
        print(f"Final analysis response generated: {response_content[:100]}...")
        return jsonify({'response': response_content})
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unhandled error in /api/document-upload: {str(e)}")
        print(error_traceback)
        # Generic message without technical details
        return jsonify({'response': 'Sorry, I encountered an issue processing your document. Please try again with a different document or format.'}), 200

@app.route('/api/download-template', methods=['POST'])
def download_template():
    try:
        print("Received request to /api/download-template")
        data = request.json
        print(f"Request data: {data}")
        template_content = data.get('template')
        template_type = data.get('templateType', 'legal_document')
        
        if not template_content:
            print("Error: Missing template content")
            return jsonify({'response': 'Missing template content'}), 200

        print(f"Creating Word document for {template_type}")
        # Create Word document
        doc = Document()
        for line in template_content.split('\n'):
            doc.add_paragraph(line)

        # Save to temporary file
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        print(f"Saving template to temporary file: {temp_path.name}")
        doc.save(temp_path.name)
        
        return send_file(
            temp_path.name,
            as_attachment=True,
            download_name=f"{template_type.replace(' ', '_')}_template.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Unhandled error in /api/download-template: {str(e)}")
        print(error_traceback)
        # Generic message without technical details
        return jsonify({'response': 'Sorry, I encountered an issue creating your template document. Please try again later.'}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)