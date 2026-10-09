package alc.viewer.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.GlyphLayout;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.badlogic.gdx.math.Matrix4;
import com.badlogic.gdx.utils.Disposable;
import alc.viewer.net.WebSocketClientService;
import alc.viewer.net.dto.AgentStateDto;
import alc.viewer.net.dto.ChatMessageDto;
import alc.viewer.net.dto.CognitionDto;
import alc.viewer.net.dto.EventLogDto;
import alc.viewer.net.dto.TickFrameDto;
import alc.viewer.render.OrbitCameraController;

import java.util.List;
import java.util.Map;

/**
 * Premium Observatory Command & Navigation HUD.
 *
 * Designed for maximum 3D visibility and research cleanliness:
 * - Top Command & Navigation Bar: Always visible, providing simulation status,
 *   panel toggles (Console, Alpha, Roselia, Events, Clean View), and camera controls.
 * - Collapsible / Togglable Panels:
 *     - Alpha Telemetry Drawer (left)
 *     - Roselia Telemetry Drawer (right)
 *     - Interaction Console (centered-bottom, focused modal)
 *     - Cognitive Event Stream (bottom drawer)
 * - All panels feature clean close [✕] buttons and status indicators in the navbar.
 */
public class ObservatoryHud implements Disposable {

    private final SpriteBatch batch;
    private final ShapeRenderer sr;
    private final BitmapFont fontLarge;
    private final BitmapFont fontMid;
    private final BitmapFont fontSmall;
    private final GlyphLayout layout = new GlyphLayout();

    // Sizing
    private int SW, SH;
    private static final int PANEL_W    = 280;
    private static final int PANEL_H    = 330;
    private static final int TOP_BAR_H  = 46;
    private static final int STREAM_H   = 85;
    private static final int PAD        = 12;
    private static final int BAR_H      = 10;

    // Panel Visibility Toggles (Clean View by default)
    public boolean showConsole        = false; // user can open via navbar or hotkey T
    public boolean showAlpha          = false; // opens via navbar or hotkey 1
    public boolean showAlbedo         = false; // opens via navbar or hotkey 2
    public boolean showRoselia        = false; // alias for compatibility
    public boolean showEvents         = true;  // event stream at bottom
    public boolean cleanViewMode      = false; // when true, hides all panels
    public boolean hasUnreadAutonomous = false;
    private int lastSeenHistorySize   = 0;

    // Interaction Console state
    public String targetRecipient = "alpha"; // "alpha", "albedo", "both"
    public final StringBuilder inputText = new StringBuilder();
    public boolean isInputFocused = false;
    private float cursorTimer = 0f;

    // Quick Question Presets
    private static final String[] QUICK_QUESTIONS = {
            "Hello!",
            "Who are you?",
            "What is water?",
            "What is fruit?",
            "Are you thirsty?",
            "How do you feel?"
    };

    // Color palette
    private static final Color BG_DARK      = new Color(0.04f, 0.05f, 0.09f, 0.90f);
    private static final Color BG_MID       = new Color(0.07f, 0.09f, 0.15f, 0.88f);
    private static final Color BG_LIGHT     = new Color(0.12f, 0.15f, 0.22f, 0.85f);
    private static final Color BG_BAR_TRACK = new Color(0.10f, 0.12f, 0.18f, 1.00f);

    private static final Color BORDER_ALPHA   = new Color(0.96f, 0.40f, 0.30f, 0.75f);
    private static final Color BORDER_ALBEDO  = new Color(0.22f, 0.82f, 0.74f, 0.75f);
    private static final Color BORDER_ROSELIA = BORDER_ALBEDO;
    private static final Color BORDER_CONSOLE = new Color(0.28f, 0.65f, 0.95f, 0.75f);
    private static final Color BORDER_STREAM  = new Color(0.35f, 0.42f, 0.60f, 0.60f);

    private static final Color TXT_HEAD  = new Color(0.96f, 0.97f, 1.00f, 1.0f);
    private static final Color TXT_BODY  = new Color(0.86f, 0.89f, 0.95f, 1.0f);
    private static final Color TXT_MUTED = new Color(0.58f, 0.64f, 0.74f, 1.0f);

    private static final Color BAR_ENERGY = new Color(0.98f, 0.78f, 0.12f, 1f);
    private static final Color BAR_WATER  = new Color(0.18f, 0.66f, 0.98f, 1f);
    private static final Color BAR_FOOD   = new Color(0.30f, 0.85f, 0.35f, 1f);
    private static final Color BAR_HEALTH = new Color(0.96f, 0.22f, 0.32f, 1f);

    private static final Color EVT_REWARD  = new Color(0.28f, 0.96f, 0.40f, 1f);
    private static final Color EVT_DAMAGE  = new Color(0.98f, 0.28f, 0.22f, 1f);
    private static final Color EVT_LEARN   = new Color(0.80f, 0.40f, 0.98f, 1f);
    private static final Color EVT_NEUTRAL = new Color(0.60f, 0.65f, 0.75f, 1f);

    private static final Color ALPHA_NAME_COLOR  = new Color(0.98f, 0.50f, 0.42f, 1f);
    private static final Color ALBEDO_NAME_COLOR = new Color(0.30f, 0.88f, 0.80f, 1f);
    private static final Color ROSELIA_NAME_COLOR = ALBEDO_NAME_COLOR;

    private final Matrix4 uiMatrix = new Matrix4();

    public ObservatoryHud() {
        batch = new SpriteBatch();
        sr    = new ShapeRenderer();

        BitmapFont fl = null, fm = null, fs = null;
        try {
            fl = new BitmapFont(Gdx.files.internal("fonts/font-large.fnt"));
            fm = new BitmapFont(Gdx.files.internal("fonts/font-mid.fnt"));
            fs = new BitmapFont(Gdx.files.internal("fonts/font-small.fnt"));

            fl.getRegion().getTexture().setFilter(Texture.TextureFilter.Linear, Texture.TextureFilter.Linear);
            fm.getRegion().getTexture().setFilter(Texture.TextureFilter.Linear, Texture.TextureFilter.Linear);
            fs.getRegion().getTexture().setFilter(Texture.TextureFilter.Linear, Texture.TextureFilter.Linear);
        } catch (Exception e) {
            System.err.println("[ObservatoryHud] Fallback to default bitmap fonts: " + e.getMessage());
            fl = new BitmapFont();
            fm = new BitmapFont();
            fs = new BitmapFont();
        }

        fontLarge = fl;
        fontMid   = fm;
        fontSmall = fs;

        fontLarge.setUseIntegerPositions(true);
        fontMid  .setUseIntegerPositions(true);
        fontSmall.setUseIntegerPositions(true);
    }


    public void resize(int w, int h) {
        SW = w; SH = h;
        uiMatrix.setToOrtho2D(0, 0, w, h);
    }

    public void toggleConsole() {
        showConsole = !showConsole;
        if (showConsole) {
            cleanViewMode = false;
            hasUnreadAutonomous = false;
            isInputFocused = true;
        }
    }

    public void toggleAlpha() {
        showAlpha = !showAlpha;
        if (showAlpha) cleanViewMode = false;
    }

    public void toggleAlbedo() {
        showAlbedo = !showAlbedo;
        showRoselia = showAlbedo;
        if (showAlbedo) cleanViewMode = false;
    }

    public void toggleRoselia() {
        toggleAlbedo();
    }

    public void toggleEvents() {
        showEvents = !showEvents;
        if (showEvents) cleanViewMode = false;
    }

    public void toggleCleanView() {
        cleanViewMode = !cleanViewMode;
        if (cleanViewMode) {
            showConsole = false;
            showAlpha = false;
            showAlbedo = false;
            showRoselia = false;
            showEvents = false;
        } else {
            showConsole = true;
            showEvents = true;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    public void render(TickFrameDto frame, List<EventLogDto> events,
                       boolean connected, boolean paused, float tps,
                       OrbitCameraController.TrackingMode trackingMode,
                       List<ChatMessageDto> conversationHistory) {

        if (SW == 0) resize(Gdx.graphics.getWidth(), Gdx.graphics.getHeight());
        cursorTimer += Gdx.graphics.getDeltaTime();

        // Check for new autonomous messages when console is closed
        if (conversationHistory != null && conversationHistory.size() > lastSeenHistorySize) {
            for (int i = lastSeenHistorySize; i < conversationHistory.size(); i++) {
                if (conversationHistory.get(i).is_autonomous && !showConsole) {
                    hasUnreadAutonomous = true;
                    break;
                }
            }
            lastSeenHistorySize = conversationHistory.size();
        }

        Gdx.gl.glEnable(GL20.GL_BLEND);
        Gdx.gl.glBlendFunc(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA);

        sr.setProjectionMatrix(uiMatrix);
        batch.setProjectionMatrix(uiMatrix);

        AgentStateDto alpha   = find(frame, 0);
        AgentStateDto albedo  = find(frame, 1);
        AgentStateDto roselia = albedo; // alias

        int navY = SH - TOP_BAR_H - PAD;
        int navW = SW - PAD * 2;

        // Dynamic panel coordinates
        int aX = PAD + 4;
        int aY = navY - 10 - PANEL_H;

        int rX = SW - PANEL_W - PAD - 4;
        int rY = navY - 10 - PANEL_H;

        int cW = Math.min(680, SW - PAD * 2 - 20);
        int cH = 240;
        int cX = (SW - cW) / 2;
        int cY = showEvents ? (PAD + STREAM_H + 8) : (PAD + 8);

        int sX = PAD;
        int sY = PAD;
        int sW = SW - PAD * 2;
        int sH = STREAM_H;

        // ── 1. FILLED BACKGROUNDS ─────────────────────────────────────────────
        sr.begin(ShapeRenderer.ShapeType.Filled);

        // A. Top Observatory Navigation Bar
        sr.setColor(BG_DARK);
        fillRounded(PAD, navY, navW, TOP_BAR_H, 6);

        // Navbar Tabs background fills
        drawNavbarPillsFilled(navY, navW, connected, paused);

        // B. Alpha Panel (if open)
        if (showAlpha) {
            sr.setColor(BG_MID);
            fillRounded(aX, aY, PANEL_W, PANEL_H, 8);
            if (alpha != null) drawBarTracks(aX + 76, aY + PANEL_H - 155, 145);
            if (alpha != null && alpha.needs != null) drawNeedBars(aX + 76, aY + PANEL_H - 155, 145, alpha.needs);
            // Close button
            sr.setColor(new Color(0.20f, 0.15f, 0.15f, 0.85f));
            fillRounded(aX + PANEL_W - 26, aY + PANEL_H - 24, 20, 18, 4);
        }

        // C. Albedo Panel (if open)
        if (showAlbedo || showRoselia) {
            sr.setColor(BG_MID);
            fillRounded(rX, rY, PANEL_W, PANEL_H, 8);
            if (albedo != null) drawBarTracks(rX + 76, rY + PANEL_H - 155, 145);
            if (albedo != null && albedo.needs != null) drawNeedBars(rX + 76, rY + PANEL_H - 155, 145, albedo.needs);
            // Close button
            sr.setColor(new Color(0.15f, 0.20f, 0.20f, 0.85f));
            fillRounded(rX + PANEL_W - 26, rY + PANEL_H - 24, 20, 18, 4);
        }


        // D. Interaction Console (if open)
        if (showConsole) {
            sr.setColor(BG_MID);
            fillRounded(cX, cY, cW, cH, 8);

            // Input box
            int inputY = cY + cH - 60;
            int inputW = cW - 100;
            sr.setColor(BG_DARK);
            fillRounded(cX + 14, inputY, inputW, 28, 4);

            // Send button
            sr.setColor(new Color(0.18f, 0.50f, 0.85f, 0.85f));
            fillRounded(cX + inputW + 22, inputY, 68, 28, 4);

            // Chat history box
            int chatBoxY = cY + 10;
            int chatBoxH = cH - 105;
            sr.setColor(BG_DARK);
            fillRounded(cX + 14, chatBoxY, cW - 28, chatBoxH, 6);

            // Close button
            sr.setColor(new Color(0.20f, 0.18f, 0.22f, 0.85f));
            fillRounded(cX + cW - 26, cY + cH - 24, 20, 18, 4);
        }

        // E. Cognitive Event Stream (if open)
        if (showEvents) {
            sr.setColor(BG_DARK);
            fillRounded(sX, sY, sW, sH, 6);
            // Close button
            sr.setColor(new Color(0.18f, 0.18f, 0.22f, 0.85f));
            fillRounded(sX + sW - 26, sY + sH - 20, 20, 16, 4);
        }

        sr.end();

        // ── 2. OUTLINES ───────────────────────────────────────────────────────
        sr.begin(ShapeRenderer.ShapeType.Line);

        // Top Nav Bar outline
        sr.setColor(new Color(0.30f, 0.38f, 0.55f, 0.65f));
        outlineRounded(PAD, navY, navW, TOP_BAR_H, 6);
        drawNavbarPillsOutlines(navY, navW, connected, paused);

        if (showAlpha) {
            sr.setColor(BORDER_ALPHA);
            outlineRounded(aX, aY, PANEL_W, PANEL_H, 8);
        }

        if (showAlbedo || showRoselia) {
            sr.setColor(BORDER_ALBEDO);
            outlineRounded(rX, rY, PANEL_W, PANEL_H, 8);
        }

        if (showConsole) {
            sr.setColor(BORDER_CONSOLE);
            outlineRounded(cX, cY, cW, cH, 8);

            int inputY = cY + cH - 60;
            int inputW = cW - 100;
            sr.setColor(isInputFocused ? new Color(0.3f, 0.85f, 1f, 0.95f) : new Color(0.3f, 0.4f, 0.5f, 0.6f));
            outlineRounded(cX + 14, inputY, inputW, 28, 4);
        }

        if (showEvents) {
            sr.setColor(BORDER_STREAM);
            outlineRounded(sX, sY, sW, sH, 6);
        }

        sr.end();

        // ── 3. TEXT & LABELS ──────────────────────────────────────────────────
        batch.begin();

        // Top Navigation Bar Content
        drawNavBarContent(navY, navW, frame, connected, paused, tps, trackingMode, alpha, albedo);

        // Panels
        if (showAlpha) {
            boolean alphaTracked = (trackingMode == OrbitCameraController.TrackingMode.ALPHA);
            drawAgentPanel(alpha, aX + 8, aY, "ALPHA", ALPHA_NAME_COLOR, BORDER_ALPHA, alphaTracked);
            fontSmall.setColor(TXT_MUTED);
            layout.setText(fontSmall, "✕");
            fontSmall.draw(batch, "✕", aX + PANEL_W - 26 + (20 - layout.width) / 2f, aY + PANEL_H - 24 + 14);
        }

        if (showAlbedo || showRoselia) {
            boolean albTracked = (trackingMode == OrbitCameraController.TrackingMode.ALBEDO || trackingMode == OrbitCameraController.TrackingMode.ROSELIA);
            drawAgentPanel(albedo, rX + 8, rY, "ALBEDO", ALBEDO_NAME_COLOR, BORDER_ALBEDO, albTracked);
            fontSmall.setColor(TXT_MUTED);
            layout.setText(fontSmall, "✕");
            fontSmall.draw(batch, "✕", rX + PANEL_W - 26 + (20 - layout.width) / 2f, rY + PANEL_H - 24 + 14);
        }

        if (showConsole) {
            drawInteractionConsole(cX, cY, cW, cH, conversationHistory);
            fontSmall.setColor(TXT_MUTED);
            layout.setText(fontSmall, "✕");
            fontSmall.draw(batch, "✕", cX + cW - 26 + (20 - layout.width) / 2f, cY + cH - 24 + 14);
        }

        if (showEvents) {
            drawEventStream(events, sX + 12, sY + sH - 8, paused);
            fontSmall.setColor(TXT_MUTED);
            layout.setText(fontSmall, "✕");
            fontSmall.draw(batch, "✕", sX + sW - 26 + (20 - layout.width) / 2f, sY + sH - 20 + 13);
        }


        batch.end();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // NAVBAR PILLS GEOMETRY & RENDERING
    // ─────────────────────────────────────────────────────────────────────────
    private int getTabsStartX(int navW) {
        int tabW = 96;
        int tabGap = 8;
        int numTabs = 5;
        int totalTabsW = numTabs * tabW + (numTabs - 1) * tabGap;
        int startX = PAD + (navW - totalTabsW) / 2;
        return Math.max(PAD + 270, startX);
    }

    private void drawNavbarPillsFilled(int navY, int navW, boolean connected, boolean paused) {
        int pillY = navY + 8;
        int pillH = 30;
        int tabW = 96;
        int tabGap = 8;
        int startX = getTabsStartX(navW);

        // 1. Console Pill
        int cX = startX;
        if (showConsole) {
            sr.setColor(new Color(0.18f, 0.45f, 0.85f, 0.90f));
        } else if (hasUnreadAutonomous) {
            float pulse = 0.7f + 0.3f * (float)Math.sin(cursorTimer * 6.0f);
            sr.setColor(new Color(0.95f, 0.65f, 0.15f, pulse));
        } else {
            sr.setColor(new Color(0.10f, 0.13f, 0.19f, 0.70f));
        }
        fillRounded(cX, pillY, tabW, pillH, 4);

        // 2. Alpha Pill
        int aX = startX + (tabW + tabGap);
        sr.setColor(showAlpha ? new Color(0.85f, 0.35f, 0.25f, 0.90f) : new Color(0.10f, 0.13f, 0.19f, 0.70f));
        fillRounded(aX, pillY, tabW, pillH, 4);

        // 3. Albedo Pill
        int rX = startX + (tabW + tabGap) * 2;
        sr.setColor((showAlbedo || showRoselia) ? new Color(0.18f, 0.70f, 0.65f, 0.90f) : new Color(0.10f, 0.13f, 0.19f, 0.70f));
        fillRounded(rX, pillY, tabW, pillH, 4);

        // 4. Events Pill
        int eX = startX + (tabW + tabGap) * 3;
        sr.setColor(showEvents ? new Color(0.35f, 0.40f, 0.58f, 0.90f) : new Color(0.10f, 0.13f, 0.19f, 0.70f));
        fillRounded(eX, pillY, tabW, pillH, 4);

        // 5. Clean View Pill
        int vX = startX + (tabW + tabGap) * 4;
        sr.setColor(cleanViewMode ? new Color(0.20f, 0.65f, 0.35f, 0.90f) : new Color(0.10f, 0.13f, 0.19f, 0.70f));
        fillRounded(vX, pillY, tabW, pillH, 4);

        // Controls on Right
        int ctrlY = navY + 8;
        int barRight = PAD + navW;

        // Play/Pause
        sr.setColor(paused ? new Color(0.85f, 0.65f, 0.15f, 0.85f) : new Color(0.14f, 0.17f, 0.24f, 0.80f));
        fillRounded(barRight - 60, ctrlY, 52, pillH, 4);

        // Step
        sr.setColor(new Color(0.14f, 0.17f, 0.24f, 0.80f));
        fillRounded(barRight - 116, ctrlY, 50, pillH, 4);

        // Camera Tracking Pills
        sr.setColor(new Color(0.12f, 0.15f, 0.22f, 0.80f));
        fillRounded(barRight - 164, ctrlY, 42, pillH, 4); // Center
        fillRounded(barRight - 212, ctrlY, 42, pillH, 4); // Albedo
        fillRounded(barRight - 260, ctrlY, 42, pillH, 4); // Alpha
    }

    private void drawNavbarPillsOutlines(int navY, int navW, boolean connected, boolean paused) {
        int pillY = navY + 8;
        int pillH = 30;
        int tabW = 96;
        int tabGap = 8;
        int startX = getTabsStartX(navW);


        // Console outline
        sr.setColor(showConsole ? new Color(0.40f, 0.75f, 1f, 0.9f) :
                (hasUnreadAutonomous ? new Color(1f, 0.8f, 0.2f, 1f) : new Color(0.25f, 0.30f, 0.40f, 0.5f)));
        outlineRounded(startX, pillY, tabW, pillH, 4);

        // Alpha outline
        sr.setColor(showAlpha ? BORDER_ALPHA : new Color(0.25f, 0.30f, 0.40f, 0.5f));
        outlineRounded(startX + (tabW + tabGap), pillY, tabW, pillH, 4);

        // Albedo outline
        sr.setColor((showAlbedo || showRoselia) ? BORDER_ALBEDO : new Color(0.25f, 0.30f, 0.40f, 0.5f));
        outlineRounded(startX + (tabW + tabGap) * 2, pillY, tabW, pillH, 4);

        // Events outline
        sr.setColor(showEvents ? BORDER_STREAM : new Color(0.25f, 0.30f, 0.40f, 0.5f));
        outlineRounded(startX + (tabW + tabGap) * 3, pillY, tabW, pillH, 4);

        // Clean view outline
        sr.setColor(cleanViewMode ? new Color(0.40f, 0.90f, 0.50f, 0.9f) : new Color(0.25f, 0.30f, 0.40f, 0.5f));
        outlineRounded(startX + (tabW + tabGap) * 4, pillY, tabW, pillH, 4);
    }

    private void drawNavBarContent(int navY, int navW, TickFrameDto frame,
                                   boolean connected, boolean paused, float tps,
                                   OrbitCameraController.TrackingMode trackingMode,
                                   AgentStateDto alpha, AgentStateDto albedo) {

        int tick = (frame != null) ? frame.tick : 0;
        boolean rain = frame != null && frame.is_raining;

        // Title and Status
        fontLarge.setColor(TXT_HEAD);
        fontLarge.draw(batch, "ALC Observatory", PAD + 14, navY + 33);

        // Status pill
        fontSmall.setColor(connected ? EVT_REWARD : EVT_DAMAGE);
        fontSmall.draw(batch, connected ? "● LIVE" : "○ OFFLINE", PAD + 14, navY + 16);

        fontSmall.setColor(TXT_BODY);
        fontSmall.draw(batch, "T" + tick + "  •  " + (rain ? "≈ RAIN" : "☼ SUN") + "  •  " + (int)tps + " TPS",
                PAD + 76, navY + 16);

        // Tabs Text
        int startX = getTabsStartX(navW);
        int tabW = 96;
        int tabGap = 8;
        int ty = navY + 28;

        // 1. Console
        fontSmall.setColor(showConsole || hasUnreadAutonomous ? Color.WHITE : TXT_MUTED);
        String cLabel = hasUnreadAutonomous ? "[!] Console" : "Console";
        layout.setText(fontSmall, cLabel);
        fontSmall.draw(batch, cLabel, startX + (tabW - layout.width) / 2f, ty);

        // 2. Alpha Tab (with mini vitals)
        fontSmall.setColor(showAlpha ? Color.WHITE : TXT_MUTED);
        String aLabel = "● Alpha";
        if (alpha != null && alpha.needs != null && !showAlpha) {
            float h = alpha.needs.getOrDefault("health", 100f);
            aLabel += " " + (int)h + "%";
        }
        layout.setText(fontSmall, aLabel);
        fontSmall.draw(batch, aLabel, startX + (tabW + tabGap) + (tabW - layout.width) / 2f, ty);

        // 3. Albedo Tab (with mini vitals)
        fontSmall.setColor((showAlbedo || showRoselia) ? Color.WHITE : TXT_MUTED);
        String rLabel = "● Albedo";
        if (albedo != null && albedo.needs != null && !(showAlbedo || showRoselia)) {
            float h = albedo.needs.getOrDefault("health", 100f);
            rLabel += " " + (int)h + "%";
        }
        layout.setText(fontSmall, rLabel);
        fontSmall.draw(batch, rLabel, startX + (tabW + tabGap) * 2 + (tabW - layout.width) / 2f, ty);

        // 4. Events Tab
        fontSmall.setColor(showEvents ? Color.WHITE : TXT_MUTED);
        String eLabel = "Events";
        layout.setText(fontSmall, eLabel);
        fontSmall.draw(batch, eLabel, startX + (tabW + tabGap) * 3 + (tabW - layout.width) / 2f, ty);

        // 5. Clean View Tab
        fontSmall.setColor(cleanViewMode ? Color.WHITE : TXT_MUTED);
        String vLabel = cleanViewMode ? "Clean: ON" : "Clean View";
        layout.setText(fontSmall, vLabel);
        fontSmall.draw(batch, vLabel, startX + (tabW + tabGap) * 4 + (tabW - layout.width) / 2f, ty);

        // Controls Text on Right
        int barRight = PAD + navW;

        // Play / Pause
        fontSmall.setColor(Color.WHITE);
        String pLabel = paused ? "▶ Play" : "⏸ Pause";
        layout.setText(fontSmall, pLabel);
        fontSmall.draw(batch, pLabel, barRight - 60 + (52 - layout.width) / 2f, ty);

        // Step
        fontSmall.setColor(TXT_BODY);
        String sLabel = "⏭ Step";
        layout.setText(fontSmall, sLabel);
        fontSmall.draw(batch, sLabel, barRight - 116 + (50 - layout.width) / 2f, ty);

        // Camera buttons
        boolean trackCenter = (trackingMode == OrbitCameraController.TrackingMode.NONE);
        boolean trackAlb    = (trackingMode == OrbitCameraController.TrackingMode.ALBEDO || trackingMode == OrbitCameraController.TrackingMode.ROSELIA);
        boolean trackAlpha  = (trackingMode == OrbitCameraController.TrackingMode.ALPHA);

        fontSmall.setColor(trackCenter ? TXT_HEAD : TXT_MUTED);
        String cCam = "[C]";
        layout.setText(fontSmall, cCam);
        fontSmall.draw(batch, cCam, barRight - 164 + (42 - layout.width) / 2f, ty);

        fontSmall.setColor(trackAlb ? ALBEDO_NAME_COLOR : TXT_MUTED);
        String rCam = "[Alb]";
        layout.setText(fontSmall, rCam);
        fontSmall.draw(batch, rCam, barRight - 212 + (42 - layout.width) / 2f, ty);

        fontSmall.setColor(trackAlpha ? ALPHA_NAME_COLOR : TXT_MUTED);
        String aCam = "[A]";
        layout.setText(fontSmall, aCam);
        fontSmall.draw(batch, aCam, barRight - 260 + (42 - layout.width) / 2f, ty);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // INTERACTION CONSOLE
    // ─────────────────────────────────────────────────────────────────────────
    private void drawInteractionConsole(int cx, int cy, int cw, int ch, List<ChatMessageDto> history) {
        // Header
        fontLarge.setColor(TXT_HEAD);
        fontLarge.draw(batch, "INTERACTION CONSOLE", cx + 16, cy + ch - 14);

        // Target Selector Pills
        fontSmall.setColor(TXT_MUTED);
        fontSmall.draw(batch, "Talking to:", cx + 225, cy + ch - 14);

        int pillX = cx + 295;
        drawPill("Alpha",   pillX,       cy + ch - 26, "alpha".equals(targetRecipient), ALPHA_NAME_COLOR);
        drawPill("Albedo",  pillX + 68,  cy + ch - 26, "albedo".equals(targetRecipient) || "roselia".equals(targetRecipient), ALBEDO_NAME_COLOR);
        drawPill("Both",    pillX + 144, cy + ch - 26, "both".equals(targetRecipient), new Color(0.95f, 0.82f, 0.25f, 1f));

        // Input Box
        int inputY = cy + ch - 60;
        int inputW = cw - 100;
        fontMid.setColor(TXT_HEAD);
        boolean showCursor = isInputFocused && ((int)(cursorTimer * 2f) % 2 == 0);
        String cursorChar = showCursor ? "|" : "";
        String displayTxt = inputText.toString();
        if (displayTxt.isEmpty() && !isInputFocused) {
            fontMid.setColor(TXT_MUTED);
            fontMid.draw(batch, "> Click to type question or select quick prompt below...", cx + 22, inputY + 19);
        } else {
            fontMid.draw(batch, "> " + displayTxt + cursorChar, cx + 22, inputY + 19);
        }

        // Send Button
        fontMid.setColor(Color.WHITE);
        layout.setText(fontMid, "Send");
        fontMid.draw(batch, "Send", cx + inputW + 22 + (68 - layout.width) / 2f, inputY + 19);

        // Quick Prompts
        int qy = cy + ch - 76;
        fontSmall.setColor(TXT_MUTED);
        fontSmall.draw(batch, "Quick Prompts:", cx + 16, qy);
        int qx = cx + 112;
        for (String q : QUICK_QUESTIONS) {
            fontSmall.setColor(new Color(0.40f, 0.75f, 0.98f, 0.95f));
            String promptLabel = "[" + q + "]";
            fontSmall.draw(batch, promptLabel, qx, qy);
            layout.setText(fontSmall, promptLabel);
            qx += (int)layout.width + 10;
        }

        // Conversation History
        int logStartY = cy + ch - 100;
        if (history == null || history.isEmpty()) {
            fontSmall.setColor(TXT_MUTED);
            fontSmall.draw(batch, "No conversation records yet. Ask Alpha or Albedo a question!", cx + 24, logStartY - 10);
            return;
        }

        int maxMsgLines = 6;
        int startIdx = Math.max(0, history.size() - maxMsgLines);
        int lineY = logStartY;

        for (int i = startIdx; i < history.size(); i++) {
            ChatMessageDto msg = history.get(i);
            boolean isHuman = "human".equalsIgnoreCase(msg.sender);
            Color tagColor = isHuman ? new Color(0.40f, 0.75f, 1.0f, 1f) :
                    ("alpha".equalsIgnoreCase(msg.sender) ? ALPHA_NAME_COLOR : ALBEDO_NAME_COLOR);

            String statusBadge = switch (msg.status != null ? msg.status : "") {
                case "KNOWN" -> "[KNOWN " + (int)(msg.confidence * 100) + "%]";
                case "UNKNOWN" -> "[UNKNOWN]";
                case "UNCERTAIN" -> "[UNCERTAIN]";
                case "CONTRADICTORY" -> "[CONTRADICTORY]";
                case "UNVERIFIED" -> "[UNVERIFIED]";
                case "CONFIRMED" -> "[CONFIRMED]";
                default -> "";
            };

            Color statusColor = switch (msg.status != null ? msg.status : "") {
                case "KNOWN", "CONFIRMED" -> EVT_REWARD;
                case "UNKNOWN" -> EVT_DAMAGE;
                case "UNCERTAIN", "UNVERIFIED" -> BAR_ENERGY;
                case "CONTRADICTORY" -> new Color(1f, 0.4f, 0.8f, 1f);
                default -> TXT_MUTED;
            };

            fontSmall.setColor(tagColor);
            String fromTo = isHuman ? "YOU → " + msg.receiver.toUpperCase() : msg.sender.toUpperCase();
            String prefix = "[T" + msg.tick + "] " + fromTo + ":";
            fontSmall.draw(batch, prefix, cx + 20, lineY);

            layout.setText(fontSmall, prefix);
            int badgeX = cx + 20 + (int)layout.width + 10;

            int textX = badgeX;
            if (!statusBadge.isEmpty()) {
                fontSmall.setColor(statusColor);
                fontSmall.draw(batch, statusBadge, badgeX, lineY);
                layout.setText(fontSmall, statusBadge);
                textX = badgeX + (int)layout.width + 10;
            }

            fontSmall.setColor(TXT_BODY);
            String text = msg.content;
            if (text.length() > 65) text = text.substring(0, 62) + "...";
            fontSmall.draw(batch, text, textX, lineY);

            lineY -= 20;
        }
    }

    private void drawPill(String label, int x, int y, boolean active, Color activeColor) {
        fontSmall.setColor(active ? activeColor : TXT_MUTED);
        fontSmall.draw(batch, (active ? "[● " : "[  ") + label + " ]", x, y + 12);
    }


    // ─────────────────────────────────────────────────────────────────────────
    // INPUT HANDLING
    // ─────────────────────────────────────────────────────────────────────────
    public boolean handleTouchDown(int screenX, int screenY, WebSocketClientService wsService,
                                   OrbitCameraController camController, Runnable onTogglePause) {

        int glY = SH - screenY; // Convert LibGDX screen coords (0=top) to GL coords (0=bottom)
        int navY = SH - TOP_BAR_H - PAD;
        int navW = SW - PAD * 2;

        // ── 1. Top Navigation Bar Clicks ──────────────────────────────────────
        if (glY >= navY && glY <= navY + TOP_BAR_H) {
            int startX = getTabsStartX(navW);
            int tabW = 96;
            int tabGap = 8;

            // Tab 0: Console
            if (screenX >= startX && screenX <= startX + tabW) {
                toggleConsole();
                return true;
            }
            // Tab 1: Alpha
            if (screenX >= startX + (tabW + tabGap) && screenX <= startX + (tabW + tabGap) + tabW) {
                toggleAlpha();
                return true;
            }
            // Tab 2: Albedo
            if (screenX >= startX + (tabW + tabGap) * 2 && screenX <= startX + (tabW + tabGap) * 2 + tabW) {
                toggleAlbedo();
                return true;
            }
            // Tab 3: Events
            if (screenX >= startX + (tabW + tabGap) * 3 && screenX <= startX + (tabW + tabGap) * 3 + tabW) {
                toggleEvents();
                return true;
            }
            // Tab 4: Clean View
            if (screenX >= startX + (tabW + tabGap) * 4 && screenX <= startX + (tabW + tabGap) * 4 + tabW) {
                toggleCleanView();
                return true;
            }

            int barRight = PAD + navW;

            // Pause / Resume
            if (screenX >= barRight - 60 && screenX <= barRight - 8) {
                if (onTogglePause != null) {
                    onTogglePause.run();
                }
                return true;
            }

            // Step
            if (screenX >= barRight - 116 && screenX <= barRight - 66) {
                wsService.sendStep();
                return true;
            }

            // Camera Center
            if (screenX >= barRight - 164 && screenX <= barRight - 122) {
                camController.setFocus(16f, 0f, 16f);
                return true;
            }

            // Camera Albedo
            if (screenX >= barRight - 212 && screenX <= barRight - 170) {
                camController.setTrackingMode(OrbitCameraController.TrackingMode.ALBEDO);
                return true;
            }

            // Camera Alpha
            if (screenX >= barRight - 260 && screenX <= barRight - 218) {
                camController.setTrackingMode(OrbitCameraController.TrackingMode.ALPHA);
                return true;
            }

            return true; // Clicked on navbar background
        }

        // ── 2. Alpha Panel Close Button ───────────────────────────────────────
        int aX = PAD + 4;
        int aY = navY - 10 - PANEL_H;
        if (showAlpha && screenX >= aX + PANEL_W - 28 && screenX <= aX + PANEL_W - 4
                && glY >= aY + PANEL_H - 26 && glY <= aY + PANEL_H - 4) {
            showAlpha = false;
            return true;
        }

        // ── 3. Albedo Panel Close Button ─────────────────────────────────────
        int rX = SW - PANEL_W - PAD - 4;
        int rY = navY - 10 - PANEL_H;
        if ((showAlbedo || showRoselia) && screenX >= rX + PANEL_W - 28 && screenX <= rX + PANEL_W - 4
                && glY >= rY + PANEL_H - 26 && glY <= rY + PANEL_H - 4) {
            showAlbedo = false;
            showRoselia = false;
            return true;
        }

        // ── 4. Cognitive Events Close Button ──────────────────────────────────
        int sX = PAD;
        int sY = PAD;
        int sW = SW - PAD * 2;
        int sH = STREAM_H;
        if (showEvents && screenX >= sX + sW - 28 && screenX <= sX + sW - 4
                && glY >= sY + sH - 24 && glY <= sY + sH - 4) {
            showEvents = false;
            return true;
        }

        // ── 5. Interaction Console Clicks ─────────────────────────────────────
        int cW = Math.min(680, SW - PAD * 2 - 20);
        int cH = 240;
        int cX = (SW - cW) / 2;
        int cY = showEvents ? (PAD + STREAM_H + 8) : (PAD + 8);

        if (showConsole) {
            // Close button
            if (screenX >= cX + cW - 28 && screenX <= cX + cW - 4
                    && glY >= cY + cH - 26 && glY <= cY + cH - 4) {
                showConsole = false;
                isInputFocused = false;
                return true;
            }

            // Target Pills
            int pillY = cY + cH - 26;
            if (glY >= pillY && glY <= pillY + 22) {
                int pillX = cX + 285;
                if (screenX >= pillX && screenX <= pillX + 65) {
                    targetRecipient = "alpha";
                    return true;
                } else if (screenX >= pillX + 68 && screenX <= pillX + 140) {
                    targetRecipient = "albedo";
                    return true;
                } else if (screenX >= pillX + 144 && screenX <= pillX + 205) {
                    targetRecipient = "both";
                    return true;
                }
            }

            // Input box focus
            int inputY = cY + cH - 60;
            int inputW = cW - 100;
            if (screenX >= cX + 14 && screenX <= cX + 14 + inputW && glY >= inputY && glY <= inputY + 28) {
                isInputFocused = true;
                return true;
            }

            // Send Button
            int sendX = cX + inputW + 22;
            if (screenX >= sendX && screenX <= sendX + 68 && glY >= inputY && glY <= inputY + 28) {
                sendMessage(wsService);
                return true;
            }

            // Quick Prompts
            int qy = cY + cH - 78;
            if (glY >= qy && glY <= qy + 18) {
                int qx = cX + 112;
                for (String q : QUICK_QUESTIONS) {
                    layout.setText(fontSmall, "[" + q + "]");
                    int qW = (int)layout.width;
                    if (screenX >= qx && screenX <= qx + qW) {
                        inputText.setLength(0);
                        inputText.append(q);
                        sendMessage(wsService);
                        return true;
                    }
                    qx += qW + 10;
                }
            }


            // Clicked inside console background -> prevent 3D camera drag
            if (screenX >= cX && screenX <= cX + cW && glY >= cY && glY <= cY + cH) {
                return true;
            }
        }

        // Clicked outside console -> unfocus input
        if (isInputFocused) {
            isInputFocused = false;
        }

        return false;
    }

    public void sendMessage(WebSocketClientService wsService) {
        String query = inputText.toString().trim();
        if (query.isEmpty()) return;

        if (wsService != null) {
            wsService.sendHumanMessage(targetRecipient, query);
        }
        inputText.setLength(0);
    }

    public boolean handleKeyTyped(char c, WebSocketClientService wsService) {
        if (!isInputFocused) return false;

        if (c == '\r' || c == '\n') {
            sendMessage(wsService);
            return true;
        } else if (c == '\b') {
            if (inputText.length() > 0) {
                inputText.deleteCharAt(inputText.length() - 1);
            }
            return true;
        } else if (c >= 32 && c <= 126) {
            if (inputText.length() < 80) {
                inputText.append(c);
            }
            return true;
        }
        return false;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // AGENT PANEL
    // ─────────────────────────────────────────────────────────────────────────
    private void drawAgentPanel(AgentStateDto a, int px, int py,
                                String name, Color nameColor, Color accentColor,
                                boolean isTracked) {

        fontLarge.setColor(nameColor);
        fontLarge.draw(batch, name, px + 4, py + PANEL_H - 12);
        layout.setText(fontLarge, name);
        fontSmall.setColor(TXT_MUTED);
        fontSmall.draw(batch, "• female", px + 4 + layout.width + 8, py + PANEL_H - 14);

        if (isTracked) {
            fontSmall.setColor(new Color(0.98f, 0.88f, 0.20f, 1f));
            fontSmall.draw(batch, "[TRACKED]", px + 155, py + PANEL_H - 14);
        }

        if (a == null) {
            fontMid.setColor(TXT_MUTED);
            fontMid.draw(batch, "Awaiting telemetry...", px + 4, py + PANEL_H - 50);
            return;
        }

        // Status
        Color dotColor = a.alive ? new Color(0.3f, 0.9f, 0.3f, 1f) : new Color(0.9f, 0.3f, 0.3f, 1f);
        fontMid.setColor(dotColor);
        fontMid.draw(batch, a.alive ? "● ALIVE" : "✕ DEAD", px + 4, py + PANEL_H - 36);

        fontSmall.setColor(TXT_MUTED);
        fontSmall.draw(batch, "Lives: " + a.lives + "   Pos: (" + a.x + ", " + a.y + ")",
                px + 88, py + PANEL_H - 36);

        // Holding & Action
        String holdStr = (a.holding != null) ? "Holding item #" + a.holding : "Hands empty";
        fontSmall.setColor(TXT_BODY);
        fontSmall.draw(batch, holdStr, px + 4, py + PANEL_H - 56);

        CognitionDto cog = a.cognition;
        String act = (cog != null) ? cog.action_name : "WAIT";
        fontMid.setColor(accentColor);
        fontMid.draw(batch, "→ " + act, px + 4, py + PANEL_H - 74);

        // Need Bars
        int bx = px + 68;
        int barBase = py + PANEL_H - 155;
        int spacing = 24;
        int barW = 145;

        fontSmall.setColor(BAR_ENERGY); fontSmall.draw(batch, "Energy", px + 4, barBase + spacing * 3 + 12);
        fontSmall.setColor(BAR_WATER);  fontSmall.draw(batch, "Water",  px + 4, barBase + spacing * 2 + 12);
        fontSmall.setColor(BAR_FOOD);   fontSmall.draw(batch, "Food",   px + 4, barBase + spacing + 12);
        fontSmall.setColor(BAR_HEALTH); fontSmall.draw(batch, "Health", px + 4, barBase + 12);

        if (a.needs != null) {
            float e = a.needs.getOrDefault("energy", 100f);
            float w = a.needs.getOrDefault("water",  100f);
            float f = a.needs.getOrDefault("food",   100f);
            float h = a.needs.getOrDefault("health", 100f);
            fontSmall.setColor(TXT_MUTED);
            fontSmall.draw(batch, String.format("%.0f%%", e), bx + barW + 6, barBase + spacing * 3 + 12);
            fontSmall.draw(batch, String.format("%.0f%%", w), bx + barW + 6, barBase + spacing * 2 + 12);
            fontSmall.draw(batch, String.format("%.0f%%", f), bx + barW + 6, barBase + spacing + 12);
            fontSmall.draw(batch, String.format("%.0f%%", h), bx + barW + 6, barBase + 12);
        }

        // Cognitive metrics
        int gy = barBase - 18;
        if (cog != null) {
            drawStatPair("Known States",  String.valueOf(cog.known_states),           px, gy,      TXT_BODY);
            drawStatPair("Experiences",   String.valueOf(cog.successful_experiences), px, gy - 18, EVT_REWARD);
            drawStatPair("Mistakes",      String.format("%.1f", cog.recorded_mistakes),px,gy - 36, EVT_DAMAGE);
            drawStatPair("Learning Evts", String.valueOf(cog.learning_events),        px, gy - 54, EVT_LEARN);
            drawStatPair("Exploration",   cog.exploration_rate + "%",                 px, gy - 72, BAR_ENERGY);
        }
    }

    private void drawStatPair(String label, String value, int px, int y, Color valColor) {
        fontSmall.setColor(TXT_MUTED);
        fontSmall.draw(batch, label, px + 4, y);
        fontSmall.setColor(valColor);
        layout.setText(fontSmall, value);
        fontSmall.draw(batch, value, px + PANEL_W - 24 - layout.width, y);
    }

    private void drawBarTracks(int bx, int barBase, int barW) {
        int spacing = 24;
        for (int i = 0; i < 4; i++) {
            sr.setColor(BG_BAR_TRACK);
            sr.rect(bx, barBase + spacing * i, barW, BAR_H);
        }
    }

    private void drawNeedBars(int bx, int barBase, int barW, Map<String, Float> needs) {
        int spacing = 24;
        drawBar(bx, barBase + spacing * 3, barW, needs.getOrDefault("energy", 100f), BAR_ENERGY);
        drawBar(bx, barBase + spacing * 2, barW, needs.getOrDefault("water",  100f), BAR_WATER);
        drawBar(bx, barBase + spacing    , barW, needs.getOrDefault("food",   100f), BAR_FOOD);
        drawBar(bx, barBase              , barW, needs.getOrDefault("health", 100f), BAR_HEALTH);
    }

    private void drawBar(int x, int y, int w, float val, Color c) {
        float ratio = Math.max(0f, Math.min(1f, val / 100f));
        sr.setColor(c.r * 0.5f, c.g * 0.5f, c.b * 0.5f, 1f);
        sr.rect(x, y, w * ratio, BAR_H);
        sr.setColor(c);
        float glow = Math.max(2, w * ratio - 4);
        sr.rect(x, y, glow, BAR_H);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // EVENT STREAM
    // ─────────────────────────────────────────────────────────────────────────
    private void drawEventStream(List<EventLogDto> events, int x, int startY, boolean paused) {
        fontSmall.setColor(new Color(0.55f, 0.65f, 0.95f, 1f));
        fontSmall.draw(batch, "LIVE COGNITIVE EVENT STREAM", x, startY);

        if (events == null || events.isEmpty()) {
            if (paused) {
                fontSmall.setColor(BAR_ENERGY);
                fontSmall.draw(batch, "[Simulation Paused — Click ▶ Play in top bar or press Space to stream experiences]", x, startY - 18);
            } else {
                fontSmall.setColor(TXT_MUTED);
                fontSmall.draw(batch, "[Observatory active — Agents exploring sanctuary and learning ...]", x, startY - 18);
            }
            return;
        }

        int maxLines = 4;
        int startIdx = Math.max(0, events.size() - maxLines);
        int ly = startY - 18;
        for (int i = startIdx; i < events.size(); i++) {
            EventLogDto evt = events.get(i);
            Color c = switch (evt.category == null ? "" : evt.category) {
                case "reward"   -> EVT_REWARD;
                case "damage"   -> EVT_DAMAGE;
                case "learning" -> EVT_LEARN;
                default         -> EVT_NEUTRAL;
            };
            fontSmall.setColor(c);
            fontSmall.draw(batch, "[T" + evt.tick + "] " + evt.text, x, ly);
            ly -= 18;
        }
    }


    // ─────────────────────────────────────────────────────────────────────────
    // SHAPE HELPERS
    // ─────────────────────────────────────────────────────────────────────────
    private void fillRounded(float x, float y, float w, float h, float r) {
        sr.rect(x + r, y, w - 2*r, h);
        sr.rect(x, y + r, r, h - 2*r);
        sr.rect(x + w - r, y + r, r, h - 2*r);
        int segs = 6;
        for (int i = 0; i < segs; i++) {
            float a0 = (float)Math.toRadians(i * 90f / segs);
            float a1 = (float)Math.toRadians((i+1) * 90f / segs);
            sr.triangle(x+r,   y+r,   x+r   + r*(float)Math.cos(a0+Math.PI),   y+r   + r*(float)Math.sin(a0+Math.PI),   x+r   + r*(float)Math.cos(a1+Math.PI),   y+r   + r*(float)Math.sin(a1+Math.PI));
            sr.triangle(x+w-r, y+r,   x+w-r + r*(float)Math.cos(a0+Math.PI/2),y+r   + r*(float)Math.sin(a0+Math.PI/2), x+w-r + r*(float)Math.cos(a1+Math.PI/2), y+r   + r*(float)Math.sin(a1+Math.PI/2));
            sr.triangle(x+r,   y+h-r, x+r   + r*(float)Math.cos(a0+3*Math.PI/2), y+h-r + r*(float)Math.sin(a0+3*Math.PI/2), x+r + r*(float)Math.cos(a1+3*Math.PI/2), y+h-r + r*(float)Math.sin(a1+3*Math.PI/2));
            sr.triangle(x+w-r, y+h-r, x+w-r + r*(float)Math.cos(a0), y+h-r + r*(float)Math.sin(a0), x+w-r + r*(float)Math.cos(a1), y+h-r + r*(float)Math.sin(a1));
        }
    }

    private void outlineRounded(float x, float y, float w, float h, float r) {
        int segs = 6;
        sr.line(x+r, y,     x+w-r, y);
        sr.line(x+r, y+h,   x+w-r, y+h);
        sr.line(x,   y+r,   x,     y+h-r);
        sr.line(x+w, y+r,   x+w,   y+h-r);
        for (int i = 0; i < segs; i++) {
            float a0 = (float)Math.toRadians(180 + i * 90f / segs);
            float a1 = (float)Math.toRadians(180 + (i+1) * 90f / segs);
            sr.line(x+r   + r*(float)Math.cos(a0), y+r   + r*(float)Math.sin(a0), x+r   + r*(float)Math.cos(a1), y+r   + r*(float)Math.sin(a1));
            a0 += (float)Math.toRadians(90);  a1 += (float)Math.toRadians(90);
            sr.line(x+r   + r*(float)Math.cos(a0), y+h-r + r*(float)Math.sin(a0), x+r   + r*(float)Math.sin(a1), y+h-r + r*(float)Math.sin(a1));
            a0 += (float)Math.toRadians(90);  a1 += (float)Math.toRadians(90);
            sr.line(x+w-r + r*(float)Math.cos(a0), y+h-r + r*(float)Math.sin(a0), x+w-r + r*(float)Math.sin(a1), y+h-r + r*(float)Math.sin(a1));
            a0 += (float)Math.toRadians(90);  a1 += (float)Math.toRadians(90);
            sr.line(x+w-r + r*(float)Math.cos(a0), y+r   + r*(float)Math.sin(a0), x+w-r + r*(float)Math.sin(a1), y+r   + r*(float)Math.sin(a1));
        }
    }

    private AgentStateDto find(TickFrameDto frame, int id) {
        if (frame == null || frame.agents == null) return null;
        for (AgentStateDto a : frame.agents) if (a.id == id) return a;
        return null;
    }

    @Override
    public void dispose() {
        batch.dispose();
        sr.dispose();
        fontLarge.dispose();
        fontMid.dispose();
        fontSmall.dispose();
    }
}
