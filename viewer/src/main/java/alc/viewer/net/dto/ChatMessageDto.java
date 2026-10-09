package alc.viewer.net.dto;

import java.util.List;

public class ChatMessageDto {
    public String id;
    public String sender;
    public String receiver;
    public int tick;
    public String content;
    public String comm_type;
    public String status;
    public float confidence;
    public boolean is_understood;
    public List<String> associated_concepts;
    public int evidence_count;
    public String source;
    public boolean is_autonomous;
    public double timestamp;
}
