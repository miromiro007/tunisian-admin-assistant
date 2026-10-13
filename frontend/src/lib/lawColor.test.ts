import { describe, expect, it } from "vitest";
import { lawHue } from "./lawColor";

function hueDistance(a: number, b: number): number {
  const d = Math.abs(a - b) % 360;
  return Math.min(d, 360 - d);
}

describe("lawHue", () => {
  it("is deterministic for the same title", () => {
    expect(lawHue("LOI N°60-30")).toBe(lawHue("LOI N°60-30"));
  });

  it("ignores case and surrounding whitespace", () => {
    expect(lawHue("  loi n°60-30 ")).toBe(lawHue("LOI N°60-30"));
  });

  it("gives visibly different hues to different laws", () => {
    const a = lawHue("LOI N°60-30");
    const b = lawHue("ANNEXES A LA LOI N°60-33");
    expect(hueDistance(a, b)).toBeGreaterThanOrEqual(30);
  });

  it("always returns a hue in [0, 360)", () => {
    for (const title of ["", "Code du travail", "مجلة الشغل", "LOI N°60-33"]) {
      const hue = lawHue(title);
      expect(hue).toBeGreaterThanOrEqual(0);
      expect(hue).toBeLessThan(360);
    }
  });
});
