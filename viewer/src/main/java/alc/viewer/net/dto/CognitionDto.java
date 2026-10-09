package alc.viewer.net.dto;

public class CognitionDto {
    public int current_action;
    public String action_name = "WAIT";
    public int known_states;
    public int memory_size;
    public int successful_experiences;
    public float exploration_rate;
    public int learning_events;
    public float recorded_mistakes;
    public int total_steps;
}
