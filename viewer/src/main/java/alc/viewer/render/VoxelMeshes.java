package alc.viewer.render;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.VertexAttributes;
import com.badlogic.gdx.graphics.g3d.Material;
import com.badlogic.gdx.graphics.g3d.Model;
import com.badlogic.gdx.graphics.g3d.attributes.BlendingAttribute;
import com.badlogic.gdx.graphics.g3d.attributes.ColorAttribute;
import com.badlogic.gdx.graphics.g3d.attributes.FloatAttribute;
import com.badlogic.gdx.graphics.g3d.utils.ModelBuilder;
import com.badlogic.gdx.utils.Disposable;

import java.util.HashMap;
import java.util.Map;

/**
 * All meshes are simple primitives created via ModelBuilder.
 * Each agent body part is a SEPARATE model so we can position/rotate them independently each frame.
 */
public class VoxelMeshes implements Disposable {

    private final ModelBuilder mb = new ModelBuilder();
    private final Map<String, Model> models = new HashMap<>();

    private static final long ATTR = VertexAttributes.Usage.Position | VertexAttributes.Usage.Normal;

    // ── Earth palette ──────────────────────────────────────────────────────
    public static final Color C_GRASS      = new Color(0.22f, 0.55f, 0.18f, 1f);
    public static final Color C_GRASS_DARK = new Color(0.14f, 0.38f, 0.10f, 1f);
    public static final Color C_SOIL       = new Color(0.40f, 0.24f, 0.10f, 1f);
    public static final Color C_WATER      = new Color(0.08f, 0.42f, 0.76f, 0.72f);
    public static final Color C_ROCK       = new Color(0.58f, 0.56f, 0.54f, 1f);
    public static final Color C_ROCK_DARK  = new Color(0.35f, 0.34f, 0.32f, 1f);
    public static final Color C_BARK       = new Color(0.30f, 0.18f, 0.06f, 1f);
    public static final Color C_LEAF       = new Color(0.12f, 0.50f, 0.14f, 1f);
    public static final Color C_LEAF_LIGHT = new Color(0.22f, 0.68f, 0.22f, 1f);
    public static final Color C_SKY        = new Color(0.42f, 0.68f, 0.98f, 1f);
    public static final Color C_SKY_TOP    = new Color(0.20f, 0.44f, 0.88f, 1f);

    // ── Crop / item ───────────────────────────────────────────────────────
    public static final Color C_SPROUT      = new Color(0.45f, 0.82f, 0.22f, 1f);
    public static final Color C_FRUIT_FOOD  = new Color(0.90f, 0.16f, 0.10f, 1f);
    public static final Color C_FRUIT_POISN = new Color(0.65f, 0.06f, 0.90f, 1f);
    public static final Color C_SEED        = new Color(0.60f, 0.40f, 0.18f, 1f);
    public static final Color C_CONTAINER   = new Color(0.80f, 0.72f, 0.44f, 1f);

    // ── Agent body colours ─────────────────────────────────────────────────
    public static final Color C_SKIN           = new Color(0.97f, 0.82f, 0.70f, 1f);
    public static final Color C_SKIN_SHADOW    = new Color(0.78f, 0.60f, 0.48f, 1f);
    public static final Color C_ALPHA_CLOTH    = new Color(0.85f, 0.26f, 0.18f, 1f);
    public static final Color C_ALPHA_HAIR     = new Color(0.92f, 0.70f, 0.12f, 1f);
    public static final Color C_ROSELIA_CLOTH  = new Color(0.14f, 0.62f, 0.56f, 1f);
    public static final Color C_ROSELIA_HAIR   = new Color(0.58f, 0.14f, 0.74f, 1f);
    public static final Color C_SHOE_DARK      = new Color(0.22f, 0.14f, 0.06f, 1f);

    public VoxelMeshes() { build(); }

    private void build() {
        long a = ATTR;

        // ── Ground tiles ──────────────────────────────────────────────────
        put("grass",       mb.createBox(1f, 0.22f, 1f, mat(C_GRASS,      C_GRASS_DARK, 0.02f, 12f), a));
        put("soil",        mb.createBox(1f, 0.18f, 1f, mat(C_SOIL,       C_SOIL.cpy().mul(0.6f,0.6f,0.6f,1f), 0.01f, 4f), a));
        put("rock_tile",   mb.createBox(1f, 0.80f, 1f, mat(C_ROCK,       C_ROCK_DARK, 0.22f, 40f), a));
        Material waterMat = new Material(
                ColorAttribute.createDiffuse(C_WATER),
                ColorAttribute.createSpecular(new Color(0.8f,0.9f,1f,1f)),
                FloatAttribute.createShininess(90f),
                new BlendingAttribute(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA, 0.72f));
        put("water_tile",  mb.createBox(1f, 0.14f, 1f, waterMat, a));

        // ── Tree parts ────────────────────────────────────────────────────
        put("tree_trunk",  mb.createCylinder(0.28f, 1.40f, 0.28f, 10, mat(C_BARK, C_BARK.cpy().mul(0.6f,0.6f,0.6f,1f), 0.04f, 8f), a));
        put("tree_leaf0",  mb.createSphere(1.10f, 0.90f, 1.10f, 14, 10, mat(C_LEAF, C_LEAF_DARK(), 0.04f, 10f), a));
        put("tree_leaf1",  mb.createSphere(0.82f, 0.80f, 0.82f, 12, 8,  mat(C_LEAF_LIGHT, C_LEAF, 0.05f, 12f), a));
        put("tree_leaf2",  mb.createSphere(0.52f, 0.65f, 0.52f, 10, 8,  mat(C_LEAF_LIGHT, C_LEAF_DARK(), 0.06f, 14f), a));

        // ── Crops & items ─────────────────────────────────────────────────
        put("sprout",      mb.createBox(0.10f, 0.30f, 0.10f, mat(C_SPROUT, C_SPROUT.cpy().mul(0.6f,0.6f,0.6f,1f), 0.04f, 8f), a));
        put("fruit_food",  mb.createSphere(0.36f, 0.36f, 0.36f, 12, 10, mat(C_FRUIT_FOOD, C_FRUIT_FOOD.cpy().mul(0.6f,0.6f,0.6f,1f), 0.26f, 44f), a));
        put("fruit_poison",mb.createSphere(0.36f, 0.36f, 0.36f, 12, 10, mat(C_FRUIT_POISN, C_FRUIT_POISN.cpy().mul(0.5f,0.5f,0.5f,1f), 0.16f, 28f), a));
        put("seed",        mb.createSphere(0.14f, 0.14f, 0.14f, 8, 6,   mat(C_SEED, C_SEED.cpy().mul(0.7f,0.7f,0.7f,1f), 0.03f, 8f), a));
        put("container",   mb.createCylinder(0.20f, 0.30f, 0.20f, 10,   mat(C_CONTAINER, C_CONTAINER.cpy().mul(0.6f,0.6f,0.6f,1f), 0.18f, 30f), a));

        // ── Agent: shared body parts ───────────────────────────────────────
        put("head",        mb.createSphere(0.30f, 0.32f, 0.28f, 14, 12, mat(C_SKIN, C_SKIN_SHADOW, 0.10f, 20f), a));
        put("neck",        mb.createCylinder(0.10f, 0.14f, 0.10f, 8,    mat(C_SKIN, C_SKIN_SHADOW, 0.06f, 10f), a));
        put("torso",       mb.createBox(0.38f, 0.44f, 0.22f,            mat(null, null, 0f, 0f), a)); // cloth color overridden per-agent below
        put("upper_arm",   mb.createCylinder(0.07f, 0.26f, 0.07f, 8,    mat(null, null, 0f, 0f), a));
        put("forearm",     mb.createCylinder(0.06f, 0.22f, 0.06f, 8,    mat(C_SKIN, C_SKIN_SHADOW, 0.08f, 14f), a));
        put("hand",        mb.createSphere(0.08f, 0.08f, 0.08f, 8, 6,   mat(C_SKIN, C_SKIN_SHADOW, 0.08f, 14f), a));
        put("thigh",       mb.createCylinder(0.09f, 0.28f, 0.09f, 8,    mat(null, null, 0f, 0f), a));
        put("shin",        mb.createCylinder(0.07f, 0.26f, 0.07f, 8,    mat(C_SKIN.cpy().mul(0.9f,0.9f,0.9f,1f), C_SKIN_SHADOW, 0.06f, 10f), a));
        put("foot",        mb.createBox(0.14f, 0.07f, 0.18f,            mat(C_SHOE_DARK, C_SHOE_DARK.cpy().mul(0.6f,0.6f,0.6f,1f), 0.20f, 28f), a));

        // Per-agent cloth-colored pieces
        put("torso_alpha",       mb.createBox(0.38f, 0.44f, 0.22f, mat(C_ALPHA_CLOTH, C_ALPHA_CLOTH.cpy().mul(0.7f,0.7f,0.7f,1f), 0.08f, 16f), a));
        put("upper_arm_alpha",   mb.createCylinder(0.07f, 0.26f, 0.07f, 8, mat(C_ALPHA_CLOTH, C_ALPHA_CLOTH.cpy().mul(0.7f,0.7f,0.7f,1f), 0.08f, 16f), a));
        put("thigh_alpha",       mb.createCylinder(0.09f, 0.28f, 0.09f, 8, mat(C_ALPHA_CLOTH, C_ALPHA_CLOTH.cpy().mul(0.7f,0.7f,0.7f,1f), 0.06f, 12f), a));
        put("hair_alpha",        mb.createSphere(0.32f, 0.22f, 0.32f, 12, 8, mat(C_ALPHA_HAIR, C_ALPHA_HAIR.cpy().mul(0.6f,0.6f,0.6f,1f), 0.14f, 28f), a));

        put("torso_roselia",     mb.createBox(0.38f, 0.44f, 0.22f, mat(C_ROSELIA_CLOTH, C_ROSELIA_CLOTH.cpy().mul(0.7f,0.7f,0.7f,1f), 0.10f, 18f), a));
        put("upper_arm_roselia", mb.createCylinder(0.07f, 0.26f, 0.07f, 8, mat(C_ROSELIA_CLOTH, C_ROSELIA_CLOTH.cpy().mul(0.7f,0.7f,0.7f,1f), 0.10f, 18f), a));
        put("thigh_roselia",     mb.createCylinder(0.09f, 0.28f, 0.09f, 8, mat(C_ROSELIA_CLOTH, C_ROSELIA_CLOTH.cpy().mul(0.7f,0.7f,0.7f,1f), 0.06f, 12f), a));
        put("hair_roselia",      mb.createSphere(0.32f, 0.22f, 0.32f, 12, 8, mat(C_ROSELIA_HAIR, C_ROSELIA_HAIR.cpy().mul(0.6f,0.6f,0.6f,1f), 0.16f, 32f), a));

        // ── Directional arrow ─────────────────────────────────────────────
        Material arrowMat = new Material(
                ColorAttribute.createDiffuse(new Color(1f, 0.94f, 0.08f, 0.88f)),
                ColorAttribute.createSpecular(new Color(1f, 1f, 0.6f, 1f)),
                FloatAttribute.createShininess(60f),
                new BlendingAttribute(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA, 0.88f));
        put("arrow", mb.createCone(0.18f, 0.40f, 0.18f, 6, arrowMat, a));

        // ── Sky hemisphere ────────────────────────────────────────────────
        put("sky", mb.createSphere(180f, 90f, 180f, 14, 10, mat(C_SKY, C_SKY_TOP, 0f, 1f), a));
    }

    private static Color C_LEAF_DARK() {
        return new Color(0.08f, 0.34f, 0.08f, 1f);
    }

    private void put(String k, Model m) { models.put(k, m); }

    private Material mat(Color diffuse, Color specular, float specFactor, float shin) {
        if (diffuse == null) diffuse = new Color(0.7f, 0.7f, 0.7f, 1f);
        Color spec = (specular != null) ? specular.cpy().mul(specFactor * 5f) : new Color(0,0,0,1f);
        spec.a = 1f;
        return new Material(
                ColorAttribute.createDiffuse(diffuse),
                ColorAttribute.createSpecular(spec),
                FloatAttribute.createShininess(shin)
        );
    }

    public Model get(String key)    { return models.get(key); }
    public boolean has(String key)  { return models.containsKey(key) && models.get(key) != null; }

    @Override
    public void dispose() {
        models.values().forEach(m -> { if (m != null) m.dispose(); });
        models.clear();
    }
}
