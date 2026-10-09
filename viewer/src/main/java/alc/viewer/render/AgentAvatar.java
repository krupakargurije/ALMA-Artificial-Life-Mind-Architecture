package alc.viewer.render;

import com.badlogic.gdx.graphics.g3d.ModelBatch;
import com.badlogic.gdx.graphics.g3d.ModelInstance;
import com.badlogic.gdx.math.MathUtils;
import com.badlogic.gdx.math.Matrix4;
import com.badlogic.gdx.math.Vector3;
import alc.viewer.net.dto.AgentStateDto;

import java.util.ArrayList;
import java.util.List;

/**
 * AgentAvatar manages the complete hierarchical skeleton, smooth position/rotation
 * interpolation, and forward-kinematic walking & idle animations for Alpha and Roselia.
 *
 * Local Coordinate Frame:
 *   +Z : Forward (agent facing direction)
 *   +X : Right
 *   +Y : Up (ground is 0)
 */
public class AgentAvatar {

    public final int id;
    public final boolean isAlpha;
    private final GardenMeshes meshes;

    // Spatial & Animation State
    public final Vector3 currentPos = new Vector3(16f, 0f, 16f);
    public final Vector3 targetPos  = new Vector3(16f, 0f, 16f);
    public float currentYaw = 0f;
    public float targetYaw  = 0f;

    private boolean isWalking = false;
    private float walkProgress = 0f;
    private float idleTimer = 0f;

    private boolean alive = true;
    private Integer holdingItem = null;

    // Body Part ModelInstances
    private final ModelInstance headSkull;
    private final ModelInstance face;
    private final ModelInstance hairCap;
    private final ModelInstance hairAccent;
    private final ModelInstance neck;
    private final ModelInstance torso;
    private final ModelInstance skirt;

    private final ModelInstance shoulderL;
    private final ModelInstance shoulderR;
    private final ModelInstance upperArmL;
    private final ModelInstance upperArmR;
    private final ModelInstance forearmL;
    private final ModelInstance forearmR;
    private final ModelInstance handL;
    private final ModelInstance handR;

    private final ModelInstance thighL;
    private final ModelInstance thighR;
    private final ModelInstance shinL;
    private final ModelInstance shinR;
    private final ModelInstance bootL;
    private final ModelInstance bootR;

    // Held item instance
    private ModelInstance heldInstance = null;
    private int currentHoldingId = -1;

    // Temporary matrices for hierarchical transformations
    private final Matrix4 rootMatrix = new Matrix4();
    private final Matrix4 tempMat = new Matrix4();
    private final Matrix4 jointMat = new Matrix4();

    // Render list for batch
    private final List<ModelInstance> parts = new ArrayList<>();

    public AgentAvatar(int id, boolean isAlpha, GardenMeshes meshes) {
        this.id = id;
        this.isAlpha = isAlpha;
        this.meshes = meshes;

        String pfx = isAlpha ? "alpha" : "rose";

        // Create all body parts
        headSkull  = new ModelInstance(meshes.get("head_skull"));
        face       = new ModelInstance(meshes.get(isAlpha ? "face_alpha" : "face_roselia"));
        hairCap    = new ModelInstance(meshes.get(isAlpha ? "hair_alpha_cap" : "hair_rose_cap"));
        hairAccent = new ModelInstance(meshes.get(isAlpha ? "hair_alpha_pony" : "hair_rose_side"));
        neck       = new ModelInstance(meshes.get("neck"));
        torso      = new ModelInstance(meshes.get("torso_" + pfx));
        skirt      = new ModelInstance(meshes.get("skirt_" + pfx));

        shoulderL  = new ModelInstance(meshes.get("shoulder_" + pfx));
        shoulderR  = new ModelInstance(meshes.get("shoulder_" + pfx));
        upperArmL  = new ModelInstance(meshes.get("upper_arm_" + pfx));
        upperArmR  = new ModelInstance(meshes.get("upper_arm_" + pfx));
        forearmL   = new ModelInstance(meshes.get("forearm"));
        forearmR   = new ModelInstance(meshes.get("forearm"));
        handL      = new ModelInstance(meshes.get("hand"));
        handR      = new ModelInstance(meshes.get("hand"));

        thighL     = new ModelInstance(meshes.get("thigh_" + pfx));
        thighR     = new ModelInstance(meshes.get("thigh_" + pfx));
        shinL      = new ModelInstance(meshes.get("shin"));
        shinR      = new ModelInstance(meshes.get("shin"));
        bootL      = new ModelInstance(meshes.get("boot"));
        bootR      = new ModelInstance(meshes.get("boot"));

        parts.add(headSkull);
        parts.add(face);
        parts.add(hairCap);
        parts.add(hairAccent);
        parts.add(neck);
        parts.add(torso);
        parts.add(skirt);
        parts.add(shoulderL);
        parts.add(shoulderR);
        parts.add(upperArmL);
        parts.add(upperArmR);
        parts.add(forearmL);
        parts.add(forearmR);
        parts.add(handL);
        parts.add(handR);
        parts.add(thighL);
        parts.add(thighR);
        parts.add(shinL);
        parts.add(shinR);
        parts.add(bootL);
        parts.add(bootR);
    }

    /**
     * Update target state from network DTO.
     */
    public void updateFromDto(AgentStateDto dto) {
        if (dto == null) return;
        this.alive = dto.alive;
        this.holdingItem = dto.holding;

        targetPos.set(dto.x, 0f, dto.y);

        // Convert 2D grid facing [fx, fy] to 3D world yaw (degrees)
        // In simulation: y is +down/-up or row/col.
        // facing [0, -1] = North -> yaw 180°
        // facing [0, 1]  = South -> yaw 0°
        // facing [1, 0]  = East  -> yaw 90°
        // facing [-1, 0] = West  -> yaw 270°
        if (dto.facing != null && dto.facing.size() >= 2) {
            int fx = dto.facing.get(0);
            int fz = dto.facing.get(1);
            if (fx != 0 || fz != 0) {
                targetYaw = (float)Math.toDegrees(Math.atan2(fx, fz));
            }
        }

        // Update held item model if changed
        int heldId = (dto.holding != null) ? dto.holding : 0;
        if (heldId != currentHoldingId) {
            currentHoldingId = heldId;
            updateHeldModel(heldId);
        }
    }

    private void updateHeldModel(int entityId) {
        heldInstance = null;
        if (entityId == 11 || entityId == 15 || entityId == 16) {
            heldInstance = new ModelInstance(meshes.get("bucket_casing"));
        } else if (entityId == 13) {
            heldInstance = new ModelInstance(meshes.get("fruit_food"));
        } else if (entityId == 14) {
            heldInstance = new ModelInstance(meshes.get("fruit_poison"));
        } else if (entityId == 10) {
            heldInstance = new ModelInstance(meshes.get("seed"));
        }
    }

    /**
     * Per-frame animation tick and hierarchical skeleton forward-kinematics.
     */
    public void update(float dt) {
        idleTimer += dt;

        // Smooth position interpolation
        float distToTarget = currentPos.dst(targetPos);
        if (distToTarget > 0.03f) {
            isWalking = true;
            // Smoothly move towards target tile
            float step = Math.min(1f, dt * 7.5f);
            currentPos.lerp(targetPos, step);
            walkProgress += dt * 8.0f;
        } else {
            isWalking = false;
            // Gently settle walkProgress back towards 0
            walkProgress += dt * 1.5f;
        }

        // Smooth yaw interpolation
        currentYaw = MathUtils.lerpAngleDeg(currentYaw, targetYaw, Math.min(1f, dt * 10.0f));

        // Master root transform: Agent's position and orientation in the world
        float standY = alive ? 0.08f : -0.25f;
        rootMatrix.idt()
                .translate(currentPos.x, standY, currentPos.z)
                .rotate(Vector3.Y, currentYaw);

        if (!alive) {
            // Crumpled unconscious pose
            rootMatrix.rotate(Vector3.X, 85f);
        }

        // Kinematic joint calculations
        animateSkeleton(dt);
    }

    private void animateSkeleton(float dt) {
        float stride = isWalking ? (float)Math.sin(walkProgress) : 0f;
        float breath = (float)Math.sin(idleTimer * 2.2f + (isAlpha ? 0f : 1.2f)) * 0.015f;
        float bob = isWalking ? -Math.abs((float)Math.sin(walkProgress)) * 0.035f : breath;

        // ── 1. PELVIS / LOWER BODY ───────────────────────────────────────────
        float hipY = 0.72f + bob;

        // Skirt attached at hips
        tempMat.set(rootMatrix).translate(0f, hipY, 0f);
        skirt.transform.set(tempMat);

        // Legs: Hip joints at x = ±0.11
        float legSwingL = stride * 30.0f; // degrees forward/backward
        float legSwingR = -stride * 30.0f;

        // Left Leg
        jointMat.set(rootMatrix).translate(-0.11f, hipY, 0f).rotate(Vector3.X, legSwingL);
        // Thigh
        tempMat.set(jointMat).translate(0f, -0.16f, 0f);
        thighL.transform.set(tempMat);

        // Knee: bends backward during back-swing
        float kneeAngleL = isWalking ? Math.max(0f, -legSwingL * 1.2f) : 0f;
        jointMat.translate(0f, -0.32f, 0f).rotate(Vector3.X, kneeAngleL);
        // Shin
        tempMat.set(jointMat).translate(0f, -0.15f, 0f);
        shinL.transform.set(tempMat);
        // Boot
        tempMat.set(jointMat).translate(0f, -0.30f, 0.04f);
        bootL.transform.set(tempMat);

        // Right Leg
        jointMat.set(rootMatrix).translate(0.11f, hipY, 0f).rotate(Vector3.X, legSwingR);
        // Thigh
        tempMat.set(jointMat).translate(0f, -0.16f, 0f);
        thighR.transform.set(tempMat);

        // Knee
        float kneeAngleR = isWalking ? Math.max(0f, -legSwingR * 1.2f) : 0f;
        jointMat.translate(0f, -0.32f, 0f).rotate(Vector3.X, kneeAngleR);
        // Shin
        tempMat.set(jointMat).translate(0f, -0.15f, 0f);
        shinR.transform.set(tempMat);
        // Boot
        tempMat.set(jointMat).translate(0f, -0.30f, 0.04f);
        bootR.transform.set(tempMat);

        // ── 2. TORSO / UPPER BODY ────────────────────────────────────────────
        float torsoY = 0.96f + bob;
        float torsoTwist = isWalking ? -stride * 4.0f : 0f;
        jointMat.set(rootMatrix).translate(0f, torsoY, 0f).rotate(Vector3.Y, torsoTwist);
        torso.transform.set(jointMat);

        // Neck & Head
        float neckY = 1.24f + bob;
        tempMat.set(rootMatrix).translate(0f, neckY, 0f);
        neck.transform.set(tempMat);

        float headY = 1.48f + bob;
        jointMat.set(rootMatrix).translate(0f, headY, 0f);
        headSkull.transform.set(jointMat);

        // Expressive Face plane placed directly on front face of head (+Z)
        tempMat.set(jointMat).translate(0f, 0f, 0.165f);
        face.transform.set(tempMat);

        // Styled Hair cap
        tempMat.set(jointMat).translate(0f, 0.06f, -0.02f);
        hairCap.transform.set(tempMat);

        // Hair accent (ponytail / side locks) swayed by movement
        float hairSway = isWalking ? (float)Math.cos(walkProgress) * 12.0f : breath * 100f;
        if (isAlpha) {
            // Ponytail out the back
            tempMat.set(jointMat)
                    .translate(0f, 0.08f, -0.20f)
                    .rotate(Vector3.X, 35.0f + hairSway);
            hairAccent.transform.set(tempMat);
        } else {
            // Roselia swept locks
            tempMat.set(jointMat)
                    .translate(0.18f, -0.08f, 0f)
                    .rotate(Vector3.Z, hairSway);
            hairAccent.transform.set(tempMat);
        }

        // ── 3. ARMS & HANDS ──────────────────────────────────────────────────
        boolean isCarrying = (holdingItem != null && holdingItem != 0);

        // Left Arm
        float shoulderPitchL;
        float elbowPitchL;
        if (isCarrying) {
            shoulderPitchL = -42.0f; // Raise forward
            elbowPitchL = 65.0f;     // Bend forward to hold item
        } else {
            shoulderPitchL = isWalking ? -stride * 26.0f : breath * 40f; // Counter-swing
            elbowPitchL = isWalking ? Math.max(8.0f, -shoulderPitchL * 0.4f) : 10.0f;
        }

        jointMat.set(rootMatrix).translate(-0.25f, 1.15f + bob, 0f);
        shoulderL.transform.set(jointMat);

        jointMat.rotate(Vector3.X, shoulderPitchL).rotate(Vector3.Z, 12.0f);
        tempMat.set(jointMat).translate(0f, -0.13f, 0f);
        upperArmL.transform.set(tempMat);

        // Elbow
        jointMat.translate(0f, -0.26f, 0f).rotate(Vector3.X, elbowPitchL);
        tempMat.set(jointMat).translate(0f, -0.12f, 0f);
        forearmL.transform.set(tempMat);

        // Hand
        tempMat.set(jointMat).translate(0f, -0.24f, 0.02f);
        handL.transform.set(tempMat);

        // Right Arm
        float shoulderPitchR;
        float elbowPitchR;
        if (isCarrying) {
            shoulderPitchR = -42.0f;
            elbowPitchR = 65.0f;
        } else {
            shoulderPitchR = isWalking ? stride * 26.0f : -breath * 40f;
            elbowPitchR = isWalking ? Math.max(8.0f, -shoulderPitchR * 0.4f) : 10.0f;
        }

        jointMat.set(rootMatrix).translate(0.25f, 1.15f + bob, 0f);
        shoulderR.transform.set(jointMat);

        jointMat.rotate(Vector3.X, shoulderPitchR).rotate(Vector3.Z, -12.0f);
        tempMat.set(jointMat).translate(0f, -0.13f, 0f);
        upperArmR.transform.set(tempMat);

        // Elbow
        jointMat.translate(0f, -0.26f, 0f).rotate(Vector3.X, elbowPitchR);
        tempMat.set(jointMat).translate(0f, -0.12f, 0f);
        forearmR.transform.set(tempMat);

        // Hand
        tempMat.set(jointMat).translate(0f, -0.24f, 0.02f);
        handR.transform.set(tempMat);

        // ── 4. HELD ITEM IN HANDS ────────────────────────────────────────────
        if (isCarrying && heldInstance != null) {
            tempMat.set(rootMatrix)
                    .translate(0f, 0.95f + bob, 0.32f)
                    .scl(0.85f);
            heldInstance.transform.set(tempMat);
        }
    }

    /**
     * Render all parts using the provided ModelBatch and Environment.
     */
    public void render(ModelBatch batch, com.badlogic.gdx.graphics.g3d.Environment env) {
        for (ModelInstance part : parts) {
            batch.render(part, env);
        }
        if (holdingItem != null && holdingItem != 0 && heldInstance != null) {
            batch.render(heldInstance, env);
        }
    }
}
