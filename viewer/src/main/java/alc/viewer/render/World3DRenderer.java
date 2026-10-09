package alc.viewer.render;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.PerspectiveCamera;
import com.badlogic.gdx.graphics.g3d.*;
import com.badlogic.gdx.graphics.g3d.attributes.BlendingAttribute;
import com.badlogic.gdx.graphics.g3d.attributes.ColorAttribute;
import com.badlogic.gdx.graphics.g3d.environment.DirectionalLight;
import com.badlogic.gdx.math.Vector3;
import com.badlogic.gdx.utils.Disposable;
import alc.viewer.net.dto.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * World3DRenderer renders the lush 3D garden world and the two artificial beings,
 * Alpha and Roselia, with realistic textures, lighting, nature props, and articulated animations.
 */
public class World3DRenderer implements Disposable {

    private final PerspectiveCamera camera;
    private final OrbitCameraController cameraController;
    private final ModelBatch modelBatch;

    private final TexturePalette palette;
    private final GardenMeshes meshes;

    private final Environment sunnyEnv = new Environment();
    private final Environment rainEnv  = new Environment();

    // Scene layers
    private final List<ModelInstance> terrainOpaque = new ArrayList<>();
    private final List<ModelInstance> terrainTransp = new ArrayList<>();
    private final List<ModelInstance> dynamicOpaque = new ArrayList<>();
    private final List<ModelInstance> rainStreaks   = new ArrayList<>();

    private ModelInstance skyDome;
    private WorldInitDto currentInit;

    // Articulated Agent Avatars (Alpha & Albedo)
    private final AgentAvatar alphaAvatar;
    private final AgentAvatar albedoAvatar;

    private float runTime = 0f;

    public World3DRenderer() {
        camera = new PerspectiveCamera(52, Gdx.graphics.getWidth(), Gdx.graphics.getHeight());
        camera.near = 0.1f;
        camera.far  = 300f;
        cameraController = new OrbitCameraController(camera);
        modelBatch = new ModelBatch();

        palette = new TexturePalette();
        meshes  = new GardenMeshes(palette);

        alphaAvatar  = new AgentAvatar(0, true,  meshes);
        albedoAvatar = new AgentAvatar(1, false, meshes);

        setupLighting();

        if (meshes.has("sky_dome")) {
            skyDome = new ModelInstance(meshes.get("sky_dome"));
        }

        // Initialize rain particles
        initRainStreaks();
    }

    private void setupLighting() {
        // Sunny garden atmosphere
        sunnyEnv.set(new ColorAttribute(ColorAttribute.AmbientLight, 0.42f, 0.42f, 0.45f, 1f));
        sunnyEnv.add(new DirectionalLight().set(1.0f, 0.95f, 0.86f, -0.6f, -1.0f, -0.4f)); // Warm Sunlight
        sunnyEnv.add(new DirectionalLight().set(0.24f, 0.35f, 0.55f, 0.5f, -0.4f, 0.4f));  // Sky Blue Fill
        sunnyEnv.add(new DirectionalLight().set(0.30f, 0.28f, 0.22f, 0.1f, 0.6f, 0.7f));   // Warm Rim Light

        // Overcast rain atmosphere
        rainEnv.set(new ColorAttribute(ColorAttribute.AmbientLight, 0.28f, 0.30f, 0.38f, 1f));
        rainEnv.add(new DirectionalLight().set(0.58f, 0.62f, 0.74f, -0.2f, -1.0f, -0.2f));
        rainEnv.add(new DirectionalLight().set(0.18f, 0.24f, 0.38f, 0.5f, -0.3f, 0.5f));
    }

    private void initRainStreaks() {
        Random rng = new Random(888);
        for (int i = 0; i < 200; i++) {
            ModelInstance r = new ModelInstance(meshes.get("rain_streak"));
            float rx = rng.nextFloat() * 34f - 1f;
            float ry = rng.nextFloat() * 12f + 1f;
            float rz = rng.nextFloat() * 34f - 1f;
            r.transform.setToTranslation(rx, ry, rz);
            rainStreaks.add(r);
        }
    }

    public OrbitCameraController getCameraController() {
        return cameraController;
    }

    public void resize(int w, int h) {
        camera.viewportWidth  = w;
        camera.viewportHeight = h;
        cameraController.updateCamera();
    }

    public void setWorldInit(WorldInitDto init) {
        if (init == null || init == currentInit) return;
        currentInit = init;
        buildGardenWorld(init);
        cameraController.setFocus(init.width / 2f, 0f, init.height / 2f);
    }

    public Vector3 getAgentPosition(int id) {
        if (id == 0) return alphaAvatar.currentPos;
        if (id == 1) return albedoAvatar.currentPos;
        return new Vector3(16, 0, 16);
    }

    public void updateAndRender(TickFrameDto frame) {
        float dt = Gdx.graphics.getDeltaTime();
        runTime += dt;

        boolean isRaining = (frame != null && frame.is_raining);
        Environment activeEnv = isRaining ? rainEnv : sunnyEnv;

        // Clear background
        if (isRaining) {
            Gdx.gl.glClearColor(0.32f, 0.40f, 0.50f, 1f);
        } else {
            Gdx.gl.glClearColor(0.48f, 0.72f, 0.98f, 1f);
        }
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT | GL20.GL_DEPTH_BUFFER_BIT);
        Gdx.gl.glViewport(0, 0, Gdx.graphics.getWidth(), Gdx.graphics.getHeight());

        // Update agents with network frame
        if (frame != null && frame.agents != null) {
            for (AgentStateDto a : frame.agents) {
                if (a.id == 0) alphaAvatar.updateFromDto(a);
                else if (a.id == 1) albedoAvatar.updateFromDto(a);
            }
        }

        // Animate agent skeletons
        alphaAvatar.update(dt);
        albedoAvatar.update(dt);

        // Update camera (handles keyboard WASD/Arrows movement and agent tracking)
        cameraController.update(dt, alphaAvatar.currentPos, albedoAvatar.currentPos);

        // Update dynamic plants & items
        buildDynamicEntities(frame);

        // Animate rain streaks
        if (isRaining) {
            for (ModelInstance r : rainStreaks) {
                Vector3 p = new Vector3();
                r.transform.getTranslation(p);
                p.y -= dt * 18.0f;
                if (p.y < 0.1f) p.y += 12.0f;
                r.transform.setTranslation(p);
            }
        }

        // ── 3D RENDER PASS ──────────────────────────────────────────────────
        modelBatch.begin(camera);

        // 1. Sky Dome
        if (skyDome != null) {
            skyDome.transform.setToTranslation(camera.position.x, camera.position.y - 15f, camera.position.z);
            modelBatch.render(skyDome);
        }

        // 2. Opaque Terrain (Grass, Raised Soil Beds, Trees, Fences, Props)
        modelBatch.render(terrainOpaque, activeEnv);

        // 3. Dynamic Items (Crops, fruits, seeds, buckets)
        modelBatch.render(dynamicOpaque, activeEnv);

        // 4. Alpha & Albedo Avatars
        alphaAvatar.render(modelBatch, activeEnv);
        albedoAvatar.render(modelBatch, activeEnv);

        // 5. Transparent Pass (Water Surface, Lily Pads, Rain)
        Gdx.gl.glEnable(GL20.GL_BLEND);
        Gdx.gl.glBlendFunc(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA);
        Gdx.gl.glDepthMask(false);

        modelBatch.render(terrainTransp, activeEnv);

        if (isRaining) {
            modelBatch.render(rainStreaks, activeEnv);
        }

        Gdx.gl.glDepthMask(true);

        modelBatch.end();
    }

    // ── GARDEN WORLD GENERATION ─────────────────────────────────────────────
    private void buildGardenWorld(WorldInitDto init) {
        terrainOpaque.clear();
        terrainTransp.clear();

        Random rng = new Random(1337);
        int w = init.width;
        int h = init.height;

        for (int row = 0; row < h; row++) {
            for (int col = 0; col < w; col++) {
                int tile = init.tiles.get(row).get(col);
                float x = col;
                float z = row;

                switch (tile) {
                    case 2: // Soil (Farming planter beds)
                        addInstance(terrainOpaque, "planter_border", x, 0.10f, z);
                        addInstance(terrainOpaque, "soil_tile", x, 0.12f, z);
                        break;

                    case 3: // Sunken Pond with water and river stones
                        addInstance(terrainOpaque, "water_basin", x, 0.04f, z);
                        // Translucent animated water surface
                        addInstance(terrainTransp, "water_surface", x, 0.08f, z);

                        // Occasional floating water lily pad
                        if (rng.nextFloat() < 0.25f) {
                            addInstance(terrainTransp, "lily_pad", x + rng.nextFloat() * 0.4f - 0.2f, 0.10f, z + rng.nextFloat() * 0.4f - 0.2f);
                            if (rng.nextFloat() < 0.6f) {
                                addInstance(terrainOpaque, "lily_blossom", x, 0.14f, z);
                            }
                        }
                        break;

                    case 4: // Trees in garden! (Correctly mapped to TILE_TREE=4)
                        addInstance(terrainOpaque, "grass_tile", x, 0.10f, z);
                        buildGardenTree(x, z, rng);
                        break;

                    default: // Grass tiles with nature details
                        addInstance(terrainOpaque, "grass_tile", x, 0.10f, z);

                        // Scattered 3D grass tufts
                        if (rng.nextFloat() < 0.35f) {
                            float gx = x + rng.nextFloat() * 0.6f - 0.3f;
                            float gz = z + rng.nextFloat() * 0.6f - 0.3f;
                            addInstance(terrainOpaque, "grass_tuft", gx, 0.24f, gz);
                        }

                        // Scattered Wildflowers (poppies, daisies, lavender)
                        float flowerChance = rng.nextFloat();
                        if (flowerChance < 0.15f) {
                            float fx = x + rng.nextFloat() * 0.5f - 0.25f;
                            float fz = z + rng.nextFloat() * 0.5f - 0.25f;
                            addInstance(terrainOpaque, "flower_stem", fx, 0.24f, fz);
                            if (flowerChance < 0.05f) {
                                addInstance(terrainOpaque, "flower_poppy", fx, 0.42f, fz);
                            } else if (flowerChance < 0.10f) {
                                addInstance(terrainOpaque, "flower_daisy", fx, 0.40f, fz);
                            } else {
                                addInstance(terrainOpaque, "flower_lavender", fx, 0.44f, fz);
                            }
                        }

                        // Stepping stone paths near center
                        if ((col == 15 || col == 16) && row > 10 && row < 22) {
                            addInstance(terrainOpaque, "stepping_stone", x, 0.21f, z);
                        }
                        break;
                }
            }
        }

        // Garden Sanctuary Architecture: Enclosing wooden fence
        buildPerimeterFence(w, h);

        // Garden Props: Well & Benches
        addInstance(terrainOpaque, "well_base", 14f, 0.32f, 15f);
        addInstance(terrainOpaque, "well_roof", 14f, 1.25f, 15f);

        addInstance(terrainOpaque, "bench_seat", 18.5f, 0.38f, 13f);
        addInstance(terrainOpaque, "bench_leg",  18.1f, 0.18f, 13f);
        addInstance(terrainOpaque, "bench_leg",  18.9f, 0.18f, 13f);

        // Garden Lanterns at key locations
        addLanternPost(8f, 8f);
        addLanternPost(24f, 8f);
        addLanternPost(8f, 24f);
        addLanternPost(24f, 24f);
    }

    private void buildGardenTree(float x, float z, Random rng) {
        // Multi-tier organic tree
        addInstance(terrainOpaque, "tree_trunk", x, 1.10f, z);

        // Branching foliage clusters
        addInstance(terrainOpaque, "canopy_large",  x, 2.60f, z);
        addInstance(terrainOpaque, "canopy_medium", x + 0.45f, 2.20f, z - 0.35f);
        addInstance(terrainOpaque, "canopy_medium", x - 0.40f, 2.30f, z + 0.40f);
        addInstance(terrainOpaque, "canopy_small",  x, 3.40f, z);

        // Hanging apples
        if (rng.nextFloat() < 0.75f) {
            addInstance(terrainOpaque, "apple", x + 0.50f, 1.70f, z + 0.30f);
            addInstance(terrainOpaque, "apple", x - 0.40f, 1.80f, z - 0.40f);
        }
    }

    private void buildPerimeterFence(int w, int h) {
        // Wooden fence enclosing the 32x32 garden sanctuary
        for (int c = 0; c < w; c++) {
            addInstance(terrainOpaque, "fence_post", c, 0.48f, -0.5f);
            addInstance(terrainOpaque, "fence_rail", c + 0.5f, 0.35f, -0.5f);
            addInstance(terrainOpaque, "fence_rail", c + 0.5f, 0.65f, -0.5f);

            addInstance(terrainOpaque, "fence_post", c, 0.48f, h - 0.5f);
            addInstance(terrainOpaque, "fence_rail", c + 0.5f, 0.35f, h - 0.5f);
            addInstance(terrainOpaque, "fence_rail", c + 0.5f, 0.65f, h - 0.5f);
        }
        for (int r = 0; r < h; r++) {
            addInstance(terrainOpaque, "fence_post", -0.5f, 0.48f, r);
            addInstance(terrainOpaque, "fence_rail", -0.5f, 0.35f, r + 0.5f, 0f, 90f, 0f);
            addInstance(terrainOpaque, "fence_rail", -0.5f, 0.65f, r + 0.5f, 0f, 90f, 0f);

            addInstance(terrainOpaque, "fence_post", w - 0.5f, 0.48f, r);
            addInstance(terrainOpaque, "fence_rail", w - 0.5f, 0.35f, r + 0.5f, 0f, 90f, 0f);
            addInstance(terrainOpaque, "fence_rail", w - 0.5f, 0.65f, r + 0.5f, 0f, 90f, 0f);
        }
    }

    private void addLanternPost(float x, float z) {
        addInstance(terrainOpaque, "fence_post",    x, 0.65f, z);
        addInstance(terrainOpaque, "lantern_glass", x, 1.25f, z);
    }

    // ── DYNAMIC CROPS & GROUND ITEMS ─────────────────────────────────────────
    private void buildDynamicEntities(TickFrameDto frame) {
        dynamicOpaque.clear();
        if (frame == null) return;

        // 1. Growing Garden Crops
        if (frame.plants != null) {
            for (PlantDto p : frame.plants) {
                if (p.has_fruit) {
                    String fruitKey = (p.fruit_type != null && p.fruit_type == 14) ? "fruit_poison" : "fruit_food";
                    addInstance(dynamicOpaque, fruitKey, p.x, 0.42f, p.y);
                    addInstance(dynamicOpaque, "sprout_leaf", p.x + 0.12f, 0.36f, p.y);
                    addInstance(dynamicOpaque, "sprout_leaf", p.x - 0.12f, 0.36f, p.y);
                } else {
                    // Gentle wind sway
                    float sway = (float)Math.sin(runTime * 2.0f + p.x) * 0.05f;
                    addInstance(dynamicOpaque, "sprout_stem", p.x, 0.28f, p.y, sway * 30f, 0f, 0f);
                    addInstance(dynamicOpaque, "sprout_leaf", p.x + 0.08f, 0.42f, p.y, 0f, 0f, 25f);
                    addInstance(dynamicOpaque, "sprout_leaf", p.x - 0.08f, 0.42f, p.y, 0f, 0f, -25f);
                }
            }
        }

        // 2. Ground Items (seeds, fruits, water containers)
        if (frame.ground_items != null) {
            for (GroundItemDto itm : frame.ground_items) {
                float bob = 0.25f + (float)Math.sin(runTime * 2.5f + itm.x * 0.7f) * 0.035f;
                switch (itm.entity_id) {
                    case 11, 15, 16 -> {
                        addInstance(dynamicOpaque, "bucket_casing", itm.x, bob, itm.y);
                        if (itm.entity_id == 16) { // Full with water
                            addInstance(dynamicOpaque, "bucket_water", itm.x, bob + 0.10f, itm.y);
                        }
                    }
                    case 13 -> addInstance(dynamicOpaque, "fruit_food", itm.x, bob, itm.y);
                    case 14 -> addInstance(dynamicOpaque, "fruit_poison", itm.x, bob, itm.y);
                    default -> addInstance(dynamicOpaque, "seed", itm.x, bob, itm.y);
                }
            }
        }
    }

    private void addInstance(List<ModelInstance> list, String key, float x, float y, float z) {
        addInstance(list, key, x, y, z, 0f, 0f, 0f);
    }

    private void addInstance(List<ModelInstance> list, String key, float x, float y, float z,
                             float rotX, float rotY, float rotZ) {
        if (!meshes.has(key)) return;
        ModelInstance inst = new ModelInstance(meshes.get(key));
        inst.transform.idt().translate(x, y, z);
        if (rotY != 0f) inst.transform.rotate(Vector3.Y, rotY);
        if (rotX != 0f) inst.transform.rotate(Vector3.X, rotX);
        if (rotZ != 0f) inst.transform.rotate(Vector3.Z, rotZ);
        list.add(inst);
    }

    @Override
    public void dispose() {
        modelBatch.dispose();
        meshes.dispose();
        palette.dispose();
    }
}
