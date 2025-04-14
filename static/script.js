document.addEventListener('DOMContentLoaded', function () {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const featureItems = document.querySelectorAll('.feature-item');

    // Update initial message timestamp
    const initialTimestamp = document.querySelector('.message.system .timestamp');
    if (initialTimestamp) {
        initialTimestamp.textContent = formatDate(new Date());
    }

    // Auto focus on input
    userInput.focus();

    // Visual effects on feature options
    featureItems.forEach(item => {
        item.addEventListener('click', function() {
            featureItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            
            // Visual selection effect
            const text = this.querySelector('span').textContent;
            addSystemMessage(`You've selected the feature: ${text}. How can I assist you?`);
        });
    });

    // Auto-resize textarea up to a maximum height
    userInput.addEventListener('input', function() {
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

    // Send message
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
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
                // Call API
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message
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
                addSystemMessage(data.response);
                
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
        const messageHTML = `
            <div class="message user">
                <div class="message-header">
                    <span class="sender">USER</span>
                    <span class="timestamp">${time}</span>
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
        
        const messageHTML = `
            <div class="message system">
                <div class="message-header">
                    <span class="sender">SYSTEM</span>
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
}); 