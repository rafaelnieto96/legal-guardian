from flask import Flask, render_template, request, jsonify, send_file
from langchain_cohere import ChatCohere
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import os
import tempfile
import io
from docx import Document
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader

load_dotenv()

app = Flask(__name__)

# Cohere configuration
cohere_api_key = os.getenv('COHERE_API_KEY')
llm = ChatCohere(temperature=0.0, cohere_api_key=cohere_api_key)

# Text splitter for long documents
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=200,
    length_function=len,
)

# Template for legal consultation
legal_consultation_template = """
You are an expert legal assistant. Your task is to respond to legal questions in a clear, precise, and professional manner.
Maintain a formal but accessible tone, and always cite relevant laws or regulations when possible.

User's legal query: {query}

Response:
"""

# Template for document chunk analysis
document_chunk_analysis_template = """
You are a legal document analyst. Review the following document chunk and extract key legal information.
This is chunk {chunk_num} of {total_chunks} from the document.

Document chunk: {document_chunk}

Key information from this chunk (focus only on what's contained in this chunk):
"""

# Template for document final analysis
document_final_analysis_template = """
You are a legal document analyst. Based on the key information extracted from all parts of a document, provide a comprehensive analysis with these key points.

Your response MUST follow this HTML structure format for proper display in our legal interface:

<h2>Document Type and Purpose</h2>
<p>[Detailed analysis of document type and its intended purpose]</p>

<h2>Key Provisions or Clauses</h2>
<p>[Analysis of major provisions, clauses, or sections]</p>
<ul>
  <li><strong>[First key provision]</strong>: [Brief explanation]</li>
  <li><strong>[Additional provisions as needed]</strong>: [Brief explanation]</li>
</ul>

<h2>Potential Legal Issues or Concerns</h2>
<p>[Analysis of possible legal issues, risks, or concerns]</p>
<ul>
  <li><strong>[First potential issue]</strong>: [Brief explanation]</li>
  <li><strong>[Additional issues as needed]</strong>: [Brief explanation]</li>
</ul>

<h2>Plain Language Summary</h2>
<p>[Clear, jargon-free explanation of the document's content and implications]</p>

<h2>Recommended Actions</h2>
<p>[Suggested next steps or considerations based on document analysis]</p>
<ul>
  <li><strong>[First recommendation]</strong>: [Brief explanation]</li>
  <li><strong>[Additional recommendations as needed]</strong>: [Brief explanation]</li>
</ul>

Key information extracted from the document:
{document_key_info}

Provide your complete analysis following the HTML structure format above:
"""

# Template for legal document templates
legal_template_generator = """
You are a legal document specialist. Create a professional {document_type} template following standard legal practices.
Make the template comprehensive but easy to customize, with clear instructions for users to fill in their specific information.

Create a complete, ready-to-use {document_type} template:
"""

# Create the chains
consultation_chain = LLMChain(llm=llm, prompt=PromptTemplate(input_variables=["query"], template=legal_consultation_template))
chunk_analysis_chain = LLMChain(llm=llm, prompt=PromptTemplate(input_variables=["document_chunk", "chunk_num", "total_chunks"], template=document_chunk_analysis_template))
final_analysis_chain = LLMChain(llm=llm, prompt=PromptTemplate(input_variables=["document_key_info"], template=document_final_analysis_template))
template_chain = LLMChain(llm=llm, prompt=PromptTemplate(input_variables=["document_type"], template=legal_template_generator))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message')
        feature = data.get('feature', 'legal-consult')
        
        if not message:
            return jsonify({'error': 'Missing message parameter'}), 400
        
        # Handle different features
        if feature == 'legal-consult':
            response = consultation_chain.invoke(query=message)
            return jsonify({'response': response})
        
        elif feature == 'document-analysis':
            # For text pasted directly in the chat, we'll use the chunking approach
            chunks = text_splitter.split_text(message)
            if len(chunks) == 1:
                # Simple case: document fits in one chunk
                response = final_analysis_chain.invoke(document_key_info=message)
            else:
                # Complex case: document needs chunking
                chunk_analyses = []
                for i, chunk in enumerate(chunks):
                    chunk_analysis = chunk_analysis_chain.invoke(
                        document_chunk=chunk,
                        chunk_num=i+1,
                        total_chunks=len(chunks)
                    )
                    chunk_analyses.append(chunk_analysis)
                
                # Combine analyses and generate final analysis
                combined_analysis = "\n\n".join(chunk_analyses)
                response = final_analysis_chain.invoke(document_key_info=combined_analysis)
            
            return jsonify({'response': response})
        
        elif feature == 'legal-templates':
            # Generate the template based on the requested type
            template = template_chain.invoke(document_type=message)
            return jsonify({
                'response': f"I've created a {message} template for you. You can use this as a starting point and customize it to your specific needs.",
                'template': template,
                'templateType': message
            })
        
        else:
            return jsonify({'error': 'Invalid feature specified'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/document-upload', methods=['POST'])
def document_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)
        
        # Use specialized document loaders based on file type
        content = ""
        filename = file.filename.lower()
        
        try:
            if filename.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
                documents = loader.load()
                for doc in documents:
                    content += doc.page_content + "\n"
                    
            elif filename.endswith('.docx'):
                loader = Docx2txtLoader(file_path)
                documents = loader.load()
                for doc in documents:
                    content += doc.page_content + "\n"
                    
            elif filename.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            else:
                return jsonify({'error': 'Unsupported file format. Please upload PDF, DOCX, or TXT files.'}), 400
        finally:
            # Clean up the file after processing
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Split content into manageable chunks
        chunks = text_splitter.split_text(content)
        
        # If content is small enough to fit in a single chunk
        if len(chunks) == 1:
            response = final_analysis_chain.invoke(document_key_info=content)
        else:
            # Process each chunk
            chunk_analyses = []
            for i, chunk in enumerate(chunks):
                chunk_analysis = chunk_analysis_chain.invoke(
                    document_chunk=chunk,
                    chunk_num=i+1,
                    total_chunks=len(chunks)
                )
                chunk_analyses.append(chunk_analysis)
            
            # Combine analyses and generate final analysis
            combined_analysis = "\n\n".join(chunk_analyses)
            response = final_analysis_chain.invoke(document_key_info=combined_analysis)
        
        return jsonify({'response': response})
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/api/download-template', methods=['POST'])
def download_template():
    data = request.json
    template_content = data.get('template')
    template_type = data.get('templateType', 'legal_document')

    # Create Word document
    doc = Document()
    for line in template_content.split('\n'):
        doc.add_paragraph(line)

    # Save to temporary file
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(temp_path.name)
    
    return send_file(
        temp_path.name,
        as_attachment=True,
        download_name=f"{template_type.replace(' ', '_')}_template.docx",
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5002)