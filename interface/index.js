const sendBtn = document.getElementById("send");
const newRoomSm = document.getElementById("new-sm");
const newRoomCm = document.getElementById("new-cm");
const messageInput = document.getElementById("message");
const inputWrapper = document.querySelector(".input-wrapper");
const chatContainer = document.querySelector(".chat");

let socketConnections = [];

const establishConnection = (mode) => {
  active_room = JSON.parse(localStorage.getItem("active_room"));

  active_room.conversations.forEach((conv) => {
    newSocket = new WebSocket(
      `ws://localhost:8002/ws/room/${mode}/${active_room.id}/${conv.id}`
    );

    newSocket.addEventListener("open", () => {
      console.log(`Connected to WebSocket server for ${conv.model}`);
    });

    newSocket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      console.log("Message from server:", message);

      if (mode === "sm") {
        appendMessageToSmChat(message.response, "assistant");
      } else {
        appendMessageToCmChat(conv.id, message.response, "assistant");
      }
    });

    socketConnections.push({
      model: conv.model,
      socket: newSocket,
    });
  });
};

const createMessageItem = (message, role) => {
  const messageItem = document.createElement("div");

  messageItem.classList.add(
    role == "user" ? "usr-message" : "assistant-message"
  );
  messageItem.textContent = message;

  return messageItem;
};

const appendMessageToCmChat = (conversation_id, message, role) => {
  const messageItem = createMessageItem(message, role);

  document.querySelectorAll(".cm-conv").forEach((container) => {
    if (container.className.includes(conversation_id)) {
      container.appendChild(messageItem);
    }
  });
};

const appendMessageToSmChat = (message, role) => {
  const messageWrapper = document.querySelector(".sm-conv");
  const messageItem = createMessageItem(message, role);

  messageWrapper.appendChild(messageItem);
};

const appendMessageToAllChats = (message, role) => {
  const convContainers = document.querySelectorAll(".conv");

  convContainers.forEach((container) => {
    const messageItem = createMessageItem(message, role);
    container.appendChild(messageItem);
  });
};

const sendMessage = () => {
  const message = messageInput.value;

  if (socketConnections.length && message) {
    socketConnections.forEach((socket) => socket.socket.send(message));
    messageInput.value = "";
    console.log("Sent to server: ", message);

    appendMessageToAllChats(message, "user");
  } else {
    console.error("WebSocket not connected or message is empty");
  }
};

const redirectToRoom = (mode, room_id) => {
  document.location.href = `/room/${mode}/${room_id}`;
};

const createNewRoom = async (mode) => {
  try {
    const response = await fetch(`http://localhost:8002/room/${mode}`, {
      method: "POST",
    });

    if (response.ok) {
      const data = await response.json();

      console.log("New room created: ", JSON.stringify(data));
      localStorage.setItem("active_room", JSON.stringify(data));

      const room_id = data.id;

      if (room_id) {
        redirectToRoom(mode, room_id);
      } else {
        console.error("Room id not found");
      }
    }
  } catch (e) {
    console.error("Error: ", e);
  }
};

const showChatUI = (isVisible, mode) => {
  inputWrapper.classList.add(isVisible ? "d-flex" : "d-none");

  if (mode === "cm") {
    const active_room = JSON.parse(localStorage.getItem("active_room"));
    const convContainers = document.querySelectorAll(".cm-conv");

    convContainers.forEach((container) => container.classList.add("d-block"));
    chatContainer.classList.add("d-flex");

    active_room.conversations.forEach((conv, index) => {
      const modelNameContainer = document.createElement("div");
      modelNameContainer.innerText = conv.model;

      convContainers[index].classList.add(conv.id);
      convContainers[index].appendChild(modelNameContainer);
    });
  } else {
    const convContainer = document.querySelector(".sm-conv");
    convContainer.classList.add("d-block");
  }
};

const initializeChatOnPageLoad = () => {
  const pathParts = window.location.pathname.split("/");

  if (pathParts.length === 4 && pathParts[1] === "room" && pathParts[2]) {
    const mode = pathParts[2];
    const room_id = pathParts[3];
    console.log(`Page loaded for room: ${room_id}. Initializing chat.`);
    establishConnection(mode);
    showChatUI(true, mode);
  } else {
    console.log(
      "Page loaded. Not a specific room URL or ID missing. Hiding chat UI by default."
    );
  }
};

if (sendBtn) {
  sendBtn.addEventListener("click", sendMessage);
}
if (newRoomSm) {
  newRoomSm.addEventListener("click", () => createNewRoom("sm"));
}
if (newRoomCm) {
  newRoomCm.addEventListener("click", () => createNewRoom("cm"));
}

document.addEventListener("DOMContentLoaded", () => {
  initializeChatOnPageLoad();
});
