const HUE_STEPS = 12;

/** FNV-1a 32-bit: small, stable string hash (same input -> same output, everywhere). */
function hashString(value: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

/**
 * Deterministic badge hue for a law title. Hues are snapped to 12 steps 30° apart
 * so two different laws land on visibly different colors rather than near-identical ones.
 */
export function lawHue(title: string): number {
  return (hashString(title.trim().toUpperCase()) % HUE_STEPS) * (360 / HUE_STEPS);
}
