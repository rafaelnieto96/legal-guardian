from flask import Flask, render_template, request, jsonify
from langchain.llms import Cohere
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# Configuración de Cohere
cohere_api_key = os.getenv('COHERE_API_KEY')
llm = Cohere(cohere_api_key=cohere_api_key, temperature=0.7)

# Template para el chat legal
legal_template = """
Eres un asistente legal experto. Tu tarea es responder preguntas legales de manera clara, precisa y profesional.
Mantén un tono formal pero accesible, y siempre cita las leyes o regulaciones relevantes cuando sea posible.

Consulta del usuario: {query}

Respuesta:
"""

prompt = PromptTemplate(
    input_variables=["query"],
    template=legal_template
)

chain = LLMChain(llm=llm, prompt=prompt)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'Missing message parameter'}), 400
        
        response = chain.run(query=message)
        return jsonify({'response': response})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 