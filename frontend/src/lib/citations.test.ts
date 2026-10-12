import { describe, expect, it } from "vitest";
import { buildValidCitationNumbers, parseCitationMarkers } from "./citations";

describe("parseCitationMarkers", () => {
  it("turns a valid [n] into a chip-eligible citation segment", () => {
    const segments = parseCitationMarkers("Le délai est de 30 jours [1].", new Set([1]));
    expect(segments).toEqual([
      { kind: "text", value: "Le délai est de 30 jours " },
      { kind: "citation", number: 1, valid: true },
      { kind: "text", value: "." },
    ]);
  });

  it("renders a number in invalid_citations as plain text (valid: false)", () => {
    // validNumbers excludes 2 because it was in invalid_citations.
    const segments = parseCitationMarkers("Selon [2] la loi.", new Set([1]));
    expect(segments).toEqual([
      { kind: "text", value: "Selon " },
      { kind: "citation", number: 2, valid: false },
      { kind: "text", value: " la loi." },
    ]);
  });

  it("renders a number with no matching source at all as plain text too", () => {
    // Only source 1 exists; [9] was never a real source and isn't in invalid_citations either.
    const segments = parseCitationMarkers("Voir [9].", new Set([1]));
    const citation = segments.find((s) => s.kind === "citation");
    expect(citation).toEqual({ kind: "citation", number: 9, valid: false });
  });

  it("treats adjacent markers [2][3] as two independent segments", () => {
    const segments = parseCitationMarkers("Les articles [2][3] s'appliquent.", new Set([2, 3]));
    expect(segments).toEqual([
      { kind: "text", value: "Les articles " },
      { kind: "citation", number: 2, valid: true },
      { kind: "citation", number: 3, valid: true },
      { kind: "text", value: " s'appliquent." },
    ]);
  });

  it("handles an answer with no markers at all", () => {
    expect(parseCitationMarkers("Aucune citation ici.", new Set())).toEqual([
      { kind: "text", value: "Aucune citation ici." },
    ]);
  });

  it("handles mixed Arabic text with a marker", () => {
    const segments = parseCitationMarkers("هذا النص [1] واضح.", new Set([1]));
    expect(segments).toEqual([
      { kind: "text", value: "هذا النص " },
      { kind: "citation", number: 1, valid: true },
      { kind: "text", value: " واضح." },
    ]);
  });
});

describe("buildValidCitationNumbers", () => {
  it("excludes numbers listed in invalid_citations", () => {
    expect(buildValidCitationNumbers([1, 2, 3], [2])).toEqual(new Set([1, 3]));
  });

  it("returns all source numbers when nothing is invalid", () => {
    expect(buildValidCitationNumbers([1, 2], [])).toEqual(new Set([1, 2]));
  });
});
