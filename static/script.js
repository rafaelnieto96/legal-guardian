document.addEventListener('DOMContentLoaded', function () {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const uploadButton = document.getElementById('upload-button');
    const featureItems = document.querySelectorAll('.feature-item');

    // Track the current active feature
    let currentFeature = 'legal-consult';

    // Update initial message timestamp
    const initialTimestamp = document.querySelector('.message.system .timestamp');
    if (initialTimestamp) {
        initialTimestamp.textContent = formatDate(new Date());
    }

    // Auto focus on input
    userInput.focus();

    // Visual effects on feature options
    featureItems.forEach(item => {
        item.addEventListener('click', function () {
            // Get the selected feature
            const feature = this.getAttribute('data-feature');
            
            // Si ya está seleccionada la misma característica, no hacer nada
            if (feature === currentFeature) {
                return;
            }
            
            // Actualizar las clases y el estado
            featureItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            currentFeature = feature;

            // Clear input
            userInput.value = '';

            // Show appropriate instructions based on the feature
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
                    // Usar placeholder más corto en móviles
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

            // Add system message with instructions
            addSystemMessage(instructionText);
        });
    });

    // Auto-resize textarea up to a maximum height
    userInput.addEventListener('input', function () {
        // Reset height to get the correct scrollHeight
        this.style.height = '42px';

        // Calculate new height based on content up to max-height
        const newHeight = Math.min(this.scrollHeight, 120);
        this.style.height = newHeight + 'px';

        // Show scrollbar only when needed
        if (this.scrollHeight > 120) {
            this.style.overflowY = 'auto';
        } else {
            this.style.overflowY = 'hidden';
        }

        // Reset scroll position if empty
        if (this.value.length === 0) {
            this.scrollTop = 0;
        }
    });

    // File upload handling
    if (uploadButton) {
        // Create a hidden file input
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

                // Add a message showing the uploaded file
                addUserMessage(`Uploaded document: ${fileName}`);

                // Show document processing message
                addSystemMessage("Processing document. This may take a few seconds...");
                
                // Show typing indicator
                showTypingIndicator();

                // Create form data for the upload
                const formData = new FormData();
                formData.append('file', file);

                try {
                    // Call API to analyze the document
                    const response = await fetch('/api/document-upload', {
                        method: 'POST',
                        body: formData
                    });

                    // Wait minimum thinking time
                    await new Promise(resolve => setTimeout(resolve, 1500));

                    // Remove indicator
                    removeTypingIndicator();

                    if (!response.ok) {
                        throw new Error('Error in document upload');
                    }

                    const data = await response.json();
                    
                    // Replace the processing message with the actual analysis
                    const processingMessage = document.querySelector('.message.system:nth-last-child(2)');
                    if (processingMessage) {
                        processingMessage.remove();
                    }
                    
                    addSystemMessage(data.response);

                    // Reset file input
                    fileInput.value = '';

                } catch (error) {
                    removeTypingIndicator();
                    console.error('Error:', error);
                    
                    // Replace the processing message with error message
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

    // Send message
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
            // Format current time
            const now = new Date();
            const timeString = formatDate(now);

            // Add user message
            addUserMessage(message, timeString);

            // Reset and focus the textarea
            userInput.value = '';
            userInput.style.height = '42px';
            userInput.focus();

            // Show typing indicator
            showTypingIndicator();

            // Thinking time simulator
            const thinkingTime = 1000 + Math.random() * 2000;

            try {
                // Call API with the current feature
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

                // Wait minimum thinking time
                await new Promise(resolve => setTimeout(resolve, thinkingTime));

                // Remove indicator
                removeTypingIndicator();

                if (!response.ok) {
                    throw new Error('Error in server response');
                }

                const data = await response.json();

                // Handle regular responses
                addSystemMessage(data.response);

                // If it's a template, add a download button
                if (currentFeature === 'legal-templates' && data.template) {
                    // Create a download button
                    const downloadButton = document.createElement('button');
                    downloadButton.className = 'glass-button-primary';
                    downloadButton.innerHTML = '<i class="fas fa-download"></i> Download Template';
                    downloadButton.style.marginTop = '10px';
                    downloadButton.style.padding = '8px 16px';
                    downloadButton.style.borderRadius = '6px';

                    // Add the button to the last system message
                    const lastMessage = document.querySelector('.message.system:last-child .message-content');
                    lastMessage.appendChild(downloadButton);

                    // Handle download click
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

                            // Create a blob from the response
                            const blob = await downloadResponse.blob();

                            // Create download link
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.style.display = 'none';
                            a.href = url;
                            a.download = `${data.templateType.replace(/ /g, '_')}_template.docx`;

                            // Trigger download
                            document.body.appendChild(a);
                            a.click();

                            // Cleanup
                            window.URL.revokeObjectURL(url);
                            document.body.removeChild(a);

                        } catch (error) {
                            console.error('Download error:', error);
                            addSystemMessage('Sorry, there was an error downloading the template. Please try again.');
                        }
                    });
                }

                // Sound effect (optional)
                playMessageSound();
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
    
        // Usar marked.js para convertir markdown a HTML
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

    function formatTime(date) {
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    function formatDate(date) {
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    function playMessageSound() {
        // This function is prepared to implement sounds
        // if desired in the future
    }

    // Initially hide upload button if we're not in document analysis mode
    if (uploadButton && currentFeature !== 'document-analysis') {
        uploadButton.style.display = 'none';
    }
});