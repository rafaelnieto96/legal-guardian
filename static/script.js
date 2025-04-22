document.addEventListener('DOMContentLoaded', function () {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const uploadButton = document.getElementById('upload-button');
    const featureItems = document.querySelectorAll('.feature-item');

    let currentFeature = 'legal-consult';

    const initialTimestamp = document.querySelector('.message.system .timestamp');
    if (initialTimestamp) {
        initialTimestamp.textContent = formatDate(new Date());
    }

    userInput.focus();

    featureItems.forEach(item => {
        item.addEventListener('click', function () {
            const feature = this.getAttribute('data-feature');

            if (feature === currentFeature) {
                return;
            }

            featureItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            currentFeature = feature;

            userInput.value = '';

            let instructionText = '';

            switch (feature) {
                case 'legal-consult':
                    instructionText = "You've selected AI Legal Consultation. Ask any legal question, and I'll provide informative guidance based on general legal principles.";
                    uploadButton.style.display = 'none';
                    userInput.placeholder = "Type your legal query or question here...";
                    break;

                case 'document-analysis':
                    instructionText = "You've selected Document Analysis. Upload a legal document or paste its text here, and I'll provide an analysis highlighting key points, potential issues, and plain language explanations.";
                    uploadButton.style.display = 'flex';

                    if (window.innerWidth <= 768) {
                        userInput.placeholder = "Paste text or upload file...";
                    } else {
                        userInput.placeholder = "Paste document text or upload a file...";
                    }
                    break;

                case 'legal-templates':
                    instructionText = "You've selected Legal Document Templates. Type the kind of document template you need (e.g., 'Non-disclosure Agreement', 'Employment Contract', 'Will'), and I'll generate a customizable template you can download.";
                    uploadButton.style.display = 'none';
                    userInput.placeholder = "Type the document template you need...";
                    break;
            }

            addSystemMessage(instructionText);
        });
    });

    userInput.addEventListener('input', function () {
        this.style.height = '42px';

        const newHeight = Math.min(this.scrollHeight, 120);
        this.style.height = newHeight + 'px';

        if (this.scrollHeight > 120) {
            this.style.overflowY = 'auto';
        } else {
            this.style.overflowY = 'hidden';
        }

        if (this.value.length === 0) {
            this.scrollTop = 0;
        }
    });

    if (uploadButton) {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.txt,.doc,.docx,.pdf';
        fileInput.style.display = 'none';
        document.body.appendChild(fileInput);

        uploadButton.addEventListener('click', function () {
            fileInput.click();
        });

        fileInput.addEventListener('change', async function () {
            if (this.files.length > 0) {
                const file = this.files[0];
                const fileName = file.name;

                addUserMessage(`Uploaded document: ${fileName}`);
                addSystemMessage("Processing document. This may take a few seconds...");

                showTypingIndicator();

                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch('/api/document-upload', {
                        method: 'POST',
                        body: formData
                    });

                    await new Promise(resolve => setTimeout(resolve, 1500));

                    removeTypingIndicator();

                    if (!response.ok) {
                        throw new Error('Error in document upload');
                    }

                    const data = await response.json();

                    const processingMessage = document.querySelector('.message.system:nth-last-child(2)');
                    if (processingMessage) {
                        processingMessage.remove();
                    }

                    addSystemMessage(data.response);

                    fileInput.value = '';

                } catch (error) {
                    removeTypingIndicator();
                    console.error('Error:', error);

                    const processingMessage = document.querySelector('.message.system:nth-last-child(2)');
                    if (processingMessage) {
                        processingMessage.remove();
                    }

                    addSystemMessage('Sorry, there was an error analyzing your document. Please try again.');
                    fileInput.value = '';
                }
            }
        });
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const message = userInput.value.trim();
        if (message) {
            const now = new Date();
            const timeString = formatDate(now);

            addUserMessage(message, timeString);

            userInput.value = '';
            userInput.style.height = '42px';
            userInput.focus();

            showTypingIndicator();

            const thinkingTime = 1000 + Math.random() * 2000;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        feature: currentFeature
                    })
                });

                await new Promise(resolve => setTimeout(resolve, thinkingTime));

                removeTypingIndicator();

                if (!response.ok) {
                    throw new Error('Error in server response');
                }

                const data = await response.json();

                addSystemMessage(data.response);

                if (currentFeature === 'legal-templates' && data.template) {
                    const downloadButton = document.createElement('button');
                    downloadButton.className = 'glass-button-primary';
                    downloadButton.innerHTML = '<i class="fas fa-download"></i> Download Template';
                    downloadButton.style.marginTop = '10px';
                    downloadButton.style.padding = '8px 16px';
                    downloadButton.style.borderRadius = '6px';

                    const lastMessage = document.querySelector('.message.system:last-child .message-content');
                    lastMessage.appendChild(downloadButton);

                    downloadButton.addEventListener('click', async function () {
                        try {
                            const downloadResponse = await fetch('/api/download-template', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    template: data.template,
                                    templateType: data.templateType
                                })
                            });

                            if (!downloadResponse.ok) {
                                throw new Error('Download failed');
                            }

                            const blob = await downloadResponse.blob();

                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.style.display = 'none';
                            a.href = url;
                            a.download = `${data.templateType.replace(/ /g, '_')}_template.docx`;

                            document.body.appendChild(a);
                            a.click();

                            window.URL.revokeObjectURL(url);
                            document.body.removeChild(a);

                        } catch (error) {
                            console.error('Download error:', error);
                            addSystemMessage('Sorry, there was an error downloading the template. Please try again.');
                        }
                    });
                }
            } catch (error) {
                removeTypingIndicator();
                console.error('Error:', error);
                addSystemMessage('Sorry, a system error has occurred. Please try again.');
            }
        }
    }

    function addUserMessage(content, time) {
        const now = new Date();
        const timeString = time || formatDate(now);

        const messageHTML = `
            <div class="message user">
                <div class="message-header">
                    <span class="sender">USER</span>
                    <span class="timestamp">${timeString}</span>
                </div>
                <div class="message-content">
                    <p>${content}</p>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        scrollToBottom();
    }

    function addSystemMessage(content) {
        const now = new Date();
        const timeString = formatDate(now);

        const formattedContent = marked.parse(content);

        const messageHTML = `
            <div class="message system">
                <div class="message-header">
                    <span class="sender">SYSTEM</span>
                    <span class="timestamp">${timeString}</span>
                </div>
                <div class="message-content">
                    <div>${formattedContent}</div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const typingHTML = `
            <div class="message system" id="typing-indicator">
                <div class="message-header">
                    <span class="sender">SYSTEM</span>
                    <span class="timestamp">${formatDate(new Date())}</span>
                </div>
                <div class="message-content">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', typingHTML);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function formatDate(date) {
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    if (uploadButton && currentFeature !== 'document-analysis') {
        uploadButton.style.display = 'none';
    }
});