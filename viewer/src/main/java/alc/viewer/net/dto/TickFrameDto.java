package alc.viewer.net.dto;

import java.util.List;

public class TickFrameDto {
    public String type;
    public int tick;
    public String weather;
    public boolean is_raining;
    public boolean is_paused;
    public List<AgentStateDto> agents;
    public List<PlantDto> plants;
    public List<GroundItemDto> ground_items;
    public List<EventLogDto> events;
    public List<ChatMessageDto> communication;
}
