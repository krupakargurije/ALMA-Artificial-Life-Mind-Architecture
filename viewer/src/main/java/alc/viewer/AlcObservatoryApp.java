package alc.viewer;

import com.badlogic.gdx.ApplicationAdapter;
import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.InputAdapter;
import com.badlogic.gdx.InputMultiplexer;
import alc.viewer.net.WebSocketClientService;
import alc.viewer.net.dto.EventLogDto;
import alc.viewer.net.dto.TickFrameDto;
import alc.viewer.net.dto.WorldInitDto;
import alc.viewer.render.OrbitCameraController;
import alc.viewer.render.World3DRenderer;
import alc.viewer.ui.ObservatoryHud;

import java.util.List;

public class AlcObservatoryApp extends ApplicationAdapter {

    private final String serverUrl;
    private WebSocketClientService wsService;
    private World3DRenderer world3DRenderer;
    private ObservatoryHud observatoryHud;

    private boolean isPaused = false;
    private float currentTps = 5.0f;

    private static final float[] SPEED_PRESETS = { 1.0f, 5.0f, 10.0f, 20.0f, 50.0f };

    public AlcObservatoryApp(String serverUrl) {
        this.serverUrl = serverUrl;
    }

    @Override
    public void create() {
        world3DRenderer = new World3DRenderer();
        observatoryHud  = new ObservatoryHud();

        wsService = new WebSocketClientService(serverUrl);
        wsService.start();

        // Input Handling
        InputMultiplexer multiplexer = new InputMultiplexer();
        multiplexer.addProcessor(new InputAdapter() {
            @Override
            public boolean keyDown(int keycode) {
                // If input box is focused, let keyTyped handle it (except Escape to unfocus)
                if (observatoryHud.isInputFocused) {
                    if (keycode == Input.Keys.ESCAPE) {
                        observatoryHud.isInputFocused = false;
                        return true;
                    }
                    return false;
                }

                switch (keycode) {
                    case Input.Keys.SPACE -> {
                        togglePause();
                        return true;
                    }
                    case Input.Keys.N -> {
                        wsService.sendStep();
                        return true;
                    }

                    // ── HUD PANEL TOGGLE HOTKEYS ──────────────────────────────
                    case Input.Keys.T, Input.Keys.SLASH -> {
                        observatoryHud.toggleConsole();
                        return true;
                    }
                    case Input.Keys.V -> {
                        observatoryHud.toggleCleanView();
                        return true;
                    }
                    case Input.Keys.NUM_1 -> {
                        observatoryHud.toggleAlpha();
                        return true;
                    }
                    case Input.Keys.NUM_2 -> {
                        observatoryHud.toggleAlbedo();
                        return true;
                    }
                    case Input.Keys.NUM_3 -> {
                        observatoryHud.toggleEvents();
                        return true;
                    }

                    // ── MONITORING / TRACKING KEYS ────────────────────────────
                    case Input.Keys.TAB -> {
                        world3DRenderer.getCameraController().cycleTrackingMode();
                        return true;
                    }
                    case Input.Keys.A, Input.Keys.F1 -> {
                        world3DRenderer.getCameraController().setTrackingMode(OrbitCameraController.TrackingMode.ALPHA);
                        return true;
                    }
                    case Input.Keys.B, Input.Keys.R, Input.Keys.F2 -> {
                        world3DRenderer.getCameraController().setTrackingMode(OrbitCameraController.TrackingMode.ALBEDO);
                        return true;
                    }
                    case Input.Keys.NUM_0, Input.Keys.NUMPAD_0, Input.Keys.C, Input.Keys.HOME -> {
                        world3DRenderer.getCameraController().setFocus(16f, 0f, 16f);
                        return true;
                    }

                    // ── SIMULATION SPEED KEYS ─────────────────────────────────
                    case Input.Keys.LEFT_BRACKET -> {
                        cycleSpeed(false);
                        return true;
                    }
                    case Input.Keys.RIGHT_BRACKET -> {
                        cycleSpeed(true);
                        return true;
                    }
                    case Input.Keys.NUM_4, Input.Keys.NUMPAD_4 -> {
                        currentTps = 10.0f;
                        wsService.sendSpeed(currentTps);
                        return true;
                    }
                    case Input.Keys.NUM_5, Input.Keys.NUMPAD_5 -> {
                        currentTps = 20.0f;
                        wsService.sendSpeed(currentTps);
                        return true;
                    }
                    case Input.Keys.NUM_6, Input.Keys.NUMPAD_6 -> {
                        currentTps = 50.0f;
                        wsService.sendSpeed(currentTps);
                        return true;
                    }
                }
                return false;
            }

            @Override
            public boolean keyTyped(char character) {
                return observatoryHud.handleKeyTyped(character, wsService);
            }

            @Override
            public boolean touchDown(int screenX, int screenY, int pointer, int button) {
                if (button == Input.Buttons.LEFT) {
                    // 1. Check if user clicked inside HUD (Navbar tabs, Close buttons, Console, etc.)
                    if (observatoryHud.handleTouchDown(screenX, screenY, wsService, world3DRenderer.getCameraController(), AlcObservatoryApp.this::togglePause)) {
                        return true;
                    }

                    int w = Gdx.graphics.getWidth();
                    // Alpha panel (top-left) -> Track Alpha if panel open
                    if (observatoryHud.showAlpha && screenX >= 10 && screenX <= 295 && screenY >= 50 && screenY <= 400) {
                        world3DRenderer.getCameraController().setTrackingMode(OrbitCameraController.TrackingMode.ALPHA);
                        observatoryHud.targetRecipient = "alpha";
                        return true;
                    }
                    // Albedo panel (top-right) -> Track Albedo if panel open
                    if ((observatoryHud.showAlbedo || observatoryHud.showRoselia) && screenX >= w - 295 && screenX <= w - 10 && screenY >= 50 && screenY <= 400) {
                        world3DRenderer.getCameraController().setTrackingMode(OrbitCameraController.TrackingMode.ALBEDO);
                        observatoryHud.targetRecipient = "albedo";
                        return true;
                    }
                }
                return false;
            }
        });

        // Add camera controller for mouse drag & scroll
        multiplexer.addProcessor(world3DRenderer.getCameraController());
        Gdx.input.setInputProcessor(multiplexer);
    }

    public void togglePause() {
        isPaused = !isPaused;
        if (isPaused) wsService.sendPause();
        else wsService.sendResume();
    }

    private void cycleSpeed(boolean faster) {
        int idx = 1;
        for (int i = 0; i < SPEED_PRESETS.length; i++) {
            if (Math.abs(SPEED_PRESETS[i] - currentTps) < 0.1f) {
                idx = i;
                break;
            }
        }
        if (faster) idx = Math.min(SPEED_PRESETS.length - 1, idx + 1);
        else idx = Math.max(0, idx - 1);
        currentTps = SPEED_PRESETS[idx];
        wsService.sendSpeed(currentTps);
    }

    @Override
    public void resize(int width, int height) {
        world3DRenderer.resize(width, height);
        observatoryHud.resize(width, height);
    }

    @Override
    public void render() {
        // Sync static world grid if newly loaded
        WorldInitDto init = wsService.getLatestWorldInit();
        if (init != null) {
            world3DRenderer.setWorldInit(init);
        }

        TickFrameDto frame = wsService.getLatestFrame();
        List<EventLogDto> events = wsService.getRecentEventsSnapshot();

        // 1. Render 3D World (terrain, crops, items, Alpha & Roselia)
        world3DRenderer.updateAndRender(frame);

        // 2. Render 2D Observatory HUD overlay with active camera tracking mode & live conversation history
        observatoryHud.render(frame, events, wsService.isConnected(), isPaused, currentTps,
                world3DRenderer.getCameraController().getTrackingMode(),
                wsService.getConversationHistorySnapshot());
    }

    @Override
    public void dispose() {
        if (wsService != null) wsService.dispose();
        if (world3DRenderer != null) world3DRenderer.dispose();
        if (observatoryHud != null) observatoryHud.dispose();
    }
}
