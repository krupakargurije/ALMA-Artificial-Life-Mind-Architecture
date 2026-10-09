package alc.viewer.render;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.utils.Disposable;

import java.util.HashMap;
import java.util.Map;
import java.util.Random;

/**
 * TexturePalette generates rich, organic procedural textures using Pixmaps.
 * Zero external asset dependencies — loads instantly and provides realistic
 * surface detail for terrain, garden props, and humanoid agents.
 */
public class TexturePalette implements Disposable {

    private final Map<String, Texture> textures = new HashMap<>();

    public TexturePalette() {
        generateAll();
    }

    private void generateAll() {
        textures.put("grass",        generateGrassTexture());
        textures.put("soil",         generateSoilTexture());
        textures.put("water",        generateWaterTexture());
        textures.put("cobble",       generateCobblestoneTexture());
        textures.put("wood",         generateWoodPlankTexture());
        textures.put("bark",         generateTreeBarkTexture());
        textures.put("leaves",       generateLeafCanopyTexture());
        textures.put("skin",         generateSkinTexture());
        textures.put("alpha_face",   generateFaceTexture(true));
        textures.put("roselia_face", generateFaceTexture(false));
        textures.put("alpha_cloth",  generateClothTexture(new Color(0.88f, 0.28f, 0.22f, 1f), new Color(0.96f, 0.78f, 0.24f, 1f)));
        textures.put("roselia_cloth",generateClothTexture(new Color(0.12f, 0.65f, 0.60f, 1f), new Color(0.75f, 0.88f, 0.95f, 1f)));
        textures.put("shoe",         generateLeatherTexture());
        textures.put("stone",        generateStoneTexture());
        textures.put("lilypad",      generateLilyPadTexture());
        textures.put("lantern",      generateLanternTexture());
    }

    // ── GRASS: Lush garden turf with blades and clover specks ────────────────
    private Texture generateGrassTexture() {
        int w = 128, h = 128;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        Random rng = new Random(101);

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                float noise = (float)Math.sin(x * 0.12f) * (float)Math.cos(y * 0.12f) * 0.08f;
                float r = 0.20f + noise + (rng.nextFloat() - 0.5f) * 0.04f;
                float g = 0.54f + noise * 1.5f + (rng.nextFloat() - 0.5f) * 0.06f;
                float b = 0.16f + noise * 0.5f + (rng.nextFloat() - 0.5f) * 0.03f;
                p.setColor(clamp(r), clamp(g), clamp(b), 1f);
                p.drawPixel(x, y);
            }
        }
        // Draw fine grass blades
        for (int i = 0; i < 400; i++) {
            int gx = rng.nextInt(w);
            int gy = rng.nextInt(h);
            int len = 3 + rng.nextInt(6);
            float bright = 0.58f + rng.nextFloat() * 0.22f;
            p.setColor(0.18f, bright, 0.14f, 0.85f);
            p.drawLine(gx, gy, gx + rng.nextInt(3) - 1, Math.max(0, gy - len));
        }
        // Tiny clover patches
        for (int i = 0; i < 25; i++) {
            int cx = rng.nextInt(w - 6) + 3;
            int cy = rng.nextInt(h - 6) + 3;
            p.setColor(0.25f, 0.68f, 0.20f, 0.9f);
            p.fillCircle(cx - 2, cy, 2);
            p.fillCircle(cx + 2, cy, 2);
            p.fillCircle(cx, cy - 2, 2);
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── SOIL: Rich dark garden loam with tilled furrows ─────────────────────
    private Texture generateSoilTexture() {
        int w = 128, h = 128;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        Random rng = new Random(202);

        for (int y = 0; y < h; y++) {
            // Horizontal furrow wave
            float furrow = (float)Math.sin(y * 0.35f) * 0.12f;
            for (int x = 0; x < w; x++) {
                float n = (rng.nextFloat() - 0.5f) * 0.07f;
                float r = 0.28f + furrow * 0.6f + n;
                float g = 0.17f + furrow * 0.4f + n * 0.6f;
                float b = 0.09f + furrow * 0.2f + n * 0.4f;
                p.setColor(clamp(r), clamp(g), clamp(b), 1f);
                p.drawPixel(x, y);
            }
        }
        // Organic soil flecks & small pebbles
        for (int i = 0; i < 180; i++) {
            int px = rng.nextInt(w);
            int py = rng.nextInt(h);
            float tone = 0.38f + rng.nextFloat() * 0.16f;
            p.setColor(tone, tone * 0.7f, tone * 0.45f, 0.8f);
            p.fillCircle(px, py, 1 + rng.nextInt(2));
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── WATER: Semi-transparent cyan-blue caustic surface ───────────────────
    private Texture generateWaterTexture() {
        int w = 128, h = 128;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                float c1 = (float)Math.sin(x * 0.15f + y * 0.10f);
                float c2 = (float)Math.cos(x * 0.10f - y * 0.15f);
                float caustic = (c1 * c2 + 1f) * 0.5f;

                float r = 0.10f + caustic * 0.15f;
                float g = 0.48f + caustic * 0.25f;
                float b = 0.80f + caustic * 0.18f;
                float a = 0.72f + caustic * 0.15f;
                p.setColor(clamp(r), clamp(g), clamp(b), clamp(a));
                p.drawPixel(x, y);
            }
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── COBBLESTONE: Natural stone path pavers with mortar grooves ──────────
    private Texture generateCobblestoneTexture() {
        int w = 128, h = 128;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        p.setColor(0.24f, 0.22f, 0.20f, 1f); // Mortar dark base
        p.fill();

        Random rng = new Random(303);
        int cols = 6, rows = 6;
        int stepX = w / cols, stepY = h / rows;

        for (int r = 0; r < rows; r++) {
            int offsetX = (r % 2 == 1) ? stepX / 2 : 0;
            for (int c = -1; c <= cols; c++) {
                int cx = c * stepX + offsetX + 2;
                int cy = r * stepY + 2;
                int sw = stepX - 4 + rng.nextInt(3) - 1;
                int sh = stepY - 4 + rng.nextInt(3) - 1;

                float stoneTone = 0.50f + (rng.nextFloat() - 0.5f) * 0.18f;
                Color stoneCol = new Color(stoneTone, stoneTone * 0.96f, stoneTone * 0.90f, 1f);

                for (int py = cy; py < cy + sh && py < h; py++) {
                    for (int px = cx; px < cx + sw && px < w; px++) {
                        if (px < 0 || py < 0) continue;
                        float edgeDist = Math.min(Math.min(px - cx, cx + sw - px), Math.min(py - cy, cy + sh - py));
                        float bevel = Math.min(1f, edgeDist / 3f);
                        float grain = (rng.nextFloat() - 0.5f) * 0.05f;
                        float finalTone = (stoneTone + grain) * (0.75f + bevel * 0.25f);
                        p.setColor(finalTone, finalTone * 0.95f, finalTone * 0.88f, 1f);
                        p.drawPixel(px, py);
                    }
                }
            }
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── WOOD PLANKS: Cedar timber for fences and planter borders ────────────
    private Texture generateWoodPlankTexture() {
        int w = 128, h = 128;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        Random rng = new Random(404);

        int plankHeight = 32;
        for (int y = 0; y < h; y++) {
            int plankIdx = y / plankHeight;
            boolean isPlankBorder = (y % plankHeight <= 1);
            float plankToneMod = ((plankIdx % 2 == 0) ? 1.0f : 0.92f);

            for (int x = 0; x < w; x++) {
                if (isPlankBorder) {
                    p.setColor(0.18f, 0.10f, 0.05f, 1f);
                } else {
                    float grain = (float)Math.sin(y * 0.8f + x * 0.05f) * 0.05f + (rng.nextFloat() - 0.5f) * 0.04f;
                    float r = (0.50f + grain) * plankToneMod;
                    float g = (0.30f + grain * 0.6f) * plankToneMod;
                    float b = (0.14f + grain * 0.3f) * plankToneMod;
                    p.setColor(clamp(r), clamp(g), clamp(b), 1f);
                }
                p.drawPixel(x, y);
            }
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── TREE BARK: Organic furrowed oak bark ────────────────────────────────
    private Texture generateTreeBarkTexture() {
        int w = 64, h = 128;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        Random rng = new Random(505);

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                float verticalGrain = (float)Math.sin(x * 0.45f + (float)Math.sin(y * 0.1f) * 2f) * 0.14f;
                float noise = (rng.nextFloat() - 0.5f) * 0.06f;
                float r = 0.34f + verticalGrain + noise;
                float g = 0.22f + verticalGrain * 0.7f + noise * 0.6f;
                float b = 0.12f + verticalGrain * 0.4f + noise * 0.3f;
                p.setColor(clamp(r), clamp(g), clamp(b), 1f);
                p.drawPixel(x, y);
            }
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── LEAF CANOPY: Multi-tone leafy cluster texture ───────────────────────
    private Texture generateLeafCanopyTexture() {
        int w = 128, h = 128;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        Random rng = new Random(606);

        p.setColor(0.12f, 0.44f, 0.14f, 1f);
        p.fill();

        for (int i = 0; i < 450; i++) {
            int cx = rng.nextInt(w);
            int cy = rng.nextInt(h);
            int rad = 3 + rng.nextInt(5);
            float bright = 0.35f + rng.nextFloat() * 0.45f;
            p.setColor(bright * 0.4f, bright, bright * 0.25f, 0.85f);
            p.fillCircle(cx, cy, rad);
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── SKIN: Soft peach porcelain skin ─────────────────────────────────────
    private Texture generateSkinTexture() {
        int w = 64, h = 64;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                float grad = 1.0f - (y / (float)h) * 0.08f;
                p.setColor(0.98f * grad, 0.84f * grad, 0.76f * grad, 1f);
                p.drawPixel(x, y);
            }
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── FACE: Expressive anime-styled face with eyes, brows, blush, smile ──
    private Texture generateFaceTexture(boolean isAlpha) {
        int w = 128, h = 128;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);

        // Skin base
        p.setColor(0.98f, 0.84f, 0.76f, 1f);
        p.fill();

        // Rosy cheek blush
        p.setColor(0.96f, 0.58f, 0.58f, 0.45f);
        p.fillCircle(30, 78, 12);
        p.fillCircle(98, 78, 12);

        // Eyes: White sclera
        p.setColor(0.96f, 0.96f, 0.98f, 1f);
        p.fillCircle(36, 56, 14);
        p.fillCircle(92, 56, 14);

        // Iris
        Color iris = isAlpha ? new Color(0.85f, 0.45f, 0.12f, 1f) : new Color(0.20f, 0.55f, 0.82f, 1f);
        Color irisDark = isAlpha ? new Color(0.48f, 0.22f, 0.05f, 1f) : new Color(0.08f, 0.25f, 0.52f, 1f);
        p.setColor(irisDark);
        p.fillCircle(36, 56, 10);
        p.fillCircle(92, 56, 10);
        p.setColor(iris);
        p.fillCircle(36, 57, 8);
        p.fillCircle(92, 57, 8);

        // Pupil
        p.setColor(0.12f, 0.10f, 0.12f, 1f);
        p.fillCircle(36, 57, 4);
        p.fillCircle(92, 57, 4);

        // Eye highlights (sparkle)
        p.setColor(1f, 1f, 1f, 0.95f);
        p.fillCircle(34, 53, 3);
        p.fillCircle(90, 53, 3);
        p.fillCircle(38, 60, 2);
        p.fillCircle(94, 60, 2);

        // Eyelashes & Upper lid
        p.setColor(0.22f, 0.14f, 0.12f, 1f);
        for (int t = 0; t < 2; t++) {
            p.drawLine(22, 45 + t, 50, 45 + t);
            p.drawLine(78, 45 + t, 106, 45 + t);
        }

        // Eyebrows
        Color browColor = isAlpha ? new Color(0.72f, 0.42f, 0.15f, 1f) : new Color(0.42f, 0.15f, 0.60f, 1f);
        p.setColor(browColor);
        for (int t = 0; t < 2; t++) {
            p.drawLine(24, 38 + t, 48, 36 + t);
            p.drawLine(80, 36 + t, 104, 38 + t);
        }

        // Cute smiling mouth
        p.setColor(0.85f, 0.32f, 0.32f, 0.9f);
        p.drawLine(56, 92, 72, 92);
        p.drawLine(58, 93, 70, 93);
        p.drawLine(60, 94, 68, 94);

        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── CLOTH: Woven textile pattern with metallic trim ─────────────────────
    private Texture generateClothTexture(Color base, Color trim) {
        int w = 128, h = 128;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                // Weave pattern
                boolean weave = ((x / 2 + y / 2) % 2 == 0);
                float mod = weave ? 1.05f : 0.95f;
                p.setColor(clamp(base.r * mod), clamp(base.g * mod), clamp(base.b * mod), 1f);
                p.drawPixel(x, y);
            }
        }
        // Gold/Silver hem trim at top and bottom
        p.setColor(trim);
        p.fillRectangle(0, 0, w, 6);
        p.fillRectangle(0, h - 8, w, 8);

        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── LEATHER SHOES ───────────────────────────────────────────────────────
    private Texture generateLeatherTexture() {
        int w = 64, h = 64;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        p.setColor(0.20f, 0.14f, 0.10f, 1f);
        p.fill();
        // Sole rim
        p.setColor(0.10f, 0.07f, 0.05f, 1f);
        p.fillRectangle(0, h - 10, w, 10);
        // Stitch line
        p.setColor(0.48f, 0.36f, 0.22f, 1f);
        p.drawLine(0, h - 11, w, h - 11);

        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── STONE MASONRY ───────────────────────────────────────────────────────
    private Texture generateStoneTexture() {
        int w = 64, h = 64;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        Random rng = new Random(707);
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                float n = 0.55f + (rng.nextFloat() - 0.5f) * 0.12f;
                p.setColor(n, n * 0.98f, n * 0.95f, 1f);
                p.drawPixel(x, y);
            }
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── LILY PAD: Floating round green water plant with notch ────────────────
    private Texture generateLilyPadTexture() {
        int w = 64, h = 64;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        p.setColor(0, 0, 0, 0);
        p.fill();

        int cx = 32, cy = 32, rad = 28;
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int dx = x - cx;
                int dy = y - cy;
                if (dx * dx + dy * dy <= rad * rad) {
                    // Pie notch
                    double angle = Math.atan2(dy, dx);
                    if (angle > -0.25 && angle < 0.25) continue;
                    float dist = (float)Math.sqrt(dx * dx + dy * dy) / rad;
                    float g = 0.60f - dist * 0.20f;
                    p.setColor(0.18f, g, 0.14f, 0.95f);
                    p.drawPixel(x, y);
                }
            }
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    // ── LANTERN GLOW ────────────────────────────────────────────────────────
    private Texture generateLanternTexture() {
        int w = 64, h = 64;
        Pixmap p = new Pixmap(w, h, Pixmap.Format.RGBA8888);
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int dx = x - 32, dy = y - 32;
                float dist = (float)Math.sqrt(dx * dx + dy * dy) / 32f;
                float glow = Math.max(0, 1f - dist);
                p.setColor(1.0f, 0.85f, 0.35f, 0.6f + glow * 0.4f);
                p.drawPixel(x, y);
            }
        }
        Texture tex = new Texture(p);
        p.dispose();
        return tex;
    }

    private float clamp(float v) {
        return Math.max(0f, Math.min(1f, v));
    }

    public Texture get(String key) {
        return textures.get(key);
    }

    @Override
    public void dispose() {
        textures.values().forEach(Texture::dispose);
        textures.clear();
    }
}
