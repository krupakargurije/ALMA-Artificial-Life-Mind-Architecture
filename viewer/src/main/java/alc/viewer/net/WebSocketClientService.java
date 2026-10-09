package alc.viewer.net;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import alc.viewer.net.dto.ChatMessageDto;
import alc.viewer.net.dto.EventLogDto;
import alc.viewer.net.dto.TickFrameDto;
import alc.viewer.net.dto.WorldInitDto;
import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;

import java.net.URI;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

public class WebSocketClientService {

    private final URI serverUri;
    private final Gson gson = new Gson();

    private WebSocketClient client;
    private final AtomicBoolean isConnected = new AtomicBoolean(false);
    private final AtomicBoolean shouldRun = new AtomicBoolean(true);

    private final AtomicReference<WorldInitDto> latestWorldInit = new AtomicReference<>();
    private final AtomicReference<TickFrameDto> latestFrame = new AtomicReference<>();

    // Thread-safe recent events buffer for Observatory HUD (up to 100 entries)
    private final List<EventLogDto> recentEvents = Collections.synchronizedList(new ArrayList<>());
    private static final int MAX_EVENTS_HISTORY = 100;

    // Thread-safe conversation history buffer for Interaction Console
    private final List<ChatMessageDto> conversationHistory = Collections.synchronizedList(new ArrayList<>());
    private static final int MAX_CHAT_HISTORY = 50;

    public WebSocketClientService(String url) {
        try {
            this.serverUri = new URI(url);
        } catch (Exception e) {
            throw new RuntimeException("Invalid WebSocket URI: " + url, e);
        }
    }

    public void start() {
        shouldRun.set(true);
        Thread connectionThread = new Thread(this::connectionLoop, "WebSocketConnectionThread");
        connectionThread.setDaemon(true);
        connectionThread.start();
    }

    private void connectionLoop() {
        while (shouldRun.get()) {
            try {
                if (client == null || client.isClosed()) {
                    client = new WebSocketClient(serverUri) {
                        @Override
                        public void onOpen(ServerHandshake handshakedata) {
                            isConnected.set(true);
                            System.out.println("[WebSocketClient] Connected to ALC Server at " + serverUri);
                            EventLogDto initEvt = new EventLogDto();
                            initEvt.tick = 0;
                            initEvt.agent_name = "Observatory";
                            initEvt.event_id = 900;
                            initEvt.text = "Observatory linked: Alpha & Albedo active in garden sanctuary.";
                            initEvt.category = "learning";
                            synchronized (recentEvents) {
                                if (recentEvents.isEmpty()) {
                                    recentEvents.add(initEvt);
                                }
                            }
                        }

                        @Override
                        public void onMessage(String message) {
                            handleMessage(message);
                        }

                        @Override
                        public void onClose(int code, String reason, boolean remote) {
                            isConnected.set(false);
                            System.out.println("[WebSocketClient] Disconnected (code=" + code + ", reason=" + reason + ")");
                        }

                        @Override
                        public void onError(Exception ex) {
                            isConnected.set(false);
                        }
                    };
                    client.connectBlocking();
                }
            } catch (Exception ignored) {
            }

            try {
                Thread.sleep(2000);
            } catch (InterruptedException e) {
                break;
            }
        }
    }

    private void handleMessage(String message) {
        try {
            JsonObject obj = JsonParser.parseString(message).getAsJsonObject();
            if (!obj.has("type")) return;
            String type = obj.get("type").getAsString();

            if ("world_init".equals(type)) {
                WorldInitDto init = gson.fromJson(message, WorldInitDto.class);
                latestWorldInit.set(init);
            } else if ("tick_frame".equals(type)) {
                TickFrameDto frame = gson.fromJson(message, TickFrameDto.class);
                latestFrame.set(frame);

                if (frame.events != null) {
                    synchronized (recentEvents) {
                        for (EventLogDto evt : frame.events) {
                            recentEvents.add(evt);
                        }
                        while (recentEvents.size() > MAX_EVENTS_HISTORY) {
                            recentEvents.remove(0);
                        }
                    }
                }

                if (frame.communication != null) {
                    synchronized (conversationHistory) {
                        for (ChatMessageDto chat : frame.communication) {
                            boolean exists = conversationHistory.stream().anyMatch(c -> c.id != null && c.id.equals(chat.id));
                            if (!exists) {
                                conversationHistory.add(chat);
                            }
                        }
                        while (conversationHistory.size() > MAX_CHAT_HISTORY) {
                            conversationHistory.remove(0);
                        }
                    }
                }
            } else if ("chat_message".equals(type)) {
                if (obj.has("message")) {
                    ChatMessageDto chat = gson.fromJson(obj.get("message"), ChatMessageDto.class);
                    synchronized (conversationHistory) {
                        boolean exists = conversationHistory.stream().anyMatch(c -> c.id != null && c.id.equals(chat.id));
                        if (!exists) {
                            conversationHistory.add(chat);
                        }
                        while (conversationHistory.size() > MAX_CHAT_HISTORY) {
                            conversationHistory.remove(0);
                        }
                    }
                }
            }
        } catch (Exception e) {
            System.err.println("[WebSocketClient] Error parsing incoming packet: " + e.getMessage());
        }
    }

    public boolean isConnected() {
        return isConnected.get();
    }

    public WorldInitDto getLatestWorldInit() {
        return latestWorldInit.get();
    }

    public TickFrameDto getLatestFrame() {
        return latestFrame.get();
    }

    public List<EventLogDto> getRecentEventsSnapshot() {
        synchronized (recentEvents) {
            return new ArrayList<>(recentEvents);
        }
    }

    public List<ChatMessageDto> getConversationHistorySnapshot() {
        synchronized (conversationHistory) {
            return new ArrayList<>(conversationHistory);
        }
    }

    public void sendHumanMessage(String target, String text) {
        JsonObject cmd = new JsonObject();
        cmd.addProperty("command", "human_message");
        cmd.addProperty("target", target.toLowerCase());
        cmd.addProperty("text", text);
        sendCommand(cmd);
    }

    public void sendTeachSymbol(String target, String symbol, String conceptType, int conceptId) {
        JsonObject cmd = new JsonObject();
        cmd.addProperty("command", "teach_symbol");
        cmd.addProperty("target", target.toLowerCase());
        cmd.addProperty("symbol", symbol);
        cmd.addProperty("concept_type", conceptType);
        cmd.addProperty("concept_id", conceptId);
        sendCommand(cmd);
    }

    public void sendCommand(JsonObject command) {
        if (client != null && client.isOpen()) {
            client.send(command.toString());
        }
    }

    public void sendPause() {
        JsonObject cmd = new JsonObject();
        cmd.addProperty("command", "pause");
        sendCommand(cmd);
    }

    public void sendResume() {
        JsonObject cmd = new JsonObject();
        cmd.addProperty("command", "resume");
        sendCommand(cmd);
    }

    public void sendStep() {
        JsonObject cmd = new JsonObject();
        cmd.addProperty("command", "step");
        sendCommand(cmd);
    }

    public void sendSpeed(float tps) {
        JsonObject cmd = new JsonObject();
        cmd.addProperty("command", "set_speed");
        cmd.addProperty("tps", tps);
        sendCommand(cmd);
    }

    public void sendReset(int seed) {
        JsonObject cmd = new JsonObject();
        cmd.addProperty("command", "reset");
        cmd.addProperty("seed", seed);
        sendCommand(cmd);
    }

    public void dispose() {
        shouldRun.set(false);
        if (client != null) {
            try {
                client.close();
            } catch (Exception ignored) {}
        }
    }
}
