from flask import Flask, render_template, request, jsonify, send_file
from langchain.llms import Cohere
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
import os
import tempfile
import io
from docx import Document

load_dotenv()

app = Flask(__name__)

# Cohere configuration
cohere_api_key = os.getenv('COHERE_API_KEY')
llm = Cohere(cohere_api_key=cohere_api_key, temperature=0.7)

# Template for legal consultation
legal_consultation_template = """
You are an expert legal assistant. Your task is to respond to legal questions in a clear, precise, and professional manner.
Maintain a formal but accessible tone, and always cite relevant laws or regulations when possible.

User's legal query: {query}

Response:
"""

# Template for document analysis
document_analysis_template = """
You are a legal document analyst. Review the following document and provide an analysis with these key points:
1. Document type and purpose
2. Key provisions or clauses
3. Potential legal issues or concerns
4. Plain language summary
5. Recommended actions if applicable

Document content: {document_content}

Analysis:
"""

# Template for legal document templates
legal_template_generator = """
You are a legal document specialist. Create a professional {document_type} template following standard legal practices.
Make the template comprehensive but easy to customize, with clear instructions for users to fill in their specific information.

Create a complete, ready-to-use {document_type} template:
"""

# Create the chains
consultation_chain = LLMChain(llm=llm, prompt=PromptTemplate(input_variables=["query"], template=legal_consultation_template))
analysis_chain = LLMChain(llm=llm, prompt=PromptTemplate(input_variables=["document_content"], template=document_analysis_template))
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
            response = consultation_chain.run(query=message)
            return jsonify({'response': response})
        
        elif feature == 'document-analysis':
            # In a real implementation, this would process an uploaded document
            # For now, we'll analyze the text provided in the message
            response = analysis_chain.run(document_content=message)
            return jsonify({'response': response})
        
        elif feature == 'legal-templates':
            # Generate the template based on the requested type
            template = template_chain.run(document_type=message)
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
    
    # Read the file content
    content = file.read().decode('utf-8')
    
    # Analyze the document
    response = analysis_chain.run(document_content=content)
    return jsonify({'response': response})

@app.route('/api/download-template', methods=['POST'])
def download_template():
    data = request.json
    template_content = data.get('template')
    template_type = data.get('templateType', 'legal_document')

    # Crear documento Word
    doc = Document()
    for line in template_content.split('\n'):
        doc.add_paragraph(line)

    # Guardar en archivo temporal
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(temp_path.name)
    print('download_namedownload_namedownload_namedownload_namedownload_name',temp_path.name)
    return send_file(
        temp_path.name,
        as_attachment=True,
        download_name=f"{template_type.replace(' ', '_')}_template.docx",
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


if __name__ == '__main__':
    app.run(debug=True, port=5002)