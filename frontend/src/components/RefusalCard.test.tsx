import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RefusalCard } from "./RefusalCard";
import { LangContext, t } from "../i18n";
import type { RefusalReason } from "../types";

function renderInEnglish(reason: RefusalReason) {
  return render(
    <LangContext value={{ lang: "en", setLang: () => {}, t: (key, vars) => t(key, "en", vars) }}>
      <RefusalCard reason={reason} />
    </LangContext>,
  );
}

afterEach(cleanup);

describe("RefusalCard", () => {
  it.each<RefusalReason>(["no_sources", "below_threshold"])(
    "shows 'No answer found in the documents' for %s",
    (reason) => {
      renderInEnglish(reason);
      expect(screen.getByText("No answer found in the documents")).toBeTruthy();
    },
  );

  it.each<RefusalReason>(["model_declined", "empty_answer"])("shows 'The model could not answer' for %s", (reason) => {
    renderInEnglish(reason);
    expect(screen.getByText("The model could not answer")).toBeTruthy();
    expect(screen.queryByText("No answer found in the documents")).toBeNull();
  });

  it("never displays the raw NO_ANSWER marker", () => {
    const { container } = renderInEnglish("model_declined");
    expect(container.textContent).not.toContain("NO_ANSWER");
  });
});
