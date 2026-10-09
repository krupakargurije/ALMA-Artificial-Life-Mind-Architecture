package alc.viewer.render;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.InputAdapter;
import com.badlogic.gdx.graphics.PerspectiveCamera;
import com.badlogic.gdx.math.MathUtils;
import com.badlogic.gdx.math.Vector3;

/**
 * OrbitCameraController provides complete keyboard and mouse controls for moving
 * around the garden world and continuously monitoring Alpha and Roselia.
 *
 * Controls:
 *   [W / A / S / D] or [Arrows] : Pan camera forward, left, backward, right
 *   [Shift] + [W/A/S/D]        : Sprint pan (2.5x speed)
 *   [Q / E]                    : Rotate / orbit view angle left / right
 *   [R / F] or [PgUp / PgDn]   : Tilt camera angle up / down
 *   [Z / X] or [- / +]         : Zoom out / zoom in
 *   [Mouse Left-Drag]          : Orbit view around target
 *   [Mouse Right-Drag]         : Pan target on ground
 *   [Mouse Scroll]             : Zoom in / out
 *   [1 / F1]                   : Monitor / Track Alpha continuously
 *   [2 / F2]                   : Monitor / Track Roselia continuously
 *   [3 / F3]                   : Monitor / Track Both agents
 *   [0 / C / Home]             : Free Camera centered on garden sanctuary
 *   [Tab]                      : Cycle tracking mode (Alpha -> Roselia -> Both -> Free)
 */
public class OrbitCameraController extends InputAdapter {

    public enum TrackingMode {
        NONE("FREE CAMERA"),
        ALPHA("MONITORING ALPHA"),
        ALBEDO("MONITORING ALBEDO"),
        ROSELIA("MONITORING ALBEDO"), // alias for compatibility
        BOTH("MONITORING BOTH");

        public final String label;
        TrackingMode(String label) { this.label = label; }
    }

    private final PerspectiveCamera camera;
    public final Vector3 target = new Vector3(16f, 0f, 16f);

    private float distance = 18.0f;  // Closer default to clearly see agents
    private float azimuth = 45.0f;   // Horizontal orbit angle (degrees)
    private float elevation = 32.0f; // Vertical angle (degrees)

    private TrackingMode trackingMode = TrackingMode.ALPHA; // Track Alpha by default

    private int lastX = -1;
    private int lastY = -1;

    public OrbitCameraController(PerspectiveCamera camera) {
        this.camera = camera;
        updateCamera();
    }

    public TrackingMode getTrackingMode() {
        return trackingMode;
    }

    public void setTrackingMode(TrackingMode mode) {
        this.trackingMode = mode;
    }

    public void cycleTrackingMode() {
        switch (trackingMode) {
            case ALPHA -> trackingMode = TrackingMode.ALBEDO;
            case ALBEDO, ROSELIA -> trackingMode = TrackingMode.BOTH;
            case BOTH -> trackingMode = TrackingMode.NONE;
            default -> trackingMode = TrackingMode.ALPHA;
        }
    }

    /**
     * Per-frame update called with delta time and current agent positions.
     * Handles smooth continuous keyboard panning, rotation, zoom, and target tracking.
     */
    public void update(float dt, Vector3 alphaPos, Vector3 albedoPos) {
        boolean shift = Gdx.input.isKeyPressed(Input.Keys.SHIFT_LEFT)
                || Gdx.input.isKeyPressed(Input.Keys.SHIFT_RIGHT);
        float moveSpeed = (shift ? 30.0f : 12.0f) * dt;

        float radAz = azimuth * MathUtils.degreesToRadians;
        float fx = MathUtils.sin(radAz);
        float fz = MathUtils.cos(radAz);
        float rx = MathUtils.cos(radAz);
        float rz = -MathUtils.sin(radAz);

        boolean keyMoved = false;

        // ── 1. KEYBOARD MOVEMENT (WASD & ARROWS) ──────────────────────────────
        // Forward / Backward
        if (Gdx.input.isKeyPressed(Input.Keys.W) || Gdx.input.isKeyPressed(Input.Keys.UP)) {
            target.x -= fx * moveSpeed;
            target.z -= fz * moveSpeed;
            keyMoved = true;
        }
        if (Gdx.input.isKeyPressed(Input.Keys.S) || Gdx.input.isKeyPressed(Input.Keys.DOWN)) {
            target.x += fx * moveSpeed;
            target.z += fz * moveSpeed;
            keyMoved = true;
        }
        // Left / Right Strafe
        if (Gdx.input.isKeyPressed(Input.Keys.A) || Gdx.input.isKeyPressed(Input.Keys.LEFT)) {
            target.x -= rx * moveSpeed;
            target.z -= rz * moveSpeed;
            keyMoved = true;
        }
        if (Gdx.input.isKeyPressed(Input.Keys.D) || Gdx.input.isKeyPressed(Input.Keys.RIGHT)) {
            target.x += rx * moveSpeed;
            target.z += rz * moveSpeed;
            keyMoved = true;
        }

        // ── 2. VIEW ROTATION & ELEVATION (Q / E / R / F) ───────────────────────
        float rotSpeed = 80.0f * dt;
        if (Gdx.input.isKeyPressed(Input.Keys.Q)) {
            azimuth += rotSpeed;
        }
        if (Gdx.input.isKeyPressed(Input.Keys.E)) {
            azimuth -= rotSpeed;
        }
        if (Gdx.input.isKeyPressed(Input.Keys.R) || Gdx.input.isKeyPressed(Input.Keys.PAGE_UP)) {
            elevation += rotSpeed * 0.6f;
        }
        if (Gdx.input.isKeyPressed(Input.Keys.F) || Gdx.input.isKeyPressed(Input.Keys.PAGE_DOWN)) {
            elevation -= rotSpeed * 0.6f;
        }

        // ── 3. ZOOM KEYS (Z / X / - / +) ──────────────────────────────────────
        float zoomSpeed = 22.0f * dt;
        if (Gdx.input.isKeyPressed(Input.Keys.Z) || Gdx.input.isKeyPressed(Input.Keys.MINUS)) {
            distance += zoomSpeed;
        }
        if (Gdx.input.isKeyPressed(Input.Keys.X) || Gdx.input.isKeyPressed(Input.Keys.PLUS)
                || Gdx.input.isKeyPressed(Input.Keys.EQUALS)) {
            distance -= zoomSpeed;
        }

        // If user manually pressed keys to move, disengage tracking to allow free exploration
        if (keyMoved) {
            trackingMode = TrackingMode.NONE;
        }

        // ── 4. CONTINUOUS MONITORING / TRACKING ────────────────────────────────
        if (trackingMode == TrackingMode.ALPHA && alphaPos != null) {
            target.lerp(alphaPos, Math.min(1.0f, dt * 5.0f));
        } else if ((trackingMode == TrackingMode.ALBEDO || trackingMode == TrackingMode.ROSELIA) && albedoPos != null) {
            target.lerp(albedoPos, Math.min(1.0f, dt * 5.0f));
        } else if (trackingMode == TrackingMode.BOTH && alphaPos != null && albedoPos != null) {
            Vector3 mid = new Vector3(alphaPos).add(albedoPos).scl(0.5f);
            target.lerp(mid, Math.min(1.0f, dt * 4.0f));
        }

        updateCamera();
    }

    public void updateCamera() {
        elevation = MathUtils.clamp(elevation, 5.0f, 85.0f);
        distance  = MathUtils.clamp(distance, 3.0f, 80.0f);

        float radAz = azimuth * MathUtils.degreesToRadians;
        float radEl = elevation * MathUtils.degreesToRadians;

        float cx = target.x + distance * MathUtils.cos(radEl) * MathUtils.sin(radAz);
        float cy = target.y + distance * MathUtils.sin(radEl);
        float cz = target.z + distance * MathUtils.cos(radEl) * MathUtils.cos(radAz);

        camera.position.set(cx, cy, cz);
        camera.lookAt(target.x, target.y + 0.6f, target.z);
        camera.up.set(0, 1, 0);
        camera.update();
    }

    // ── MOUSE CONTROLS ────────────────────────────────────────────────────────
    @Override
    public boolean touchDown(int screenX, int screenY, int pointer, int button) {
        lastX = screenX;
        lastY = screenY;
        return false;
    }

    @Override
    public boolean touchDragged(int screenX, int screenY, int pointer) {
        int deltaX = screenX - lastX;
        int deltaY = screenY - lastY;
        lastX = screenX;
        lastY = screenY;

        if (Gdx.input.isButtonPressed(Input.Buttons.LEFT)) {
            // Orbit view
            azimuth -= deltaX * 0.40f;
            elevation += deltaY * 0.40f;
            updateCamera();
            return true;
        } else if (Gdx.input.isButtonPressed(Input.Buttons.RIGHT)) {
            // Free pan — disengages tracking
            trackingMode = TrackingMode.NONE;

            float factor = distance * 0.0022f;
            float radAz = azimuth * MathUtils.degreesToRadians;
            float fx = MathUtils.sin(radAz);
            float fz = MathUtils.cos(radAz);
            float rx = MathUtils.cos(radAz);
            float rz = -MathUtils.sin(radAz);

            target.x += (-rx * deltaX + fx * deltaY) * factor;
            target.z += (-rz * deltaX + fz * deltaY) * factor;
            updateCamera();
            return true;
        }
        return false;
    }

    @Override
    public boolean scrolled(float amountX, float amountY) {
        distance += amountY * 2.2f;
        updateCamera();
        return true;
    }

    public void setFocus(float x, float y, float z) {
        trackingMode = TrackingMode.NONE;
        target.set(x, y, z);
        updateCamera();
    }
}
