# Legal Guardian

A modern AI-powered legal assistant application that provides legal consultation, document analysis, and legal templates.

## Overview

Legal Guardian is a web application designed to help users with various legal needs through AI-powered assistance. The application features a modern, responsive interface with an intuitive chat-based interaction model.

## Features

### 1. AI Legal Consultation
Ask any legal question and receive informative guidance based on general legal principles. The consultation feature provides:
- Answers to legal questions
- Explanations of legal concepts
- General legal guidance

### 2. Document Analysis
Upload or paste text from legal documents for analysis. The system will:
- Highlight key points
- Identify potential issues
- Provide plain language explanations
- Summarize complex legal content

### 3. Legal Templates
Generate customizable legal document templates for various purposes:
- Non-disclosure Agreements
- Employment Contracts
- Wills
- Power of Attorney
- And many more

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python (API endpoints for chat, document processing, and template generation)
- **UI**: Custom-built responsive interface with glassmorphism design

## Setup

### Prerequisites

- Python 3.8+
- Node.js (optional, for development)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/legal-guardian.git
cd legal-guardian
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (create a `.env` file):
```
COHERE_API_KEY=your_secret_key
```

4. Run the application:
```bash
python app.py
```

5. Access the application in your browser at `http://localhost:5000`

## Usage

1. **Select a Feature**: Choose from Legal Consultation, Document Analysis, or Legal Templates
2. **Interact via Chat**:
   - Type legal questions for consultation
   - Upload documents for analysis
   - Request specific templates
3. **Download or Save Results**: Templates can be downloaded in DOCX format

## Project Structure

```
legal-guardian/
├── app.py              # Main application file
├── static/             # Static assets
│   ├── style.css       # CSS styling
│   ├── script.js       # Frontend JavaScript
│   └── images/         # Images and icons
├── templates/          # HTML templates
├── api/                # API endpoints
└── utils/              # Utility functions
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
