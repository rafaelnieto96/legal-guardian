from flask import Flask, render_template, request, jsonify, send_file
from langchain_cohere import ChatCohere
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import os
import tempfile
import io
import traceback
from docx import Document
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader

load_dotenv()

app = Flask(__name__)

# Cohere configuration
cohere_api_key = os.getenv('COHERE_API_KEY')
llm = ChatCohere(temperature=0.0, cohere_api_key=cohere_api_key)

# Text splitter for long documents
text_splitter = RecursiveCharacterTextSplitter(
   chunk_size=32000,
   chunk_overlap=500,
   length_function=len,
)

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
- DO NOT add footnotes, endnotes, or comments explaining the limitations of the template
- DO NOT include any text suggesting the document requires professional review or validation
- DO NOT add headers, footers, or watermarks containing advisory statements about professional consultation
- DO NOT add instructions on how to use the template
- All customization instructions should be embedded within the document as clear placeholders (e.g., [COMPANY NAME]) without additional explanatory commentary

Create a complete, ready-to-use {document_type} template:
"""

# Create the chains using the new recommended approach with pipe operator
print("Initializing LLM chains...")
consultation_prompt = PromptTemplate(input_variables=["query"], template=legal_consultation_template)
consultation_chain = consultation_prompt | llm

chunk_analysis_prompt = PromptTemplate(input_variables=["document_chunk", "chunk_num", "total_chunks"], template=document_chunk_analysis_template)
chunk_analysis_chain = chunk_analysis_prompt | llm

final_analysis_prompt = PromptTemplate(input_variables=["document_key_info"], template=document_final_analysis_template)
final_analysis_chain = final_analysis_prompt | llm

template_prompt = PromptTemplate(input_variables=["document_type"], template=legal_template_generator)
template_chain = template_prompt | llm
print("LLM chains initialized successfully")

@app.route('/')
def index():
   print("Loading index page")
   return render_template('index.html')

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
               response = consultation_chain.invoke({"query": message})
               print(f"Consultation response generated: {str(response)[:100]}...")
               # Extract content from AIMessage
               response_content = response.content if hasattr(response, 'content') else str(response)
           except Exception as chain_error:
               print(f"Error in consultation chain: {str(chain_error)}")
               print(traceback.format_exc())
               # Generic message without technical details
               return jsonify({'response': 'Sorry, I encountered an issue answering your legal question. Please try again or rephrase your question.'}), 200
           return jsonify({'response': response_content})
       
       elif feature == 'document-analysis':
           print("Processing document analysis")
           try:
               # Check if the full document fits within 120k characters
               if len(message) <= 120000:
                   # If it fits, process it directly without chunking
                   print("Document fits within 120k characters, processing as a whole")
                   response = final_analysis_chain.invoke({"document_key_info": message})
                   response_content = response.content if hasattr(response, 'content') else str(response)
               else:
                   # If not, use chunking
                   print("Document exceeds 120k characters, splitting into chunks")
                   chunks = text_splitter.split_text(message)
                   print(f"Split document into {len(chunks)} chunks")
                   
                   if len(chunks) == 1:
                       # If chunking results in a single chunk
                       print("Document split into one chunk")
                       response = final_analysis_chain.invoke({"document_key_info": chunks[0]})
                       response_content = response.content if hasattr(response, 'content') else str(response)
                   else:
                       # Process multiple chunks
                       print(f"Processing {len(chunks)} chunks")
                       chunk_analyses = []
                       for i, chunk in enumerate(chunks):
                           print(f"Processing chunk {i+1}/{len(chunks)}")
                           chunk_analysis = chunk_analysis_chain.invoke({
                               "document_chunk": chunk,
                               "chunk_num": i+1,
                               "total_chunks": len(chunks)
                           })
                           chunk_content = chunk_analysis.content if hasattr(chunk_analysis, 'content') else str(chunk_analysis)
                           chunk_analyses.append(chunk_content)
                       
                       # Combine analyses
                       print("Combining chunk analyses and generating final analysis")
                       combined_analysis = "\n\n".join(chunk_analyses)
                       response = final_analysis_chain.invoke({"document_key_info": combined_analysis})
                       response_content = response.content if hasattr(response, 'content') else str(response)
               
               print(f"Analysis response generated: {response_content[:100]}...")
               
           except Exception as analysis_error:
               print(f"Error in document analysis: {str(analysis_error)}")
               print(traceback.format_exc())
               return jsonify({'response': 'Sorry, I encountered an issue analyzing this document. Please try again with a different document or format.'}), 200
           
           return jsonify({'response': response_content})
       
       elif feature == 'legal-templates':
           print("Processing legal template generation")
           try:
               # Generate the template based on the requested type
               template = template_chain.invoke({"document_type": message})
               template_content = template.content if hasattr(template, 'content') else str(template)
               print(f"Template generated for '{message}'")
           except Exception as template_error:
               print(f"Error in template generation: {str(template_error)}")
               print(traceback.format_exc())
               # Generic message without technical details
               return jsonify({'response': 'Sorry, I encountered an issue creating this template. Please try a different template type or check your request.'}), 200
               
           return jsonify({
               'response': f"I've created a {message} template for you. You can use this as a starting point and customize it to your specific needs.",
               'template': template_content,
               'templateType': message
           })
       
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
               loader = PyPDFLoader(file_path)
               documents = loader.load()
               for doc in documents:
                   content += doc.page_content + "\n"
               print(f"Extracted {len(documents)} pages from PDF")
                   
           elif filename.endswith('.docx'):
               print("Processing DOCX file")
               loader = Docx2txtLoader(file_path)
               documents = loader.load()
               for doc in documents:
                   content += doc.page_content + "\n"
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
       
       # Check if the full document fits within 120k characters
       if len(content) <= 120000:
           # If it fits, process it directly without chunking
           print("Document fits within 120k characters, processing as a whole")
           response = final_analysis_chain.invoke({"document_key_info": content})
           response_content = response.content if hasattr(response, 'content') else str(response)
       else:
           # If not, use chunking
           print("Document exceeds 120k characters, splitting into chunks")
           chunks = text_splitter.split_text(content)
           print(f"Document split into {len(chunks)} chunks")
           
           if len(chunks) == 1:
               # If chunking results in a single chunk
               print("Document split into one chunk")
               response = final_analysis_chain.invoke({"document_key_info": chunks[0]})
               response_content = response.content if hasattr(response, 'content') else str(response)
           else:
               # Process multiple chunks
               print("Processing multiple chunks")
               chunk_analyses = []
               for i, chunk in enumerate(chunks):
                   print(f"Processing chunk {i+1}/{len(chunks)}")
                   chunk_analysis = chunk_analysis_chain.invoke({
                       "document_chunk": chunk,
                       "chunk_num": i+1,
                       "total_chunks": len(chunks)
                   })
                   chunk_content = chunk_analysis.content if hasattr(chunk_analysis, 'content') else str(chunk_analysis)
                   chunk_analyses.append(chunk_content)
               
               # Combine analyses
               print("Combining chunk analyses for final analysis")
               combined_analysis = "\n\n".join(chunk_analyses)
               response = final_analysis_chain.invoke({"document_key_info": combined_analysis})
               response_content = response.content if hasattr(response, 'content') else str(response)
       
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
   print("Starting Flask server on port 5002")
   app.run()
