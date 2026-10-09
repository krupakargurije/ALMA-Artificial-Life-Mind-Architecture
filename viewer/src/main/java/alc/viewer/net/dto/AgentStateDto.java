package alc.viewer.net.dto;

import java.util.List;
import java.util.Map;

public class AgentStateDto {
    public int id;
    public String name;
    public String gender;
    public int x;
    public int y;
    public List<Integer> facing;
    public Integer holding;
    public Map<String, Float> needs;
    public boolean alive;
    public int lives;
    public CognitionDto cognition;
}
