package alc.viewer.net.dto;

import java.util.List;

public class WorldInitDto {
    public String type;
    public int width;
    public int height;
    public int seed;
    public List<List<Integer>> tiles;
    public List<AgentInitDto> agents;

    public static class AgentInitDto {
        public int id;
        public String name;
        public String gender;
        public int x;
        public int y;
    }
}
