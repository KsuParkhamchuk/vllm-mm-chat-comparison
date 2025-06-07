const sendBtn = document.getElementById("send");
const newConvBtn = document.getElementById("new");
const messageInput = document.getElementById("message");
const inputContainer = document.querySelector(".input-container");
const chatContainer = document.querySelector(".chat");

let socket;

const establishConnection = (conversation_id) => {
    socket = new WebSocket(`ws://localhost:8000/ws/conversation/${conversation_id}`);

    socket.addEventListener("open", () => {
        console.log("Connected to WebSocket server");
    });
    
    socket.addEventListener("message", (event) => {
        const message = event.data
        console.log("Message from server:", message);
        appendMessageToTheChat(message, "assistant")
    });
}

const appendMessageToTheChat = (message, role) => {
    const messageWrapper = document.createElement("div");
    const messageItem = document.createElement("div");
    
    messageWrapper.classList.add("msg-wrapper");
    messageItem.classList.add(role == "user" ? "usr-message" : "assistant-message");
    
    messageItem.textContent = message;
    messageWrapper.appendChild(messageItem);
    chatContainer.appendChild(messageWrapper);
}

const sendMessage = () => {
    const message = messageInput.value;

    if (socket && socket.readyState === WebSocket.OPEN && message) {
        socket.send(message);
        messageInput.value = '';
        console.log("Sent to server: ", message);
        appendMessageToTheChat(message, "user")
    } else {
        console.error("WebSocket not connected or message is empty")
    }
}

const redirectToConversation = (conversation_id) => {
    document.location.href = `/conversation/${conversation_id}`;
}

const createNewChat = async () => {
    try {
        const response = await fetch("http://localhost:8000/conversation", { method: "POST" })
    
        if (response.ok) {
            const data = await response.json();
            console.log("New conversation created: ", data.conversation_id);

            const conversation_id = data.conversation_id;
            if (conversation_id) {
                redirectToConversation(conversation_id);
            } else {
                console.error("Conversation id not found");
            }
        }
    } 
    catch(e) {
        console.error("Error: ", e);
    }
}

const showChatUI = (isVisible) => {
    inputContainer.style.display = isVisible ? "block" : "none"; 
}

const initializeChatOnPageLoad = () => {
    const pathParts = window.location.pathname.split('/');
    if (pathParts.length === 3 && pathParts[1] === 'conversation' && pathParts[2]) {
        const conversationIdFromUrl = pathParts[2];
        console.log(`Page loaded for conversation: ${conversationIdFromUrl}. Initializing chat.`);
        establishConnection(conversationIdFromUrl);
        showChatUI(true);
    } else {
        console.log("Page loaded. Not a specific conversation URL or ID missing. Hiding chat UI by default.");
    }
};


if (sendBtn) {
    sendBtn.addEventListener("click", sendMessage);
}
if (newConvBtn) {
    newConvBtn.addEventListener("click", createNewChat);
}

document.addEventListener('DOMContentLoaded', () => {
    initializeChatOnPageLoad();
});