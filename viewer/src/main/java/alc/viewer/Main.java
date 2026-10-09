package alc.viewer;

import com.badlogic.gdx.backends.lwjgl3.Lwjgl3Application;
import com.badlogic.gdx.backends.lwjgl3.Lwjgl3ApplicationConfiguration;

public class Main {

    public static void main(String[] args) {
        String serverUrl = "ws://127.0.0.1:8765";
        if (args.length > 0) {
            serverUrl = args[0];
        }

        Lwjgl3ApplicationConfiguration config = new Lwjgl3ApplicationConfiguration();
        config.setTitle("ALC — Artificial Learning Civilization  |  Alpha & Albedo Observatory");
        config.setWindowedMode(1440, 900);
        config.useVsync(true);
        config.setForegroundFPS(60);
        config.setResizable(true);

        System.out.println("============================================================");
        System.out.println(" ALC 3D Desktop Observatory — Java / LibGDX");
        System.out.println(" Connecting to:  " + serverUrl);
        System.out.println(" Alpha (female, coral) & Albedo (female, turquoise)");
        System.out.println("============================================================");

        new Lwjgl3Application(new AlcObservatoryApp(serverUrl), config);
    }
}
