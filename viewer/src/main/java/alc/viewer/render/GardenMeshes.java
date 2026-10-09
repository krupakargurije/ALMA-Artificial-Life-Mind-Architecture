package alc.viewer.render;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.VertexAttributes;
import com.badlogic.gdx.graphics.g3d.Material;
import com.badlogic.gdx.graphics.g3d.Model;
import com.badlogic.gdx.graphics.g3d.attributes.BlendingAttribute;
import com.badlogic.gdx.graphics.g3d.attributes.ColorAttribute;
import com.badlogic.gdx.graphics.g3d.attributes.FloatAttribute;
import com.badlogic.gdx.graphics.g3d.attributes.TextureAttribute;
import com.badlogic.gdx.graphics.g3d.utils.ModelBuilder;
import com.badlogic.gdx.utils.Disposable;

import java.util.HashMap;
import java.util.Map;

/**
 * GardenMeshes constructs rich, realistic 3D models with textured materials:
 * - Garden terrain: lush grass with variations, raised tilled soil beds, cobblestone paths
 * - Water sanctuary: sunken stone pond, animated translucent water, floating lily pads
 * - Garden architecture: rustic wooden fences, gnarled trees with leaf canopies and apples, stone well, lanterns
 * - Nature details: 3D grass tufts, poppies, daisies, lavenders
 * - Articulated humanoid avatars for Alpha and Roselia with expressive faces, styled hair, hands, and boots
 */
public class GardenMeshes implements Disposable {

    private final ModelBuilder mb = new ModelBuilder();
    private final Map<String, Model> models = new HashMap<>();
    private final TexturePalette palette;

    private static final long ATTR = VertexAttributes.Usage.Position
            | VertexAttributes.Usage.Normal
            | VertexAttributes.Usage.TextureCoordinates;

    public GardenMeshes(TexturePalette palette) {
        this.palette = palette;
        buildAll();
    }

    private void buildAll() {
        buildTerrainMeshes();
        buildFloraAndSanctuaryMeshes();
        buildItemAndCropMeshes();
        buildHumanoidAvatarMeshes();
        buildSkyAndWeather();
    }

    // ── 1. TERRAIN MESHES ───────────────────────────────────────────────────
    private void buildTerrainMeshes() {
        Material grassMat = texMat("grass", 0.08f, 15f);
        Material soilMat  = texMat("soil",  0.02f, 8f);
        Material cobbleMat= texMat("cobble",0.12f, 25f);
        Material woodMat  = texMat("wood",  0.06f, 12f);

        // Standard lush grass tile (1m x 0.2m x 1m)
        put("grass_tile", mb.createBox(1.0f, 0.20f, 1.0f, grassMat, ATTR));

        // Raised garden bed for soil: rich dark loam with cedar timber border
        put("soil_tile", mb.createBox(0.96f, 0.22f, 0.96f, soilMat, ATTR));
        put("planter_border", mb.createBox(1.02f, 0.25f, 1.02f, woodMat, ATTR));

        // Cobblestone path tile
        put("cobble_tile", mb.createBox(1.0f, 0.21f, 1.0f, cobbleMat, ATTR));

        // Sunken pond basin (recessed ground)
        Material basinMat = texMat("stone", 0.15f, 30f);
        put("water_basin", mb.createBox(1.0f, 0.08f, 1.0f, basinMat, ATTR));

        // Translucent water surface quad with caustic texture & specular shine
        Material waterMat = new Material(
                TextureAttribute.createDiffuse(palette.get("water")),
                ColorAttribute.createSpecular(new Color(0.9f, 0.95f, 1.0f, 1.0f)),
                FloatAttribute.createShininess(120.0f),
                new BlendingAttribute(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA, 0.78f)
        );
        put("water_surface", mb.createBox(1.0f, 0.04f, 1.0f, waterMat, ATTR));

        // Stepping stone
        put("stepping_stone", mb.createCylinder(0.42f, 0.06f, 0.42f, 8, cobbleMat, ATTR));
    }

    // ── 2. FLORA & GARDEN SANCTUARY MESHES ─────────────────────────────────
    private void buildFloraAndSanctuaryMeshes() {
        Material barkMat  = texMat("bark", 0.05f, 10f);
        Material leafMat  = texMat("leaves", 0.08f, 18f);
        Material woodMat  = texMat("wood", 0.08f, 15f);
        Material stoneMat = texMat("stone", 0.10f, 20f);

        // Realistic tree: gnarled trunk & branching canopy
        put("tree_trunk", mb.createCylinder(0.36f, 2.2f, 0.36f, 10, barkMat, ATTR));
        put("tree_branch", mb.createCylinder(0.18f, 1.1f, 0.18f, 8, barkMat, ATTR));
        put("canopy_large", mb.createSphere(1.8f, 1.4f, 1.8f, 14, 10, leafMat, ATTR));
        put("canopy_medium", mb.createSphere(1.3f, 1.1f, 1.3f, 12, 8, leafMat, ATTR));
        put("canopy_small", mb.createSphere(0.9f, 0.8f, 0.9f, 10, 8, leafMat, ATTR));

        // Hanging apples on tree
        Material appleMat = colorMat(new Color(0.92f, 0.15f, 0.12f, 1f), 0.35f, 50f);
        put("apple", mb.createSphere(0.20f, 0.22f, 0.20f, 8, 6, appleMat, ATTR));

        // 3D Grass Tufts (clumps of tall grass blades)
        Material grassBladeMat = colorMat(new Color(0.28f, 0.68f, 0.20f, 1f), 0.05f, 10f);
        put("grass_tuft", mb.createCone(0.28f, 0.38f, 0.28f, 6, grassBladeMat, ATTR));

        // Wildflowers
        put("flower_poppy", mb.createSphere(0.16f, 0.14f, 0.16f, 8, 6,
                colorMat(new Color(0.95f, 0.18f, 0.14f, 1f), 0.2f, 30f), ATTR));
        put("flower_daisy", mb.createSphere(0.15f, 0.12f, 0.15f, 8, 6,
                colorMat(new Color(0.98f, 0.98f, 0.94f, 1f), 0.2f, 30f), ATTR));
        put("flower_lavender", mb.createCylinder(0.10f, 0.34f, 0.10f, 6,
                colorMat(new Color(0.65f, 0.32f, 0.88f, 1f), 0.1f, 15f), ATTR));
        put("flower_stem", mb.createCylinder(0.04f, 0.32f, 0.04f, 4,
                colorMat(new Color(0.22f, 0.52f, 0.16f, 1f), 0.02f, 5f), ATTR));

        // Water Lily Pads & Blossoms
        Material lilyMat = new Material(
                TextureAttribute.createDiffuse(palette.get("lilypad")),
                ColorAttribute.createSpecular(new Color(0.2f, 0.4f, 0.2f, 1f)),
                FloatAttribute.createShininess(30f),
                new BlendingAttribute(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA, 0.95f)
        );
        put("lily_pad", mb.createBox(0.48f, 0.02f, 0.48f, lilyMat, ATTR));
        put("lily_blossom", mb.createSphere(0.16f, 0.14f, 0.16f, 8, 6,
                colorMat(new Color(0.98f, 0.88f, 0.92f, 1f), 0.2f, 40f), ATTR));

        // Rustic wooden perimeter fence
        put("fence_post", mb.createBox(0.14f, 0.95f, 0.14f, woodMat, ATTR));
        put("fence_rail", mb.createBox(1.02f, 0.09f, 0.07f, woodMat, ATTR));

        // Garden stone well
        put("well_base", mb.createCylinder(0.85f, 0.55f, 0.85f, 12, stoneMat, ATTR));
        put("well_roof", mb.createCone(1.05f, 0.65f, 1.05f, 4, woodMat, ATTR));
        put("well_beam", mb.createBox(0.08f, 1.10f, 0.08f, woodMat, ATTR));

        // Rustic wooden garden bench
        put("bench_seat", mb.createBox(0.85f, 0.07f, 0.34f, woodMat, ATTR));
        put("bench_leg",  mb.createBox(0.08f, 0.32f, 0.30f, woodMat, ATTR));

        // Garden lantern post
        Material glowMat = new Material(
                TextureAttribute.createDiffuse(palette.get("lantern")),
                ColorAttribute.createSpecular(new Color(1f, 0.9f, 0.6f, 1f)),
                FloatAttribute.createShininess(80f),
                new BlendingAttribute(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA, 0.9f)
        );
        put("lantern_glass", mb.createBox(0.20f, 0.28f, 0.20f, glowMat, ATTR));
    }

    // ── 3. ITEMS & CROPS ────────────────────────────────────────────────────
    private void buildItemAndCropMeshes() {
        Material woodMat = texMat("wood", 0.08f, 15f);

        // Seed: golden-brown grain
        put("seed", mb.createSphere(0.14f, 0.18f, 0.14f, 8, 6,
                colorMat(new Color(0.68f, 0.48f, 0.22f, 1f), 0.15f, 20f), ATTR));

        // Sprout: curved young plant with green leaves
        put("sprout_stem", mb.createCylinder(0.06f, 0.36f, 0.06f, 6,
                colorMat(new Color(0.42f, 0.82f, 0.24f, 1f), 0.08f, 15f), ATTR));
        put("sprout_leaf", mb.createSphere(0.16f, 0.06f, 0.12f, 6, 6,
                colorMat(new Color(0.48f, 0.88f, 0.26f, 1f), 0.12f, 20f), ATTR));

        // Food Fruit (Ruby garden tomato/berry)
        put("fruit_food", mb.createSphere(0.34f, 0.34f, 0.34f, 12, 10,
                colorMat(new Color(0.94f, 0.18f, 0.12f, 1f), 0.38f, 60f), ATTR));

        // Poison Berry (Iridescent dark purple nightshade)
        put("fruit_poison", mb.createSphere(0.34f, 0.34f, 0.34f, 12, 10,
                colorMat(new Color(0.55f, 0.08f, 0.78f, 1f), 0.45f, 75f), ATTR));

        // Water container (Wooden garden bucket with water inside)
        put("bucket_casing", mb.createCylinder(0.32f, 0.38f, 0.32f, 10, woodMat, ATTR));
        put("bucket_water",  mb.createCylinder(0.28f, 0.06f, 0.28f, 8,
                colorMat(new Color(0.12f, 0.55f, 0.88f, 0.9f), 0.4f, 70f), ATTR));
    }

    // ── 4. HUMANOID CHARACTER AVATARS (ALPHA & ROSELIA) ────────────────────
    private void buildHumanoidAvatarMeshes() {
        Material skinMat      = texMat("skin", 0.08f, 15f);
        Material alphaFaceMat = texMat("alpha_face", 0.10f, 20f);
        Material roseFaceMat  = texMat("roselia_face", 0.10f, 20f);
        Material alphaCloth   = texMat("alpha_cloth", 0.12f, 22f);
        Material roseCloth    = texMat("roselia_cloth", 0.12f, 22f);
        Material shoeMat      = texMat("shoe", 0.25f, 40f);

        // Alpha hair (Warm golden-blonde with ponytail)
        Material alphaHair = colorMat(new Color(0.94f, 0.74f, 0.18f, 1f), 0.22f, 35f);
        put("hair_alpha_cap", mb.createSphere(0.36f, 0.28f, 0.36f, 12, 8, alphaHair, ATTR));
        put("hair_alpha_pony",mb.createCylinder(0.12f, 0.44f, 0.12f, 8, alphaHair, ATTR));

        // Roselia hair (Amethyst / plum-violet twin swept hairstyle)
        Material roseHair = colorMat(new Color(0.58f, 0.18f, 0.72f, 1f), 0.24f, 40f);
        put("hair_rose_cap",  mb.createSphere(0.36f, 0.28f, 0.36f, 12, 8, roseHair, ATTR));
        put("hair_rose_side", mb.createSphere(0.16f, 0.38f, 0.16f, 8, 8, roseHair, ATTR));

        // Shared head base & faces
        put("head_skull",   mb.createSphere(0.34f, 0.36f, 0.32f, 14, 12, skinMat, ATTR));
        put("face_alpha",   mb.createBox(0.28f, 0.28f, 0.02f, alphaFaceMat, ATTR));
        put("face_roselia", mb.createBox(0.28f, 0.28f, 0.02f, roseFaceMat, ATTR));
        put("neck",         mb.createCylinder(0.11f, 0.14f, 0.11f, 8, skinMat, ATTR));

        // Torso / Outfits
        put("torso_alpha",  mb.createBox(0.38f, 0.44f, 0.22f, alphaCloth, ATTR));
        put("skirt_alpha",  mb.createCone(0.46f, 0.28f, 0.34f, 10, alphaCloth, ATTR));

        put("torso_rose",   mb.createBox(0.38f, 0.44f, 0.22f, roseCloth, ATTR));
        put("skirt_rose",   mb.createCone(0.46f, 0.28f, 0.34f, 10, roseCloth, ATTR));

        // Articulated Arms & Hands
        // Shoulders (spherical deltoid caps)
        put("shoulder_alpha", mb.createSphere(0.12f, 0.12f, 0.12f, 8, 8, alphaCloth, ATTR));
        put("shoulder_rose",  mb.createSphere(0.12f, 0.12f, 0.12f, 8, 8, roseCloth, ATTR));

        // Upper arm (sleeved)
        put("upper_arm_alpha", mb.createCylinder(0.08f, 0.26f, 0.08f, 8, alphaCloth, ATTR));
        put("upper_arm_rose",  mb.createCylinder(0.08f, 0.26f, 0.08f, 8, roseCloth, ATTR));

        // Forearm (skin tone with wrist cuff)
        put("forearm", mb.createCylinder(0.07f, 0.24f, 0.07f, 8, skinMat, ATTR));

        // Detailed Hands (palm + fingers mitt)
        put("hand", mb.createBox(0.09f, 0.12f, 0.05f, skinMat, ATTR));

        // Articulated Legs & Boots
        // Thighs
        put("thigh_alpha", mb.createCylinder(0.11f, 0.32f, 0.11f, 8, alphaCloth, ATTR));
        put("thigh_rose",  mb.createCylinder(0.11f, 0.32f, 0.11f, 8, roseCloth, ATTR));

        // Shins / Calves
        put("shin", mb.createCylinder(0.085f, 0.30f, 0.085f, 8, skinMat, ATTR));

        // Shoes / Boots (sculpted foot with heel and toe box)
        put("boot", mb.createBox(0.13f, 0.10f, 0.22f, shoeMat, ATTR));
    }

    // ── 5. SKY & WEATHER ────────────────────────────────────────────────────
    private void buildSkyAndWeather() {
        // Horizon sky hemisphere
        Material skyMat = colorMat(new Color(0.46f, 0.72f, 0.98f, 1f), 0f, 1f);
        put("sky_dome", mb.createSphere(220f, 110f, 220f, 16, 12, skyMat, ATTR));

        // Rain streak
        Material rainMat = new Material(
                ColorAttribute.createDiffuse(new Color(0.75f, 0.85f, 0.98f, 0.70f)),
                new BlendingAttribute(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA, 0.70f)
        );
        put("rain_streak", mb.createCylinder(0.02f, 0.65f, 0.02f, 4, rainMat, ATTR));
    }

    // ── HELPERS ─────────────────────────────────────────────────────────────
    private Material texMat(String key, float specFactor, float shininess) {
        Texture tex = palette.get(key);
        Color spec = new Color(specFactor, specFactor, specFactor, 1f);
        return new Material(
                TextureAttribute.createDiffuse(tex),
                ColorAttribute.createSpecular(spec),
                FloatAttribute.createShininess(shininess)
        );
    }

    private Material colorMat(Color diff, float specFactor, float shininess) {
        Color spec = new Color(specFactor, specFactor, specFactor, 1f);
        return new Material(
                ColorAttribute.createDiffuse(diff),
                ColorAttribute.createSpecular(spec),
                FloatAttribute.createShininess(shininess)
        );
    }

    private void put(String key, Model model) {
        models.put(key, model);
    }

    public Model get(String key) {
        return models.get(key);
    }

    public boolean has(String key) {
        return models.containsKey(key) && models.get(key) != null;
    }

    @Override
    public void dispose() {
        models.values().forEach(m -> { if (m != null) m.dispose(); });
        models.clear();
    }
}
